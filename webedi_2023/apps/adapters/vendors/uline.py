import json
import os
from datetime import date

from selenium.webdriver.common.by import By
from selenium.webdriver.remote.webdriver import WebDriver
from selenium.webdriver.support import expected_conditions as EC

from apps.adapters.framework import download
from apps.adapters.framework.context import ExecutionContext
from apps.adapters.framework.registry import connectors
from apps.adapters.framework.operations.vendor import BaseVendorConnector
from apps.adapters.framework.steps.primitives import SequentialSteps
from apps.adapters.framework.steps.web import (
    NavigateToUrl,
    SubmitLoginPassword,
    ExplicitWait,
)
from apps.adapters.helpers.helper import sleep
from apps.adapters.helpers.webdriver_helper import (
    wait_for_loaders,
    handle_popup,
    has_invoices,
    take_screenshot,
)
from apps.runs.models import FileFormat
from spices.datetime_utils import date_from_string

from integrator import LOGGER

_INVOICES_URL = "https://www.uline.com/MyAccount/Invoices"
_LOGIN_URL = "https://www.uline.com/Signin/Signin"
_DOWNLOAD_URL = (
    "https://www.uline.com/Shared/DownloadOrEmail/DownloadDocumentAsync?idList="
    "InvoiceNumber:{}|"
    "OrderNumber:{}|"
    "CustomerNumber:{}&documentType=1&"
    "downloadFileName={}"
)


class HandleReLogin:
    """Handle re-login"""

    def __init__(self, username_textbox, password_textbox, login_button, error_message):
        self.username_textbox = username_textbox
        self.password_textbox = password_textbox
        self.login_button = login_button
        self.error_message = error_message

    def __call__(self, execution_context: ExecutionContext):
        driver: WebDriver = execution_context.driver
        for index in range(5):
            take_screenshot(driver, f"{index}_debug.png")
            if self.found_signin_page(driver):
                _submit_login_info = SubmitLoginPassword(
                    username_textbox=self.username_textbox,
                    password_textbox=self.password_textbox,
                    login_button=self.login_button,
                    error_message=self.error_message,
                )
                _submit_login_info(execution_context)

            else:
                LOGGER.info(f"Navigated to {driver.current_url}")
                break

        if self.found_signin_page(driver):
            raise _LoginError("Unable to login even after tried for five attempts.")

    def found_signin_page(self, driver):
        return "signin" in driver.current_url.lower() or driver.find_elements(
            *self.username_textbox
        )


class _LoginError(Exception):
    pass


class HandlePopup:
    """Handle popup"""

    def __init__(self, value, msg):
        self.value = value
        self.msg = msg

    def __call__(self, execution_context: ExecutionContext):
        handle_popup(
            execution_context.driver,
            by_selector=By.CSS_SELECTOR,
            value=self.value,
            msg=self.msg,
            retry_attempts=1,
        )
        sleep(5)


@connectors.add("uline")
class UlineConnector(BaseVendorConnector):
    # uses_proxy = True
    vendor_name = "Uline"
    invoice_file_format = FileFormat.PDF.ident  # pylint: disable=no-member

    class Selectors:
        LOGIN__USERNAME_TEXTBOX = (By.CSS_SELECTOR, "input#txtEmail")
        LOGIN__PASSWORD_TEXTBOX = (By.CSS_SELECTOR, "input#txtPassword")
        LOGIN__LOGIN_BUTTON = (By.CSS_SELECTOR, "input#btnSignIn")
        LOGIN__ERROR_MESSAGE_TEXT = (By.CSS_SELECTOR, "span.messageListWarning")

        INVOICE_TABLE_ROW = (By.CSS_SELECTOR, "div.myInvoices table tbody tr")
        INVOICE_TD_INPUT = (By.CSS_SELECTOR, "td input")
        INVOICE_DATE = (By.CSS_SELECTOR, "td:nth-child(3)")
        INVOICE_TOTAL_AMOUNT = (By.CSS_SELECTOR, "td #lblInvoiceTotal")
        RESTAURANT_NAME = (By.CSS_SELECTOR, "label#CustomerName")
        NO_INVOICE = (By.CSS_SELECTOR, "div#NoInvoices")
        MODAL_CLOSE = "a#modalClose"

    _navigate_to_login_page = NavigateToUrl(_LOGIN_URL, retry_attempts=5)

    _submit_login_info__pre = SequentialSteps(
        [
            HandlePopup(value=Selectors.MODAL_CLOSE, msg="Welcome to Uline"),
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

    _submit_login_info__post = SequentialSteps(
        [
            HandleReLogin(
                username_textbox=Selectors.LOGIN__USERNAME_TEXTBOX,
                password_textbox=Selectors.LOGIN__PASSWORD_TEXTBOX,
                login_button=Selectors.LOGIN__LOGIN_BUTTON,
                error_message=Selectors.LOGIN__ERROR_MESSAGE_TEXT,
            ),
            NavigateToUrl(_INVOICES_URL, retry_attempts=5),
        ]
    )

    def _iter_invoice_row_elements(self, start_date: date, end_date: date):

        if not has_invoices(
            self.driver,
            value=self.Selectors.INVOICE_TABLE_ROW[1],
            retry_attempts=3,
        ):
            no_invoice = self.get_no_invoice_element()
            LOGGER.info(no_invoice.text)
            return

        invoices_data_list = self.get_invoices_data_list(start_date, end_date)
        for invoice_data in invoices_data_list:
            yield invoice_data

    def get_no_invoice_element(self):
        return self.driver.find_element(*self.Selectors.NO_INVOICE)

    def get_table_rows(self):
        return self.driver.find_elements(*self.Selectors.INVOICE_TABLE_ROW)

    def get_restaurant_name_element(self):
        return self.driver.find_element(*self.Selectors.RESTAURANT_NAME)

    @staticmethod
    def get_row_child_element(driver, selector):
        return driver.find_element(*selector)

    def get_invoices_data_list(self, start_date: date, end_date: date):
        invoices_data_list = []

        wait_for_loaders(
            self.driver,
            value=self.Selectors.INVOICE_DATE[1],
            retry_attempts=1,
        )
        restaurant_name = self.get_restaurant_name_element().text
        rows = self.get_table_rows()
        for row in rows:
            td_invoice_date = self.get_row_child_element(
                row, self.Selectors.INVOICE_DATE
            )
            invoice_date = date_from_string(td_invoice_date.text, "%m/%d/%y")

            if not start_date <= invoice_date <= end_date:
                LOGGER.info(
                    f"Skipping invoice because date '{invoice_date}' is outside requested range"
                )
                break

            td_input = self.get_row_child_element(row, self.Selectors.INVOICE_TD_INPUT)
            self.driver.execute_script(
                "arguments[0].setAttribute('type', '')", td_input
            )
            input_value = self.get_row_child_element(
                row, self.Selectors.INVOICE_TD_INPUT
            ).get_attribute("value")
            td_total_amount = self.get_row_child_element(
                row, self.Selectors.INVOICE_TOTAL_AMOUNT
            )

            input_value_json = json.loads(input_value)
            id_json = input_value_json["Id"]

            invoices_data_list.append(
                {
                    "customer_number": id_json["CustomerNumber"],
                    "invoice_number": id_json["InvoiceNumber"],
                    "order_number": id_json["OrderNumber"],
                    "download_file_name": input_value_json["DownloadFileName"],
                    "total_amount": td_total_amount.text,
                    "invoice_date": invoice_date,
                    "restaurant_name": restaurant_name,
                    "download_url": _DOWNLOAD_URL.format(
                        id_json["InvoiceNumber"],
                        id_json["OrderNumber"],
                        id_json["CustomerNumber"],
                        input_value_json["DownloadFileName"],
                    ),
                }
            )

        return invoices_data_list

    def _construct_downloader(
        self, invoice_row_element, **invoice_fields
    ) -> download.BaseDownloader:

        return download.DriverBasedUrlGetDownloader(
            self.driver,
            download_url=invoice_fields["original_download_url"],
            local_filepath=f'{self.download_location}/{invoice_row_element["download_file_name"]}.pdf',
            rename_to=os.path.join(
                self.download_location, invoice_fields["original_filename"]
            ),
            file_exists_check_kwargs=dict(timeout=20),
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
        return invoice_row_element["total_amount"]

    def _extract_vendor_name(self, invoice_row_element, **invoice_fields) -> str:
        return self.vendor_name

    def _extract_restaurant_name(self, invoice_row_element, **invoice_fields) -> str:
        return invoice_row_element["restaurant_name"]

    def _extract_reference_code(self, invoice_row_element, **invoice_fields) -> str:
        customer_number = invoice_fields["customer_number"]
        invoice_number = invoice_fields["invoice_number"]
        invoice_date = invoice_fields["invoice_date"]
        return f"{customer_number}_{invoice_number}_{invoice_date}"

    def _extract_original_download_url(
        self, invoice_row_element, **invoice_fields
    ) -> str:
        return invoice_row_element["download_url"]

    def _extract_original_filename(self, invoice_row_element, **invoice_fields) -> str:
        return f"{invoice_fields['reference_code']}.pdf"
