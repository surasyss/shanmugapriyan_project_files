import os
from collections import defaultdict

from datetime import date
from typing import Optional, List

from selenium.webdriver.common.by import By
from selenium.common.exceptions import ElementNotInteractableException
from selenium.webdriver.support import expected_conditions as EC

from apps.adapters.framework import download
from apps.adapters.framework.registry import connectors
from apps.adapters.framework.operations.vendor import BaseVendorConnector

from apps.adapters.framework.steps.web import (
    NavigateToUrl,
    SubmitLoginPassword,
    ExplicitWait,
)
from apps.adapters.helpers.webdriver_helper import (
    wait_for_element,
    get_url,
    wait_for_loaders,
    WEB_DRIVER_EXCEPTIONS,
    handle_popup,
)
from apps.runs.models import FileFormat
from spices.datetime_utils import date_from_string

from integrator import LOGGER

_LOGIN_URL = "https://www.bekentree.com/"
_INVOICE_PAGE_URL = "https://www.bekentree.com/invoice/list"


@connectors.add("benekeith")
class EntreeSystem(BaseVendorConnector):
    vendor_name = "Entree System"
    invoice_file_format = FileFormat.PDF.ident  # pylint: disable=no-member
    df_download_url_skip_duplicates = True
    restaurant_name = None

    class Selectors:
        LOGIN__USERNAME_TEXTBOX = (By.CSS_SELECTOR, 'input[id="signInName"]')
        LOGIN__PASSWORD_TEXTBOX = (By.CSS_SELECTOR, 'input[id="password"]')
        LOGIN__LOGIN_BUTTON = (By.CSS_SELECTOR, 'button[id="next"]')
        LOGIN__ERROR_MESSAGE_TEXT = (
            By.CSS_SELECTOR,
            "form#localAccountForm div.error",
        )

        DATE_COLUMN_HEADER = (
            By.CSS_SELECTOR,
            "th.invoices-table__dt-col--invoicedate",
        )
        LOADER = "div[class='loader app-js__loader']"
        DROPDOWN_BUTTON = (
            By.CSS_SELECTOR,
            "div.invoices-detail__filter button.dropdown__btn",
        )
        ACCOUNTS_BUTTON_LIST = (
            By.CSS_SELECTOR,
            "div.invoices-detail__filter div.dropdown-menu div.list-group button",
        )
        FILTER_BY_TYPE = (
            By.CSS_SELECTOR,
            "div.invoices-table__dropdown button.dropdown__btn",
        )
        INVOICE_TYPES_LIST = (
            By.CSS_SELECTOR,
            "div.invoices-table__dropdown div.dropdown-menu div.list-group button",
        )
        EMPTY_TABLE = (
            By.CSS_SELECTOR,
            "table.invoices-table__table tbody tr td.dataTables_empty",
        )
        TABLE_ROWS = (
            By.CSS_SELECTOR,
            "table.invoices-table__table tbody tr",
        )
        INVOICE_DATE = (
            By.CSS_SELECTOR,
            "td.invoices-table__dt-col--invoicedate",
        )
        INVOICE_NUMBER = (
            By.CSS_SELECTOR,
            "td.invoices-table__dt-col--invoice",
        )
        TOTAL_AMOUNT = (
            By.CSS_SELECTOR,
            "td.invoices-table__dt-col--invoiceamount",
        )
        ORIGINAL_DOWNLOAD_URL = (
            By.CSS_SELECTOR,
            "td.invoices-table__dt-col--invoice a",
        )
        POPUP_CLOSE = "div.walkme-to-remove button svg.wm-ignore-css-reset"

    # login
    _navigate_to_login_page = NavigateToUrl(_LOGIN_URL, retry_attempts=5)
    _submit_login_info__pre = ExplicitWait(
        until=EC.visibility_of_element_located(
            locator=Selectors.LOGIN__USERNAME_TEXTBOX
        )
    )
    _submit_login_info = SubmitLoginPassword(
        username_textbox=Selectors.LOGIN__USERNAME_TEXTBOX,
        password_textbox=Selectors.LOGIN__PASSWORD_TEXTBOX,
        login_button=Selectors.LOGIN__LOGIN_BUTTON,
        error_message=Selectors.LOGIN__ERROR_MESSAGE_TEXT,
    )

    def sort_invoices_by_descending(self):
        self.driver.find_element(*self.Selectors.DATE_COLUMN_HEADER).click()
        wait_for_loaders(
            self.driver, value=self.Selectors.LOADER, retry_attempts=1, timeout=10
        )
        self.driver.find_element(*self.Selectors.DATE_COLUMN_HEADER).click()

    def get_account_elements(self, index=None):
        accounts_dropdown_button = self.driver.find_element(
            *self.Selectors.DROPDOWN_BUTTON
        )
        accounts_dropdown_button.click()
        account_elements = self.driver.find_elements(
            *self.Selectors.ACCOUNTS_BUTTON_LIST
        )[1:]
        if index is not None:
            return account_elements[index]
        return account_elements

    def get_invoice_types(self, index=None):
        filter_by = self.driver.find_element(*self.Selectors.FILTER_BY_TYPE)
        filter_by.click()
        invoice_types = self.driver.find_elements(*self.Selectors.INVOICE_TYPES_LIST)
        if index is not None:
            return invoice_types[index]
        return invoice_types

    def _handle_popup(self, msg):
        handle_popup(
            self.driver, value=self.Selectors.POPUP_CLOSE, msg=msg, retry_attempts=1
        )

    def _iter_customer_number_selections(self, customer_numbers: Optional[List[str]]):

        self._handle_popup("Set up your profile")

        get_url(self.driver, "https://www.bekentree.com/invoice/list")
        wait_for_loaders(self.driver, value=self.Selectors.LOADER, timeout=10)

        self._handle_popup("Maintenance Announcement")

        accounts = [account.text for account in self.get_account_elements()]
        LOGGER.info(f"Total accounts found: {len(accounts)}")

        for index, account in enumerate(accounts):
            if index > 0:
                get_url(self.driver, "https://www.bekentree.com/invoice/list")

            self.retry_finding_element(index, self.get_account_elements)

            wait_for_loaders(
                self.driver, value=self.Selectors.LOADER, retry_attempts=1, timeout=10
            )
            customer_number, restaurant_name = account.split("-")
            setattr(self, "restaurant_name", restaurant_name)
            yield customer_number, None

    def retry_finding_element(self, index, dropdown_func):
        for _ in range(5):
            try:
                dropdown_element = dropdown_func(index)
                dropdown_text = dropdown_element.text
                dropdown_element.click()
                LOGGER.info(f"Selected '{dropdown_text}' from the dropdown list.")

                wait_for_loaders(self.driver, value="div.loader__container", timeout=10)
                break
            except (ElementNotInteractableException, *WEB_DRIVER_EXCEPTIONS) as excep:
                LOGGER.info(f"{excep} Retrying clicking dropdown element...")

    def get_invoices_data(self, start_date: date, end_date: date):
        invoice_rows_data = defaultdict(dict)
        invoice_types = self.get_invoice_types()
        for index, _ in enumerate(invoice_types):
            self.retry_finding_element(index, self.get_invoice_types)

            wait_for_loaders(
                self.driver, value=self.Selectors.LOADER, retry_attempts=1, timeout=10
            )
            self.sort_invoices_by_descending()

            if self.driver.find_elements(*self.Selectors.EMPTY_TABLE):
                LOGGER.info("No invoices found.")
                continue

            table_rows = self.driver.find_elements(*self.Selectors.TABLE_ROWS)[1:]
            LOGGER.info(f"Total invoice rows found: {len(table_rows)}")

            for invoice_row_element in table_rows:
                invoice_date = invoice_row_element.find_element(
                    *self.Selectors.INVOICE_DATE
                ).text
                invoice_date = date_from_string(invoice_date.split(", ")[1], "%m-%d-%y")

                if not start_date <= invoice_date <= end_date:
                    LOGGER.info(
                        f"Skipping invoice because date '{invoice_date}' is outside requested range"
                    )
                    break

                invoice_number = invoice_row_element.find_element(
                    *self.Selectors.INVOICE_NUMBER
                ).text

                if invoice_number in invoice_rows_data:
                    LOGGER.info(
                        f"Skipping invoice because '{invoice_number}' was already seen in this run."
                    )
                    continue

                row_data_dict = invoice_rows_data[invoice_number]
                row_data_dict["invoice_number"] = invoice_number
                row_data_dict["invoice_date"] = invoice_date
                row_data_dict["total_amount"] = invoice_row_element.find_element(
                    *self.Selectors.TOTAL_AMOUNT
                ).text
                row_data_dict[
                    "original_download_url"
                ] = invoice_row_element.find_element(
                    *self.Selectors.ORIGINAL_DOWNLOAD_URL
                ).get_attribute(
                    "href"
                )
                LOGGER.info(f"Invoice row data: {row_data_dict}")
        return invoice_rows_data

    def _iter_invoice_row_elements(self, start_date: date, end_date: date):
        invoices_data = self.get_invoices_data(start_date, end_date)
        for invoice_number, invoice_data in invoices_data.items():
            yield invoice_data

    def _construct_downloader(
        self, invoice_row_element, **invoice_fields
    ) -> download.BaseDownloader:
        get_url(self.driver, invoice_fields["original_download_url"])
        LOGGER.info("Navigating to invoice detail page...")
        wait_for_element(
            self.driver,
            value=self.Selectors.TABLE_ROWS[1],
            msg="Line Items table",
            retry_attempts=1,
        )

        return download.WebElementClickBasedDownloader(
            element=self.driver.find_element(
                By.CSS_SELECTOR, "button.js-invoices-format-btn-print"
            ),
            local_filepath=os.path.join(
                self.download_location,
                f"Invoice# {invoice_fields['invoice_number']}.pdf",
            ),
            rename_to=os.path.join(
                self.download_location, invoice_fields["original_filename"]
            ),
            file_exists_check_kwargs=dict(timeout=40),
        )

    def _extract_invoice_date(self, invoice_row_element) -> date:
        return invoice_row_element["invoice_date"]

    def _extract_customer_number(
        self, invoice_row_element, customer_number, customer_number_element
    ) -> str:
        if customer_number:
            return customer_number
        return None

    def _extract_invoice_number(self, invoice_row_element, **invoice_fields) -> str:
        return invoice_row_element["invoice_number"]

    def _extract_total_amount(self, invoice_row_element, **invoice_fields) -> str:
        return invoice_row_element["total_amount"]

    def _extract_vendor_name(self, invoice_row_element, **invoice_fields) -> str:
        return "Entree System"

    def _extract_restaurant_name(self, invoice_row_element, **invoice_fields) -> str:
        return getattr(self, "restaurant_name", None)

    def _extract_reference_code(self, invoice_row_element, **invoice_fields) -> str:
        return f'{invoice_fields["customer_number"]}_{invoice_fields["invoice_number"]}'

    def _extract_original_download_url(
        self, invoice_row_element, **invoice_fields
    ) -> str:
        return invoice_row_element["original_download_url"]

    def _extract_original_filename(self, invoice_row_element, **invoice_fields) -> str:
        return f'{invoice_fields["reference_code"]}.pdf'
