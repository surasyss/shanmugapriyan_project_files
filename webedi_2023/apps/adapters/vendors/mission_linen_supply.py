import os
from datetime import date
from dateutil.relativedelta import relativedelta
from typing import List, Optional

from integrator import LOGGER

from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import NoSuchElementException
from selenium.webdriver.support.ui import Select

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

_LOGIN_URL = "https://myaccount.missionlinen.com/"
_STATEMENT_VIEW_URL = "https://myaccount.missionlinen.com/statement-view"


@connectors.add("mission_linen_supply")
class MissionLinenSupplyConnector(BaseVendorConnector):
    vendor_name = "Mission Linen Supply"
    invoice_file_format = FileFormat.PDF.ident  # pylint: disable=no-member
    df_download_url_skip_duplicates = True
    is_invoice_detail_page = False

    class Selectors:
        LOGIN__USERNAME_TEXTBOX = (
            By.CSS_SELECTOR,
            'input[id="LeftSideBar_LoginView1_Login1_UserName"]',
        )
        LOGIN__PASSWORD_TEXTBOX = (
            By.CSS_SELECTOR,
            'input[id="LeftSideBar_LoginView1_Login1_Password"]',
        )
        LOGIN__LOGIN_BUTTON = (
            By.CSS_SELECTOR,
            'input[id="LeftSideBar_LoginView1_Login1_Login"]',
        )
        LOGIN__ERROR_MESSAGE_TEXT = (By.CSS_SELECTOR, "span.loginfailuremessage")

        HOME__STATEMENT_ROWS = (
            By.CSS_SELECTOR,
            "table.statementtable tbody tr:not(.statementheader)",
        )
        HOME__VIEW_STATEMENT = (By.CSS_SELECTOR, "a#ViewStatement_MenuItem")
        HOME__SELECT_BILLING_PERIOD = (
            By.CSS_SELECTOR,
            "select#Content_MonthYearListDropDown",
        )
        HOME__PREVIOUS_MONTH = (By.CSS_SELECTOR, "a#Content_PreviousMonthLinkButton")

        CUSTOMER_NUMBER = (By.CSS_SELECTOR, "div#Content_accountnumber")
        RESTAURANT_NAME = (By.CSS_SELECTOR, "div#Content_deliveryname")
        INVOICE_NUMBER = (By.CSS_SELECTOR, "div#Content_invoicenumber")
        INVOICE_DATE = (By.CSS_SELECTOR, "div#Content_invoicedate")
        TOTAL_AMOUNT = (By.CSS_SELECTOR, "div#Content_invoicetotal")
        PDF_DOWNLOAD = (By.CSS_SELECTOR, "input#ArchivePageContent_Button1")
        OPEN_INVOICE_BUTTON = (By.CSS_SELECTOR, "input.hideforprint")

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
        until=EC.visibility_of_element_located(locator=Selectors.HOME__VIEW_STATEMENT)
    )

    _step_navigate_to_invoices_list_page__before_account_selection = NavigateToUrl(
        _STATEMENT_VIEW_URL, retry_attempts=3
    )

    def get_table_rows(self):
        wait_for_element(
            self.driver, value=self.Selectors.HOME__STATEMENT_ROWS[1], msg="Table Rows"
        )
        return self.driver.find_elements(*self.Selectors.HOME__STATEMENT_ROWS)[:-1]

    def get_open_invoice_button(self, row):
        return row.find_element(*self.Selectors.OPEN_INVOICE_BUTTON)

    def get_billing_period_dropdown(self):
        return self.driver.find_element(*self.Selectors.HOME__SELECT_BILLING_PERIOD)

    def get_previous_month(self):
        return self.driver.find_element(*self.Selectors.HOME__PREVIOUS_MONTH)

    def _iter_customer_number_selections(self, customer_numbers: Optional[List[str]]):
        select = Select(self.get_billing_period_dropdown())
        values = [option.get_attribute("value") for option in select.options]

        for index, value in enumerate(values):

            if index > 0:
                if self.is_invoice_detail_page:
                    self.driver.back()
                    self.is_invoice_detail_page = False
                self.get_previous_month().click()

            start_date = self._get_start_invoice_date()
            end_date = self._get_end_invoice_date()

            billing_period = date_from_string(value, "%b %Y") + relativedelta(
                months=1, days=-1
            )

            if not start_date <= billing_period <= end_date:
                LOGGER.info(
                    f"Skipping billing period because date '{billing_period}' is outside requested range"
                )
                break

            yield None, None

    @staticmethod
    def get_invoice_date(row):
        invoice_date = row.find_element(By.CSS_SELECTOR, "td:nth-child(2)").text
        return date_from_string(invoice_date, "%m/%d/%Y")

    def _iter_invoice_row_elements(self, start_date: date, end_date: date):

        table_rows = self.get_table_rows()
        for index, _ in enumerate(table_rows):

            if self.is_invoice_detail_page and index > 0:
                self.driver.back()
                self.is_invoice_detail_page = False

            row = self.get_table_rows()[index]
            invoice_date = MissionLinenSupplyConnector.get_invoice_date(row)

            if not start_date <= invoice_date <= end_date:
                LOGGER.info(
                    f"Skipping invoice because date '{invoice_date}' is outside requested range"
                )
                continue

            try:
                self.get_open_invoice_button(row).click()
                self.is_invoice_detail_page = True
            except NoSuchElementException as excep:
                LOGGER.info(excep)
                continue

            yield row

    def _construct_downloader(
        self, invoice_row_element, **invoice_fields
    ) -> BaseDownloader:

        return WebElementClickBasedDownloader(
            element=self.driver.find_element(*self.Selectors.PDF_DOWNLOAD),
            local_filepath=os.path.join(
                self.download_location,
                f"Invoice_{invoice_fields['invoice_number']}.pdf",
            ),
            rename_to=os.path.join(
                self.download_location, invoice_fields["original_filename"]
            ),
            file_exists_check_kwargs=dict(timeout=20),
        )

    def _extract_invoice_date(self, invoice_row_element) -> date:
        return date_from_string(
            self.driver.find_element(*self.Selectors.INVOICE_DATE).text, "%m/%d/%Y"
        )

    def _extract_customer_number(
        self, invoice_row_element, customer_number, customer_number_element
    ) -> str:
        return self.driver.find_element(*self.Selectors.CUSTOMER_NUMBER).text

    def _extract_invoice_number(self, invoice_row_element, **invoice_fields) -> str:
        return self.driver.find_element(*self.Selectors.INVOICE_NUMBER).text

    def _extract_total_amount(self, invoice_row_element, **invoice_fields) -> str:
        return self.driver.find_element(*self.Selectors.TOTAL_AMOUNT).text

    def _extract_vendor_name(self, invoice_row_element, **invoice_fields) -> str:
        return self.vendor_name

    def _extract_restaurant_name(self, invoice_row_element, **invoice_fields) -> str:
        return self.driver.find_element(*self.Selectors.RESTAURANT_NAME).text

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
