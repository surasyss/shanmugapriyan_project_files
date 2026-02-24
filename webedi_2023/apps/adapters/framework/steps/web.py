from django.conf import settings
from selenium.common.exceptions import TimeoutException
from selenium.webdriver.remote.webdriver import WebDriver
from selenium.webdriver.remote.webelement import WebElement
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.wait import WebDriverWait
from spices.services import ContextualError

from apps.adapters import LOGGER
from apps.adapters.framework.context import ExecutionContext
from apps.adapters.framework.steps.constants import (
    DISABLE_ACCOUNT_MESSAGES,
    LOGIN_FAILED_MESSAGES,
    UNDER_MAINTENANCE_MESSAGES,
)
from apps.adapters.helpers import webdriver_helper
from apps.adapters.helpers.webdriver_helper import get_url
from apps.error_codes import ErrorCode


class NavigateToUrl:
    """Navigate to URL"""

    def __init__(self, url: str, retry_attempts: int = 1):
        self.url = url
        self.retry_attempts = retry_attempts

    def __call__(self, execution_context: ExecutionContext):
        get_url(execution_context.driver, self.url, self.retry_attempts)


class NavigateToUrlFromElement:
    """Navigate to URL"""

    def __init__(self, link, retry_attempts: int = 1, url_from_element=None):
        self.link = link
        self.retry_attempts = retry_attempts
        self.url_from_element = url_from_element or (lambda e: e.get_attribute("href"))

    def __call__(self, execution_context: ExecutionContext):
        if isinstance(self.link, str):
            url = self.link
        else:
            element = _get_element(execution_context.driver, self.link)
            url = self.url_from_element(element)

        get_url(execution_context.driver, url, self.retry_attempts)


def _get_element(driver: WebDriver, element) -> WebElement:
    if isinstance(element, WebElement):
        return element
    if isinstance(element, tuple):
        return driver.find_element(*element)
    raise TypeError(f"Unexpected element: {element}")


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


def handle_login_errors(error_text, username):
    LOGGER.warning(f"Login attempt failed with error: {error_text}")
    if validate_error_message_for_msg_list(error_text, LOGIN_FAILED_MESSAGES):
        # pylint: disable=no-member
        raise ContextualError(
            code=ErrorCode.AUTHENTICATION_FAILED_WEB.ident,
            message=ErrorCode.AUTHENTICATION_FAILED_WEB.message.format(
                username=username
            ),
            params={"error_msg": error_text},
        )
    if validate_error_message_for_msg_list(error_text, DISABLE_ACCOUNT_MESSAGES):
        # pylint: disable=no-member
        raise ContextualError(
            code=ErrorCode.ACCOUNT_DISABLED_FAILED_WEB.ident,
            message=ErrorCode.ACCOUNT_DISABLED_FAILED_WEB.message.format(
                username=username
            ),
            params={"error_msg": error_text},
        )
    if validate_error_message_for_msg_list(error_text, UNDER_MAINTENANCE_MESSAGES):
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


class ExplicitWait:
    def __init__(self, until: callable, **wait_kwargs):
        """
        :param until: the expected condition to wait for
        :param wait_timeout: explicit timeout to use
        :param wait_poll_frequency: polling frequency
        :param wait_ignored_exceptions: ignored exceptions
        """
        self.expectation = until
        self.wait_kwargs = wait_kwargs
        self.wait_kwargs.setdefault("timeout", settings.DRIVER_DEFAULT_EXPLICIT_WAIT)

    def __call__(self, execution_context: ExecutionContext):
        return WebDriverWait(execution_context.driver, **self.wait_kwargs).until(
            self.expectation
        )


class ClickElement:
    def __init__(self, element):
        self.element = element

    def __call__(self, execution_context: ExecutionContext):
        element = _get_element(execution_context.driver, self.element)
        element.click()


class ImplicitWait:
    def __init__(self, timeout):
        self.timeout = timeout

    def __call__(self, execution_context: ExecutionContext):
        execution_context.driver.implicitly_wait(self.timeout)


class SubmitLoginPassword:
    def __init__(self, username_textbox, password_textbox, login_button, error_message):
        self.username_textbox = username_textbox
        self.password_textbox = password_textbox
        self.login_button = login_button
        self.error_message = error_message

    @staticmethod
    def _get_and_fill_textbox(
        execution_context,
        element,
        element_name: str,
        element_value: str,
        masked_element_value: str,
    ) -> WebElement:
        textbox = _get_element(execution_context.driver, element)
        textbox.clear()
        LOGGER.info(f"Typing {masked_element_value} in {element_name} textbox.")
        textbox.send_keys(element_value)
        return textbox

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
        except TimeoutException:
            LOGGER.info(f"No Alert present")

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
        self._get_and_fill_textbox(
            execution_context,
            self.password_textbox,
            "password",
            execution_context.job.password,
            masked_password,
        )

        login_button = _get_element(execution_context.driver, self.login_button)

        driver.implicitly_wait(5)
        LOGGER.info("Clicking on Login button")
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
