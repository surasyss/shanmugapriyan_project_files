import os.path
from datetime import date
from typing import List

from apps.adapters.framework.context import ExecutionContext
from apps.adapters.helpers import webdriver_helper
from integrator import LOGGER
from django.conf import settings

from selenium.webdriver.remote.webelement import WebElement
from selenium.webdriver.remote.webdriver import WebDriver
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
    handle_login_errors,
)
from apps.adapters.helpers.webdriver_helper import wait_for_element
from apps.runs.models import FileFormat
from spices.datetime_utils import date_from_string

_LOGIN_URL = "https://www.pinnacol.com/policyholder-sign-in"
_VIEW_INVOICES_URL = "https://policyholder.pinnacol.com/finance/invoices"


class PinnacolSubmitLoginPassword(SubmitLoginPassword):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    @staticmethod
    def _get_element(driver, element) -> WebElement:
        if isinstance(element, WebElement):
            return element
        if isinstance(element, tuple):
            return driver.find_element(*element)
        raise TypeError(f"Unexpected element: {element}")

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

        login_button = PinnacolSubmitLoginPassword._get_element(
            execution_context.driver, self.login_button
        )

        driver.implicitly_wait(5)
        LOGGER.info("Clicking on Next button")
        login_button.click()

        self._get_and_fill_textbox(
            execution_context,
            self.password_textbox,
            "password",
            execution_context.job.password,
            masked_password,
        )

        login_button = PinnacolSubmitLoginPassword._get_element(
            execution_context.driver, self.login_button
        )

        driver.implicitly_wait(5)
        LOGGER.info("Clicking on Login Submit button")
        login_button.click()

        # handling alert if exists
        self.handle_alert_if_exists(driver)

        find_error = ExplicitWait(
            until=EC.visibility_of_element_located(self.error_message)
        )
        try:
            error_message_element = find_error(execution_context)
            if error_message_element:
                error_text = (
                    error_message_element.text and error_message_element.text.strip()
                )
                handle_login_errors(error_text, execution_context.job.username)

        except webdriver_helper.WEB_DRIVER_EXCEPTIONS:
            # Catching these exceptions for backward compatibility
            LOGGER.info("Login successful")
        finally:
            driver.implicitly_wait(settings.DRIVER_DEFAULT_IMPLICIT_WAIT)


@connectors.add("pinnacol_work_comp_insurance")
class PinnacolWorkCompInsuranceConnector(BaseVendorConnector):
    vendor_name = "Pinnacol Work Comp Insurance"
    invoice_file_format = FileFormat.PDF.ident  # pylint: disable=no-member
    df_download_url_skip_duplicates = True

    class Selectors:
        LOGIN__USERNAME_TEXTBOX = (By.CSS_SELECTOR, "input[id='user_email']")
        LOGIN__PASSWORD_TEXTBOX = (By.CSS_SELECTOR, "input[id='user_password']")
        LOGIN__LOGIN_BUTTON = (By.CSS_SELECTOR, "button[type='submit']")
        LOGIN__ERROR_MESSAGE_TEXT = (
            By.CSS_SELECTOR,
            "div.login-card form[id='new_user'] div.email + span.alert",
        )

        CUSTOMER_NUMBER = (
            By.CSS_SELECTOR,
            "span.policy-bar--dashboard-name-link-large span.policy-bar--policy-number",
        )
        RESTAURANT_NAME = (
            By.CSS_SELECTOR,
            "span.policy-bar--dashboard-name-link-large",
        )
        INVOICE_TABLE_ROWS = (By.CSS_SELECTOR, "table[id='invoices-table'] tbody tr")
        INVOICE_NUMBER = (By.CSS_SELECTOR, "td a")
        INVOICE_DATE = (By.CSS_SELECTOR, "td:nth-child(3)")
        TOTAL_AMOUNT = (By.CSS_SELECTOR, "td:nth-child(5)")
        VIEW_LINK = (By.CSS_SELECTOR, "a.view-link")

    # login
    _navigate_to_login_page = NavigateToUrl(_LOGIN_URL, retry_attempts=5)

    _submit_login_info__pre = ExplicitWait(
        until=EC.visibility_of_element_located(
            locator=Selectors.LOGIN__USERNAME_TEXTBOX
        )
    )

    _submit_login_info = PinnacolSubmitLoginPassword(
        username_textbox=Selectors.LOGIN__USERNAME_TEXTBOX,
        password_textbox=Selectors.LOGIN__PASSWORD_TEXTBOX,
        login_button=Selectors.LOGIN__LOGIN_BUTTON,
        error_message=Selectors.LOGIN__ERROR_MESSAGE_TEXT,
    )
    _submit_login_info__post = ExplicitWait(
        until=EC.visibility_of_element_located(locator=Selectors.VIEW_LINK)
    )

    _step_navigate_to_invoices_list_page__before_account_selection = NavigateToUrl(
        _VIEW_INVOICES_URL
    )

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
            element=invoice_row_element.find_element(*self.Selectors.INVOICE_NUMBER),
            local_filepath=os.path.join(
                self.download_location, invoice_fields["original_filename"]
            ),
            rename_to=os.path.join(
                self.download_location, f"{invoice_fields['reference_code']}.pdf"
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
        return (
            self.driver.find_element(*self.Selectors.CUSTOMER_NUMBER)
            .text.split()[1]
            .replace("#", "")
            .replace(")", "")
        )

    def _extract_invoice_number(self, invoice_row_element, **invoice_fields) -> str:
        return invoice_row_element.find_element(*self.Selectors.INVOICE_NUMBER).text

    def _extract_total_amount(self, invoice_row_element, **invoice_fields) -> str:
        return invoice_row_element.find_element(*self.Selectors.TOTAL_AMOUNT).text

    def _extract_vendor_name(self, invoice_row_element, **invoice_fields) -> str:
        return self.vendor_name

    def _extract_restaurant_name(self, invoice_row_element, **invoice_fields) -> str:
        return self.driver.find_element(*self.Selectors.RESTAURANT_NAME).text.split(
            " ("
        )[0]

    def _extract_reference_code(self, invoice_row_element, **invoice_fields) -> str:
        return (
            f"{invoice_fields['customer_number']}"
            f"_{invoice_fields['invoice_number']}"
            f"_{invoice_fields['invoice_date']}"
        )

    def _extract_original_download_url(
        self, invoice_row_element, **invoice_fields
    ) -> str:
        return invoice_row_element.find_element(
            *self.Selectors.INVOICE_NUMBER
        ).get_attribute("href")

    def _extract_original_filename(self, invoice_row_element, **invoice_fields) -> str:
        invoice_date = invoice_fields["invoice_date"].strftime("%m_%d_%Y")
        return f"Pinnacol-Assurance-Invoice-{invoice_fields['invoice_number']}-{invoice_date}.pdf"
