import os
from django.conf import settings
from datetime import date
from typing import List, Optional
from integrator import LOGGER

from selenium.webdriver import ActionChains
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import (
    TimeoutException,
    WebDriverException,
    NoSuchElementException,
)
from selenium.webdriver.support.wait import WebDriverWait
from spices.services import ContextualError


from apps.adapters.helpers import webdriver_helper
from apps.adapters.framework.context import ExecutionContext
from apps.adapters.framework.steps.constants import (
    DISABLE_ACCOUNT_MESSAGES,
    LOGIN_FAILED_MESSAGES,
    UNDER_MAINTENANCE_MESSAGES,
)
from apps.adapters.framework.registry import connectors
from apps.adapters.framework.operations.vendor import BaseVendorConnector
from apps.adapters.framework.steps.web import (
    NavigateToUrl,
    ExplicitWait,
)
from apps.adapters.helpers.webdriver_helper import (
    wait_for_element,
    get_url,
)
from apps.adapters.framework import download
from apps.runs.models import FileFormat
from spices.datetime_utils import date_from_string
from apps.error_codes import ErrorCode

_LOGIN_URL = "https://apps.vtinfo.com/retailer-portal/login"
_RETAILER_PORTAL_URL = "https://apps.vtinfo.com/retailer-portal"


class UnionBeerDistributorsLogin:
    """Login"""

    def __init__(
        self,
        username_textbox,
        next_button,
        password_textbox,
        login_button,
        error_message,
    ):
        self.username_textbox = username_textbox
        self.next_button = next_button
        self.password_textbox = password_textbox
        self.login_button = login_button
        self.error_message = error_message

    @staticmethod
    def validate_error_message_for_msg_list(error_message, msg_list) -> bool:
        """
        This method validates current error message with existing auth-failed errors.
        If there are some error messages which are not in the list, feel free to update the list of messages.
        """
        for msg in msg_list:
            lower_msg = msg.lower().replace(" ", "")
            lower_error_msg = error_message.lower().replace(" ", "")
            if lower_msg in lower_error_msg or lower_error_msg in lower_msg:
                return True
        return False

    @staticmethod
    def handle_alert_if_exists(driver):
        try:
            WebDriverWait(driver, 3).until(
                EC.alert_is_present(),
                "Timed out waiting for PA creation " + "confirmation popup to appear.",
            )

            alert = driver.switch_to.alert
            LOGGER.info(f"Alert is present with text :  {alert.text}")
            alert.accept()
            LOGGER.info(f"Accepted alert.")
        except (TimeoutException, WebDriverException):
            LOGGER.info(f"No Alert present")

    @staticmethod
    def handle_login_errors(error_text, username):
        LOGGER.warning(f"Login attempt failed with error: {error_text}")
        if UnionBeerDistributorsLogin.validate_error_message_for_msg_list(
            error_text, LOGIN_FAILED_MESSAGES
        ):
            # pylint: disable=no-member
            raise ContextualError(
                code=ErrorCode.AUTHENTICATION_FAILED_WEB.ident,
                message=ErrorCode.AUTHENTICATION_FAILED_WEB.message.format(
                    username=username
                ),
                params={"error_msg": error_text},
            )
        if UnionBeerDistributorsLogin.validate_error_message_for_msg_list(
            error_text, DISABLE_ACCOUNT_MESSAGES
        ):
            # pylint: disable=no-member
            raise ContextualError(
                code=ErrorCode.ACCOUNT_DISABLED_FAILED_WEB.ident,
                message=ErrorCode.ACCOUNT_DISABLED_FAILED_WEB.message.format(
                    username=username
                ),
                params={"error_msg": error_text},
            )
        if UnionBeerDistributorsLogin.validate_error_message_for_msg_list(
            error_text, UNDER_MAINTENANCE_MESSAGES
        ):
            # pylint: disable=no-member
            raise ContextualError(
                code=ErrorCode.WEBSITE_UNDER_MAINTENANCE.ident,
                message=ErrorCode.WEBSITE_UNDER_MAINTENANCE.message,
                params={"error_msg": error_text},
            )
        raise Exception(
            f"Something went wrong while logging in "
            f"for user({username}) "
            f"failed with error :  {error_text}"
        )

    def __call__(self, execution_context: ExecutionContext):
        """Passing values to login field."""
        ExplicitWait(
            until=EC.visibility_of_element_located(locator=self.username_textbox)
        )

        user_name = execution_context.driver.find_element_by_css_selector(
            self.username_textbox[1]
        )
        user_name.clear()

        masked_username = execution_context.job.username[:3] + "x" * (
            len(execution_context.job.username) - 3
        )

        masked_password = execution_context.job.password[:1] + "x" * (
            len(execution_context.job.password) - 1
        )

        user_name.send_keys(execution_context.job.username)

        next_button = execution_context.driver.find_element_by_css_selector(
            self.next_button[1]
        )
        next_button.click()

        password = execution_context.driver.find_element_by_css_selector(
            self.password_textbox[1]
        )
        password.clear()

        password.send_keys(execution_context.job.password)

        LOGGER.info(
            f"Attempting login into {execution_context.driver.current_url} with "
            f"username: {masked_username}, password: {masked_password}"
        )

        login_button = execution_context.driver.find_element_by_css_selector(
            self.login_button[1]
        )
        execution_context.driver.implicitly_wait(5)
        LOGGER.info("Clicking on Login button")
        login_button.click()

        # handling alert if exists
        self.handle_alert_if_exists(execution_context.driver)

        find_error = ExplicitWait(
            until=EC.visibility_of_element_located(self.error_message)
        )
        try:
            error_message_element = find_error(execution_context)
            if error_message_element:
                error_text = (
                    error_message_element.text and error_message_element.text.strip()
                )
                UnionBeerDistributorsLogin.handle_login_errors(
                    error_text, execution_context.job.username
                )

        except webdriver_helper.WEB_DRIVER_EXCEPTIONS:
            # Catching these exceptions for backward compatibility
            LOGGER.info("Login successful")
        finally:
            execution_context.driver.implicitly_wait(
                settings.DRIVER_DEFAULT_IMPLICIT_WAIT
            )


@connectors.add("union_beer_distributors")
class UnionBeerDistributorsConnector(BaseVendorConnector):
    vendor_name = "Union Beer Distributors"
    invoice_file_format = FileFormat.PDF.ident  # pylint: disable=no-member
    df_download_url_skip_duplicates = True

    class Selectors:

        LOGIN__USERNAME_TEXTBOX = (By.CSS_SELECTOR, "#emailInput")
        LOGIN__PASSWORD_TEXTBOX = (By.CSS_SELECTOR, "#passwordInput")
        LOGIN__NEXT_BUTTON = (By.CSS_SELECTOR, "#submissionArea input")
        LOGIN__LOGIN_BUTTON = (By.CSS_SELECTOR, "#submitButton")
        LOGIN__ERROR_MESSAGE_TEXT = (By.CSS_SELECTOR, "#errorText")

        HOME__ACCOUNT_DROP_DOWN_BUTTON = (
            By.CSS_SELECTOR,
            "nav span.ng-star-inserted a",
        )
        HOME__ACCOUNT_DROP_DOWN_CLOSE = (By.CSS_SELECTOR, "#mat-dialog-title-0 button")
        HOME__EACH_ACCOUNT = (By.CSS_SELECTOR, "div.mat-dialog-content mat-nav-list a")

        INVOICE__HISTORY_PAGE = (
            By.CSS_SELECTOR,
            "div.list-group.visible-lg.main-actions a:nth-child(4)",
        )
        INVOICE__HISTORY_DROP_DOWN = (By.CSS_SELECTOR, "div.list-group-mat a")
        INVOICE_NUMBER = (By.CSS_SELECTOR, "td a[ng-if='order.orderId']")
        INVOICE__TABLE_ROW = (
            By.CSS_SELECTOR,
            "md-content md-table-container table tbody tr",
        )
        INVOICE__PDF_LINK = (By.CSS_SELECTOR, "td:nth-child(1) a")
        INVOICE__DATE = (By.CSS_SELECTOR, "td:nth-child(5)")
        INVOICE_TOTAL_AMOUNT = (By.CSS_SELECTOR, "td:nth-child(7)")
        RESTAURANT_NAME = (By.CSS_SELECTOR, "span.ng-star-inserted a.mat-button span")

    # login
    _navigate_to_login_page = NavigateToUrl(_LOGIN_URL, retry_attempts=5)

    _submit_login_info__pre = ExplicitWait(
        until=EC.visibility_of_element_located(
            locator=Selectors.LOGIN__USERNAME_TEXTBOX
        )
    )

    _submit_login_info = UnionBeerDistributorsLogin(
        username_textbox=Selectors.LOGIN__USERNAME_TEXTBOX,
        password_textbox=Selectors.LOGIN__PASSWORD_TEXTBOX,
        next_button=Selectors.LOGIN__NEXT_BUTTON,
        login_button=Selectors.LOGIN__LOGIN_BUTTON,
        error_message=Selectors.LOGIN__ERROR_MESSAGE_TEXT,
    )

    _submit_login_info__post = ExplicitWait(
        until=EC.visibility_of_element_located(
            locator=Selectors.HOME__ACCOUNT_DROP_DOWN_BUTTON
        )
    )

    def _account_drop_down(self):
        """click account drop down."""

        # account drop down element
        wait_for_element(
            self.driver,
            value=self.Selectors.HOME__ACCOUNT_DROP_DOWN_BUTTON[1],
            msg="Account Dropdown",
        )
        actions = ActionChains(self.driver)
        button_element = self.driver.find_element(
            *self.Selectors.HOME__ACCOUNT_DROP_DOWN_BUTTON
        )
        actions.move_to_element(button_element)
        actions.click().perform()

    def _iter_customer_number_selections(self, customer_numbers: Optional[List[str]]):

        self._account_drop_down()

        wait_for_element(
            self.driver,
            value=self.Selectors.HOME__EACH_ACCOUNT[1],
            msg="Switch Retailer Popup",
        )
        total_accounts = self.driver.find_elements(*self.Selectors.HOME__EACH_ACCOUNT)
        self.driver.find_element(*self.Selectors.HOME__ACCOUNT_DROP_DOWN_CLOSE).click()

        for index, _ in enumerate(total_accounts):
            self._account_drop_down()

            # click each account.
            self.driver.find_elements(*self.Selectors.HOME__EACH_ACCOUNT)[index].click()

            wait_for_element(
                self.driver,
                value=self.Selectors.INVOICE__HISTORY_DROP_DOWN[1],
                retry_attempts=2,
                raise_exception=False,
                msg="Invoice History Dropdown",
            )
            self.driver.find_element(*self.Selectors.INVOICE__HISTORY_PAGE).click()
            yield None, None

    def get_restaurant_name(self):
        return self.driver.find_element(*self.Selectors.RESTAURANT_NAME)

    def get_invoices_list(self, start_date: date, end_date: date):
        invoices_data_list = []

        wait_for_element(
            self.driver,
            value=self.Selectors.INVOICE__TABLE_ROW[1],
            msg="Invoice Table Row",
        )

        table_rows = self.driver.find_elements(*self.Selectors.INVOICE__TABLE_ROW)

        for index, row_element in enumerate(table_rows):

            invoice_number = row_element.find_element(
                *self.Selectors.INVOICE_NUMBER
            ).text

            invoice_date_str = row_element.find_element(
                *self.Selectors.INVOICE__DATE
            ).text
            invoice_date = date_from_string(invoice_date_str, "%b %d, %Y")

            try:
                original_download_url = row_element.find_element(
                    *self.Selectors.INVOICE__PDF_LINK
                ).get_attribute("href")
            except NoSuchElementException:
                LOGGER.info("No invoice download link found.")
                continue

            total_amount = row_element.find_element(
                *self.Selectors.INVOICE_TOTAL_AMOUNT
            ).text

            restaurant_name = (
                self.get_restaurant_name().text.replace("arrow_drop_down", "").strip()
            )

            if not start_date <= invoice_date <= end_date:
                LOGGER.info(
                    f"Skipping remaining invoices because date '{invoice_date}' is outside requested range"
                )
                break

            invoices_data_list.append(
                {
                    "customer_number": original_download_url.split("/")[-1][4:],
                    "invoice_number": invoice_number,
                    "invoice_date": invoice_date,
                    "original_download_url": original_download_url,
                    "total_amount": total_amount,
                    "restaurant_name": restaurant_name,
                }
            )
        return invoices_data_list

    def _iter_invoice_row_elements(self, start_date: date, end_date: date):
        invoices_data_list = self.get_invoices_list(start_date, end_date)

        for invoice in invoices_data_list:
            LOGGER.info(f"Invoice data: {invoice}")

            yield invoice

        get_url(self.driver, _RETAILER_PORTAL_URL)

    def _construct_downloader(
        self, invoice_row_element, **invoice_fields
    ) -> download.BaseDownloader:

        _pattern = "Invoice-B_" + invoice_fields["customer_number"] + ".pdf"

        return download.DriverBasedUrlGetDownloader(
            self.driver,
            download_url=invoice_row_element["original_download_url"],
            local_filepath=os.path.join(self.download_location, _pattern),
            rename_to=os.path.join(
                self.download_location, invoice_fields["original_filename"]
            ),
            file_exists_check_kwargs=dict(timeout=40),
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
        return f"{invoice_fields['customer_number']}_{invoice_fields['invoice_number']}_{invoice_fields['invoice_date']}"

    def _extract_original_download_url(
        self, invoice_row_element, **invoice_fields
    ) -> str:
        return invoice_row_element["original_download_url"]

    def _extract_original_filename(self, invoice_row_element, **invoice_fields) -> str:
        return f"{invoice_fields['reference_code']}.pdf"
