import os
import re
from datetime import date
from typing import Optional, List

from apps.adapters.helpers.webdriver_helper import get_url, wait_for_element
from integrator import LOGGER
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC

from apps.adapters.framework.registry import connectors
from apps.adapters.framework.operations.vendor import BaseVendorConnector
from apps.adapters.framework.steps.web import (
    NavigateToUrl,
    SubmitLoginPassword,
    ExplicitWait,
    ClickElement,
)

from apps.adapters.framework import download
from apps.runs.models import FileFormat
from spices.datetime_utils import date_from_string

_LOGIN_URL = "https://www.onlinebiller.com/omwd/login_submit.html"
_DASHBOARD_URL = "https://billpay.onlinebiller.com/ebpp/olivenhain/Dashboard"


@connectors.add("olivenhain")
class OlivenhainConnector(BaseVendorConnector):
    vendor_name = "Olivenhain"
    invoice_file_format = FileFormat.PDF.ident  # pylint: disable=no-member
    df_download_url_skip_duplicates = True

    class Selectors:
        LOGIN__USERNAME_TEXTBOX = (By.CSS_SELECTOR, "input#Login")
        LOGIN__PASSWORD_TEXTBOX = (By.CSS_SELECTOR, "input#Password")
        LOGIN__LOGIN_BUTTON = (By.CSS_SELECTOR, "button#login-button")
        LOGIN__ERROR_MESSAGE_TEXT = (By.CSS_SELECTOR, "div#alert_panel")

        ACCOUNT__DROPDOWN = (By.CSS_SELECTOR, "#account-dropdown-button")
        INVOICE__TABLE_ROW = (By.CSS_SELECTOR, "div#detail_list table tbody tr")
        VIEW_BILL_FOR_ACCOUNT = (
            By.CSS_SELECTOR,
            "div.input-group-btn button.dropdown-toggle",
        )
        ACCOUNT_DROPDOWN_OPTIONS = (
            By.CSS_SELECTOR,
            "ul#account-selector li a.account-display-item",
        )
        VIEW_INVOICE = (By.CSS_SELECTOR, "button#invoice-view")
        IFRAME = (By.CSS_SELECTOR, "iframe#bill-view-frame")
        TABLE_HEADER = "table#detail_header"
        INVOICE_DATE = (By.CSS_SELECTOR, "td[data-label='Bill Date']")
        RESTAURANT_NAME = (By.CSS_SELECTOR, "td[data-label='Name']")
        VIEW_DOCUMENT = (
            By.CSS_SELECTOR,
            "td[data-label='View Document'] a.desktop_view",
        )

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
        until=EC.visibility_of_element_located(locator=Selectors.ACCOUNT__DROPDOWN)
    )

    _step_navigate_to_invoices_list_page__before_account_selection = ClickElement(
        Selectors.VIEW_BILL_FOR_ACCOUNT
    )

    def _iter_customer_number_selections(self, customer_numbers: Optional[List[str]]):
        account_dd_options = self.driver.find_elements(
            *self.Selectors.ACCOUNT_DROPDOWN_OPTIONS
        )
        account_numbers = [
            option.get_attribute("data-ref_id") for option in account_dd_options
        ]

        for index, account_number in enumerate(account_numbers):
            if index > 0:
                get_url(self.driver, _DASHBOARD_URL)
                self.driver.find_element(*self.Selectors.VIEW_BILL_FOR_ACCOUNT).click()

            self.driver.find_element(
                By.CSS_SELECTOR,
                f"{self.Selectors.ACCOUNT_DROPDOWN_OPTIONS[1]}[data-ref_id='{account_number}']",
            ).click()
            self.driver.find_element(*self.Selectors.VIEW_INVOICE).click()
            self.step_post_account_selection()

            yield account_number, None

    def step_post_account_selection(self):
        invoice_history_url = self.driver.find_element(
            *self.Selectors.IFRAME
        ).get_attribute("src")
        get_url(self.driver, invoice_history_url)
        wait_for_element(
            self.driver,
            value=self.Selectors.TABLE_HEADER,
            msg="Click to View History",
        )
        self.driver.execute_script("display_list();return false;")

    def _iter_invoice_row_elements(self, start_date: date, end_date: date):
        table_rows = self.driver.find_elements(*self.Selectors.INVOICE__TABLE_ROW)

        invoices_list = []
        for index, row in enumerate(table_rows):
            invoice_date = date_from_string(
                row.find_element(*self.Selectors.INVOICE_DATE).text,
                "%Y-%m-%d",
            )
            if not start_date <= invoice_date <= end_date:
                LOGGER.info(
                    f"Skipping remaining invoices because date '{invoice_date}' is outside requested range"
                )
                break

            restaurant_name = row.find_element(*self.Selectors.RESTAURANT_NAME).text
            pdf_url_elem = row.find_element(
                *self.Selectors.VIEW_DOCUMENT
            ).get_attribute("onclick")

            invoices_list.append(
                {
                    "invoice_date": invoice_date,
                    "restaurant_name": restaurant_name,
                    "original_download_url": re.search(
                        "\('(http\S+)'\)", pdf_url_elem
                    ).group(1),
                }
            )

        for invoice in invoices_list:
            yield invoice

    def _construct_downloader(
        self, invoice_row_element, **invoice_fields
    ) -> download.BaseDownloader:

        return download.DriverBasedUrlGetDownloader(
            driver=self.driver,
            download_url=invoice_fields["original_download_url"],
            local_filepath=os.path.join(self.download_location, "document.pdf"),
            rename_to=os.path.join(
                self.download_location, invoice_fields["original_filename"]
            ),
            file_exists_check_kwargs=dict(timeout=20),
        )

    def _extract_invoice_date(self, invoice_row_element) -> date:
        return invoice_row_element["invoice_date"]

    def _extract_customer_number(
        self, invoice_row_element, customer_number, customer_number_element
    ) -> str:
        return customer_number

    def _extract_invoice_number(self, invoice_row_element, **invoice_fields) -> str:
        return None

    def _extract_total_amount(self, invoice_row_element, **invoice_fields) -> str:
        return None

    def _extract_vendor_name(self, invoice_row_element, **invoice_fields) -> str:
        return self.vendor_name

    def _extract_restaurant_name(self, invoice_row_element, **invoice_fields) -> str:
        return invoice_row_element["restaurant_name"]

    def _extract_reference_code(self, invoice_row_element, **invoice_fields) -> str:
        customer_number = invoice_fields["customer_number"]
        invoice_date = invoice_fields["invoice_date"]
        return f"{customer_number}_{invoice_date}"

    def _extract_original_download_url(
        self, invoice_row_element, **invoice_fields
    ) -> str:
        return invoice_row_element["original_download_url"]

    def _extract_original_filename(self, invoice_row_element, **invoice_fields) -> str:
        return f"{invoice_fields['reference_code']}.pdf"
