import os
from datetime import date
from typing import List
from integrator import LOGGER

from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.remote.webelement import WebElement

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
    hover_over_element,
)
from apps.runs.models import FileFormat
from spices.datetime_utils import date_from_string

_LOGIN_URL = "https://prd-aramark.cec.ocp.oraclecloud.com/site/authsite/aramark_site"
_INVOICE_HISTORY_URL = "https://myaccount.aramark.com/invoicing/statements"


@connectors.add("ameripride")
class AmeriprideConnector(BaseVendorConnector):
    vendor_name = "AmeriPride Linen & Uniform Services"
    invoice_file_format = FileFormat.PDF.ident  # pylint: disable=no-member
    df_download_url_skip_duplicates = True

    class Selectors:
        LOGIN__USERNAME_TEXTBOX = (By.CSS_SELECTOR, 'input[id="userid"]')
        LOGIN__PASSWORD_TEXTBOX = (By.CSS_SELECTOR, 'input[id="password"]')
        LOGIN__LOGIN_BUTTON = (By.CSS_SELECTOR, 'button[id="submit-btn"]')
        LOGIN__ERROR_MESSAGE_TEXT = (By.CSS_SELECTOR, "label[id='login-error-msg']")

        ASCENDING_ORDER_ELEMENT = (
            By.CSS_SELECTOR,
            "datatable-header-cell:nth-child(2) app-table-header-cell div aus-icon-button button",
        )
        INVOICES__TABLE_ROW = (
            By.CSS_SELECTOR,
            "datatable-body-row div.datatable-row-center",
        )
        INVOICES__INVOICE_DATE = (
            By.CSS_SELECTOR,
            "datatable-body-cell:nth-child(2) div aus-typography",
        )
        INVOICES__CUSTOMER_NUMBER = (
            By.CSS_SELECTOR,
            "datatable-body-cell:nth-child(1) div aus-typography",
        )
        INVOICES__INVOICE_NUMBER = (
            By.CSS_SELECTOR,
            "td[data-bind='text: invoicenumber']",
        )
        INVOICES__DOWNLOAD_PDF = (
            By.CSS_SELECTOR,
            "datatable-body-cell:nth-child(3) div div aus-icon-button:nth-child(1) button",
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

    _step_navigate_to_invoices_list_page__before_account_selection = NavigateToUrl(
        _INVOICE_HISTORY_URL
    )

    def get_invoice_table_rows(self) -> List[WebElement]:
        wait_for_element(
            self.driver,
            value=self.Selectors.INVOICES__TABLE_ROW[1],
            retry_attempts=5,
            msg="Invoice Table Rows",
        )
        return self.driver.find_elements(*self.Selectors.INVOICES__TABLE_ROW)

    @property
    def get_statement_date_header(self) -> WebElement:
        wait_for_element(
            self.driver,
            value=self.Selectors.ASCENDING_ORDER_ELEMENT[1],
            retry_attempts=5,
            msg="Wait for statement date header...",
        )
        return self.driver.find_element(*self.Selectors.ASCENDING_ORDER_ELEMENT)

    def _iter_invoice_row_elements(self, start_date: date, end_date: date):
        self.get_statement_date_header.click()
        wait_for_element(
            self.driver,
            value=self.Selectors.INVOICES__TABLE_ROW[1],
            retry_attempts=5,
            msg="Wait for invoice table...",
        )

        self.get_statement_date_header.click()
        table_rows = self.get_invoice_table_rows()
        LOGGER.info(f"Total invoices found: {len(table_rows)}")

        for row_element in table_rows:

            invoice_date = self._extract_invoice_date(row_element)
            if not start_date <= invoice_date <= end_date:
                LOGGER.info(
                    f"Skipping remaining invoices because date '{invoice_date}' is outside requested range"
                )
                break

            yield row_element

    def get_download__element(self, invoice_row_element):
        hover_over_element(self.driver, invoice_row_element)
        return invoice_row_element.find_element(*self.Selectors.INVOICES__DOWNLOAD_PDF)

    def _construct_downloader(
        self, invoice_row_element, **invoice_fields
    ) -> download.BaseDownloader:
        return download.WebElementClickBasedDownloader(
            element=self.get_download__element(invoice_row_element),
            local_filepath=os.path.join(
                self.download_location, invoice_fields["original_filename"]
            ),
            file_exists_check_kwargs=dict(timeout=40),
        )

    def _extract_invoice_date(self, invoice_row_element) -> date:
        return date_from_string(
            invoice_row_element.find_element(
                *self.Selectors.INVOICES__INVOICE_DATE
            ).text,
            "%m/%d/%y",
        )

    def _extract_customer_number(
        self, invoice_row_element, customer_number, customer_number_element
    ) -> str:
        customer_number = invoice_row_element.find_element(
            *self.Selectors.INVOICES__CUSTOMER_NUMBER
        ).text
        return customer_number

    def _extract_invoice_number(self, invoice_row_element, **invoice_fields) -> str:
        return None

    def _extract_total_amount(self, invoice_row_element, **invoice_fields) -> str:
        return None

    def _extract_vendor_name(self, invoice_row_element, **invoice_fields) -> str:
        return self.vendor_name

    def _extract_restaurant_name(self, invoice_row_element, **invoice_fields) -> str:
        return None

    def _extract_reference_code(self, invoice_row_element, **invoice_fields) -> str:
        return f"{invoice_fields['customer_number']}_{invoice_fields['invoice_date']}"

    def _extract_original_download_url(
        self, invoice_row_element, **invoice_fields
    ) -> str:
        return f"{invoice_fields['reference_code']}"

    def _extract_original_filename(self, invoice_row_element, **invoice_fields) -> str:
        return f"{invoice_fields['reference_code']}.pdf"
