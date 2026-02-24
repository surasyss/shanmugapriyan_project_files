import os
from datetime import date
from typing import List, Optional
from integrator import LOGGER

from selenium.webdriver.common.by import By
from selenium.webdriver.support.select import Select
from selenium.webdriver.support import expected_conditions as EC

from apps.adapters.framework.operations.vendor import BaseVendorConnector
from apps.adapters.framework.steps.web import (
    NavigateToUrl,
    ExplicitWait,
    SubmitLoginPassword,
)
from apps.adapters.framework.registry import connectors
from apps.adapters.helpers.webdriver_helper import (
    has_invoices,
    wait_for_element,
    select_dropdown_option_by_value,
    wait_for_loaders,
)
from apps.adapters.framework import download
from apps.runs.models import FileFormat
from spices.datetime_utils import date_from_string

_LOGIN_URL = "https://www.txu.com/login.aspx"
_VIEW_BILL_URL = "https://business.txu.com/Manage-MyAccount/View-All-Accounts/View-Bill"


@connectors.add("txu")
class TXUEnergyConnector(BaseVendorConnector):
    vendor_name = "TXU Energy"
    invoice_file_format = FileFormat.PDF.ident  # pylint: disable=no-member
    df_download_url_skip_duplicates = True

    class Selectors:
        LOGIN__USERNAME_TEXTBOX = (
            By.CSS_SELECTOR,
            'input[id="ContentPlaceHolderMain_rightsidebar_0_txtUsername"]',
        )
        LOGIN__PASSWORD_TEXTBOX = (
            By.CSS_SELECTOR,
            'input[id="ContentPlaceHolderMain_rightsidebar_0_txtPassword"]',
        )
        LOGIN__LOGIN_BUTTON = (By.CSS_SELECTOR, "div.signin a.btn-signin")
        LOGIN__ERROR_MESSAGE_TEXT = (By.CSS_SELECTOR, "label.error")

        HOME__ACCOUNTS_DROPDOWN = (By.CSS_SELECTOR, "select#ddl_AccountFilter_CA")
        INVOICE_DATE_DROPDOWN = (By.CSS_SELECTOR, "select#ddl_viewBillDate")

        BILLING__INVOICE_TABLE_ROW = (
            By.CSS_SELECTOR,
            "table#BillHistoryGridDesktop_content_table tbody tr",
        )
        BILLING__INVOICE_PDF = (By.CSS_SELECTOR, "a#loadPdf")
        BILLING__TOTAL_AMOUNT = (
            By.CSS_SELECTOR,
            "div#viewBillSummaryContent > :nth-child(2) > :nth-child(2)",
        )
        LOADER = "div.loading[style='display: block;']"

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
        until=EC.visibility_of_element_located(
            locator=Selectors.HOME__ACCOUNTS_DROPDOWN
        )
    )

    _step_navigate_to_invoices_list_page__before_account_selection = NavigateToUrl(
        _VIEW_BILL_URL
    )

    def get_accounts(self):

        wait_for_element(
            self.driver,
            value=self.Selectors.HOME__ACCOUNTS_DROPDOWN[1],
            msg="Accounts Dropdown",
            retry_attempts=3,
        )
        select = Select(self.get_accounts_dropdown())
        account_numbers = [
            option.get_attribute("value")
            for option in select.options
            if option.get_attribute("data-status") == "Active"
        ]
        return [*set(account_numbers)]

    def get_invoices(self):

        wait_for_element(
            self.driver,
            value=self.Selectors.INVOICE_DATE_DROPDOWN[1],
            msg="Invoices Dropdown",
            retry_attempts=3,
        )
        select = Select(self.get_invoices_dropdown())
        values = [
            (option.get_attribute("value"), option.text) for option in select.options
        ]
        return values

    def get_accounts_dropdown(self):
        return self.driver.find_element(*self.Selectors.HOME__ACCOUNTS_DROPDOWN)

    def get_invoices_dropdown(self):
        return self.driver.find_element(*self.Selectors.INVOICE_DATE_DROPDOWN)

    def _iter_customer_number_selections(self, customer_numbers: Optional[List[str]]):
        wait_for_loaders(self.driver, value=self.Selectors.LOADER, retry_attempts=1)
        account_numbers = self.get_accounts()
        LOGGER.info(f"Total accounts found: {account_numbers}")

        for index, account_num in enumerate(account_numbers):
            select_dropdown_option_by_value(self.get_accounts_dropdown(), account_num)
            LOGGER.info(f"Selected account: {account_num}")
            wait_for_loaders(self.driver, value=self.Selectors.LOADER)

            if not has_invoices(
                self.driver, value=self.Selectors.BILLING__INVOICE_PDF[1]
            ):
                continue
            yield account_num, None

    def _iter_invoice_row_elements(self, start_date: date, end_date: date):

        invoice_numbers_list = self.get_invoices()

        for _, (invoice_number, invoice_date_str) in enumerate(invoice_numbers_list):
            select = Select(self.get_invoices_dropdown())
            select.select_by_value(invoice_number)
            LOGGER.info(f"Selected invoice: {invoice_number}")

            invoice_date = date_from_string(invoice_date_str, "%B %d, %Y")
            if not start_date <= invoice_date <= end_date:
                LOGGER.info(
                    f"Skipping invoices because date '{invoice_date}' is outside requested range"
                )
                break
            wait_for_loaders(self.driver, value=self.Selectors.LOADER)
            yield invoice_number, invoice_date

    def _construct_downloader(
        self, invoice_row_element, **invoice_fields
    ) -> download.BaseDownloader:

        return download.WebElementClickBasedDownloader(
            element=self.driver.find_element(*self.Selectors.BILLING__INVOICE_PDF),
            local_filepath=os.path.join(self.download_location, "GetBillPdf.pdf"),
            rename_to=os.path.join(
                self.download_location, invoice_fields["original_filename"]
            ),
            file_exists_check_kwargs=dict(timeout=40),
        )

    def _extract_invoice_date(self, invoice_row_element) -> date:
        return invoice_row_element[1]

    def _extract_customer_number(
        self, invoice_row_element, customer_number, customer_number_element
    ) -> str:
        return customer_number

    def _extract_invoice_number(self, invoice_row_element, **invoice_fields) -> str:
        return invoice_row_element[0]

    def _extract_total_amount(self, invoice_row_element, **invoice_fields) -> str:
        return self.driver.find_element(*self.Selectors.BILLING__TOTAL_AMOUNT).text

    def _extract_vendor_name(self, invoice_row_element, **invoice_fields) -> str:
        return self.vendor_name

    def _extract_restaurant_name(self, invoice_row_element, **invoice_fields) -> str:
        return None

    def _extract_reference_code(self, invoice_row_element, **invoice_fields) -> str:
        customer_number = invoice_fields["customer_number"]
        invoice_number = invoice_fields["invoice_number"]
        return f"{customer_number}_{invoice_number}"

    def _extract_original_download_url(
        self, invoice_row_element, **invoice_fields
    ) -> str:
        return invoice_fields["reference_code"]

    def _extract_original_filename(self, invoice_row_element, **invoice_fields) -> str:
        return f"{invoice_fields['reference_code']}.pdf"
