import os.path
from datetime import date
from typing import List

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
)
from apps.adapters.helpers.webdriver_helper import wait_for_element
from apps.runs.models import FileFormat
from spices.datetime_utils import date_from_string

_LOGIN_URL = "https://www.onlinebiller.com/tcpud/index.html"
_VIEW_BILLS_URL = "https://www.onlinebiller.com/tcpud/statements.html"


@connectors.add("tahoe_city_public_utility_district")
class TahoeCityPublicUtilityDistrictConnector(BaseVendorConnector):
    vendor_name = "Tahoe City Public Utility District"
    invoice_file_format = FileFormat.PDF.ident  # pylint: disable=no-member
    df_download_url_skip_duplicates = True

    class Selectors:
        LOGIN__USERNAME_TEXTBOX = (By.CSS_SELECTOR, "input[name='principal']")
        LOGIN__PASSWORD_TEXTBOX = (By.CSS_SELECTOR, "input[name='password']")
        LOGIN__LOGIN_BUTTON = (By.CSS_SELECTOR, "input[name='submitbtn']")
        LOGIN__ERROR_MESSAGE_TEXT = (By.CSS_SELECTOR, "p.error_message")

        INVOICE_TABLE_ROWS = (By.CSS_SELECTOR, "table[class='list_table'] tbody tr")
        CUSTOMER_NUMBER = (By.CSS_SELECTOR, "td")
        INVOICE_DATE = (By.CSS_SELECTOR, "td:nth-child(3)")
        TOTAL_AMOUNT = (By.CSS_SELECTOR, "td:nth-child(5)")
        PDF_DOWNLOAD_BUTTON = (By.CSS_SELECTOR, "td:nth-child(6) input")

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
        until=EC.visibility_of_element_located(locator=Selectors.INVOICE_TABLE_ROWS)
    )

    _step_navigate_to_invoices_list_page__before_account_selection = NavigateToUrl(
        _VIEW_BILLS_URL
    )

    def get_invoice_table_rows(self) -> List[WebElement]:
        return self.driver.find_elements(*self.Selectors.INVOICE_TABLE_ROWS)[2:]

    def _iter_invoice_row_elements(self, start_date: date, end_date: date):
        wait_for_element(
            self.driver,
            value=self.Selectors.INVOICE_TABLE_ROWS[1],
            retry_attempts=3,
            msg="Invoice Table Rows",
        )

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
            element=invoice_row_element.find_element(
                *self.Selectors.PDF_DOWNLOAD_BUTTON
            ),
            local_filepath=os.path.join(
                self.download_location, invoice_fields["original_filename"]
            ),
            rename_to=os.path.join(
                self.download_location, f"{invoice_fields['reference_code']}.pdf"
            ),
            file_exists_check_kwargs=dict(timeout=20),
        )

    def _extract_invoice_date(self, invoice_row_element) -> date:
        return date_from_string(
            invoice_row_element.find_element(*self.Selectors.INVOICE_DATE).text,
            "%b %d, %Y",
        )

    def _extract_customer_number(
        self, invoice_row_element, customer_number, customer_number_element
    ) -> str:
        return invoice_row_element.find_element(
            *self.Selectors.CUSTOMER_NUMBER
        ).text.split()[0]

    def _extract_invoice_number(self, invoice_row_element, **invoice_fields) -> str:
        return None

    def _extract_total_amount(self, invoice_row_element, **invoice_fields) -> str:
        return invoice_row_element.find_element(*self.Selectors.TOTAL_AMOUNT).text

    def _extract_vendor_name(self, invoice_row_element, **invoice_fields) -> str:
        return self.vendor_name

    def _extract_restaurant_name(self, invoice_row_element, **invoice_fields) -> str:
        return None

    def _extract_reference_code(self, invoice_row_element, **invoice_fields) -> str:
        customer_number = invoice_fields["customer_number"]
        invoice_date = invoice_fields["invoice_date"]
        return f"{customer_number}_{invoice_date}"

    def _extract_original_download_url(
        self, invoice_row_element, **invoice_fields
    ) -> str:
        return invoice_fields["reference_code"]

    def _extract_original_filename(self, invoice_row_element, **invoice_fields) -> str:
        return f"eBill_{invoice_fields['invoice_date'].strftime('%m_%d_%Y')}.pdf"
