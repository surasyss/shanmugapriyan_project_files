import os
from django.conf import settings
from datetime import date
from typing import List, Optional

from selenium.webdriver.chrome.webdriver import WebDriver
from selenium.webdriver.remote.webelement import WebElement

from apps.adapters.framework.context import ExecutionContext
from apps.adapters.framework.steps.primitives import SequentialSteps
from integrator import LOGGER

from selenium.webdriver.common.by import By
from selenium.common.exceptions import (
    WebDriverException,
    NoSuchElementException,
)
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

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
from apps.adapters.helpers.webdriver_helper import (
    get_url,
    wait_for_element,
    close_extra_handles,
    WEB_DRIVER_EXCEPTIONS,
    handle_popup,
)
from apps.runs.models import FileFormat
from spices.datetime_utils import date_from_string

_LOGIN_URL = "https://www.fpl.com/my-account/login.html"
_ACCOUNTS_URL = (
    "https://www.fpl.com/my-account/multi-dashboard.html#multi-manageAccounts"
)
_BILLING_HISTORY_URL = (
    "https://www.fpl.com/my-account/view-bill.html#BillHistoryViewBill"
)


class FplClickElement:
    def __init__(self, element):
        self.element = element

    def __call__(self, execution_context: ExecutionContext):
        try:
            element = execution_context.driver.find_element(*self.element)
            element.click()
        except NoSuchElementException as excep:
            LOGGER.info(excep)


class LoginErrorCheck:
    def __init__(self, error_locator):
        self.error_locator = error_locator

    def __call__(self, execution_context: ExecutionContext):
        find_error = ExplicitWait(
            until=EC.visibility_of_element_located(self.error_locator)
        )
        try:
            error_message_element = find_error(execution_context)
            if error_message_element:
                error_text = (
                    error_message_element.text and error_message_element.text.strip()
                )
                handle_login_errors(error_text, execution_context.job.username)

        except WEB_DRIVER_EXCEPTIONS:
            LOGGER.info("Login successful")
        finally:
            execution_context.driver.implicitly_wait(15)


@connectors.add("florida_power_and_light")
class FloridaPowerLightConnector(BaseVendorConnector):
    vendor_name = "Florida Power & Light"
    invoice_file_format = FileFormat.PDF.ident  # pylint: disable=no-member
    df_download_url_skip_duplicates = True

    class Selectors:
        LOGIN__USERNAME_TEXTBOX = (By.CSS_SELECTOR, 'input[id="emailOrUserId"]')
        LOGIN__PASSWORD_TEXTBOX = (By.CSS_SELECTOR, 'input[id="pwd"]')
        LOGIN__LOGIN_BUTTON = (By.CSS_SELECTOR, 'button[id="loginButton"]')
        LOGIN__ERROR_MESSAGE_TEXT = (
            By.CSS_SELECTOR,
            "form#nee-login-form div[class*='error--text'][style='']",
        )
        LOGIN__SELECT_REGION = (
            By.CSS_SELECTOR,
            "div#conditionalSelectorModal  div.v-input--radio-group__input div.v-radio",
        )
        LOGIN__REGION_LOGIN_BUTTON = (
            By.CSS_SELECTOR,
            'button[id="conditionalSelectorLoginBtn"]',
        )

        HOME__ACCOUNT_ROWS = (
            By.CSS_SELECTOR,
            "div.accounts-table ul li[id^='core__ModelBase']",
        )
        HOME__ACCOUNT_NUMBER = (
            By.CSS_SELECTOR,
            "div.account-details div.account "
            "div.account-number a.account-number-link",
        )
        HOME__RESTAURANT_NAME = (By.CSS_SELECTOR, "div.account-details div.name p")
        HOME__LOGOUT = "a[id='nav-bar-logout']"

        ACCOUNT__VIEW_BILL = (By.CSS_SELECTOR, "div.account-balance a.view-bill-btn")

        BILLING_HISTORY__TABLE_ROWS = (
            By.CSS_SELECTOR,
            "div.bill-history ul.breakdown-list li.breakdown-item",
        )
        BILLING_HISTORY__INVOICE_DATE = (By.CSS_SELECTOR, "span.item-info span")
        BILLING_HISTORY__TOTAL_AMOUNT = (By.CSS_SELECTOR, "span.item-value span")
        BILLING_HISTORY__INVOICE_DOWNLOAD_ELEMENT = (
            By.CSS_SELECTOR,
            "span.item-info a.download-pdf-link",
        )

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
            FplClickElement(Selectors.LOGIN__SELECT_REGION),
            FplClickElement(Selectors.LOGIN__REGION_LOGIN_BUTTON),
            LoginErrorCheck(error_locator=Selectors.LOGIN__ERROR_MESSAGE_TEXT),
        ]
    )

    def get_account_rows(self):
        """Return all account rows or single account row element."""

        try:
            wait_for_element(
                self.driver,
                value=self.Selectors.HOME__ACCOUNT_ROWS[1],
                msg="Accounts Table Rows",
            )
        except WebDriverException as excep:
            LOGGER.info(f"No accounts found: {excep}")

        customer_row_elems = self.driver.find_elements(
            *self.Selectors.HOME__ACCOUNT_ROWS
        )
        return customer_row_elems

    def check_for_login_error(self):
        """Check for login error messages"""

        try:
            error_message_element = WebDriverWait(self.driver, 20).until(
                EC.presence_of_element_located(self.Selectors.LOGIN__ERROR_MESSAGE_TEXT)
            )
            if error_message_element:
                error_text = (
                    error_message_element.text and error_message_element.text.strip()
                )
                handle_login_errors(error_text, self.run.job.username)

        except WEB_DRIVER_EXCEPTIONS:
            LOGGER.info("Login successful")
        finally:
            self.driver.implicitly_wait(settings.DRIVER_DEFAULT_IMPLICIT_WAIT)

    def relogin(self):
        """Re-login on unsuccessful login attempt"""

        for _ in range(3):
            if self.driver.find_elements(*self.Selectors.LOGIN__USERNAME_TEXTBOX):
                self.perform_login()
                self.check_for_login_error()

            try:
                wait_for_element(
                    self.driver,
                    value=self.Selectors.HOME__LOGOUT,
                    msg="Logout",
                    retry_attempts=3,
                )
                break
            except WebDriverException as excep:
                LOGGER.info(excep)
                continue

    def navigate_to_billing_history(self):
        """Navigate to Billing history Page"""

        for _ in range(5):
            get_url(self.driver, _BILLING_HISTORY_URL)

            if self.driver.find_elements(*self.Selectors.LOGIN__USERNAME_TEXTBOX):
                self.perform_login()
                self.check_for_login_error()

                if (
                    "https://www.fpl.com/my-account/view-bill.html"
                    not in self.driver.current_url
                ):
                    self.navigate_to_accounts_list_page()
                    self.navigate_to_account_summary_page()
                continue

            if not self.driver.find_elements(
                *self.Selectors.BILLING_HISTORY__TABLE_ROWS
            ):
                continue
            break

    def navigate_to_accounts_list_page(self):
        """Navigate to Accounts List Page"""

        for _ in range(5):
            get_url(self.driver, _ACCOUNTS_URL)

            if self.driver.find_elements(*self.Selectors.LOGIN__USERNAME_TEXTBOX):
                self.perform_login()
                self.check_for_login_error()
                continue

            if not self.driver.find_elements(*self.Selectors.HOME__ACCOUNT_ROWS):
                continue

            self.remove_footer_element()
            break

    def remove_footer_element(self):
        """
        Removing footer web-element from the html since it interrupts account selection element
        """

        self.driver.execute_script(
            """
            var elements = document.querySelectorAll("div.hideToShowAccountSettings");
            for (const element of elements) {
                element.parentNode.removeChild(element);
            }"""
        )

    def _iter_customer_number_selections(self, customer_numbers: Optional[List[str]]):

        self.relogin()
        self.navigate_to_accounts_list_page()

        account_numbers = {}

        customer_row_elems = self.get_account_rows()

        for _, account_row in enumerate(customer_row_elems):
            account_number = account_row.find_element(
                *self.Selectors.HOME__ACCOUNT_NUMBER
            ).text
            restaurant_name = account_row.find_element(
                *self.Selectors.HOME__RESTAURANT_NAME
            ).get_attribute("title")

            account_numbers[account_number] = restaurant_name

        for customer_number, restaurant_name in account_numbers.items():
            setattr(self, "restaurant_name", restaurant_name)

            get_url(
                self.driver,
                f"https://www.fpl.com/api/resources/account/{customer_number}/select?view=account-lander",
            )
            yield customer_number, None

    def _iter_invoice_row_elements(self, start_date: date, end_date: date):
        get_url(self.driver, _BILLING_HISTORY_URL)

        try:
            wait_for_element(
                self.driver,
                value=self.Selectors.BILLING_HISTORY__TABLE_ROWS[1],
                msg="Table Rows",
            )
        except WebDriverException as excep:
            LOGGER.info(f"No invoice found: {excep}")

        table_rows = self.driver.find_elements(
            *self.Selectors.BILLING_HISTORY__TABLE_ROWS
        )
        for index, row in enumerate(table_rows):
            if index > 0:
                close_extra_handles(self.driver)

            invoice_date = self._extract_invoice_date(row)
            if not start_date <= invoice_date <= end_date:
                LOGGER.info(
                    f"Skipping remaining invoices because date '{invoice_date}' is outside requested range"
                )
                break

            try:
                row.find_element(
                    *self.Selectors.BILLING_HISTORY__INVOICE_DOWNLOAD_ELEMENT
                )
            except NoSuchElementException:
                LOGGER.info("Pdf not found.")
                continue

            yield row

    def _construct_downloader(
        self, invoice_row_element, **invoice_fields
    ) -> BaseDownloader:

        return FPLWebElementClickBasedDownloader(
            driver=self.driver,
            element=invoice_row_element.find_element(
                *self.Selectors.BILLING_HISTORY__INVOICE_DOWNLOAD_ELEMENT
            ),
            local_filepath=os.path.join(self.download_location, "Document.pdf"),
            rename_to=os.path.join(
                self.download_location, invoice_fields["original_filename"]
            ),
            file_exists_check_kwargs=dict(timeout=20),
        )

    def _extract_invoice_date(self, invoice_row_element) -> date:
        return date_from_string(
            invoice_row_element.find_element(
                *self.Selectors.BILLING_HISTORY__INVOICE_DATE
            ).text,
            "%b %d, %Y",
        )

    def _extract_customer_number(
        self, invoice_row_element, customer_number, customer_number_element
    ) -> str:
        return customer_number if customer_number else None

    def _extract_invoice_number(self, invoice_row_element, **invoice_fields) -> str:
        return None

    def _extract_total_amount(self, invoice_row_element, **invoice_fields) -> str:
        return invoice_row_element.find_element(
            *self.Selectors.BILLING_HISTORY__TOTAL_AMOUNT
        ).text

    def _extract_vendor_name(self, invoice_row_element, **invoice_fields) -> str:
        return self.vendor_name

    def _extract_restaurant_name(self, invoice_row_element, **invoice_fields) -> str:
        return getattr(self, "restaurant_name")

    def _extract_reference_code(self, invoice_row_element, **invoice_fields) -> str:
        customer_number = invoice_fields["customer_number"]
        invoice_date = invoice_fields["invoice_date"]
        return f"{customer_number}_{invoice_date}"

    def _extract_original_download_url(
        self, invoice_row_element, **invoice_fields
    ) -> str:
        return invoice_fields["reference_code"]

    def _extract_original_filename(self, invoice_row_element, **invoice_fields) -> str:
        reference_code = self._extract_reference_code(
            invoice_row_element, **invoice_fields
        )
        return f"{reference_code}.pdf"


class FPLWebElementClickBasedDownloader(WebElementClickBasedDownloader):
    def __init__(self, driver: WebDriver, element: WebElement, **kwargs):
        super().__init__(element, **kwargs)
        self.driver = driver
        self.element = element

    def _perform_download_action(self):
        """Perform the download action using action-chain"""
        ActionChains(self.driver).click(self.element).perform()
        handle_popup(
            self.driver,
            value="div.fplModal a.noThanks",
            msg="FPL eBill Enrollment",
            retry_attempts=1,
        )
