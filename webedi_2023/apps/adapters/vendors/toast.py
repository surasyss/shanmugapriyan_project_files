import os
from datetime import date
from typing import Optional, List

from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.common.exceptions import UnexpectedAlertPresentException
from selenium.webdriver.support import expected_conditions as EC

from apps.adapters import LOGGER
from apps.adapters.framework import download
from apps.adapters.framework.context import ExecutionContext
from apps.adapters.framework.registry import connectors
from apps.adapters.framework.operations.vendor import BaseVendorConnector
from apps.adapters.framework.steps.primitives import SequentialSteps
from apps.adapters.framework.steps.web import (
    NavigateToUrl,
    SubmitLoginPassword,
    ExplicitWait,
)
from apps.adapters.helpers.webdriver_helper import (
    wait_for_ajax,
    wait_for_loaders,
    get_url,
    explicit_wait_till_clickable,
    handle_popup,
    explicit_wait_till_visibility,
    WEB_DRIVER_EXCEPTIONS,
)
from apps.runs.models import FileFormat
from spices.datetime_utils import date_from_string

_LOGIN_URL = (
    "https://auth.toasttab.com/login?"
    "state=g6Fo2SBTeHpNYWNNZmhKdlY1dFV0OFZSNThac3NBRFhvb3lTbaN0aWTZIF9tZ05YMmZsMm9WenNla0xOM3h1aW5QTHJ"
    "VWDZEUXYyo2NpZNkgcFZJdGJCWldrcHd1OEg5RGRtMG9QY1NmYWd4cmtydEI&client=pVItbBZWkpwu8H9Ddm0oPcSfagxrkrt"
    "B&protocol=oauth2&force_mfa=false&redirect_uri=https%3A%2F%2Fwww.toasttab.com%2Fauthentication%2F"
    "callback&response_type=code&scope=openid%20profile&audience=https%3A%2F%2Ftoast-users-api%2F"
)
_HOME_PAGE_URL = "https://www.toasttab.com/restaurants/admin/home"
_INVOICES_PAGE_URL = (
    "https://www.toasttab.com/restaurants/admin/legacyReports/deposits#invoices"
)


class NavigateToHomepage:
    """Navigate to Homepage"""

    def __init__(self, url: str, retry_attempts: int = 1):
        self.url = url
        self.retry_attempts = retry_attempts

    def __call__(self, execution_context: ExecutionContext):
        if execution_context.driver.current_url != self.url:
            get_url(execution_context.driver, self.url, self.retry_attempts)


@connectors.add("toast")
class ToastConnector(BaseVendorConnector):
    vendor_name = "Toast"
    invoice_file_format = FileFormat.PDF.ident  # pylint: disable=no-member
    df_download_url_skip_duplicates = True

    class Selectors:
        HOME__LOADER = "div.loading, div.loadmask"

        LOGIN__USERNAME_TEXTBOX = (By.CSS_SELECTOR, "input#username")
        LOGIN__PASSWORD_TEXTBOX = (By.CSS_SELECTOR, "input#password")
        LOGIN__LOGIN_BUTTON = (By.CSS_SELECTOR, 'button[type="submit"]')
        LOGIN__ERROR_MESSAGE_TEXT = (
            By.CSS_SELECTOR,
            "#error-element-password, p#message.error",
        )

        INVOICES_HISTORY__UPDATE_BUTTON = (By.CSS_SELECTOR, "button#update-btn")
        INVOICES_HISTORY__TABLE_ROWS = (
            By.CSS_SELECTOR,
            "table#invoices-table tbody tr",
        )
        INVOICES_HISTORY__RESTAURANT_NAME = (
            By.CSS_SELECTOR,
            "div[data-testid='restaurant-name']",
        )
        INVOICES_HISTORY__DATE_DROPDOWN = (
            By.CSS_SELECTOR,
            "div#date-dropdown-container button",
        )
        INVOICES_HISTORY__CUSTOM_DATE = (
            By.CSS_SELECTOR,
            'ul.dropdown-menu li a[data-value="custom"]',
        )
        INVOICES_HISTORY__START_DATE_INPUT = 'input[name="reportDateStart"]'
        INVOICES_HISTORY__WAIT_FOR_TABLE_DATA = (
            By.CSS_SELECTOR,
            "table#invoices-table tbody tr td",
        )
        RESTAURANT_NAMES = (
            By.CSS_SELECTOR,
            "#switch-restaurants-menu #restaurant-switch-menu li.search-option a, "
            "div[id^='downshift-'][id$='-menu']  li.search-option a",
        )
        SWITCH_ACCOUNT_DROPDOWN = (
            By.CSS_SELECTOR,
            "button#switch-restaurants-menu, "
            "li#switch-restaurants-menu a#switch-toggle",
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
            NavigateToHomepage(_HOME_PAGE_URL),
            ExplicitWait(
                until=EC.visibility_of_element_located(
                    locator=Selectors.SWITCH_ACCOUNT_DROPDOWN
                )
            ),
        ]
    )

    def get_account_links(self):
        account_links = []
        handle_popup(
            self.driver,
            value="button[id^='pendo-close-guide']",
            msg="Toast Capital Loans Popup",
            retry_attempts=1,
        )

        self.driver.find_element(*self.Selectors.SWITCH_ACCOUNT_DROPDOWN).click()
        customer_name_elements = self.driver.find_elements(
            *self.Selectors.RESTAURANT_NAMES
        )
        if customer_name_elements:
            LOGGER.info(
                f"Totally {len(customer_name_elements)} accounts found: "
                f"{[account.text for account in customer_name_elements]}"
            )
            for customer_name_element in customer_name_elements:
                customer_name_url = customer_name_element.get_attribute("href")
                account_links.append(customer_name_url)
        return account_links

    def _iter_customer_number_selections(self, customer_numbers: Optional[List[str]]):
        account_links = self.get_account_links()
        if account_links:
            for _, account_link in enumerate(account_links):
                get_url(self.driver, account_link)
                yield None, None
        else:
            yield None, None

    def _step_post_account_selection(self):
        get_url(
            self.driver,
            url=_INVOICES_PAGE_URL,
        )
        wait_for_loaders(self.driver, value="div.loading", timeout=10, retry_attempts=2)
        explicit_wait_till_clickable(
            self.driver,
            self.Selectors.INVOICES_HISTORY__DATE_DROPDOWN,
            timeout=10,
            msg="Date Dropdown",
        )
        handle_popup(
            self.driver,
            value="div#pendo-guide-container button._pendo-close-guide",
            msg="SETUP SCAN TO PAY POPUP",
            retry_attempts=1,
        )
        self.driver.find_element(
            *self.Selectors.INVOICES_HISTORY__DATE_DROPDOWN
        ).click()
        explicit_wait_till_clickable(
            self.driver,
            self.Selectors.INVOICES_HISTORY__CUSTOM_DATE,
            timeout=10,
            msg="Custom Date",
        )
        self.driver.find_element(*self.Selectors.INVOICES_HISTORY__CUSTOM_DATE).click()

    def _iter_invoice_row_elements(self, start_date: date, end_date: date):
        try:
            self._step_post_account_selection()
            self.select_custom_date_range(start_date)
        except WEB_DRIVER_EXCEPTIONS as excep:
            LOGGER.warning(excep)

        table_rows = self.driver.find_elements(
            *self.Selectors.INVOICES_HISTORY__TABLE_ROWS
        )
        if table_rows and "No invoices" not in table_rows[0].text:
            for row in table_rows:
                yield row

    def select_custom_date_range(self, start_date):
        wait_for_ajax(self.driver)

        start_date_input_box = self.driver.find_element_by_css_selector(
            self.Selectors.INVOICES_HISTORY__START_DATE_INPUT
        )

        for _ in range(10):
            start_date_input_box.send_keys(Keys.BACKSPACE)

        start_date_input_box.send_keys(start_date.strftime("%m-%d-%Y"))
        wait_for_ajax(self.driver)

        explicit_wait_till_clickable(
            self.driver,
            self.Selectors.INVOICES_HISTORY__UPDATE_BUTTON,
            msg="Update buttton",
        )
        self.driver.find_element(
            *self.Selectors.INVOICES_HISTORY__UPDATE_BUTTON
        ).click()

        for index in range(5):
            try:
                wait_for_loaders(self.driver, value=self.Selectors.HOME__LOADER)
                explicit_wait_till_visibility(
                    self.driver,
                    self.driver.find_element(
                        *self.Selectors.INVOICES_HISTORY__WAIT_FOR_TABLE_DATA
                    ),
                    msg="Table Data",
                )
                break
            except WEB_DRIVER_EXCEPTIONS as excep:
                LOGGER.warning(excep)
            except UnexpectedAlertPresentException as alert_excep:
                LOGGER.warning(alert_excep)
                alert = self.driver.switch_to.alert
                alert.accept()
                if (
                    self.driver.current_url
                    != "https://www.toasttab.com/restaurants/admin/reports/home#invoices"
                ):
                    get_url(
                        self.driver,
                        url=_INVOICES_PAGE_URL,
                    )

    def _construct_downloader(
        self, invoice_row_element, **invoice_fields
    ) -> download.BaseDownloader:
        return download.DriverBasedUrlGetDownloader(
            self.driver,
            download_url=invoice_fields["original_download_url"],
            local_filepath=os.path.join(
                self.download_location, f"{invoice_fields['invoice_number']}.pdf"
            ),
            rename_to=os.path.join(
                self.download_location, invoice_fields["original_filename"]
            ),
            file_exists_check_kwargs=dict(timeout=20),
        )

    def _extract_invoice_date(self, invoice_row_element) -> date:
        return date_from_string(
            invoice_row_element.find_elements_by_css_selector("td")[2].text, "%m/%d/%Y"
        )

    def _extract_customer_number(
        self, invoice_row_element, customer_number, customer_number_element
    ) -> str:
        return customer_number

    def _extract_invoice_number(self, invoice_row_element, **invoice_fields) -> str:
        return invoice_row_element.find_elements_by_css_selector("td")[1].text

    def _extract_total_amount(self, invoice_row_element, **invoice_fields) -> str:
        return invoice_row_element.find_elements_by_css_selector("td")[3].text

    def _extract_vendor_name(self, invoice_row_element, **invoice_fields) -> str:
        return self.vendor_name

    def _extract_restaurant_name(self, invoice_row_element, **invoice_fields) -> str:
        return self.driver.find_element(
            *self.Selectors.INVOICES_HISTORY__RESTAURANT_NAME
        ).text

    def _extract_reference_code(self, invoice_row_element, **invoice_fields) -> str:
        invoice_number = invoice_fields["invoice_number"]
        invoice_date = invoice_fields["invoice_date"]
        return f"{invoice_number}_{invoice_date}"

    def _extract_original_download_url(
        self, invoice_row_element, **invoice_fields
    ) -> str:
        table_data = invoice_row_element.find_elements_by_css_selector("td")[0]
        return table_data.find_element_by_css_selector("a").get_attribute("href")

    def _extract_original_filename(self, invoice_row_element, **invoice_fields) -> str:
        reference_code = self._extract_reference_code(
            invoice_row_element, **invoice_fields
        )
        return f"{reference_code}.pdf"
