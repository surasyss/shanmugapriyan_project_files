import os
from datetime import date
from typing import List, Optional

from apps.adapters.helpers.helper import sleep
from integrator import LOGGER

from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import StaleElementReferenceException

from apps.adapters.framework.download import (
    BaseDownloader,
    WebElementClickBasedDownloader,
)
from apps.adapters.framework.registry import connectors
from apps.adapters.framework.operations.vendor import BaseVendorConnector
from apps.adapters.framework.steps.web import (
    NavigateToUrl,
    SubmitLoginPassword,
    ExplicitWait,
)
from apps.adapters.helpers.webdriver_helper import (
    get_url,
    wait_for_loaders,
)
from apps.runs.models import FileFormat
from spices.datetime_utils import date_from_string

_LOGIN_URL = "https://myaccount.sdge.com/portal/PreLogin/Validate"
_BILLING_HISTORY = "https://myaccount.sdge.com/portal/BillingHistory/index"


@connectors.add("san_diego_gas_electric")
class TampaElectricConnector(BaseVendorConnector):
    vendor_name = "San Diego Gas & Electric"
    invoice_file_format = FileFormat.PDF.ident  # pylint: disable=no-member
    df_download_url_skip_duplicates = True

    class Selectors:
        LOGIN__USERNAME_TEXTBOX = (By.CSS_SELECTOR, 'input[id="usernamex"]')
        LOGIN__PASSWORD_TEXTBOX = (By.CSS_SELECTOR, 'input[id="passwordx"]')
        LOGIN__LOGIN_BUTTON = (By.CSS_SELECTOR, 'button[id="btnlogin"] span')
        LOGIN__ERROR_MESSAGE_TEXT = (
            By.CSS_SELECTOR,
            "div.toast-error div.toast-message, div.toast-warning div.toast-message",
        )

        HOME__ACCOUNT_DROPDOWN = (By.CSS_SELECTOR, "button[data-id='accountList']")
        ACCOUNT_DROPDOWN_BUTTON = (
            By.CSS_SELECTOR,
            "div.AccountslctClass div.dropdown button[data-id='accountListHistory']",
        )
        ACCOUNT_LIST = (
            By.CSS_SELECTOR,
            "div[class='dropdown-menu show'] ul.dropdown-menu.show li a.dropdown-item",
        )

        BILLING_HISTORY__TABLE_ROWS = (
            By.CSS_SELECTOR,
            "table#billHistoryTable tbody tr[invoiceid]",
        )
        BILLING_HISTORY__INVOICE_DATE = (By.CSS_SELECTOR, "td")
        BILLING_HISTORY__RESTAURANT_NAME = (By.CSS_SELECTOR, "span.UserNameMain")
        BILLING_HISTORY__ROW_EXPAND = (
            By.CSS_SELECTOR,
            "td.details-control a.downloadPdf",
        )
        BILLING_HISTORY__INVOICE_DOWNLOAD = (
            By.CSS_SELECTOR,
            "tr.expandedRow tr.expandedRowTotal td a#downloadBillingHisotry",
        )
        LOADER = "div[id='preloader'][style='display: block;']"

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
        until=EC.visibility_of_element_located(locator=Selectors.HOME__ACCOUNT_DROPDOWN)
    )

    _step_navigate_to_invoices_list_page__before_account_selection = NavigateToUrl(
        _BILLING_HISTORY
    )

    def get_account_dropdown(self):
        return self.driver.find_element(*self.Selectors.ACCOUNT_DROPDOWN_BUTTON)

    def get_accounts(self):
        return self.driver.find_elements(*self.Selectors.ACCOUNT_LIST)

    def get_table_rows(self):
        return self.driver.find_elements(*self.Selectors.BILLING_HISTORY__TABLE_ROWS)

    def get_details_control(self, invoice_row_element):
        return invoice_row_element.find_element(
            *self.Selectors.BILLING_HISTORY__ROW_EXPAND
        )

    def get_accounts_list(self, index=None):
        wait_for_loaders(self.driver, value=self.Selectors.LOADER, retry_attempts=3)

        if not index == 0:
            self.get_account_dropdown().click()

        accounts_list = self.get_accounts()
        if index is not None:
            return accounts_list[index]
        return accounts_list

    def _iter_customer_number_selections(self, customer_numbers: Optional[List[str]]):
        accounts_list = self.get_accounts_list()

        for index, _ in enumerate(accounts_list):
            self.get_accounts_list(index).click()
            yield None, None

    def _iter_invoice_row_elements(self, start_date: date, end_date: date):
        table_rows = self.get_table_rows()
        for index, _ in enumerate(table_rows):

            setattr(self, "row_index", index)

            if self.driver.current_url != _BILLING_HISTORY:
                get_url(self.driver, _BILLING_HISTORY)

            row = self.get_table_rows()[index]

            invoice_date = self._extract_invoice_date(row)
            if not start_date <= invoice_date <= end_date:
                LOGGER.info(
                    f"Skipping remaining invoices because date '{invoice_date}' is outside requested range"
                )
                break
            yield row

    def _construct_downloader(
        self, invoice_row_element, **invoice_fields
    ) -> BaseDownloader:

        wait_for_loaders(self.driver, value=self.Selectors.LOADER, retry_attempts=3)

        for retry in range(5):
            try:
                invoice_row_element = self.get_table_rows()[getattr(self, "row_index")]

                self.get_details_control(invoice_row_element).click()

                wait_for_loaders(
                    self.driver, value=self.Selectors.LOADER, retry_attempts=3
                )
                break
            except StaleElementReferenceException as excep:
                LOGGER.info(excep)
                sleep(10, msg="Waiting for invoice row element")

                if retry == 4:
                    raise

        return WebElementClickBasedDownloader(
            element=self.driver.find_element(
                *self.Selectors.BILLING_HISTORY__INVOICE_DOWNLOAD
            ),
            local_filepath=os.path.join(self.download_location, "DownloadBillPdf.pdf"),
            rename_to=os.path.join(
                self.download_location, invoice_fields["original_filename"]
            ),
            file_exists_check_kwargs=dict(timeout=20),
        )

    def _extract_invoice_date(self, invoice_row_element) -> date:
        return date_from_string(
            invoice_row_element.find_element(
                *self.Selectors.BILLING_HISTORY__INVOICE_DATE
            ).text,
            "%b %d, %Y",
        )

    def _extract_customer_number(
        self, invoice_row_element, customer_number, customer_number_element
    ) -> str:
        return invoice_row_element.get_attribute("contractaccount")

    def _extract_invoice_number(self, invoice_row_element, **invoice_fields) -> str:
        return invoice_row_element.get_attribute("invoiceid")

    def _extract_total_amount(self, invoice_row_element, **invoice_fields) -> str:
        return invoice_row_element.get_attribute("totalamount")

    def _extract_vendor_name(self, invoice_row_element, **invoice_fields) -> str:
        return self.vendor_name

    def _extract_restaurant_name(self, invoice_row_element, **invoice_fields) -> str:
        return self.driver.find_element(
            *self.Selectors.BILLING_HISTORY__RESTAURANT_NAME
        ).text

    def _extract_reference_code(self, invoice_row_element, **invoice_fields) -> str:
        customer_number = invoice_fields["customer_number"]
        invoice_number = invoice_fields["invoice_number"]
        invoice_date = invoice_fields["invoice_date"]
        return f"{customer_number}_{invoice_number}_{invoice_date}"

    def _extract_original_download_url(
        self, invoice_row_element, **invoice_fields
    ) -> str:
        return invoice_fields["reference_code"]

    def _extract_original_filename(self, invoice_row_element, **invoice_fields) -> str:
        reference_code = self._extract_reference_code(
            invoice_row_element, **invoice_fields
        )
        return f"{reference_code}.pdf"
