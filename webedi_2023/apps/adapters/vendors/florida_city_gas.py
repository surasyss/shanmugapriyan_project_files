import os
from datetime import date
from typing import List, Optional
from selenium.webdriver.chrome.webdriver import WebDriver

from selenium.webdriver.common.by import By
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
    handle_login_errors,
    ClickElement,
)
from apps.adapters.helpers.webdriver_helper import (
    get_url,
    wait_for_element,
    has_invoices,
    WEB_DRIVER_EXCEPTIONS,
)
from apps.adapters.framework import download
from apps.runs.models import FileFormat
from spices.datetime_utils import date_from_string

from integrator.conf import DRIVER_DEFAULT_IMPLICIT_WAIT

_LOGIN_URL = "https://www.floridacitygas.com/"
_ACCOUNT_PAGE_URL = "https://www.floridacitygas.com/my-account/account-lander"
_STATEMENT_HISTORY_URL = "https://www.floridacitygas.com/my-account/statement-history"


class FloridaGasSubmitLoginPassword(SubmitLoginPassword):
    def __init__(
        self,
        username_textbox,
        password_textbox,
        login_button,
        error_message,
        username_error_message,
    ):
        super().__init__(
            username_textbox, password_textbox, login_button, error_message
        )
        self.username_textbox = username_textbox
        self.password_textbox = password_textbox
        self.login_button = login_button
        self.error_message = error_message
        self.username_error_message = username_error_message

    def click_login_and_check_error(
        self, driver, execution_context, error_locator, partial_url="floridacitygas"
    ):
        login_button = driver.find_element(*self.login_button)

        driver.implicitly_wait(5)
        LOGGER.info("Clicking on continue button")
        login_button.click()

        # handling alert if exists
        self.handle_alert_if_exists(driver)

        find_error = ExplicitWait(until=EC.visibility_of_element_located(error_locator))
        try:
            error_message_element = find_error(execution_context)
            if error_message_element and (partial_url in driver.current_url):
                error_text = (
                    error_message_element.text and error_message_element.text.strip()
                )
                handle_login_errors(error_text, execution_context.job.username)

        except WEB_DRIVER_EXCEPTIONS:
            # Catching these exceptions for backward compatibility
            LOGGER.info("Username login successful")
        finally:
            driver.implicitly_wait(DRIVER_DEFAULT_IMPLICIT_WAIT)

    def __call__(self, execution_context: ExecutionContext):
        driver: WebDriver = execution_context.driver

        masked_username = execution_context.job.username[:3] + "x" * (
            len(execution_context.job.username) - 3
        )
        masked_password = execution_context.job.password[:1] + "x" * (
            len(execution_context.job.password) - 1
        )

        LOGGER.info(
            f"Attempting login into {driver.current_url} with "
            f"username: {masked_username}, password: {masked_password}"
        )
        self._get_and_fill_textbox(
            execution_context,
            self.username_textbox,
            "username",
            execution_context.job.username,
            masked_username,
        )

        self.click_login_and_check_error(
            driver,
            execution_context,
            self.username_error_message,
            partial_url="pre-registration",
        )

        self._get_and_fill_textbox(
            execution_context,
            self.password_textbox,
            "password",
            execution_context.job.password,
            masked_password,
        )

        self.click_login_and_check_error(driver, execution_context, self.error_message)


@connectors.add("florida_city_gas")
class FloridaCityGasConnector(BaseVendorConnector):
    vendor_name = "Florida City Gas"
    invoice_file_format = FileFormat.PDF.ident  # pylint: disable=no-member
    df_download_url_skip_duplicates = True

    class Selectors:

        LOGIN__INITIATE_BUTTON = (By.CSS_SELECTOR, "button#login")
        LOGIN__USERNAME_TEXTBOX = (
            By.CSS_SELECTOR,
            "form#nee-login-form input[type='text']",
        )
        LOGIN__PASSWORD_TEXTBOX = (
            By.CSS_SELECTOR,
            "form#nee-login-form input[type='password']",
        )
        LOGIN__LOGIN_BUTTON = (By.CSS_SELECTOR, "form#nee-login-form button")
        LOGIN_USERNAME_ERROR_MESSAGE_TEXT = (By.CSS_SELECTOR, "h2.text-xs-left")
        LOGIN_PASSWORD_ERROR_MESSAGE_TEXT = (
            By.CSS_SELECTOR,
            "div.font-base.error--text",
        )

        HOME__ACCOUNT_ROWS = (
            By.CSS_SELECTOR,
            "main.v-content div.v-card div.v-card__title",
        )
        HOME__VIEW_BILL = (By.CSS_SELECTOR, "div#btnViewPayBill")

        INVOICE__TABLE_ROW = (By.CSS_SELECTOR, "table.DocumentList tr.DataRow")
        INVOICE__ACCOUNT_NUMBER = (By.CSS_SELECTOR, "td.AccountColumn")
        INVOICE__RESTAURANT_NAME = (By.CSS_SELECTOR, "td.NameColumn")
        INVOICE__DATE = (By.CSS_SELECTOR, "td.BillDateColumn")
        INVOICE_TOTAL_AMOUNT = (By.CSS_SELECTOR, "td.AmountColumn")
        INVOICE__PDF_DOWNLOAD_URL = (By.CSS_SELECTOR, "td.ViewColumn a")

    # login
    _navigate_to_login_page = NavigateToUrl(_LOGIN_URL, retry_attempts=5)

    _submit_login_info__pre = SequentialSteps(
        [
            ClickElement(Selectors.LOGIN__INITIATE_BUTTON),
            ExplicitWait(
                until=EC.visibility_of_element_located(
                    locator=Selectors.LOGIN__USERNAME_TEXTBOX
                )
            ),
        ]
    )

    _submit_login_info = FloridaGasSubmitLoginPassword(
        username_textbox=Selectors.LOGIN__USERNAME_TEXTBOX,
        password_textbox=Selectors.LOGIN__PASSWORD_TEXTBOX,
        login_button=Selectors.LOGIN__LOGIN_BUTTON,
        error_message=Selectors.LOGIN_PASSWORD_ERROR_MESSAGE_TEXT,
        username_error_message=Selectors.LOGIN_USERNAME_ERROR_MESSAGE_TEXT,
    )

    _submit_login_info__post = ExplicitWait(
        until=EC.visibility_of_element_located(locator=Selectors.HOME__VIEW_BILL)
    )

    _step_navigate_to_invoices_list_page__before_account_selection = NavigateToUrl(
        _ACCOUNT_PAGE_URL
    )
    _step_navigate_to_invoices_list_page__after_account_selection = NavigateToUrl(
        _STATEMENT_HISTORY_URL
    )

    def _iter_customer_number_selections(self, customer_numbers: Optional[List[str]]):

        account_row_elems = self.driver.find_elements(
            *self.Selectors.HOME__ACCOUNT_ROWS
        )

        for index, account in enumerate(account_row_elems):

            if index > 0:
                get_url(self.driver, _ACCOUNT_PAGE_URL)

            wait_for_element(
                self.driver,
                value=self.Selectors.HOME__ACCOUNT_ROWS[1],
                msg="Account Row",
            )

            account_row = self.driver.find_elements(*self.Selectors.HOME__ACCOUNT_ROWS)[
                index
            ]
            LOGGER.info(f"Selected account: {account_row.text}")

            account_row.click()

            yield None, None

    def _iter_invoice_row_elements(self, start_date: date, end_date: date):

        has_invoices(
            self.driver, value=self.Selectors.INVOICE__TABLE_ROW[1], retry_attempts=3
        )

        table_rows = self.driver.find_elements(*self.Selectors.INVOICE__TABLE_ROW)

        for index, row_element in enumerate(table_rows):

            invoice_date = self._extract_invoice_date(row_element)

            if not start_date <= invoice_date <= end_date:
                LOGGER.info(
                    f"Skipping remaining invoices because date '{invoice_date}' is outside requested range"
                )
                break

            yield row_element

    def _construct_downloader(
        self, invoice_row_element, **invoice_fields
    ) -> download.BaseDownloader:
        return download.WebElementClickBasedDownloader(
            element=invoice_row_element.find_element(
                *self.Selectors.INVOICE__PDF_DOWNLOAD_URL
            ),
            local_filepath=os.path.join(self.download_location, "document.pdf"),
            rename_to=os.path.join(
                self.download_location, invoice_fields["original_filename"]
            ),
            file_exists_check_kwargs=dict(timeout=30),
        )

    def _extract_invoice_date(self, invoice_row_element) -> date:
        return date_from_string(
            invoice_row_element.find_element(
                *self.Selectors.INVOICE__DATE
            ).get_attribute("textContent"),
            "%Y-%m-%d",
        )

    def _extract_customer_number(
        self, invoice_row_element, customer_number, customer_number_element
    ) -> str:
        return invoice_row_element.find_element(
            *self.Selectors.INVOICE__ACCOUNT_NUMBER
        ).get_attribute("textContent")

    def _extract_invoice_number(self, invoice_row_element, **invoice_fields) -> str:
        return None

    def _extract_total_amount(self, invoice_row_element, **invoice_fields) -> str:
        return invoice_row_element.find_element(
            *self.Selectors.INVOICE_TOTAL_AMOUNT
        ).text

    def _extract_vendor_name(self, invoice_row_element, **invoice_fields) -> str:
        return self.vendor_name

    def _extract_restaurant_name(self, invoice_row_element, **invoice_fields) -> str:
        return invoice_row_element.find_element(
            *self.Selectors.INVOICE__RESTAURANT_NAME
        ).get_attribute("textContent")

    def _extract_reference_code(self, invoice_row_element, **invoice_fields) -> str:
        customer_number = invoice_fields["customer_number"]
        invoice_date = invoice_fields["invoice_date"]
        total_amount = invoice_fields["total_amount"].replace(",", "").replace(".", "")

        return f"{customer_number}_{invoice_date}_{total_amount}"

    def _extract_original_download_url(
        self, invoice_row_element, **invoice_fields
    ) -> str:
        return invoice_row_element.find_element(
            *self.Selectors.INVOICE__PDF_DOWNLOAD_URL
        ).get_attribute("href")

    def _extract_original_filename(self, invoice_row_element, **invoice_fields) -> str:
        reference_code = self._extract_reference_code(
            invoice_row_element, **invoice_fields
        )
        return f"{reference_code}.pdf"
