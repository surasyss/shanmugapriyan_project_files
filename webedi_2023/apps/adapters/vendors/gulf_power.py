import os
from django.conf import settings
from datetime import date
from typing import List, Optional

from apps.adapters.framework.steps.primitives import SequentialSteps
from integrator import LOGGER

from selenium.webdriver import ActionChains
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import (
    TimeoutException,
    WebDriverException,
    ElementClickInterceptedException,
    ElementNotInteractableException,
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
    get_url,
    wait_for_element,
    close_extra_handles,
)
from apps.adapters.framework import download
from apps.runs.models import FileFormat
from spices.datetime_utils import date_from_string
from apps.error_codes import ErrorCode

_LOGIN_URL = "https://www.fpl.com/my-account/login.html?cid=aliasUniversallogin"
_ACCOUNT_PAGE = "https://www.fpl.com/northwest/my-account/account-lander"
_statement_history = "https://www.fpl.com/northwest/my-account/statement-history"


class GulfPowerSubmitLoginPassword:
    """Login"""

    def __init__(
        self,
        username_textbox,
        password_textbox,
        login_button,
        error_message,
        select_region,
        accept_button,
    ):
        self.username_textbox = username_textbox
        self.password_textbox = password_textbox
        self.login_button = login_button
        self.error_message = error_message
        self.select_region = select_region
        self.accept_button = accept_button

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
        if GulfPowerSubmitLoginPassword.validate_error_message_for_msg_list(
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
        if GulfPowerSubmitLoginPassword.validate_error_message_for_msg_list(
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
        if GulfPowerSubmitLoginPassword.validate_error_message_for_msg_list(
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

        try:
            wait_for_element(
                execution_context.driver,
                value=self.select_region[1],
                retry_attempts=1,
                raise_exception=False,
                msg="Select Region",
            )
            execution_context.driver.find_elements_by_css_selector(
                self.select_region[1]
            )[1].click()
            execution_context.driver.find_element_by_css_selector(
                self.accept_button[1]
            ).click()
        except (IndexError, ElementNotInteractableException):
            LOGGER.info("No select region check box")

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
                GulfPowerSubmitLoginPassword.handle_login_errors(
                    error_text, execution_context.job.username
                )

        except webdriver_helper.WEB_DRIVER_EXCEPTIONS:
            # Catching these exceptions for backward compatibility
            LOGGER.info("Login successful")
        finally:
            execution_context.driver.implicitly_wait(
                settings.DRIVER_DEFAULT_IMPLICIT_WAIT
            )


@connectors.add("gulf_power")
class GulfPowerConnector(BaseVendorConnector):
    vendor_name = "Gulf Power"
    invoice_file_format = FileFormat.PDF.ident  # pylint: disable=no-member
    df_download_url_skip_duplicates = True
    restaurant_name = None

    class Selectors:

        LOGIN__USERNAME_TEXTBOX = (By.CSS_SELECTOR, "#emailOrUserId")
        LOGIN__PASSWORD_TEXTBOX = (By.CSS_SELECTOR, "#pwd")
        LOGIN__LOGIN_BUTTON = (By.CSS_SELECTOR, "#loginButton")
        LOGIN__LOGIN_ALERT = (
            By.CSS_SELECTOR,
            "div#conditionalSelectorModal label.v-label.theme--light",
        )
        LOGIN__ACCEPT_BUTTON = (By.CSS_SELECTOR, "#conditionalSelectorLoginBtn")
        LOGIN__ERROR_MESSAGE_TEXT = (
            By.CSS_SELECTOR,
            "#nee-login-form div:nth-child(1) div.flex",
        )

        HOME__ACCOUNT = (
            By.CSS_SELECTOR,
            "div.v-window div div div main div[class^='x-flex']",
        )
        HOME__ACCOUNT_VIEW_BUTTON = (
            By.CSS_SELECTOR,
            "div.v-input--selection-controls__ripple",
        )
        HOME__ACCOUNT_BOXES = (
            By.CSS_SELECTOR,
            "div div.v-card__title.v-card__title.u-px-1",
        )
        HOME__ACCOUNT_NUMBER = (
            By.CSS_SELECTOR,
            "div.flex.font-size-5.sm2.md2.text-sm-center",
        )
        HOME__ACCOUNT_VIEW = (
            By.CSS_SELECTOR,
            "td.map-table-header.text-center.mobile-hide.activity a span",
        )

        INVOICE__TABLE_ROW = (
            By.CSS_SELECTOR,
            "div.v-window div div:nth-child(1) div div div div.layout.row.wrap.align-center.px-5",
        )
        INVOICE__PDF_BUTTON = (
            By.CSS_SELECTOR,
            "div div:nth-child(3) div div.flex.font-size-1.shrink i",
        )
        INVOICE__DATE = (
            By.CSS_SELECTOR,
            "div div:nth-child(2) div div div div.v-list__tile__title",
        )
        INVOICE_TOTAL_AMOUNT = (
            By.CSS_SELECTOR,
            "div div:nth-child(3) div div.flex.grow div div div div.v-list__tile__title",
        )

    # login
    _navigate_to_login_page = NavigateToUrl(_LOGIN_URL, retry_attempts=5)

    _submit_login_info__pre = ExplicitWait(
        until=EC.visibility_of_element_located(
            locator=Selectors.LOGIN__USERNAME_TEXTBOX
        )
    )

    _submit_login_info = GulfPowerSubmitLoginPassword(
        username_textbox=Selectors.LOGIN__USERNAME_TEXTBOX,
        password_textbox=Selectors.LOGIN__PASSWORD_TEXTBOX,
        login_button=Selectors.LOGIN__LOGIN_BUTTON,
        error_message=Selectors.LOGIN__ERROR_MESSAGE_TEXT,
        select_region=Selectors.LOGIN__LOGIN_ALERT,
        accept_button=Selectors.LOGIN__ACCEPT_BUTTON,
    )

    _submit_login_info__post = SequentialSteps(
        [
            NavigateToUrl(_ACCOUNT_PAGE),
            ExplicitWait(
                until=EC.visibility_of_element_located(
                    locator=Selectors.HOME__ACCOUNT_VIEW_BUTTON
                )
            ),
        ]
    )

    def _iter_customer_number_selections(self, customer_numbers: Optional[List[str]]):

        cus_rows = self.driver.find_elements(*self.Selectors.HOME__ACCOUNT_BOXES)
        for index, row in enumerate(cus_rows):
            close_extra_handles(self.driver)

            self.restaurant_name = self.driver.find_elements(
                *self.Selectors.HOME__ACCOUNT_BOXES
            )[index].text.splitlines()[0]
            wait_for_element(
                self.driver,
                value=self.Selectors.HOME__ACCOUNT[1],
                retry_attempts=2,
                raise_exception=False,
                msg="Account",
            )

            try:
                self.driver.find_elements(*self.Selectors.HOME__ACCOUNT_BOXES)[
                    index
                ].click()
            except ElementClickInterceptedException:
                element = self.driver.find_elements(
                    *self.Selectors.HOME__ACCOUNT_BOXES
                )[index]
                ActionChains(self.driver).move_to_element(element).click().perform()

            # find account row elements before every account selection as it becomes stale.
            wait_for_element(
                self.driver,
                value=self.Selectors.HOME__ACCOUNT_NUMBER[1],
                msg="Account Number",
            )
            customer_number = self.driver.find_element(
                *self.Selectors.HOME__ACCOUNT_NUMBER
            ).text[1:]

            get_url(self.driver, _statement_history)
            yield customer_number, None

    def _iter_invoice_row_elements(self, start_date: date, end_date: date):

        wait_for_element(
            self.driver, value=self.Selectors.INVOICE__TABLE_ROW[1], msg="Invoice Row"
        )
        table_rows = self.driver.find_elements(*self.Selectors.INVOICE__TABLE_ROW)

        for index, row in enumerate(table_rows):
            close_extra_handles(self.driver)

            invoice_date = self._extract_invoice_date(row)
            if not start_date <= invoice_date <= end_date:
                LOGGER.info(
                    f"Skipping remaining invoices because date '{invoice_date}' is outside requested range"
                )
                break
            yield self.driver.find_elements(*self.Selectors.INVOICE__TABLE_ROW)[index]
        get_url(self.driver, _ACCOUNT_PAGE)

    def _construct_downloader(
        self, invoice_row_element, **invoice_fields
    ) -> download.BaseDownloader:

        return download.DriverExecuteScriptBasedDownloader(
            self.driver,
            script="arguments[0].click();",
            script_args=(
                invoice_row_element.find_element(*self.Selectors.INVOICE__PDF_BUTTON),
            ),
            local_filepath=os.path.join(self.download_location, "BillStatement.pdf"),
            rename_to=os.path.join(
                self.download_location, invoice_fields["original_filename"]
            ),
            file_exists_check_kwargs=dict(timeout=40),
        )

    def _extract_invoice_date(self, invoice_row_element) -> date:
        return date_from_string(
            invoice_row_element.find_element(*self.Selectors.INVOICE__DATE).text,
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
            *self.Selectors.INVOICE_TOTAL_AMOUNT
        ).text

    def _extract_vendor_name(self, invoice_row_element, **invoice_fields) -> str:
        return self.vendor_name

    def _extract_restaurant_name(self, invoice_row_element, **invoice_fields) -> str:
        return self.restaurant_name

    def _extract_reference_code(self, invoice_row_element, **invoice_fields) -> str:
        customer_number = invoice_fields["customer_number"]
        invoice_date = invoice_fields["invoice_date"]
        return f"{customer_number}_{invoice_date}"

    def _extract_original_download_url(
        self, invoice_row_element, **invoice_fields
    ) -> str:
        return f"{invoice_fields['reference_code']}_{invoice_fields['total_amount']}"

    def _extract_original_filename(self, invoice_row_element, **invoice_fields) -> str:
        reference_code = self._extract_reference_code(
            invoice_row_element, **invoice_fields
        )
        return f"{reference_code}.pdf"
