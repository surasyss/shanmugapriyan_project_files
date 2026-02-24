import os
from datetime import date

from selenium.webdriver.common.by import By
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
    select_dropdown_option_by_value,
    close_extra_handles,
)
from apps.runs.models import FileFormat
from spices.datetime_utils import date_from_string

_LOGIN_URL = "https://www.homedepot.com/auth/view/signin"
_ORDER_PAGE_URL = "https://www.homedepot.com/order/view/summary"


@connectors.add("homedepot")
class StaplesConnector(BaseVendorConnector):
    vendor_name = "The Home Depot"
    invoice_file_format = FileFormat.PDF.ident  # pylint: disable=no-member
    df_download_url_skip_duplicates = True

    class Selectors:
        LOGIN__USERNAME_TEXTBOX = (By.CSS_SELECTOR, 'input[name="email"]')
        LOGIN__PASSWORD_TEXTBOX = (By.CSS_SELECTOR, 'input[name="password"]')
        LOGIN__LOGIN_BUTTON = (
            By.CSS_SELECTOR,
            'button[data-automation-id="signInSignInButton"]',
        )
        LOGIN__ERROR_MESSAGE_TEXT = (
            By.CSS_SELECTOR,
            'span.alert-inline__message, input[data-automation-id="TwoFactorAuthPassCodeField"]',
        )

        BILLING_HISTORY__TABLE_ROWS = (
            By.CSS_SELECTOR,
            'label[data-automation-id^="authOrderHeader"]',
        )
        INVOICE_DATE = 'h6[data-automation-id="orderHeaderDateOrderedValue"]'
        ORDER_NUMBER = 'h6[data-automation-id="orderHeaderOrderNumberValue"]'
        INVOICE_TOTAL = 'h6[data-automation-id="orderHeaderOrderTotalValue"]'
        VIEW_PDF = 'button[data-automation-id="viewReceipt"]'
        DELIVERED_ADDRESS = 'li[data-automation-id$="AddressDetailsName"]'

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

    # order page navigation
    _submit_login_info__post = NavigateToUrl(_ORDER_PAGE_URL, retry_attempts=5)

    _step_navigate_to_invoices_list_page__after_account_selection = ExplicitWait(
        until=EC.visibility_of_element_located(
            locator=Selectors.BILLING_HISTORY__TABLE_ROWS
        )
    )

    def _iter_invoice_row_elements(self, start_date: date, end_date: date):
        select_dropdown_option_by_value(
            self.driver.find_element_by_css_selector("#orderSummaryDateFilter"),
            "All time",
        )
        table_rows = self.driver.find_elements(
            *self.Selectors.BILLING_HISTORY__TABLE_ROWS
        )
        for row in table_rows:
            if "View Receipt" in row.text:
                yield row

    def _construct_downloader(
        self, invoice_row_element, **invoice_fields
    ) -> download.BaseDownloader:
        invoice_row_element.find_element_by_css_selector(
            self.Selectors.VIEW_PDF
        ).click()
        self.driver.switch_to.window(self.driver.window_handles[1])
        _downloader = download.DriverExecuteCDPCmdBasedDownloader(
            self.driver,
            cmd="Page.printToPDF",
            cmd_args={"printBackground": True},
            local_filepath=f"{self.download_location}/invoice.pdf",
            rename_to=os.path.join(
                self.download_location, invoice_fields["original_filename"]
            ),
            file_exists_check_kwargs=dict(timeout=20),
        )
        close_extra_handles(self.drive)
        return _downloader

    def _extract_invoice_date(self, invoice_row_element) -> date:
        return date_from_string(
            invoice_row_element.find_element_by_css_selector(
                self.Selectors.INVOICE_DATE
            ).text,
            "%B %d, %Y",
        )

    def _extract_invoice_number(self, invoice_row_element, **invoice_fields) -> str:
        return invoice_row_element.find_element_by_css_selector(
            self.Selectors.ORDER_NUMBER
        ).text

    def _extract_total_amount(self, invoice_row_element, **invoice_fields) -> str:
        return invoice_row_element.find_element_by_css_selector(
            self.Selectors.INVOICE_TOTAL
        ).text

    def _extract_vendor_name(self, invoice_row_element, **invoice_fields) -> str:
        return self.vendor_name

    def _extract_reference_code(self, invoice_row_element, **invoice_fields) -> str:
        return f'{invoice_fields["invoice_number"]}_{invoice_fields["invoice_date"]}'

    def _extract_original_download_url(
        self, invoice_row_element, **invoice_fields
    ) -> str:
        return f"{invoice_fields['reference_code']}"

    def _extract_original_filename(self, invoice_row_element, **invoice_fields) -> str:
        return f"{invoice_fields['reference_code']}.pdf"

    def _extract_customer_number(
        self, invoice_row_element, customer_number, customer_number_element
    ) -> str:
        return None
