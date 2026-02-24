import os
from datetime import date
from typing import List, Optional
from integrator import LOGGER

from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException
from selenium.webdriver.support.wait import WebDriverWait

from apps.adapters.framework.context import ExecutionContext
from apps.adapters.framework.registry import connectors
from apps.adapters.framework.operations.vendor import BaseVendorConnector
from apps.adapters.framework.steps.web import (
    NavigateToUrl,
    SubmitLoginPassword,
    ExplicitWait,
    handle_login_errors,
)
from apps.adapters.framework.steps.primitives import SequentialSteps
from apps.adapters.helpers.webdriver_helper import wait_for_element
from apps.adapters.framework import download
from apps.runs.models import FileFormat
from spices.datetime_utils import date_from_string

_LOGIN_URL = "http://cityline.foodorderentry.com/cfm/welcome.cfm"


class HandleMaintenanceAlert:
    def __call__(self, execution_context: ExecutionContext):
        try:
            WebDriverWait(execution_context.driver, 3).until(
                EC.alert_is_present(),
                "Timed out waiting for PA creation " + "confirmation popup to appear.",
            )

            alert = execution_context.driver.switch_to.alert
            LOGGER.info(f"Alert is present with text :  {alert.text}")

            error_text = alert.text and alert.text.strip()

            handle_login_errors(error_text, execution_context.job.username)
        except TimeoutException:
            LOGGER.info(f"No Maintenance Alert present")


@connectors.add("city_line_foodservice")
class CityLineFoodServiceConnector(BaseVendorConnector):
    vendor_name = "City Line Foodservice"
    invoice_file_format = FileFormat.PDF.ident  # pylint: disable=no-member
    df_download_url_skip_duplicates = True
    restaurant_name = None

    class Selectors:

        LOGIN__USERNAME_TEXTBOX = (By.CSS_SELECTOR, "input[type=text]")
        LOGIN__PASSWORD_TEXTBOX = (By.CSS_SELECTOR, "input[type=password]")
        LOGIN__LOGIN_BUTTON = (By.CSS_SELECTOR, "input[type=submit]")
        LOGIN__ERROR_MESSAGE_TEXT = (By.CSS_SELECTOR, "td strong font")

        CUSTOMER__LINK = (By.CSS_SELECTOR, "tr:nth-child(2) td a font")
        CUSTOMER__NAME = (By.CSS_SELECTOR, "p font b u")
        CUSTOMER__NUMBER = (By.CSS_SELECTOR, "tr td font a")

        INVOICE__TABLE_ROW = (By.CSS_SELECTOR, "body p table tbody tr")
        INVOICE_ROW_TYPE = (By.CSS_SELECTOR, "td:nth-child(1) font")
        INVOICE__PDF_LINK_NUMBER = (By.CSS_SELECTOR, "td:nth-child(2) font a")
        INVOICE__DATE = (By.CSS_SELECTOR, "td:nth-child(3) font")
        INVOICE_TOTAL_AMOUNT = (By.CSS_SELECTOR, "td:nth-child(9) font")
        INVOICE__TABLE_PAGE_BUTTON = (
            By.CSS_SELECTOR,
            "tbody tr td:nth-child(5) input[type=submit]",
        )

    # login
    _navigate_to_login_page = NavigateToUrl(_LOGIN_URL, retry_attempts=5)

    _submit_login_info__pre = SequentialSteps(
        [
            HandleMaintenanceAlert(),
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
        until=EC.visibility_of_element_located(locator=Selectors.CUSTOMER__LINK)
    )

    def _iter_customer_number_selections(self, customer_numbers: Optional[List[str]]):

        self.driver.find_element(*self.Selectors.CUSTOMER__LINK).click()

        self.restaurant_name = self.driver.find_element(
            *self.Selectors.CUSTOMER__NAME
        ).text

        customer_number = (
            self.driver.find_element(*self.Selectors.CUSTOMER__NUMBER)
            .get_attribute("href")
            .split("=")[-1]
        )

        yield customer_number, None

    def _iter_invoice_row_elements(self, start_date: date, end_date: date):

        wait_for_element(self.driver, value=self.Selectors.INVOICE__TABLE_ROW[1])
        table_rows = len(self.driver.find_elements(*self.Selectors.INVOICE__TABLE_ROW))
        invoice_lst = list(range(1, table_rows - 1))
        invoice_lst.sort(reverse=True)

        for row in invoice_lst[:-2]:

            if self.driver.find_elements(*self.Selectors.INVOICE__TABLE_PAGE_BUTTON):
                self.driver.find_element(
                    *self.Selectors.INVOICE__TABLE_PAGE_BUTTON
                ).click()

            wait_for_element(self.driver, value=self.Selectors.INVOICE__TABLE_ROW[1])
            _row = self.driver.find_elements(*self.Selectors.INVOICE__TABLE_ROW)[row]

            if _row.text.split(" ")[0] == "INV":
                invoice_date = self._extract_invoice_date(_row)
                if not start_date <= invoice_date <= end_date:
                    LOGGER.info(
                        f"Skipping remaining invoices because date '{invoice_date}' is outside requested range."
                    )
                    break
                yield self.driver.find_elements(*self.Selectors.INVOICE__TABLE_ROW)[row]

    def _construct_downloader(
        self, invoice_row_element, **invoice_fields
    ) -> download.BaseDownloader:

        invoice_row_element.find_element(
            *self.Selectors.INVOICE__PDF_LINK_NUMBER
        ).click()

        return download.DriverExecuteCDPCmdBasedDownloader(
            self.driver,
            cmd="Page.printToPDF",
            cmd_args={"printBackground": True},
            local_filepath=os.path.join(self.download_location, "invoice.pdf"),
            rename_to=os.path.join(
                self.download_location, invoice_fields["original_filename"]
            ),
            file_exists_check_kwargs=dict(timeout=40),
        )

    def _extract_invoice_date(self, invoice_row_element) -> date:
        return date_from_string(
            invoice_row_element.find_element(*self.Selectors.INVOICE__DATE).text,
            "%m/%d/%Y",
        )

    def _extract_customer_number(
        self, invoice_row_element, customer_number, customer_number_element
    ) -> str:
        return customer_number if customer_number else None

    def _extract_invoice_number(self, invoice_row_element, **invoice_fields) -> str:
        return invoice_row_element.find_element(
            *self.Selectors.INVOICE__PDF_LINK_NUMBER
        ).text

    def _extract_total_amount(self, invoice_row_element, **invoice_fields) -> str:
        return invoice_row_element.find_element(
            *self.Selectors.INVOICE_TOTAL_AMOUNT
        ).text

    def _extract_vendor_name(self, invoice_row_element, **invoice_fields) -> str:
        return self.vendor_name

    def _extract_restaurant_name(self, invoice_row_element, **invoice_fields) -> str:
        return self.restaurant_name

    def _extract_reference_code(self, invoice_row_element, **invoice_fields) -> str:
        customer_number = invoice_fields["customer_number"]
        invoice_number = invoice_fields["invoice_number"]
        invoice_date = invoice_fields["invoice_date"]
        return f"{customer_number}_{invoice_number}_{invoice_date}"

    def _extract_original_download_url(
        self, invoice_row_element, **invoice_fields
    ) -> str:
        return f"{invoice_fields['reference_code']}_{invoice_fields['total_amount']}"

    def _extract_original_filename(self, invoice_row_element, **invoice_fields) -> str:
        reference_code = self._extract_reference_code(
            invoice_row_element, **invoice_fields
        )
        return f"{reference_code}.pdf"
