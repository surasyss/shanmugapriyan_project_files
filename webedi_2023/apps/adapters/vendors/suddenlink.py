import os.path
from datetime import date
from typing import List

from integrator import LOGGER

from selenium.webdriver.remote.webelement import WebElement
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC

from apps.adapters.framework.download import (
    BaseDownloader,
    DriverBasedUrlGetDownloader,
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

_LOGIN_URL = (
    "https://authorize.suddenlink.net/saml/module.php/authSynacor/login.php?"
    "AuthState=_4c43f6ee66becc70140958f7d09afdf6ec472e9bec%3Ahttps%3A%2F%2Fauthorize.suddenlink.net"
    "%2Fsaml%2Fsaml2%2Fidp%2FSSOService.php%3Fspentityid%3Daccount.suddenlink.net%26cookieTime%3D1615406272"
)
_VIEW_STATEMENTS_URL = (
    "https://account.suddenlink.net/my-account/mybill/viewstatements.html"
)


@connectors.add("suddenlink")
class SuddenlinkConnector(BaseVendorConnector):
    vendor_name = "Suddenlink"
    invoice_file_format = FileFormat.PDF.ident  # pylint: disable=no-member
    df_download_url_skip_duplicates = True

    class Selectors:
        LOGIN__USERNAME_TEXTBOX = (By.CSS_SELECTOR, "input[id='username']")
        LOGIN__PASSWORD_TEXTBOX = (By.CSS_SELECTOR, "input[id='password']")
        LOGIN__LOGIN_BUTTON = (By.CSS_SELECTOR, "button[id='login']")
        LOGIN__ERROR_MESSAGE_TEXT = (By.CSS_SELECTOR, "div[role='alert']")

        VIEW_STATEMENTS = (By.CSS_SELECTOR, "a#viewStatementsButton")
        CUSTOMER_NUMBER = (
            By.XPATH,
            "//div[text()='View Statements']/following-sibling::div",
        )
        INVOICE_TABLE_ROWS = (By.CSS_SELECTOR, "table.table tbody tr.statementObject")
        INVOICE_NUMBER = (By.CSS_SELECTOR, "td")
        INVOICE_DATE = (By.CSS_SELECTOR, "td:nth-child(2)")
        VIEW_PDF = (By.CSS_SELECTOR, "td:nth-child(3) a")

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
        until=EC.visibility_of_element_located(locator=Selectors.VIEW_STATEMENTS)
    )

    _step_navigate_to_invoices_list_page__before_account_selection = NavigateToUrl(
        _VIEW_STATEMENTS_URL
    )

    def get_invoice_table_rows(self) -> List[WebElement]:
        wait_for_element(
            self.driver,
            value=self.Selectors.INVOICE_TABLE_ROWS[1],
            retry_attempts=3,
            msg="Invoice Table Rows",
        )
        return self.driver.find_elements(*self.Selectors.INVOICE_TABLE_ROWS)

    @staticmethod
    def invoice_table_data_element(row_element, td_selector):
        return row_element.find_element(*td_selector)

    def get_customer_number(self):
        return self.driver.find_element(*self.Selectors.CUSTOMER_NUMBER)

    def _iter_invoice_row_elements(self, start_date: date, end_date: date):
        invoices_list = []
        customer_number = self.get_customer_number().text

        invoice_row_elements = self.get_invoice_table_rows()

        for index, invoice_row_element in enumerate(invoice_row_elements):
            invoice_number = SuddenlinkConnector.invoice_table_data_element(
                invoice_row_element, self.Selectors.INVOICE_NUMBER
            ).text
            invoice_date_str = SuddenlinkConnector.invoice_table_data_element(
                invoice_row_element, self.Selectors.INVOICE_DATE
            ).text
            download_url = SuddenlinkConnector.invoice_table_data_element(
                invoice_row_element, self.Selectors.VIEW_PDF
            ).get_attribute("href")

            invoice_date = date_from_string(invoice_date_str, "%m/%d/%Y")

            if not start_date <= invoice_date <= end_date:
                LOGGER.info(
                    f"Skipping remaining invoices because date '{invoice_date}' is outside requested range"
                )
                break

            invoice_data = {
                "customer_number": customer_number,
                "invoice_number": invoice_number,
                "invoice_date": invoice_date,
                "original_download_url": download_url,
            }

            invoices_list.append(invoice_data)

        for invoice in invoices_list:
            yield invoice

    def _construct_downloader(
        self, invoice_row_element, **invoice_fields
    ) -> BaseDownloader:

        return DriverBasedUrlGetDownloader(
            driver=self.driver,
            download_url=invoice_fields["original_download_url"],
            local_filepath=os.path.join(
                self.download_location, invoice_fields["original_filename"]
            ),
            rename_to=os.path.join(
                self.download_location, f'{invoice_fields["reference_code"]}.pdf'
            ),
            file_exists_check_kwargs=dict(timeout=30),
        )

    def _extract_invoice_date(self, invoice_row_element) -> date:
        return invoice_row_element["invoice_date"]

    def _extract_customer_number(
        self, invoice_row_element, customer_number, customer_number_element
    ) -> str:
        return invoice_row_element["customer_number"]

    def _extract_invoice_number(self, invoice_row_element, **invoice_fields) -> str:
        return invoice_row_element["invoice_number"]

    def _extract_total_amount(self, invoice_row_element, **invoice_fields) -> str:
        return None

    def _extract_vendor_name(self, invoice_row_element, **invoice_fields) -> str:
        return self.vendor_name

    def _extract_restaurant_name(self, invoice_row_element, **invoice_fields) -> str:
        return None

    def _extract_reference_code(self, invoice_row_element, **invoice_fields) -> str:
        return f"{invoice_fields['customer_number']}_{invoice_fields['invoice_number']}"

    def _extract_original_download_url(
        self, invoice_row_element, **invoice_fields
    ) -> str:
        return invoice_row_element["original_download_url"]

    def _extract_original_filename(self, invoice_row_element, **invoice_fields) -> str:
        return "viewStatement.pdf"
