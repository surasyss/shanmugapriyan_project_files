import os.path
from datetime import date
from typing import List

from apps.adapters.framework.context import ExecutionContext
from apps.adapters.framework.steps.primitives import SequentialSteps
from integrator import LOGGER

from selenium.webdriver.remote.webelement import WebElement
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC

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
    ClickElement,
)
from apps.adapters.helpers.webdriver_helper import wait_for_element
from apps.runs.models import FileFormat
from spices.datetime_utils import date_from_string

_LOGIN_URL = "https://www.hawaiiantel.com/My-Account"


class RemoveElement:
    def __call__(self, execution_context: ExecutionContext):
        execution_context.driver.execute_script(
            """
            var elements = document.querySelectorAll("div.cc-window");
            for (const element of elements) {
                element.parentNode.removeChild(element);
            }
        """
        )


@connectors.add("hawaiian_telcom")
class HawaiianTelcomConnector(BaseVendorConnector):
    vendor_name = "Hawaiian Telcom"
    invoice_file_format = FileFormat.PDF.ident  # pylint: disable=no-member
    df_download_url_skip_duplicates = True

    class Selectors:
        LOGIN__USERNAME_TEXTBOX = (By.CSS_SELECTOR, "input[id='userNameInput']")
        LOGIN__PASSWORD_TEXTBOX = (By.CSS_SELECTOR, "input[id='passwordInput']")
        LOGIN__LOGIN_BUTTON = (By.CSS_SELECTOR, "span[id='submitButton']")
        LOGIN__ERROR_MESSAGE_TEXT = (By.CSS_SELECTOR, "span[id='errorText']")

        LOGIN_IFRAME = (By.CSS_SELECTOR, "iframe[id='iframeUumax']")
        BILLING_TAB = (By.LINK_TEXT, "Billing")
        SEARCH_BUTTON = (
            By.CSS_SELECTOR,
            "div.billing-historical-data div.search-btn-wrapper button",
        )

        INVOICE_TABLE_ROWS = (By.CSS_SELECTOR, "table.table tbody tr")
        INVOICE_DATE = (By.CSS_SELECTOR, "td a")
        CUSTOMER_NUMBER = (By.XPATH, "//span[text()='Account Number:']/..")
        RESTAURANT_NAME = (By.XPATH, "//span[text()='Customer Name:']/..")

    # login
    _navigate_to_login_page = NavigateToUrl(_LOGIN_URL, retry_attempts=5)

    _submit_login_info__pre = SequentialSteps(
        [
            RemoveElement(),
            ExplicitWait(
                until=EC.frame_to_be_available_and_switch_to_it(
                    locator=Selectors.LOGIN_IFRAME
                )
            ),
            ExplicitWait(
                until=EC.visibility_of_element_located(
                    locator=Selectors.LOGIN__USERNAME_TEXTBOX
                )
            ),
        ]
    )

    _submit_login_info = SubmitLoginPassword(
        username_textbox=Selectors.LOGIN__USERNAME_TEXTBOX,
        password_textbox=Selectors.LOGIN__PASSWORD_TEXTBOX,
        login_button=Selectors.LOGIN__LOGIN_BUTTON,
        error_message=Selectors.LOGIN__ERROR_MESSAGE_TEXT,
    )
    _submit_login_info__post = ExplicitWait(
        until=EC.visibility_of_element_located(locator=Selectors.BILLING_TAB)
    )

    _step_navigate_to_invoices_list_page__before_account_selection = ClickElement(
        Selectors.BILLING_TAB
    )

    def get_invoice_table_rows(self) -> List[WebElement]:
        wait_for_element(
            self.driver,
            value=self.Selectors.INVOICE_TABLE_ROWS[1],
            retry_attempts=3,
            msg="Invoice Table Rows",
        )
        return self.driver.find_elements(*self.Selectors.INVOICE_TABLE_ROWS)

    def get_search_button(self):
        wait_for_element(
            self.driver,
            value=self.Selectors.SEARCH_BUTTON[1],
            retry_attempts=3,
            msg="Search Button",
        )
        return self.driver.find_element(*self.Selectors.SEARCH_BUTTON)

    def _iter_invoice_row_elements(self, start_date: date, end_date: date):
        self.get_search_button().click()

        invoice_row_elements = self.get_invoice_table_rows()

        for index, invoice_row_element in enumerate(invoice_row_elements):

            invoice_date = self._extract_invoice_date(invoice_row_element)

            if not start_date <= invoice_date <= end_date:
                LOGGER.info(
                    f"Skipping remaining invoices because date '{invoice_date}' is outside requested range"
                )
                break

            yield invoice_row_element

    def _construct_downloader(
        self, invoice_row_element, **invoice_fields
    ) -> BaseDownloader:

        return WebElementClickBasedDownloader(
            element=invoice_row_element.find_element(*self.Selectors.INVOICE_DATE),
            local_filepath=os.path.join(
                self.download_location, invoice_fields["original_filename"]
            ),
            rename_to=os.path.join(
                self.download_location, f"{invoice_fields['reference_code']}.pdf"
            ),
            file_exists_check_kwargs=dict(timeout=40),
        )

    def _extract_invoice_date(self, invoice_row_element) -> date:
        return date_from_string(
            invoice_row_element.find_element(*self.Selectors.INVOICE_DATE).text,
            "%m/%d/%Y",
        )

    def _extract_customer_number(
        self, invoice_row_element, customer_number, customer_number_element
    ) -> str:
        return self.driver.find_element(*self.Selectors.CUSTOMER_NUMBER).text.split(
            ":"
        )[1]

    def _extract_invoice_number(self, invoice_row_element, **invoice_fields) -> str:
        return None

    def _extract_total_amount(self, invoice_row_element, **invoice_fields) -> str:
        return None

    def _extract_vendor_name(self, invoice_row_element, **invoice_fields) -> str:
        return self.vendor_name

    def _extract_restaurant_name(self, invoice_row_element, **invoice_fields) -> str:
        return self.driver.find_element(*self.Selectors.RESTAURANT_NAME).text

    def _extract_reference_code(self, invoice_row_element, **invoice_fields) -> str:
        customer_number = invoice_fields["customer_number"]
        invoice_date = invoice_fields["invoice_date"]
        return f"{customer_number}_{invoice_date}"

    def _extract_original_download_url(
        self, invoice_row_element, **invoice_fields
    ) -> str:
        return invoice_row_element.find_element(
            *self.Selectors.INVOICE_DATE
        ).get_attribute("href")

    def _extract_original_filename(self, invoice_row_element, **invoice_fields) -> str:
        return "SSEPDFExtractor.pdf"
