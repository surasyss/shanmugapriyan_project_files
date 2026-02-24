import os
import re
from datetime import date
from typing import List, Optional

from integrator import LOGGER
from integrator.conf import DRIVER_DEFAULT_IMPLICIT_WAIT

from selenium.webdriver.common.by import By
from selenium.common.exceptions import NoSuchWindowException
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.webdriver import WebDriver

from apps.adapters.framework.context import ExecutionContext
from apps.adapters.framework.registry import connectors
from apps.adapters.framework.operations.vendor import BaseVendorConnector
from apps.adapters.framework.steps.web import (
    NavigateToUrl,
    ExplicitWait,
    SubmitLoginPassword,
    handle_login_errors,
)
from apps.adapters.helpers.webdriver_helper import (
    get_url,
    wait_for_ajax,
    wait_for_element,
    wait_for_loaders,
    WEB_DRIVER_EXCEPTIONS,
    explicit_wait_for_frame,
)
from apps.adapters.framework import download
from apps.runs.models import FileFormat
from spices.datetime_utils import date_from_string

_LOGIN_URL = "https://customerservice2.southerncompany.com/Login?mnuOpco=APC"
_BILLING_HISTORY_URL = (
    "https://customerservice2.southerncompany.com/Billing/BillHistory"
)


class SwitchToLoginIframe:
    def __init__(self, iframe_selector):
        self.iframe_selector = iframe_selector

    def __call__(self, execution_context: ExecutionContext):
        explicit_wait_for_frame(
            execution_context.driver,
            self.iframe_selector,
            timeout=30,
            msg="Login Igframe",
        )


class AlabamaSubmitLoginPassword(SubmitLoginPassword):
    def __init__(self, username_textbox, password_textbox, login_button, error_message):
        super().__init__(
            username_textbox, password_textbox, login_button, error_message
        )
        self.username_textbox = username_textbox
        self.password_textbox = password_textbox
        self.login_button = login_button
        self.error_message = error_message

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
        login_button = driver.find_element(*self.login_button)

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

        except (*WEB_DRIVER_EXCEPTIONS, NoSuchWindowException):
            # Catching these exceptions for backward compatibility
            LOGGER.info("Login successful")
        finally:
            driver.implicitly_wait(DRIVER_DEFAULT_IMPLICIT_WAIT)


@connectors.add("alabama_power")
class AlabamaPowerConnector(BaseVendorConnector):
    vendor_name = "Alabama Power"
    invoice_file_format = FileFormat.PDF.ident  # pylint: disable=no-member
    df_download_url_skip_duplicates = True
    restaurant_name = None

    class Selectors:
        LOGIN__IFRAME = (By.CSS_SELECTOR, "#loginIframe")
        LOGIN__USERNAME_TEXTBOX = (By.CSS_SELECTOR, "input#username")
        LOGIN__PASSWORD_TEXTBOX = (By.CSS_SELECTOR, "input#password")
        LOGIN__LOGIN_BUTTON = (By.CSS_SELECTOR, "#log-in-button")
        LOGIN__ERROR_MESSAGE_TEXT = (By.CSS_SELECTOR, "div.ErrorMessageText ul li")

        HOME__ACCOUNT_BOX = (By.CSS_SELECTOR, "#billingButton > a")
        HOME__ACCOUNT_DROP_DOWN = (
            By.CSS_SELECTOR,
            "span.form-control.ui-select-toggle",
        )
        HOME__ACCOUNT_ROWS = (By.CSS_SELECTOR, "div.ui-select-choices-row.ng-scope")
        HOME__ACCOUNT_NUMBER = (By.CSS_SELECTOR, "div div.acct-num-nav.ng-binding")

        BILLING_HISTORY__TABLE_ROWS = (
            By.CSS_SELECTOR,
            "#BillHistoryTable div table tbody tr",
        )
        BILLING_HISTORY__INVOICE_DATE = (By.CSS_SELECTOR, "td.date-column")
        BILLING_HISTORY__TOTAL_AMOUNT = (By.CSS_SELECTOR, "td.cell-amount > a + span")
        BILLING_HISTORY__INVOICE_PDF = (
            By.CSS_SELECTOR,
            '#BillHistoryTable div table tbody tr td > a[title="View Paper Bill"]',
        )
        BILLING_HISTORY__INVOICES__DOWNLOAD_PDF = (
            By.CSS_SELECTOR,
            'td > a[title="View Paper Bill"]',
        )

    # login
    _navigate_to_login_page = NavigateToUrl(_LOGIN_URL, retry_attempts=5)
    _navigate_to_login_page__post = SwitchToLoginIframe(Selectors.LOGIN__IFRAME)
    _submit_login_info__pre = ExplicitWait(
        until=EC.visibility_of_element_located(
            locator=Selectors.LOGIN__USERNAME_TEXTBOX
        )
    )

    _submit_login_info = AlabamaSubmitLoginPassword(
        username_textbox=Selectors.LOGIN__USERNAME_TEXTBOX,
        password_textbox=Selectors.LOGIN__PASSWORD_TEXTBOX,
        login_button=Selectors.LOGIN__LOGIN_BUTTON,
        error_message=Selectors.LOGIN__ERROR_MESSAGE_TEXT,
    )

    def _account_drop_down(self):
        """Click account drop down element."""
        wait_for_element(
            self.driver,
            value=self.Selectors.HOME__ACCOUNT_DROP_DOWN[1],
            msg="Account Dropdown",
        )
        self.driver.find_element(*self.Selectors.HOME__ACCOUNT_DROP_DOWN).click()

    def _iter_customer_number_selections(self, customer_numbers: Optional[List[str]]):

        wait_for_element(
            self.driver,
            value=self.Selectors.HOME__ACCOUNT_BOX[1],
            retry_attempts=3,
            raise_exception=False,
            msg="Billing and Payments",
        )
        get_url(self.driver, _BILLING_HISTORY_URL)

        self._account_drop_down()

        customer_row_elems = self.driver.find_elements(
            *self.Selectors.HOME__ACCOUNT_ROWS
        )

        # remove add account row
        customer_row_elems.pop()
        for index, _ in enumerate(customer_row_elems):

            if index > 0:
                # click account drop down element
                self._account_drop_down()

            # find account row elements before every account selection as it becomes stale
            customer_row_elem = self.driver.find_elements(
                *self.Selectors.HOME__ACCOUNT_ROWS
            )[index]
            self.restaurant_name = customer_row_elem.text.splitlines()[0]
            customer_number = customer_row_elem.find_element(
                *self.Selectors.HOME__ACCOUNT_NUMBER
            ).text

            # click each account
            customer_row_elem.click()

            wait_for_loaders(self.driver, value="div[class='spinner']")
            yield customer_number, None

    def _iter_invoice_row_elements(self, start_date: date, end_date: date):

        wait_for_ajax(self.driver, msg="invoice table")

        table_rows = self.driver.find_elements(
            *self.Selectors.BILLING_HISTORY__TABLE_ROWS
        )

        for index, _ in enumerate(table_rows):

            wait_for_element(
                self.driver,
                value=self.Selectors.BILLING_HISTORY__INVOICE_PDF[1],
                msg="View Paper Bill",
            )
            row_element = self.driver.find_elements(
                *self.Selectors.BILLING_HISTORY__TABLE_ROWS
            )[index]
            row_has_pdf = row_element.find_elements(
                *self.Selectors.BILLING_HISTORY__INVOICES__DOWNLOAD_PDF
            )

            if (
                self.driver.find_elements(*self.Selectors.BILLING_HISTORY__TABLE_ROWS)[
                    index
                ].text
                and row_has_pdf
            ):

                invoice_date = self._extract_invoice_date(
                    self.driver.find_elements(
                        *self.Selectors.BILLING_HISTORY__TABLE_ROWS
                    )[index]
                )

                if not start_date <= invoice_date <= end_date:
                    LOGGER.info(
                        f"Skipping remaining invoices because date '{invoice_date}' is outside requested range"
                    )
                    break
                yield self.driver.find_elements(
                    *self.Selectors.BILLING_HISTORY__TABLE_ROWS
                )[index]

    def _construct_downloader(
        self, invoice_row_element, **invoice_fields
    ) -> download.BaseDownloader:
        return download.WebElementClickBasedDownloader(
            element=invoice_row_element.find_element(
                *self.Selectors.BILLING_HISTORY__INVOICES__DOWNLOAD_PDF
            ),
            local_filepath=self.download_location,
            rename_to=os.path.join(
                self.download_location, invoice_fields["original_filename"]
            ),
            file_exists_check_kwargs=dict(pattern=r"^Bill.(?:pdf|PDF)$", timeout=40),
        )

    def _extract_invoice_date(self, invoice_row_element) -> date:
        return date_from_string(
            invoice_row_element.find_element(
                *self.Selectors.BILLING_HISTORY__INVOICE_DATE
            ).text,
            "%m/%d/%y",
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
        return self.restaurant_name

    def _extract_reference_code(self, invoice_row_element, **invoice_fields) -> str:
        customer_number = invoice_fields["customer_number"]
        invoice_date = invoice_fields["invoice_date"]
        return f"{customer_number}_{invoice_date}"

    def _extract_original_download_url(
        self, invoice_row_element, **invoice_fields
    ) -> str:
        formatted_total = re.sub(r"\D", "", invoice_fields["total_amount"])
        return f"{invoice_fields['reference_code']}_{formatted_total}"

    def _extract_original_filename(self, invoice_row_element, **invoice_fields) -> str:
        reference_code = self._extract_reference_code(
            invoice_row_element, **invoice_fields
        )
        return f"{reference_code}.pdf"
