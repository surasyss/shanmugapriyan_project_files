import os
import re
from datetime import date
from typing import Optional, List

from apps.adapters.framework.context import ExecutionContext
from apps.adapters.framework.steps.primitives import SequentialSteps
from integrator import LOGGER

from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import NoSuchElementException

from apps.adapters.framework.download import (
    BaseDownloader,
    DriverExecuteScriptBasedDownloader,
)
from apps.adapters.framework.registry import connectors
from apps.adapters.framework.operations.vendor import BaseVendorConnector
from apps.adapters.framework.steps.web import (
    NavigateToUrl,
    SubmitLoginPassword,
    ExplicitWait,
    handle_login_errors,
)
from apps.adapters.helpers.webdriver_helper import (
    WEB_DRIVER_EXCEPTIONS,
    handle_popup,
    wait_for_element,
    wait_for_loaders,
)
from apps.runs.models import FileFormat
from spices.datetime_utils import date_from_string

_LOGIN_URL = "https://customerportal.sandiego.gov/portal/default.aspx"
_BILLING_HISTORY = "https://customerportal.sandiego.gov/Portal/BillingHistory.aspx"


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


class HandleMaintenancePage:

    MAINTENANCE_MESSAGE_TEXT = "div#divsitestatus"

    def __call__(self, execution_context: ExecutionContext):
        try:
            wait_for_element(
                execution_context.driver,
                value=self.MAINTENANCE_MESSAGE_TEXT,
                msg="Maintenance msg",
                retry_attempts=1,
                raise_exception=False,
            )
            error_message_element = (
                execution_context.driver.find_element_by_css_selector(
                    self.MAINTENANCE_MESSAGE_TEXT
                )
            )
            if error_message_element:
                error_text = (
                    error_message_element.text and error_message_element.text.strip()
                )
                handle_login_errors(error_text, execution_context.job.username)
        except WEB_DRIVER_EXCEPTIONS:
            LOGGER.info("No maintenance page found.")


@connectors.add("the_city_of_san_diego_water")
class TheCityOfSanDiegoWaterConnector(BaseVendorConnector):
    vendor_name = "The City of San Diego - Water"
    invoice_file_format = FileFormat.PDF.ident  # pylint: disable=no-member
    df_download_url_skip_duplicates = True

    class Selectors:
        LOGIN__USERNAME_TEXTBOX = (By.CSS_SELECTOR, 'input[id="txtLogin"]')
        LOGIN__PASSWORD_TEXTBOX = (By.CSS_SELECTOR, 'input[id="txtpwd"]')
        LOGIN__LOGIN_BUTTON = (By.CSS_SELECTOR, 'input[id="btnlogin"]')
        LOGIN__ERROR_MESSAGE_TEXT = (
            By.CSS_SELECTOR,
            "div.toast-error div.toast-message",
        )

        BILLING_HISTORY__ACCOUNTS_DROPDOWN = (By.CSS_SELECTOR, "button#dLabel")
        BILLING_HISTORY__TABLE_ROWS = (
            By.CSS_SELECTOR,
            "table#tblBillingHistory tbody tr",
        )
        BILLING_HISTORY__ACCOUNT_DD_CONTAINER = (By.CSS_SELECTOR, "li#AddressInfo")
        BILLING_HISTORY__ACCOUNTS_LIST = (By.CSS_SELECTOR, "ul#UlddlAddress li")
        BILLING_HISTORY__RESTAURANT_NAME = (By.CSS_SELECTOR, "span#lblCustName")
        BILLING_HISTORY__INVOICE_DATE = (By.CSS_SELECTOR, "td")
        BILLING_HISTORY__TOTAL_AMOUNT = (
            By.CSS_SELECTOR,
            "td[id^='tbltdBillingHistoryAmount']",
        )
        BILLING_HISTORY__ORIGINAL_DOWNLOAD_URL = (By.CSS_SELECTOR, "td:nth-child(3) a")

    # login
    _navigate_to_login_page = NavigateToUrl(_LOGIN_URL, retry_attempts=5)
    _navigate_to_login_page__post = SequentialSteps(
        [
            HandlePopup(value="div.modal.in button.close", msg="Production Upgrade"),
            HandleMaintenancePage(),
        ]
    )

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
        until=EC.visibility_of_element_located(
            locator=Selectors.BILLING_HISTORY__RESTAURANT_NAME
        )
    )

    _step_navigate_to_invoices_list_page__before_account_selection = NavigateToUrl(
        url=_BILLING_HISTORY
    )

    def get_invoice_table_rows(self):
        return self.driver.find_elements(*self.Selectors.BILLING_HISTORY__TABLE_ROWS)

    def get_account_dropdown(self):
        wait_for_element(
            self.driver, value="button#dLabel", retry_attempts=3, msg="Account dropdown"
        )
        return self.driver.find_element(
            *self.Selectors.BILLING_HISTORY__ACCOUNTS_DROPDOWN
        )

    def get_dd_container(self):
        return self.driver.find_element(
            *self.Selectors.BILLING_HISTORY__ACCOUNT_DD_CONTAINER
        )

    def get_accounts_list(self):
        return self.driver.find_elements(*self.Selectors.BILLING_HISTORY__ACCOUNTS_LIST)

    def get_dropdown_option(self, customer_number):
        return self.driver.find_element(
            By.CSS_SELECTOR, f'ul#UlddlAddress li[accountnumber="{customer_number}"] a'
        )

    def get_restaurant_name(self):
        return self.driver.find_element(
            *self.Selectors.BILLING_HISTORY__RESTAURANT_NAME
        )

    def _iter_customer_number_selections(self, customer_numbers: Optional[List[str]]):
        dd_container = self.get_dd_container()
        if "block" not in dd_container.get_attribute("style"):
            self.driver.execute_script(
                "arguments[0].style.display='block';", dd_container
            )

        self.get_account_dropdown().click()

        accounts_li = self.get_accounts_list()
        customer_numbers = [li.get_attribute("accountnumber") for li in accounts_li]

        for index, customer_number in enumerate(customer_numbers):
            if index > 0:
                self.get_account_dropdown().click()

            dd_li = self.get_dropdown_option(customer_number)
            LOGGER.info(f"Selected account: {dd_li.text}")

            dd_li.click()

            wait_for_loaders(self.driver, value="div#page_loader div.spinner")
            yield customer_number, None

    def get_invoices_data_list(self, start_date: date, end_date: date):
        invoices_list = []

        restaurant_name = self.get_restaurant_name().text

        table_rows = self.get_invoice_table_rows()
        for index, row_element in enumerate(table_rows):

            try:
                inv_download_element = row_element.find_element(
                    *self.Selectors.BILLING_HISTORY__ORIGINAL_DOWNLOAD_URL
                )
            except NoSuchElementException as excep:
                LOGGER.info(f"No invoice found in the table row {index} - {excep}")
                continue

            invoice_date_str = row_element.find_element(
                *self.Selectors.BILLING_HISTORY__INVOICE_DATE
            ).text
            invoice_date = date_from_string(invoice_date_str, "%m/%d/%y")

            total_amount = row_element.find_element(
                *self.Selectors.BILLING_HISTORY__TOTAL_AMOUNT
            ).text

            if not start_date <= invoice_date <= end_date:
                LOGGER.info(
                    f"Skipping remaining invoices because date '{invoice_date}' is outside requested range"
                )
                break

            invoice_data = {
                "invoice_date": invoice_date,
                "total_amount": total_amount,
                "original_download_url": inv_download_element.get_attribute("onclick"),
                "restaurant_name": restaurant_name,
            }

            LOGGER.info(f"Invoice data: {invoice_data}")
            invoices_list.append(invoice_data)

        return invoices_list

    def _iter_invoice_row_elements(self, start_date: date, end_date: date):

        invoices_list = self.get_invoices_data_list(start_date, end_date)

        for invoice in invoices_list:
            yield invoice

    def _construct_downloader(
        self, invoice_row_element, **invoice_fields
    ) -> BaseDownloader:
        return DriverExecuteScriptBasedDownloader(
            driver=self.driver,
            script=invoice_fields["original_download_url"],
            local_filepath=self.download_location,
            rename_to=os.path.join(
                self.download_location, invoice_fields["original_filename"]
            ),
            file_exists_check_kwargs=dict(timeout=20, pattern=r"^Invoice_EXT\d+\.pdf$"),
        )

    def _extract_invoice_date(self, invoice_row_element) -> date:
        return invoice_row_element["invoice_date"]

    def _extract_customer_number(
        self, invoice_row_element, customer_number, customer_number_element
    ) -> str:
        return customer_number

    def _extract_invoice_number(self, invoice_row_element, **invoice_fields) -> str:
        return None

    def _extract_total_amount(self, invoice_row_element, **invoice_fields) -> str:
        return invoice_row_element["total_amount"]

    def _extract_vendor_name(self, invoice_row_element, **invoice_fields) -> str:
        return self.vendor_name

    def _extract_restaurant_name(self, invoice_row_element, **invoice_fields) -> str:
        return invoice_row_element["restaurant_name"]

    def _extract_reference_code(self, invoice_row_element, **invoice_fields) -> str:
        customer_number = invoice_fields["customer_number"]
        invoice_date = invoice_fields["invoice_date"]
        total_amount = re.sub(r"[^\d]", "", invoice_fields["total_amount"])
        return f"{customer_number}_{invoice_date}_{total_amount}"

    def _extract_original_download_url(
        self, invoice_row_element, **invoice_fields
    ) -> str:
        return invoice_row_element["original_download_url"]

    def _extract_original_filename(self, invoice_row_element, **invoice_fields) -> str:
        return f"{invoice_fields['reference_code']}.pdf"
