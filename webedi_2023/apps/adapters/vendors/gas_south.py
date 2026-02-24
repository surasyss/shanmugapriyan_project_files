import os
import re
from datetime import date
from typing import List, Optional
from retry.api import retry

from selenium.webdriver.common.by import By
from selenium.common.exceptions import WebDriverException, NoSuchElementException
from selenium.webdriver.support import expected_conditions as EC

from apps.adapters.framework.context import ExecutionContext
from apps.adapters.framework.steps.primitives import SequentialSteps
from integrator import LOGGER
from apps.adapters.framework.registry import connectors
from apps.adapters.framework.operations.vendor import BaseVendorConnector
from apps.adapters.framework.steps.web import (
    NavigateToUrl,
    SubmitLoginPassword,
    ExplicitWait,
)
from apps.adapters.helpers.webdriver_helper import (
    get_url,
    wait_for_element,
    select_dropdown_option_by_value,
    has_invoices,
    wait_for_loaders,
)
from apps.adapters.framework import download
from apps.runs.models import FileFormat
from spices.datetime_utils import date_from_string

_LOGIN_URL = "https://manage.gassouth.com/?_ga=2.242577158.562618239.1641928902-198303624.1641928902"
_ACCOUNT_PAGE_URL = (
    "https://manage.gassouth.com/CMSPages/VCustom/AccountSummary/index.html"
)
_ERROR_URL = "https://manage.gassouth.com/error"


class WaitForLoaders:
    def __init__(self, loader):
        """
        :param loader: locator
        """
        self.loader = loader

    def __call__(self, execution_context: ExecutionContext):
        wait_for_loaders(
            execution_context.driver,
            value=self.loader,
            timeout=10,
        )


@connectors.add("gas_south")
class GasSouthConnector(BaseVendorConnector):
    vendor_name = "Gas South"
    invoice_file_format = FileFormat.PDF.ident  # pylint: disable=no-member
    df_download_url_skip_duplicates = True
    restaurant_name = None

    class Selectors:

        LOGIN__USERNAME_TEXTBOX = (By.CSS_SELECTOR, "input.form-control.iUserName")
        LOGIN__PASSWORD_TEXTBOX = (By.CSS_SELECTOR, "input.iUserPassword.form-control")
        LOGIN__LOGIN_BUTTON = (By.CSS_SELECTOR, "input[type='submit']")
        LOGIN__ERROR_MESSAGE_TEXT = (By.CSS_SELECTOR, "div.alert-box span")

        HOME__MENU_DROPDOWN = (By.CSS_SELECTOR, "button.menudropdown")
        HOME__ACCOUNT_ROWS = (By.CSS_SELECTOR, "#table tbody tr")
        HOME__ACCOUNT_NUMBER = (By.CSS_SELECTOR, "td.account")
        HOME__ACCOUNT_NICK_NAME = (By.CSS_SELECTOR, "td input.datainput")
        HOME__ACCOUNT_VIEW = (By.CSS_SELECTOR, "td.activity a span")
        HOME__RESTAURANT_NAME = (By.CSS_SELECTOR, "span#welcomeText")
        HOME_SIGNUP = (
            By.CSS_SELECTOR,
            "div.header-sign-up, input.form-control.iUserName",
        )

        INVOICE__TABLE_ROW = (By.CSS_SELECTOR, "div.history-table div.Bill")
        INVOICE__PDF_LINK = (By.CSS_SELECTOR, 'span[ng-show="true"] a.link-session')
        INVOICE__DATE = (By.CSS_SELECTOR, "div[class^='col-4']")
        INVOICE_TOTAL_AMOUNT = (By.CSS_SELECTOR, "div[class^='col-3']")
        INVOICE__ADDRESS = (By.CSS_SELECTOR, "div.global-address")
        ACTIVITY_DROPDOWN_SELECT = (By.CSS_SELECTOR, "select#Activity_dropDownList")
        SPINNER = 'div.spinner[style="display:block"]'

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

    _submit_login_info__post = SequentialSteps(
        [
            WaitForLoaders(loader=Selectors.SPINNER),
            ExplicitWait(
                until=EC.visibility_of_element_located(
                    locator=Selectors.HOME__MENU_DROPDOWN
                )
            ),
        ]
    )

    def get_account_rows(self):
        return self.driver.find_elements(*self.Selectors.HOME__ACCOUNT_ROWS)

    def in_login_page(self):
        try:
            self.driver.find_element(*self.Selectors.HOME_SIGNUP)
            return True
        except NoSuchElementException:
            return False

    @retry(WebDriverException, tries=3, delay=1)
    def relogin(self):
        """Re-login on unsuccessful login attempt"""
        if self.driver.current_url == _ERROR_URL or self.in_login_page():
            self.perform_login()

    @retry((WebDriverException, IndexError), tries=3, delay=1)
    def navigate_to_account_by_index(self, index):
        if self.driver.current_url == _ERROR_URL or self.in_login_page():
            self.perform_login()

        wait_for_element(
            self.driver,
            value=self.Selectors.HOME__ACCOUNT_NUMBER[1],
            msg="Account Number",
        )

        row = self.get_account_rows()[index]

        customer_number = row.find_element(*self.Selectors.HOME__ACCOUNT_NUMBER).text

        # click each invoice row
        view = row.find_element(*self.Selectors.HOME__ACCOUNT_VIEW)
        view.click()

        wait_for_element(
            self.driver,
            value=self.Selectors.ACTIVITY_DROPDOWN_SELECT[1],
            msg="Activity DropDownList",
            retry_attempts=3,
        )

        return customer_number

    def has_multiple_accounts(self):
        try:
            wait_for_element(
                self.driver,
                value=self.Selectors.HOME__ACCOUNT_ROWS[1],
                retry_attempts=3,
                msg="Accounts Table",
            )
            return True
        except WebDriverException:
            return False

    def _iter_customer_number_selections(self, customer_numbers: Optional[List[str]]):
        self.relogin()

        if self.has_multiple_accounts():
            restaurant_name = self.driver.find_element(
                *self.Selectors.HOME__RESTAURANT_NAME
            ).text.replace("Welcome Back, ", "")

            setattr(self, "restaurant_name", restaurant_name)

            customer_row_elems = self.get_account_rows()

            for index, row in enumerate(customer_row_elems):

                if index > 0:
                    get_url(self.driver, _ACCOUNT_PAGE_URL)

                customer_number = self.navigate_to_account_by_index(index)

                yield customer_number, None

        else:
            customer_number = self.get_account_number()
            get_url(self.driver, "https://manage.gassouth.com/payments/Paymentdetail")

            wait_for_element(
                self.driver,
                value=self.Selectors.ACTIVITY_DROPDOWN_SELECT[1],
                retry_attempts=3,
                msg="Activity DropDownList",
            )

            yield customer_number, None

    def _iter_invoice_row_elements(self, start_date: date, end_date: date):

        select_dropdown_option_by_value(
            self.driver.find_element(*self.Selectors.ACTIVITY_DROPDOWN_SELECT), "Bill"
        )

        has_invoices(
            self.driver, value=self.Selectors.INVOICE__TABLE_ROW[1], retry_attempts=3
        )

        invoices_list = []

        table_rows = self.driver.find_elements(*self.Selectors.INVOICE__TABLE_ROW)

        for index, row_element in enumerate(table_rows):
            invoice_date = date_from_string(
                row_element.find_element(*self.Selectors.INVOICE__DATE).text, "%m/%d/%Y"
            )
            if not start_date <= invoice_date <= end_date:
                LOGGER.info(
                    f"Skipping remaining invoices because date '{invoice_date}' is outside requested range"
                )
                break

            total_amount = row_element.find_element(
                *self.Selectors.INVOICE_TOTAL_AMOUNT
            ).text

            try:
                download_url = row_element.find_element(
                    *self.Selectors.INVOICE__PDF_LINK
                ).get_attribute("href")

                invoice_data = {
                    "invoice_date": invoice_date,
                    "total_amount": total_amount,
                    "original_download_url": download_url,
                }
                invoices_list.append(invoice_data)
            except NoSuchElementException:
                LOGGER.info("No Documents Found.")
                continue

        for invoice in invoices_list:
            LOGGER.info(f"Invoice data: {invoice}")
            yield invoice

    def _construct_downloader(
        self, invoice_row_element, **invoice_fields
    ) -> download.BaseDownloader:
        return download.DriverBasedUrlGetDownloader(
            self.driver,
            download_url=invoice_fields["original_download_url"],
            local_filepath=os.path.join(self.download_location, "api.pdf"),
            rename_to=os.path.join(
                self.download_location, invoice_fields["original_filename"]
            ),
            file_exists_check_kwargs=dict(timeout=40),
        )

    def _extract_invoice_date(self, invoice_row_element) -> date:
        return invoice_row_element["invoice_date"]

    def get_account_number(self):
        account_number = self.driver.find_element(*self.Selectors.INVOICE__ADDRESS).text
        return re.findall(r"\d+", account_number)[0]

    def _extract_customer_number(
        self, invoice_row_element, customer_number, customer_number_element
    ) -> str:
        return customer_number if customer_number else self.get_account_number()

    def _extract_invoice_number(self, invoice_row_element, **invoice_fields) -> str:
        return None

    def _extract_total_amount(self, invoice_row_element, **invoice_fields) -> str:
        return invoice_row_element["total_amount"]

    def _extract_vendor_name(self, invoice_row_element, **invoice_fields) -> str:
        return self.vendor_name

    def _extract_restaurant_name(self, invoice_row_element, **invoice_fields) -> str:
        return getattr(self, "restaurant_name", None)

    def _extract_reference_code(self, invoice_row_element, **invoice_fields) -> str:
        customer_number = invoice_fields["customer_number"]
        invoice_date = invoice_fields["invoice_date"]
        return f"{customer_number}_{invoice_date}"

    def _extract_original_download_url(
        self, invoice_row_element, **invoice_fields
    ) -> str:
        return invoice_row_element["original_download_url"]

    def _extract_original_filename(self, invoice_row_element, **invoice_fields) -> str:
        reference_code = self._extract_reference_code(
            invoice_row_element, **invoice_fields
        )
        return f"{reference_code}.pdf"
