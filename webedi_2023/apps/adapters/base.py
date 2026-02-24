"""Runner Interface"""

import abc
from datetime import date, timedelta
from spices import datetime_utils
from typing import List

from django.conf import settings
from selenium.webdriver.ie.webdriver import WebDriver
from selenium.webdriver.remote.webelement import WebElement

from apps.adapters.framework.steps.web import handle_login_errors
from apps.adapters.helpers.webdriver_helper import (
    DriverFactory,
    WEB_DRIVER_EXCEPTIONS,
    wait_for_element,
)
from apps.adapters.vendors import LOGGER
from apps.runs.models import Run, DiscoveredFile, CheckRun, VendorPayment

TEMP_DOWNLOAD_DIR = settings.TEMP_DOWNLOAD_DIR


class VendorDocumentDownloadInterface(abc.ABC):
    """
    Runner Interface will ensure the implementation of the following methods
    Whenever any new 3rd party website is added then it need to implement the following methods
    """

    is_angular = False
    uses_proxy = False

    def __init__(self, run: Run):
        self.run = run
        self.download_location = f"{TEMP_DOWNLOAD_DIR}/runs/{self.run.id}"
        self.driver = DriverFactory.new(
            download_location=self.download_location,
            is_angular=self.is_angular,
            uses_proxy=run.job.connector.get_custom_properties.get(
                "vpn_required", False
            ),
        )

    @abc.abstractmethod
    def start_documents_download_flow(self, run: Run) -> List[DiscoveredFile]:
        """
        Need to implement this Abstract method with the steps to download documents
        :param run: Run model instance containing execution parameters
        :return: list of files discovered during the run
        """
        pass

    @abc.abstractmethod
    def login_flow(self, run: Run) -> bool:
        """
        Need to implement this Abstract method with the steps to check login credentials
        :param run: Run model instance containing execution parameters
        :return: True/False based on success or failure
        """
        pass

    def _quit_driver(self):
        LOGGER.info("Closing all instances of the browser")
        self.driver.quit()

    def start_payment_flow(self, run: Run) -> List[VendorPayment]:
        """
        Need to implement this Abstract method with the steps to do a payment
        :param run: Run model instance containing execution parameters
        :return: payment status
        """
        pass


class AccountingPaymentUpdateInterface(abc.ABC):
    """
    Runner Interface will ensure the implementation of the following methods
    Whenever any new 3rd party website is added then it need to implement the following methods
    """

    create_driver = True

    def __init__(self, run: Run, is_angular: bool = False):
        self.run = run

        self.driver = None
        if self.create_driver:
            self.driver = DriverFactory.new(download_location="", is_angular=is_angular)

    @abc.abstractmethod
    def start_payment_update_flow(self, run: Run) -> List[CheckRun]:
        """
        Need to implement this Abstract method with the steps to update payment records
        :param run: Run model instance containing execution parameters
        :return: list of payments updated during the run
        """
        pass

    @abc.abstractmethod
    def login_flow(self, run: Run) -> bool:
        """
        Need to implement this Abstract method with the steps to check login credentials
        :param run: Run model instance containing execution parameters
        :return: True/False based on success or failure
        """
        pass

    def _quit_driver(self):
        if self.driver:
            LOGGER.info("Closing all instances of the browser")
            self.driver.quit()


class AccountingSyncInterface(abc.ABC):
    """
    Runner Interface will ensure the implementation of the following methods
    Whenever any new Sync Process is added then it need to implement the following methods
    """

    def __init__(self, run: Run):
        self.run = run

    @abc.abstractmethod
    def start_sync_flow(self, run: Run) -> List:
        """
        Need to implement this Abstract method with the steps to update payment records
        :param run: Run model instance containing execution parameters
        :return: list of syncs updated during the run
        """
        pass


class PaymentInformationImportInterface(abc.ABC):
    def __init__(self, run: Run):
        self.run = run

    @abc.abstractmethod
    def start_payment_import_flow(self):
        pass


class BaseLoginPage:
    """
    Abstract base Class for vendor-specific "Login Page" classes which are based on the Page Object model.
    This class simply exposes a login() interface
    """

    @abc.abstractmethod
    def login(self, **kwargs):
        """Log into a website using the login page we are currently on"""
        pass


class PasswordBasedLoginPage(BaseLoginPage):
    """Login page which uses a username / password combination to log a user in"""

    SELECTOR_USERNAME_TEXTBOX = None
    SELECTOR_PASSWORD_TEXTBOX = None
    SELECTOR_LOGIN_BUTTON = None
    SELECTOR_ERROR_MESSAGE_TEXT = None

    def __init__(self, driver: WebDriver):
        assert (
            self.SELECTOR_USERNAME_TEXTBOX is not None
        ), "Username selector is required"
        assert (
            self.SELECTOR_PASSWORD_TEXTBOX is not None
        ), "Password selector is required"
        assert (
            self.SELECTOR_LOGIN_BUTTON is not None
        ), "Login button selector is required"
        assert (
            self.SELECTOR_ERROR_MESSAGE_TEXT is not None
        ), "Error message selector is required"

        self.driver = driver

    def get_user_name_textbox(self) -> WebElement:
        """Returns UserName TextBox WebElement"""
        return self.driver.find_element_by_css_selector(self.SELECTOR_USERNAME_TEXTBOX)

    def get_password_textbox(self) -> WebElement:
        """Returns Password TextBox WebElement"""
        return self.driver.find_element_by_css_selector(self.SELECTOR_PASSWORD_TEXTBOX)

    def get_login_button(self) -> WebElement:
        """Returns Login Button WebElement"""
        return self.driver.find_element_by_css_selector(self.SELECTOR_LOGIN_BUTTON)

    def get_error_message(self):
        """Returns Error message WebElement"""
        return self.driver.find_element_by_css_selector(
            self.SELECTOR_ERROR_MESSAGE_TEXT
        )

    def _perform_login(self, username: str):
        self.driver.implicitly_wait(5)

        LOGGER.info("Clicking on Login button")
        self.get_login_button().click()

        try:
            wait_for_element(
                self.driver,
                value=self.SELECTOR_ERROR_MESSAGE_TEXT,
                msg="Login Error msg",
                timeout=5,
                retry_attempts=1,
                raise_exception=False,
            )
            error_message_element = self.get_error_message()
            if error_message_element:
                error_text = (
                    error_message_element.text and error_message_element.text.strip()
                )
                handle_login_errors(error_text, username)
        except WEB_DRIVER_EXCEPTIONS:
            LOGGER.info("Login successful.")
        finally:
            self.driver.implicitly_wait(15)

    def login(self, username: str, password: str):  # pylint: disable=arguments-differ
        # this is probably a design smell that we have differing arguments in the interface versus implementation.
        # if we wanted to use this in any generic interface, this would definitely be a bad idea.
        # but we're just using this in each Runner explicitly, so it's ok.

        wait_for_element(
            self.driver, value=self.SELECTOR_USERNAME_TEXTBOX, msg="Username textbox"
        )

        site_page = self.__class__.__name__
        masked_username = username[:3] + "x" * (len(username) - 3)
        masked_password = password[:1] + "x" * (len(password) - 1)
        LOGGER.info(
            f"Attempting login into {site_page} with username: {masked_username}, password: {masked_password}"
        )

        LOGGER.info("Clearing username and password text boxes")
        self.get_user_name_textbox().clear()
        self.get_password_textbox().clear()

        LOGGER.info(f"Typing {masked_username} in username textbox.")
        self.get_user_name_textbox().send_keys(username)

        LOGGER.info(f"Typing {masked_password} in password textbox.")
        self.get_password_textbox().send_keys(password)

        self._perform_login(username)


def get_end_invoice_date(run: Run):
    """DFI = download_future_invoices in custom_properties
    if DFI flag is missing in custom_properties => download future invoices
    if DFI flag is (False or None) => don't download future invoices
    in all other cases => download future invoices
    """
    end_date_str = run.request_parameters.get("end_date")
    download_future_invoices = True
    conn_custom_properties = run.job.connector.custom_properties
    job_custom_properties = run.job.custom_properties

    if (
        conn_custom_properties
        and "download_future_invoices" in conn_custom_properties
        and not conn_custom_properties.get("download_future_invoices")
    ):
        download_future_invoices = False

    if (
        not download_future_invoices
        and job_custom_properties
        and "download_future_invoices" in job_custom_properties
        and not job_custom_properties.get("download_future_invoices")
    ):
        download_future_invoices = False

    if not end_date_str or download_future_invoices:
        return date.today() + timedelta(days=60)

    return datetime_utils.date_from_isoformat(end_date_str)
