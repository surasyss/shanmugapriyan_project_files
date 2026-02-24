import os.path
from datetime import date
from typing import List, Optional

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
)
from apps.adapters.helpers.webdriver_helper import (
    wait_for_element,
    handle_popup,
    hover_over_element,
)
from apps.runs.models import FileFormat
from spices.datetime_utils import date_from_string

_LOGIN_URL = "https://myaccount.ranchowater.com/"


class HandlePopup:
    """Handle popup"""

    def __init__(self, msg: str):
        self.msg = msg

    def __call__(self, execution_context: ExecutionContext):
        handle_popup(
            execution_context.driver,
            by_selector=By.CSS_SELECTOR,
            value="div.dx-popup-draggable div.dx-closebutton i",
            msg=self.msg,
            retry_attempts=1,
        )


@connectors.add("rancho_california_water")
class RanchoCaliforniaWaterConnector(BaseVendorConnector):
    vendor_name = "Rancho California Water"
    invoice_file_format = FileFormat.PDF.ident  # pylint: disable=no-member
    df_download_url_skip_duplicates = True
    # uses_proxy = True

    class Selectors:
        LOGIN__USERNAME_TEXTBOX = (
            By.CSS_SELECTOR,
            "input[id='ContentPlaceHolder1_txtUsername_I']",
        )
        LOGIN__PASSWORD_TEXTBOX = (
            By.CSS_SELECTOR,
            "input[id='ContentPlaceHolder1_txtPassword_I']",
        )
        LOGIN__LOGIN_BUTTON = (
            By.CSS_SELECTOR,
            "div[id='ContentPlaceHolder1_btnSignIn'] div",
        )
        LOGIN__ERROR_MESSAGE_TEXT = (
            By.CSS_SELECTOR,
            "span[id='ContentPlaceHolder1_lblError']",
        )

        ACCOUNT_DROPDOWN = (
            By.CSS_SELECTOR,
            "table#ContentPlaceHolder1_accountselect_ddAccount",
        )
        ACCOUNT_DROPDOWN_OPTIONS = (
            By.CSS_SELECTOR,
            "table#ContentPlaceHolder1_accountselect_ddAccount_DDD_L_LBT tr.dxeListBoxItemRow",
        )

        RESTAURANT_NAME = (By.CSS_SELECTOR, "span#ContentPlaceHolder1_lblServiceName")
        INVOICE_TABLE_ROWS = (
            By.CSS_SELECTOR,
            "div[id='historyGrid'] div.dx-datagrid-rowsview table tbody tr",
        )
        INVOICE_DATE = (By.CSS_SELECTOR, "td")
        TOTAL_AMOUNT = (By.CSS_SELECTOR, "td:nth-child(3)")
        VIEW_BILL = (By.CSS_SELECTOR, "td:nth-child(2) a")

    # login
    _navigate_to_login_page = NavigateToUrl(_LOGIN_URL, retry_attempts=5)
    _navigate_to_login_page__post = HandlePopup("Water Supply Warning")

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
    _submit_login_info__post = SequentialSteps(
        [
            HandlePopup("Important Question about Leak Alerts"),
            ExplicitWait(
                until=EC.visibility_of_element_located(
                    locator=Selectors.ACCOUNT_DROPDOWN
                )
            ),
        ]
    )

    def get_account_dropdown(self):
        return self.driver.find_element(*self.Selectors.ACCOUNT_DROPDOWN)

    def get_account_dropdown_options(self):

        account_dropdown = self.get_account_dropdown()
        hover_over_element(self.driver, account_dropdown)
        account_dropdown.click()

        wait_for_element(
            self.driver,
            value=self.Selectors.ACCOUNT_DROPDOWN_OPTIONS[1],
            retry_attempts=3,
            msg="Account Dropdown Options",
        )

        return self.driver.find_elements(*self.Selectors.ACCOUNT_DROPDOWN_OPTIONS)

    def _iter_customer_number_selections(self, customer_numbers: Optional[List[str]]):

        customer_num_elems = self.get_account_dropdown_options()
        for index, customer_number_elem in enumerate(customer_num_elems):

            if index > 0:
                customer_number_elem = self.get_account_dropdown_options()[index]

            customer_number = customer_number_elem.text
            customer_number_elem.click()
            yield customer_number, None

    def get_invoice_table_rows(self) -> List[WebElement]:
        wait_for_element(
            self.driver,
            value=self.Selectors.INVOICE_TABLE_ROWS[1],
            retry_attempts=3,
            msg="Invoice Table Rows",
        )
        return self.driver.find_elements(*self.Selectors.INVOICE_TABLE_ROWS)

    def _iter_invoice_row_elements(self, start_date: date, end_date: date):
        invoice_row_elements = self.get_invoice_table_rows()

        for index, invoice_row_element in enumerate(invoice_row_elements):

            if not invoice_row_element.find_elements(*self.Selectors.VIEW_BILL):
                continue

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
            element=invoice_row_element.find_element(*self.Selectors.VIEW_BILL),
            local_filepath=os.path.join(
                self.download_location, invoice_fields["original_filename"]
            ),
            file_exists_check_kwargs=dict(timeout=30),
        )

    def _extract_invoice_date(self, invoice_row_element) -> date:
        return date_from_string(
            invoice_row_element.find_element(*self.Selectors.INVOICE_DATE).text,
            "%m/%d/%Y",
        )

    def _extract_customer_number(
        self, invoice_row_element, customer_number, customer_number_element
    ) -> str:
        return customer_number

    def _extract_invoice_number(self, invoice_row_element, **invoice_fields) -> str:
        return None

    def _extract_total_amount(self, invoice_row_element, **invoice_fields) -> str:
        return invoice_row_element.find_element(*self.Selectors.TOTAL_AMOUNT).text

    def _extract_vendor_name(self, invoice_row_element, **invoice_fields) -> str:
        return self.vendor_name

    def _extract_restaurant_name(self, invoice_row_element, **invoice_fields) -> str:
        return self.driver.find_element(*self.Selectors.RESTAURANT_NAME).text

    def _extract_reference_code(self, invoice_row_element, **invoice_fields) -> str:
        return f"{invoice_fields['customer_number']}_{invoice_fields['invoice_date']}"

    def _extract_original_download_url(
        self, invoice_row_element, **invoice_fields
    ) -> str:
        return invoice_fields["reference_code"]

    def _extract_original_filename(self, invoice_row_element, **invoice_fields) -> str:
        return f"{invoice_fields['reference_code']}T00_00_00_bill.pdf"
