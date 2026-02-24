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
from apps.runs.models import FileFormat
from spices.datetime_utils import date_from_string

_LOGIN_URL = "https://www3.edocuvault.com/pos-cust/"


@connectors.add("prudential_overall_supply")
class PrudentialOverallSupplyConnector(BaseVendorConnector):
    vendor_name = "PRUDENTIAL OVERALL SUPPLY"
    invoice_file_format = FileFormat.PDF.ident  # pylint: disable=no-member
    df_download_url_skip_duplicates = True

    class Selectors:
        LOGIN__USERNAME_TEXTBOX = (By.CSS_SELECTOR, 'input[name="Login1$UserName"]')
        LOGIN__PASSWORD_TEXTBOX = (By.CSS_SELECTOR, 'input[name="Login1$Password"]')
        LOGIN__LOGIN_BUTTON = (By.CSS_SELECTOR, 'input[name="Login1$LoginButton"]')
        LOGIN__ERROR_MESSAGE_TEXT = (
            By.CSS_SELECTOR,
            "#Login1>tbody>tr>td>table>tbody>tr:nth-child(5)>td",
        )

        BILLING_HISTORY__TABLE_ROWS = (
            By.CSS_SELECTOR,
            '#GridView2>tbody>tr[style="background-color:White;"]',
        )
        BILLING_HISTORY__CUSTOMER_NUMBER = (By.CSS_SELECTOR, "#lblCustNo")

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

    def _iter_invoice_row_elements(self, start_date: date, end_date: date):
        table_rows = self.driver.find_elements(
            *self.Selectors.BILLING_HISTORY__TABLE_ROWS
        )
        for row in table_rows:
            yield row

    def _construct_downloader(
        self, invoice_row_element, **invoice_fields
    ) -> download.BaseDownloader:
        temp_url = self.get_url_and_switch_page(invoice_row_element)
        self.driver.close()
        self.driver.switch_to.window(self.driver.window_handles[0])

        return download.DriverBasedUrlGetDownloader(
            self.driver,
            download_url=temp_url,
            local_filepath=os.path.join(
                self.download_location, temp_url.split("/")[-1]
            ),
            file_exists_check_kwargs=dict(timeout=80),
        )

    def get_url_and_switch_page(self, invoice_row_element):
        invoice_row_element.find_elements_by_css_selector("td")[0].click()
        self.driver.switch_to.window(self.driver.window_handles[1])
        return (
            self.driver.find_element_by_css_selector("iframe")
            .get_attribute("href")
            .replace("</a", "")
        )

    def _extract_invoice_date(self, invoice_row_element) -> date:
        return date_from_string(
            invoice_row_element.find_elements_by_css_selector("td")[2].text, "%m/%d/%Y"
        )

    def _extract_customer_number(
        self, invoice_row_element, customer_number, customer_number_element
    ) -> str:
        return self.driver.find_element(
            *self.Selectors.BILLING_HISTORY__CUSTOMER_NUMBER
        ).text

    def _extract_invoice_number(self, invoice_row_element, **invoice_fields) -> str:
        return invoice_row_element.find_elements_by_css_selector("td")[1].text

    def _extract_total_amount(self, invoice_row_element, **invoice_fields) -> str:
        return invoice_row_element.find_elements_by_css_selector("td")[4].text

    def _extract_vendor_name(self, invoice_row_element, **invoice_fields) -> str:
        return "PRUDENTIAL OVERALL SUPPLY"

    def _extract_reference_code(self, invoice_row_element, **invoice_fields) -> str:
        return (
            f"{invoice_fields['customer_number']}_{invoice_fields['invoice_number']}_"
            f"{invoice_fields['invoice_date']}"
        )

    def _extract_original_download_url(
        self, invoice_row_element, **invoice_fields
    ) -> str:
        return invoice_row_element.find_element_by_css_selector("td>a").get_attribute(
            "href"
        )

    def _extract_original_filename(self, invoice_row_element, **invoice_fields) -> str:
        reference_code = self._extract_reference_code(
            invoice_row_element, **invoice_fields
        )
        return f"{reference_code}.pdf"
