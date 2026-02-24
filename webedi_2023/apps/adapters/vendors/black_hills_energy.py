import os
from datetime import date
from typing import List, Optional
from integrator import LOGGER

from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC

from apps.adapters.framework.registry import connectors
from apps.adapters.framework.operations.vendor import BaseVendorConnector
from apps.adapters.framework.steps.web import (
    get_url,
    NavigateToUrl,
    SubmitLoginPassword,
    ExplicitWait,
)
from apps.adapters.helpers.webdriver_helper import (
    wait_for_element,
)
from apps.adapters.framework import download
from apps.runs.models import FileFormat
from spices.datetime_utils import date_from_string


_LOGIN_URL = "https://www.blackhillsenergy.com/my-account/#/dashboard"
_BILLING_HISTORY = "https://www.blackhillsenergy.com/my-account/#/billing/history"


@connectors.add("black_hills_energy")
class BlackHillsEnergyConnector(BaseVendorConnector):
    vendor_name = "Black Hills Energy"
    invoice_file_format = FileFormat.PDF.ident  # pylint: disable=no-member
    df_download_url_skip_duplicates = True
    restaurant_name = None
    download_pattern = ""

    class Selectors:
        LOGIN__USERNAME_TEXTBOX = (By.CSS_SELECTOR, "#userNameInput")
        LOGIN__PASSWORD_TEXTBOX = (By.CSS_SELECTOR, "#passwordInput")
        LOGIN__LOGIN_BUTTON = (By.CSS_SELECTOR, "#submitButton")
        LOGIN__ERROR_MESSAGE_TEXT = (By.CSS_SELECTOR, "#errorText")

        RESTAURANT__NAME = (By.CSS_SELECTOR, "app-nav-side-menu div b")
        ACCOUNT__NUMBER = (By.CSS_SELECTOR, "app-nav-side-menu div div div")
        BILLING_HISTORY__TABLE = (By.CSS_SELECTOR, "mat-list mat-list-item")

        INVOICE__PAGE = (By.CSS_SELECTOR, "app-bill-details section div")
        INVOICE_TABLE__DATE = (By.CSS_SELECTOR, "div.section-heading.ng-star-inserted")
        INVOICE_TABLE__TOTAL_AMOUNT = (
            By.CSS_SELECTOR,
            "div.billing--amountdue.text-center",
        )
        INVOICE_TABLE__PDF = (By.CSS_SELECTOR, "div div.button-link-container button")

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
        until=EC.visibility_of_element_located(locator=Selectors.RESTAURANT__NAME)
    )

    def _iter_customer_number_selections(self, customer_numbers: Optional[List[str]]):

        self.restaurant_name = self.driver.find_element(
            *self.Selectors.RESTAURANT__NAME
        ).text
        customer_number = self.driver.find_element(*self.Selectors.ACCOUNT__NUMBER).text
        self.download_pattern = customer_number

        get_url(self.driver, _BILLING_HISTORY)
        yield customer_number, None

    def _iter_invoice_row_elements(self, start_date: date, end_date: date):

        wait_for_element(self.driver, value=self.Selectors.BILLING_HISTORY__TABLE[1])
        table_rows = self.driver.find_elements(*self.Selectors.BILLING_HISTORY__TABLE)

        for index, row in enumerate(table_rows):

            if index > 0:
                get_url(self.driver, _BILLING_HISTORY)

            wait_for_element(
                self.driver, value=self.Selectors.BILLING_HISTORY__TABLE[1]
            )
            self.driver.find_elements(*self.Selectors.BILLING_HISTORY__TABLE)[
                index
            ].click()

            invoice_date = self._extract_invoice_date(
                self.driver.find_element(*self.Selectors.INVOICE__PAGE)
            )
            if not start_date <= invoice_date <= end_date:
                LOGGER.info(
                    f"Skipping remaining invoices because date '{invoice_date}' is outside requested range"
                )
                break
            yield self.driver.find_element(*self.Selectors.INVOICE__PAGE)

    def _construct_downloader(
        self, invoice_row_element, **invoice_fields
    ) -> download.BaseDownloader:
        _pattern = (
            self.download_pattern
            + "_"
            + self.driver.current_url.split("/")[-1]
            + "_Customer_Bill.pdf"
        )
        return download.WebElementClickBasedDownloader(
            element=invoice_row_element.find_element(
                *self.Selectors.INVOICE_TABLE__PDF
            ),
            local_filepath=os.path.join(self.download_location, _pattern),
            rename_to=os.path.join(
                self.download_location, invoice_fields["original_filename"]
            ),
            file_exists_check_kwargs=dict(timeout=40),
        )

    def _extract_invoice_date(self, invoice_row_element) -> date:
        return date_from_string(
            invoice_row_element.find_element(*self.Selectors.INVOICE_TABLE__DATE).text,
            "%B %Y",
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
        return self.restaurant_name

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
