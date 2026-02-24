import os
from datetime import date
from typing import List, Optional

from django.db.models import Q
from retry import retry
from selenium.common.exceptions import WebDriverException
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.select import Select

from integrator import LOGGER
from apps.adapters.framework.registry import connectors
from apps.adapters.framework.operations.vendor import BaseVendorConnector
from apps.adapters.framework.steps.web import (
    NavigateToUrl,
    ExplicitWait,
    SubmitLoginPassword,
)
from apps.adapters.helpers.webdriver_helper import (
    get_url,
    wait_for_element,
    wait_for_loaders,
    has_invoices,
    handle_popup,
    select_dropdown_option_by_value,
)
from apps.adapters.framework import download
from apps.runs.models import FileFormat, DiscoveredFile
from spices.datetime_utils import date_from_string

_LOGIN_URL = "https://account.cintas.com/online/login"
_LOGOUT_URL = "https://account.cintas.com/online/logout"
_INVOICE_SUMMARY_URL = "https://account.cintas.com/online/invoice-summary"


@connectors.add("cintas_new")
class CintasNewConnector(BaseVendorConnector):
    vendor_name = "Cintas"
    invoice_file_format = FileFormat.PDF.ident  # pylint: disable=no-member
    df_download_url_skip_duplicates = True

    class Selectors:
        LOGIN__USERNAME_TEXTBOX = (By.CSS_SELECTOR, "input[id='j_username']")
        LOGIN__PASSWORD_TEXTBOX = (By.CSS_SELECTOR, "input[id='j_password']")
        LOGIN__LOGIN_BUTTON = (By.CSS_SELECTOR, "button.js-btn-login")
        LOGIN__ERROR_MESSAGE_TEXT = (By.CSS_SELECTOR, "div.alert")

        HOME__BILLING = (By.CSS_SELECTOR, "div.js-dropdown-billing")
        ACCOUNT_DETAILS = (By.CSS_SELECTOR, "div#company-id")
        SELECT_ACCOUNT_BUTTON = (By.CSS_SELECTOR, "button.js-btn-select-payer")
        SELECT_STATUS_DROPDOWN = (By.CSS_SELECTOR, "select#selectStatus")
        DATE_COL_HEADER = (By.CSS_SELECTOR, "div#issueDate")
        BILLING_HISTORY__TABLE_ROWS = (By.CSS_SELECTOR, "li.invoice-summary-list-item")
        BILLING_HISTORY__INVOICE_NUMBER = (
            By.CSS_SELECTOR,
            "div.col-invoice div.col-invoice-details div",
        )
        BILLING_HISTORY__INVOICE_DATE = (By.CSS_SELECTOR, "div.col-issue-date")
        BILLING_HISTORY__TOTAL_AMOUNT = (By.CSS_SELECTOR, "div[class^='col-balance']")
        BILLING_HISTORY__INVOICE_PDF = (
            By.CSS_SELECTOR,
            "div.col-invoice div.col-invoice-details div.invoice-download-pdf a",
        )
        NO_TABLE_ROWS = (
            By.CSS_SELECTOR,
            "div.invoice-summary-list div.default-wrapper",
        )
        INVOICE_TABLE = "div.invoice-summary-list"
        PAYMENT_DUE_POPUP = "div#invoiceDuePaymentModal.modal.fade.in button.close"

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

    _submit_login_info__post = ExplicitWait(
        until=EC.visibility_of_element_located(locator=Selectors.HOME__BILLING)
    )

    def get_accounts_data_list(self):
        accounts_data_list = []
        count = 1
        while count:
            accounts_page_url = (
                f"https://account.cintas.com/online/payerlist?filterDistributionChannel=&"
                f"payerAccountNum=&payerAccountName=&address=&city=&state=&zipCode=&isSearch=false&"
                f"currentPage={count}"
            )
            get_url(self.driver, url=accounts_page_url)
            if not has_invoices(
                self.driver,
                value=self.Selectors.ACCOUNT_DETAILS[1],
                retry_attempts=3,
                msg="Accounts Table",
            ):
                LOGGER.info(f"No more accounts available")
                break

            account_data_elements = self.driver.find_elements(
                *self.Selectors.ACCOUNT_DETAILS
            )
            accounts = [
                elem.text.strip().rsplit(maxsplit=1) for elem in account_data_elements
            ]
            LOGGER.info(f"Found accounts: {accounts}")
            accounts_data_list.extend(accounts)
            count += 1
        return accounts_data_list

    @retry(WebDriverException, tries=3, delay=2)
    def get_account_page(self, customer_number):
        account_search_url = (
            f"https://account.cintas.com/online/payerlist?filterDistributionChannel=&"
            f"payerAccountNum={customer_number}&payerAccountName=&address=&city=&state=&"
            f"zipCode=&isSearch=true&currentPage=1"
        )
        get_url(self.driver, account_search_url)
        wait_for_element(
            self.driver,
            value=self.Selectors.SELECT_ACCOUNT_BUTTON[1],
            msg="Account search results",
            retry_attempts=1,
        )
        self.driver.find_element(*self.Selectors.SELECT_ACCOUNT_BUTTON).click()
        LOGGER.info(
            f"Found account {customer_number} and navigating to invoice summary page..."
        )

    def _iter_customer_number_selections(self, customer_numbers: Optional[List[str]]):
        accounts_data_list = self.get_accounts_data_list()
        for index, (restaurant_name, customer_number) in enumerate(accounts_data_list):

            if index > 0 and (index % 10) == 0:
                get_url(self.driver, _LOGOUT_URL)
                self.perform_login()

            LOGGER.info(
                f"Customer Number: {customer_number}, Restaurant Name: {restaurant_name}"
            )
            setattr(self, "restaurant_name", restaurant_name)
            self.get_account_page(customer_number)
            yield customer_number, None

    def get_select_status_option_values(self):
        dropdown_select = Select(self.get_select_dd())
        return [option.get_attribute("value") for option in dropdown_select.options]

    def get_select_dd(self):
        return self.driver.find_element(*self.Selectors.SELECT_STATUS_DROPDOWN)

    def sort_invoices_by_desc(self):
        self.driver.find_element(*self.Selectors.DATE_COL_HEADER).click()
        wait_for_loaders(
            self.driver,
            value=self.Selectors.INVOICE_TABLE,
            retry_attempts=1,
            timeout=10,
        )
        wait_for_element(
            self.driver,
            value=self.Selectors.BILLING_HISTORY__TABLE_ROWS[1],
            retry_attempts=3,
            msg="Invoice Rows Sorted Descending",
        )

    @retry(WebDriverException, tries=3, delay=2)
    def _has_invoices(self):
        if "invoice-summary" not in self.driver.current_url:
            LOGGER.info(f"Current page url - {self.driver.current_url}")
            get_url(self.driver, _INVOICE_SUMMARY_URL)

        table_content_selector = (
            self.Selectors.BILLING_HISTORY__TABLE_ROWS[1]
            + ", "
            + self.Selectors.NO_TABLE_ROWS[1]
        )
        wait_for_element(
            self.driver,
            value=table_content_selector,
            retry_attempts=3,
            msg="Invoice table content",
        )

        table_content_elem = self.driver.find_element(
            By.CSS_SELECTOR, table_content_selector
        )
        if "default-wrapper" in table_content_elem.get_attribute("class"):
            LOGGER.info(table_content_elem.text)
            return False
        return True

    def _iter_invoice_row_elements(self, start_date: date, end_date: date):
        opt_values = self.get_select_status_option_values()
        for idx, value in enumerate(opt_values):
            if idx > 0:
                select_dropdown_option_by_value(self.get_select_dd(), value)
                wait_for_loaders(
                    self.driver,
                    value=self.Selectors.INVOICE_TABLE,
                    retry_attempts=1,
                    timeout=10,
                )
            if not self._has_invoices():
                continue

            handle_popup(
                self.driver,
                value=self.Selectors.PAYMENT_DUE_POPUP,
                msg="ATTENTION: ACCOUNT PAST DUE",
                retry_attempts=1,
            )
            self.sort_invoices_by_desc()
            table_rows = self.driver.find_elements(
                *self.Selectors.BILLING_HISTORY__TABLE_ROWS
            )

            for index, invoice_row_element in enumerate(table_rows):
                invoice_date = self._extract_invoice_date(invoice_row_element)
                if not start_date <= invoice_date <= end_date:
                    LOGGER.info(
                        f"Skipping remaining invoices because date '{invoice_date}' is outside requested range"
                    )
                    break

                invoice_number = self._extract_invoice_number(invoice_row_element)
                found_duplicate = _validate_duplicate_invoices_by(invoice_number)
                if found_duplicate:
                    continue

                yield invoice_row_element

    def _construct_downloader(
        self, invoice_row_element, **invoice_fields
    ) -> download.BaseDownloader:
        return download.WebElementClickBasedDownloader(
            element=invoice_row_element.find_element(
                *self.Selectors.BILLING_HISTORY__INVOICE_PDF
            ),
            local_filepath=self.download_location,
            rename_to=os.path.join(
                self.download_location, invoice_fields["original_filename"]
            ),
            file_exists_check_kwargs=dict(
                pattern=rf"{invoice_fields['invoice_number']}_\d+-\d+-\d+.pdf$",
                timeout=20,
            ),
        )

    def _extract_invoice_date(self, invoice_row_element) -> date:
        return date_from_string(
            invoice_row_element.find_element(
                *self.Selectors.BILLING_HISTORY__INVOICE_DATE
            ).text,
            "%m/%d/%Y",
        )

    def _extract_customer_number(
        self, invoice_row_element, customer_number, customer_number_element
    ) -> str:
        return customer_number if customer_number else None

    def _extract_invoice_number(self, invoice_row_element, **invoice_fields) -> str:
        return invoice_row_element.find_element(
            *self.Selectors.BILLING_HISTORY__INVOICE_NUMBER
        ).text

    def _extract_total_amount(self, invoice_row_element, **invoice_fields) -> str:
        return invoice_row_element.find_element(
            *self.Selectors.BILLING_HISTORY__TOTAL_AMOUNT
        ).text

    def _extract_vendor_name(self, invoice_row_element, **invoice_fields) -> str:
        return self.vendor_name

    def _extract_restaurant_name(self, invoice_row_element, **invoice_fields) -> str:
        return getattr(self, "restaurant_name", None)

    def _extract_reference_code(self, invoice_row_element, **invoice_fields) -> str:
        customer_number = invoice_fields["customer_number"]
        invoice_number = invoice_fields["invoice_number"]
        invoice_date = invoice_fields["invoice_date"]
        return f"{customer_number}_{invoice_number}_{invoice_date}"

    def _extract_original_download_url(
        self, invoice_row_element, **invoice_fields
    ) -> str:
        return invoice_row_element.find_element(
            *self.Selectors.BILLING_HISTORY__INVOICE_PDF
        ).get_attribute("href")

    def _extract_original_filename(self, invoice_row_element, **invoice_fields) -> str:
        return f"{invoice_fields['reference_code']}.pdf"


def _validate_duplicate_invoices_by(invoice_number):
    existing = (
        DiscoveredFile.objects.select_related("run")
        .filter(Q(original_filename__contains=invoice_number))
        .first()
    )
    if existing:
        LOGGER.warning(
            f"Found existing matching DF with original filename {existing.original_filename}"
            f" whose run ({existing.run_id}) matches."
        )
        return True
    LOGGER.debug(f"No duplicate found.")
    return False
