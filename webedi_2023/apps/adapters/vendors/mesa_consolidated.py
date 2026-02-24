import os
from datetime import date
from typing import List, Optional
from integrator import LOGGER

from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import WebDriverException

from apps.adapters.framework.registry import connectors
from apps.adapters.framework.operations.vendor import BaseVendorConnector
from apps.adapters.framework.steps.web import (
    NavigateToUrl,
    SubmitLoginPassword,
    ExplicitWait,
)
from apps.adapters.helpers.webdriver_helper import (
    wait_for_element,
    get_url,
)
from apps.adapters.framework import download
from apps.runs.models import FileFormat
from spices.datetime_utils import date_from_string


_LOGIN_URL = (
    "https://www.invoicecloud.com/portal/(S(ota5cwfoef3x1xjzv0luz5ys))/2/customerlogin.aspx?billerguid="
    "e8b516ef-cf5f-4ca4-87d8-20d4122076ba"
)


@connectors.add("mesa_consolidated")
class MesaWaterDistrictConnector(BaseVendorConnector):
    vendor_name = "Mesa Consolidated"
    invoice_file_format = FileFormat.PDF.ident  # pylint: disable=no-member
    df_download_url_skip_duplicates = True

    class Selectors:
        LOGIN__USERNAME_TEXTBOX = (By.CSS_SELECTOR, "input[type='text']")
        LOGIN__PASSWORD_TEXTBOX = (By.CSS_SELECTOR, "input[type='password']")
        LOGIN__LOGIN_BUTTON = (
            By.CSS_SELECTOR,
            "#ctl00_ctl00_cphBody_cphBodyLeft_btnLogin",
        )
        LOGIN__ERROR_MESSAGE_TEXT = (By.CSS_SELECTOR, "span#ic-well-message")

        ACCOUNT__NUMBER = (
            By.CSS_SELECTOR,
            "tbody tr td.hidden-xs.icvisible div:nth-child(2)",
        )
        INVOICE_HISTORY_PAGE = (
            By.CSS_SELECTOR,
            "div.summary-title.sso-ic-button-link a",
        )
        BILLING_HISTORY__TABLE = (
            By.CSS_SELECTOR,
            "#ctl00_ctl00_cphBody_cphBodyLeft_Invoices1_dgData2 tbody tr",
        )

        INVOICE_TABLE__DATE = (By.CSS_SELECTOR, "td:nth-child(4)")
        INVOICE_TABLE__TOTAL_AMOUNT = (By.CSS_SELECTOR, "td:nth-child(5)")
        INVOICE_TABLE__PDF = (By.CSS_SELECTOR, "td a.item-first.sso-item-first")

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
        until=EC.visibility_of_element_located(locator=Selectors.INVOICE_HISTORY_PAGE)
    )

    def get_invoice_url(self):
        return self.driver.find_element(
            *self.Selectors.INVOICE_HISTORY_PAGE
        ).get_attribute("href")

    def _iter_customer_number_selections(self, customer_numbers: Optional[List[str]]):
        invoice_types = ["open", "closed"]
        invoice_url = self.get_invoice_url()

        for mode in invoice_types:
            get_url(self.driver, invoice_url.replace("open", mode))

            try:
                wait_for_element(
                    self.driver,
                    value=self.Selectors.ACCOUNT__NUMBER[1],
                    msg="Account Number",
                )
            except WebDriverException as excep:
                LOGGER.info(f"No invoice found {excep}")
                continue

            customer_number = self.driver.find_element(
                *self.Selectors.ACCOUNT__NUMBER
            ).text.split("#")[-1]
            yield customer_number, None

    def _iter_invoice_row_elements(self, start_date: date, end_date: date):

        table_rows = self.driver.find_elements(*self.Selectors.BILLING_HISTORY__TABLE)

        for index, row in enumerate(table_rows):
            invoice_date = self._extract_invoice_date(row)
            if not start_date <= invoice_date <= end_date:
                LOGGER.info(
                    f"Skipping remaining invoices because date '{invoice_date}' is outside requested range"
                )
                break
            yield self.driver.find_elements(*self.Selectors.BILLING_HISTORY__TABLE)[
                index
            ]

    def _construct_downloader(
        self, invoice_row_element, **invoice_fields
    ) -> download.BaseDownloader:
        return download.DriverBasedUrlGetDownloader(
            self.driver,
            download_url=invoice_row_element.find_element(
                *self.Selectors.INVOICE_TABLE__PDF
            ).get_attribute("href"),
            local_filepath=os.path.join(self.download_location, "document.pdf"),
            rename_to=os.path.join(
                self.download_location, invoice_fields["original_filename"]
            ),
            file_exists_check_kwargs=dict(timeout=40),
        )

    def _extract_invoice_date(self, invoice_row_element) -> date:
        return date_from_string(
            invoice_row_element.find_element(*self.Selectors.INVOICE_TABLE__DATE).text,
            "%m/%d/%Y",
        )

    def _extract_customer_number(
        self, invoice_row_element, customer_number, customer_number_element
    ) -> str:
        return customer_number if customer_number else None

    def _extract_invoice_number(self, invoice_row_element, **invoice_fields) -> str:
        return None

    def _extract_total_amount(self, invoice_row_element, **invoice_fields) -> str:
        return invoice_row_element.find_element(
            *self.Selectors.INVOICE_TABLE__TOTAL_AMOUNT
        ).text

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
        return f"{invoice_fields['reference_code']}_{invoice_fields['total_amount']}"

    def _extract_original_filename(self, invoice_row_element, **invoice_fields) -> str:
        reference_code = self._extract_reference_code(
            invoice_row_element, **invoice_fields
        )
        return f"{reference_code}.pdf"
