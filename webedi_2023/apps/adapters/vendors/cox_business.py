import os
import re
from datetime import date
from typing import List, Optional

from retry import retry
from selenium.webdriver.remote.webelement import WebElement

from apps.adapters.framework.context import ExecutionContext
from apps.adapters.framework.download import WebElementClickBasedDownloader
from apps.adapters.framework.registry import connectors
from apps.adapters.framework.steps.primitives import SequentialSteps
from apps.adapters.helpers.helper import sleep
from integrator import LOGGER

from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import NoSuchElementException, WebDriverException

from apps.adapters.framework.operations.vendor import BaseVendorConnector
from apps.adapters.framework.steps.web import (
    NavigateToUrl,
    ExplicitWait,
    SubmitLoginPassword,
)
from apps.adapters.helpers.webdriver_helper import (
    wait_for_loaders,
    close_extra_handles,
    hover_over_element,
    handle_popup,
    wait_for_element,
)
from apps.adapters.framework import download
from apps.runs.models import FileFormat
from spices.datetime_utils import date_from_string

_LOGIN_URL = "https://myaccount.coxbusiness.com/cbma/unauth/login"
_BILLING_HOME_URL = "https://myaccount.coxbusiness.com/cbma/billinghome"


def _handle_popup(driver, value, msg):
    try:
        iframe = driver.find_element(By.CSS_SELECTOR, "iframe#kampyleInvite")
        driver.switch_to.frame(iframe)
        handle_popup(
            driver,
            value=value,
            msg=msg,
            retry_attempts=1,
        )
    except NoSuchElementException:
        LOGGER.info("Popup not found.")


def _has_invoices(
    driver,
    table_selector: str,
    row_selector: str,
    empty_selector: str,
    attribute_value: str,
    attribute="class",
    by_selector=By.CSS_SELECTOR,
):
    table_content_selector = row_selector + ", " + empty_selector
    table = driver.find_element(by_selector, table_selector)
    wait_for_element(
        table,
        value=table_content_selector,
        retry_attempts=3,
        msg="Invoice table content",
    )

    table_content_elem = table.find_element(by_selector, table_content_selector)
    if attribute_value in table_content_elem.get_attribute(attribute):
        LOGGER.info(table_content_elem.text)
        return False

    LOGGER.info("Invoices found.")
    return True


class HandlePopup:
    """Handle popup"""

    def __init__(self, value, msg):
        self.value = value
        self.msg = msg

    def __call__(self, execution_context: ExecutionContext):
        _handle_popup(execution_context.driver, self.value, self.msg)


@connectors.add("cox_business")
class CoxBusinessConnector(BaseVendorConnector):
    vendor_name = "Cox Business"
    invoice_file_format = FileFormat.PDF.ident  # pylint: disable=no-member
    df_download_url_skip_duplicates = True

    class Selectors:
        LOGIN__USERNAME_TEXTBOX = (By.CSS_SELECTOR, 'input[id="okta-signin-username"]')
        LOGIN__PASSWORD_TEXTBOX = (By.CSS_SELECTOR, 'input[id="okta-signin-password"]')
        LOGIN__LOGIN_BUTTON = (By.CSS_SELECTOR, 'input[id="okta-signin-submit"]')
        LOGIN__ERROR_MESSAGE_TEXT = (By.CSS_SELECTOR, "div.okta-form-infobox-error")

        HOME__ACCOUNT_BOX = (By.CSS_SELECTOR, "div#accountBox")
        HOME__ACCOUNTS_DROPDOWN = (
            By.CSS_SELECTOR,
            "div#dropdownContainer div.dropdown_content",
        )

        BILLING__INVOICE_TABLE = "ngx-datatable#recentAccountTransaction datatable-body"
        BILLING__EMPTY_TABLE_ROW = "div.empty-row"
        BILLING__TABLE_ROW = "datatable-body-row"
        BILLING__TABLE_DATA = (By.CSS_SELECTOR, "datatable-body-cell")
        BILLING_INVOICE_PDF = (By.CSS_SELECTOR, "button#view")
        BILLING_CANCEL_BUTTON = (By.CSS_SELECTOR, "button#cancel")
        BILLING_VIEW_ALL_STATEMENTS = (By.CSS_SELECTOR, "app-paymentwidget a.card-link")
        BILLING_DROPDOWN_BUTTON = (By.CSS_SELECTOR, "div.selected-list div.c-btn")
        BILLING_DROPDOWN_OPTIONS = (
            By.CSS_SELECTOR,
            "div.list-area ul.lazyContainer li.pure-checkbox",
        )
        CUSTOMER_NUMBER_SINGLE_ACCOUNT = (By.CSS_SELECTOR, "app-navigation + div")
        DROPDOWN_CONTAINER = (By.CSS_SELECTOR, "div#dropdownContainer")
        DROPDOWN_CONTAINER_SEARCH = (
            By.CSS_SELECTOR,
            "div#dropdownContainer input.search_input",
        )
        ACCOUNT_LENGTH = (By.CSS_SELECTOR, "div#accLength")
        FEEDBACK_POPUP = "#invitationApp button#kplDeferButton"

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
            HandlePopup(
                value=Selectors.FEEDBACK_POPUP, msg="Invitation to provide feedback"
            ),
            NavigateToUrl(_BILLING_HOME_URL),
        ]
    )

    def get_accounts(self):
        wait_for_element(
            self.driver,
            value=self.Selectors.HOME__ACCOUNT_BOX[1],
            msg="Account Dropdown",
            retry_attempts=3,
        )
        self.driver.find_element(*self.Selectors.HOME__ACCOUNT_BOX).click()

        dropdown_container = self.driver.find_element(
            *self.Selectors.DROPDOWN_CONTAINER
        )
        acc_length_text = self.driver.find_element(*self.Selectors.ACCOUNT_LENGTH).text
        acc_length = int(re.findall(r"\d+", acc_length_text)[-1]) // 2
        for _ in range(acc_length):
            self.driver.execute_script(
                "arguments[0].scrollTop = arguments[0].scrollHeight", dropdown_container
            )
            sleep(2, msg="Scrolling down...")

        self.driver.execute_script("arguments[0].scrollTop = 0", dropdown_container)
        account_options = self.driver.find_elements(
            *self.Selectors.HOME__ACCOUNTS_DROPDOWN
        )
        accounts = [option.text.split("\n")[-2:] for option in account_options]
        return accounts

    @retry(NoSuchElementException, tries=5, delay=1)
    def get_search_input_box(self):
        self.driver.find_element(*self.Selectors.HOME__ACCOUNT_BOX).click()
        search_input = self.driver.find_element(
            *self.Selectors.DROPDOWN_CONTAINER_SEARCH
        )
        search_input.clear()
        return search_input

    def search_and_get_account(self, account_number):
        search_input = self.get_search_input_box()
        search_input.send_keys(account_number.split("-")[1].strip())
        dd_option = self.driver.find_element(*self.Selectors.HOME__ACCOUNTS_DROPDOWN)
        LOGGER.info(f"Selected account: {dd_option.text}")
        dd_option.click()

    def _iter_customer_number_selections(self, customer_numbers: Optional[List[str]]):

        try:
            accounts = self.get_accounts()
            LOGGER.info(f"Total accounts found: {accounts}")

            for index, (customer_number, restaurant_name) in enumerate(accounts):
                if index > 0:
                    close_extra_handles(self.driver)

                self.search_and_get_account(customer_number)
                setattr(self, "restaurant_name", restaurant_name.strip())

                wait_for_loaders(
                    self.driver,
                    value="ngx-skeleton-loader .loader",
                )

                if not _has_invoices(
                    self.driver,
                    self.Selectors.BILLING__INVOICE_TABLE,
                    self.Selectors.BILLING__TABLE_ROW,
                    self.Selectors.BILLING__EMPTY_TABLE_ROW,
                    "empty-row",
                ):
                    continue
                yield customer_number.strip(), None
        except NoSuchElementException as excep:
            LOGGER.info(excep)

            wait_for_loaders(
                self.driver,
                value="ngx-skeleton-loader .loader",
            )

            if not _has_invoices(
                self.driver,
                self.Selectors.BILLING__INVOICE_TABLE,
                self.Selectors.BILLING__TABLE_ROW,
                self.Selectors.BILLING__EMPTY_TABLE_ROW,
                "empty-row",
            ):
                return

            customer_number = self.driver.find_element(
                *self.Selectors.CUSTOMER_NUMBER_SINGLE_ACCOUNT
            ).text

            yield customer_number, None

    def click_view_all_statements(self):
        _handle_popup(
            self.driver,
            self.Selectors.FEEDBACK_POPUP,
            "Invitation to provide feedback",
        )
        self.wait_and_reload_if_no_element(
            self.Selectors.BILLING_VIEW_ALL_STATEMENTS[1],
            "View all statements",
        )
        view_all_statements = self.driver.find_element(
            *self.Selectors.BILLING_VIEW_ALL_STATEMENTS
        )
        view_all_statements.click()

    def wait_and_reload_if_no_element(self, value, msg, retries=1):
        for _ in range(3):
            try:
                wait_for_element(
                    self.driver, value=value, msg=msg, retry_attempts=retries
                )
                break
            except WebDriverException as excep:
                LOGGER.info(excep)
                self.driver.refresh()
                continue

    def click_view_billing_statements_dropdown(self):
        dropdown_element = self.driver.find_element(
            *self.Selectors.BILLING_DROPDOWN_BUTTON
        )
        dropdown_element.click()

    def _iter_invoice_row_elements(self, start_date: date, end_date: date):
        self.click_view_all_statements()
        self.click_view_billing_statements_dropdown()
        dd_options = self.driver.find_elements(*self.Selectors.BILLING_DROPDOWN_OPTIONS)

        for index, option in enumerate(dd_options):
            close_extra_handles(self.driver)

            if index > 0:
                self.click_view_billing_statements_dropdown()

            invoice_date = date_from_string(option.text, "%m/%d/%Y")
            if not start_date <= invoice_date <= end_date:
                LOGGER.info(
                    f"Skipping invoices because date '{invoice_date}' is outside requested range"
                )
                break
            setattr(self, "invoice_date", invoice_date)

            if index == 0:
                self.click_view_billing_statements_dropdown()
            else:
                hover_over_element(self.driver, option)
                option.click()
            yield invoice_date

        self.driver.find_element(*self.Selectors.BILLING_CANCEL_BUTTON).click()

    def _construct_downloader(
        self, invoice_row_element, **invoice_fields
    ) -> download.BaseDownloader:

        return CoxWebElementClickBasedDownloader(
            driver=self.driver,
            element=self.driver.find_element(*self.Selectors.BILLING_INVOICE_PDF),
            local_filepath=self.download_location,
            rename_to=os.path.join(
                self.download_location, invoice_fields["original_filename"]
            ),
            file_exists_check_kwargs=dict(timeout=60, pattern=r"^[a-z\d-]+.pdf$"),
        )

    def _extract_invoice_date(self, invoice_row_element) -> date:
        return getattr(self, "invoice_date", None)

    def _extract_customer_number(
        self, invoice_row_element, customer_number, customer_number_element
    ) -> str:
        return customer_number

    def _extract_invoice_number(self, invoice_row_element, **invoice_fields) -> str:
        return None

    def _extract_total_amount(self, invoice_row_element, **invoice_fields) -> str:
        return None

    def _extract_vendor_name(self, invoice_row_element, **invoice_fields) -> str:
        return self.vendor_name

    def _extract_restaurant_name(self, invoice_row_element, **invoice_fields) -> str:
        return getattr(self, "restaurant_name", None)

    def _extract_reference_code(self, invoice_row_element, **invoice_fields) -> str:
        customer_number = invoice_fields["customer_number"].replace(" ", "")
        invoice_date = invoice_fields["invoice_date"]
        return f"{customer_number}_{invoice_date}"

    def _extract_original_download_url(
        self, invoice_row_element, **invoice_fields
    ) -> str:
        return invoice_fields["reference_code"]

    def _extract_original_filename(self, invoice_row_element, **invoice_fields) -> str:
        return f"{invoice_fields['reference_code']}.pdf"


class CoxWebElementClickBasedDownloader(WebElementClickBasedDownloader):
    def __init__(self, driver, element: WebElement, **kwargs):
        super().__init__(element, **kwargs)
        self.driver = driver

    def _perform_download_action(self):
        close_extra_handles(self.driver)
        self.element.click()
