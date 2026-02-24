import os
from datetime import date
from typing import List, Optional

from selenium.webdriver.chrome.webdriver import WebDriver
from selenium.webdriver.remote.webelement import WebElement
from selenium.webdriver.common.by import By
from selenium.common.exceptions import NoSuchElementException, WebDriverException
from selenium.webdriver.support import expected_conditions as EC

from integrator import LOGGER
from apps.adapters.framework.context import ExecutionContext
from apps.adapters.framework.steps.primitives import SequentialSteps
from apps.adapters.framework import download
from apps.adapters.framework.registry import connectors
from apps.adapters.framework.operations.vendor import BaseVendorConnector
from apps.adapters.framework.steps.web import (
    NavigateToUrl,
    SubmitLoginPassword,
    ExplicitWait,
)
from apps.adapters.helpers.helper import sleep
from apps.adapters.helpers.webdriver_helper import (
    get_url,
    handle_popup,
    scroll_down_to_element,
    explicit_wait_till_visibility,
    has_invoices,
)
from apps.runs.models import FileFormat, DiscoveredFile
from spices.datetime_utils import date_from_string

_LOGIN_URL = "https://www.airgas.com/login"


class HandlePopup:
    """Handle popup"""

    def __init__(self, value, msg, confirm_selector=None):
        self.value = value
        self.msg = msg
        self.confirm_selector = confirm_selector

    def __call__(self, execution_context: ExecutionContext):
        handle_popup(
            execution_context.driver,
            by_selector=By.CSS_SELECTOR,
            value=self.value,
            msg=self.msg,
            retry_attempts=1,
        )
        if self.confirm_selector:
            try:
                execution_context.driver.find_element(*self.confirm_selector).click()
            except WebDriverException:
                pass


class NavigateToLoginUrl(NavigateToUrl):
    """Navigate to URL"""

    def __call__(self, execution_context: ExecutionContext):
        driver = execution_context.driver
        for index in range(self.retry_attempts):
            try:
                LOGGER.info(f"{index}. Navigating to {self.url}")
                driver.get(self.url)
                if self.url in driver.current_url:
                    break
                LOGGER.info(f"{index}. Navigated to {driver.current_url}")
            except Exception as excep:  # pylint: disable=broad-except
                LOGGER.warning(
                    f"{index}. Some error while opening url: {self.url} - {excep}"
                )
                sleep(2, msg="Retry url")


@connectors.add("airgas")
class AirgasConnector(BaseVendorConnector):
    vendor_name = "Airgas"
    invoice_file_format = FileFormat.PDF.ident  # pylint: disable=no-member
    df_download_url_skip_duplicates = True
    restaurant_name = None
    invoices_data_container = []

    class Selectors:
        HOME__ACCOUNT_ROWS = (
            By.CSS_SELECTOR,
            "div.form-switch-account-container form.js-form table tr",
        )
        HOME__ACCOUNT_TABLE_DATA = (By.CSS_SELECTOR, "td")
        HOME_FIRST_ACCOUNT_RADIO = (
            By.CSS_SELECTOR,
            "form.js-form table.my-lists div.input-radio",
        )

        LOGIN__USERNAME_TEXTBOX = (By.CSS_SELECTOR, "div.form-login input#j_username")
        LOGIN__PASSWORD_TEXTBOX = (By.CSS_SELECTOR, "div.form-login input#j_password")
        LOGIN__LOGIN_BUTTON = (By.CSS_SELECTOR, "div.form-login button#loginid")
        LOGIN__ERROR_MESSAGE_TEXT = (By.CSS_SELECTOR, "#loginForm div div.error-msg")
        LOGIN__POST = (By.CSS_SELECTOR, "ul.admin-account-links")

        RECENT_INVOICES__TABLE_ROWS = (
            By.CSS_SELECTOR,
            "div.recent-invoices div.table-responsive table tbody tr",
        )
        RECENT_INVOICES__DOWNLOAD_FILE = (
            By.CSS_SELECTOR,
            "td.options i.invoiceOption li a.js-invoice-file",
        )
        RECENT_INVOICES__INVOICE_NUMBER = (By.CSS_SELECTOR, "td.invoice-number")
        RECENT_INVOICES__TOTAL_AMOUNT = (By.CSS_SELECTOR, "td.amount")
        RECENT_INVOICES__INVOICE_DATE = (By.CSS_SELECTOR, "td.invoice-date")
        CONFIRM_CLOSE = (By.CSS_SELECTOR, "button.confirmation-dialog__button--yes")

    _navigate_to_login_page = NavigateToLoginUrl(_LOGIN_URL, retry_attempts=5)
    _submit_login_info__pre = SequentialSteps(
        [
            ExplicitWait(
                until=EC.visibility_of_element_located(
                    locator=Selectors.LOGIN__USERNAME_TEXTBOX
                )
            ),
            HandlePopup(
                value="div#mt-ltbx-content map area[href*='close']",
                msg="Goal Accomplish Popup",
            ),
        ]
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
                value="map#monetate_lightbox_contentMap area",
                msg="We want to hear from you!",
            ),
            ExplicitWait(
                until=EC.visibility_of_element_located(locator=Selectors.LOGIN__POST)
            ),
            HandlePopup(
                value="button.widget-floating__button--close",
                msg="Helper Bot",
                confirm_selector=Selectors.CONFIRM_CLOSE,
            ),
        ]
    )

    def get_current_account(self):
        account_number_elem = self.driver.find_element(
            By.CSS_SELECTOR, "div.row-canvas input#customerAccountNumber"
        )
        self.driver.execute_script(
            "arguments[0].setAttribute('type','text');", account_number_elem
        )
        account_number = account_number_elem.get_attribute("value")
        restaurant_name = self.driver.find_element(
            By.CSS_SELECTOR, "div.customer-contact div.ora-line"
        ).text
        return account_number, restaurant_name

    def get_accounts(self):
        self.driver.find_element(By.CSS_SELECTOR, "div.list-start-items").click()
        account_number_options = self.driver.find_elements(
            By.CSS_SELECTOR, "div.list-start-items div.display-menu ul li a"
        )
        accounts = []
        current_account = self.get_current_account()
        accounts.append(current_account)
        for elem in account_number_options:
            account_number, restaurant_name = elem.text.split(" - ")
            accounts.append(
                (
                    account_number,
                    restaurant_name,
                )
            )
        return accounts

    def navigate_to_account_detail_page(self, account_number):
        account_url = (
            f"https://www.airgas.com/switchAccount?accountNumber={account_number}"
        )
        get_url(self.driver, account_url)

        get_url(self.driver, "https://www.airgas.com/dashboard")
        LOGGER.info(f"Navigating to the account {account_number}'s dashboard")
        self._handle_popup()

    def _iter_customer_number_selections(self, customer_numbers: Optional[List[str]]):
        self._handle_popup()
        if "dashboard" in self.driver.current_url:
            try:
                account_number = self.driver.find_element_by_css_selector(
                    "div.list-start-items a.account-number-ribbon"
                ).text
                self.restaurant_name = self.driver.find_element_by_css_selector(
                    "div.list-start-items span.account-name"
                ).text
                yield account_number, None
            except NoSuchElementException:
                accounts = self.get_accounts()
                for index, (
                    account_number,
                    restaurant_name,
                ) in enumerate(accounts):
                    self.restaurant_name = restaurant_name

                    if index > 0:
                        self.navigate_to_account_detail_page(account_number)

                    yield account_number, None

        else:
            accounts_details = self.get_multiple_accounts_details()

            for index, account in enumerate(accounts_details[1:]):
                account_data = dict(zip(accounts_details[0], account))
                if index == 0:
                    self.driver.find_element(
                        *self.Selectors.HOME_FIRST_ACCOUNT_RADIO
                    ).click()
                    self.driver.find_element_by_css_selector(
                        "div.switch-account-footer.selectAccount-header div button"
                    ).click()
                else:
                    self.navigate_to_account_detail_page(account_data["ACCOUNT #"])
                self.restaurant_name = account_data["NAME"]
                yield account_data["ACCOUNT #"], None

    def get_multiple_accounts_details(self):
        accounts_details, page_number = [], 0
        while True:
            account_rows = self.driver.find_elements(*self.Selectors.HOME__ACCOUNT_ROWS)

            if page_number > 0:
                account_rows = account_rows[1:]

            for row in account_rows:
                table_datas = row.find_elements_by_css_selector("td")
                accounts_details.append([table_data.text for table_data in table_datas])

            next_page = self.driver.find_elements(
                By.CSS_SELECTOR, "div.pagination li a[rel='next']"
            )
            if not next_page:
                if page_number > 0:
                    get_url(self.driver, "https://www.airgas.com/selectAccount")
                break
            page_number += 1
            next_page[0].click()
            explicit_wait_till_visibility(
                self.driver,
                element=self.driver.find_element(
                    By.CSS_SELECTOR, "div.pagination li a[rel='prev']"
                ),
                timeout=10,
                msg="Next page account rows",
            )
        LOGGER.info(f"Total accounts found: {len(accounts_details)}")
        return accounts_details

    def _iter_invoice_row_elements(self, start_date: date, end_date: date):

        has_invoices(
            self.driver,
            value=self.Selectors.RECENT_INVOICES__TABLE_ROWS[1],
            retry_attempts=2,
        )
        table_rows = self.driver.find_elements(
            *self.Selectors.RECENT_INVOICES__TABLE_ROWS
        )
        for row in table_rows:
            scroll_down_to_element(self.driver, row)
            invoice_number = self._extract_invoice_number(row)
            total_amount = self._extract_invoice_number(row)
            invoice_date = self._extract_invoice_number(row)
            row_data = (invoice_number, invoice_date, total_amount)

            if row_data in self.invoices_data_container:
                LOGGER.info(
                    f"Invoice with invoice number {invoice_number} was already downloaded"
                )
                continue

            self.invoices_data_container.append(row_data)
            yield row

    def _handle_popup(self):
        handle_popup(
            self.driver,
            by_selector=By.CSS_SELECTOR,
            value="div#mt-ltbx-content map area[href*='close']",
            msg="Goal Accomplish Popup",
            retry_attempts=1,
        )

    def _construct_downloader(
        self, invoice_row_element, **invoice_fields
    ) -> download.BaseDownloader:
        return AirgasWebElementClickBasedDownloader(
            self.driver,
            element=invoice_row_element,
            local_filepath=os.path.join(self.download_location, "SSEPDFExtractor.pdf"),
            rename_to=os.path.join(
                self.download_location, invoice_fields["original_filename"]
            ),
            file_exists_check_kwargs=dict(timeout=40),
        )

    def _extract_invoice_date(self, invoice_row_element) -> date:
        return date_from_string(
            invoice_row_element.find_element(
                *self.Selectors.RECENT_INVOICES__INVOICE_DATE
            ).text,
            "%m/%d/%Y",
        )

    def _extract_customer_number(
        self, invoice_row_element, customer_number, customer_number_element
    ) -> str:
        if customer_number:
            return customer_number
        return None

    def _extract_invoice_number(self, invoice_row_element, **invoice_fields) -> str:
        return invoice_row_element.find_element(
            *self.Selectors.RECENT_INVOICES__INVOICE_NUMBER
        ).text

    def _extract_total_amount(self, invoice_row_element, **invoice_fields) -> str:
        return invoice_row_element.find_element(
            *self.Selectors.RECENT_INVOICES__TOTAL_AMOUNT
        ).text

    def _extract_vendor_name(self, invoice_row_element, **invoice_fields) -> str:
        return self.vendor_name

    def _extract_restaurant_name(self, invoice_row_element, **invoice_fields) -> str:
        return self.restaurant_name

    def _extract_reference_code(self, invoice_row_element, **invoice_fields) -> str:
        customer_number = invoice_fields["customer_number"]
        invoice_number = invoice_fields["invoice_number"]
        invoice_date = invoice_fields["invoice_date"]
        return f"{customer_number}_{invoice_number}_{invoice_date}"

    def _extract_original_download_url(
        self, invoice_row_element, **invoice_fields
    ) -> str:
        return invoice_fields["reference_code"]

    def _extract_original_filename(self, invoice_row_element, **invoice_fields) -> str:
        reference_code = self._extract_reference_code(
            invoice_row_element, **invoice_fields
        )
        return f"{reference_code}.pdf"

    @staticmethod
    def _clean_original_download_url(original_download_url) -> str:
        return original_download_url

    def _download_invoices(self):
        start_date = self._get_start_invoice_date()
        end_date = self._get_end_invoice_date()
        customer_numbers = self.run.request_parameters.get("customer_numbers")

        self._step_navigate_to_invoices_list_page__before_account_selection(
            self.execution_context
        )

        seen_download_urls = set()
        discovered_files = []
        for (
            customer_number,
            customer_number_element,
        ) in self._iter_customer_number_selections(customer_numbers):
            if (
                customer_numbers
                and customer_number
                and (customer_number not in customer_numbers)
            ):
                continue

            self._navigate_to_invoices_list_page__after_account_selection(
                customer_number, customer_number_element
            )

            invoices_iterator = self._iter_invoices(
                customer_number, customer_number_element, start_date, end_date
            )
            for (invoice_dict, file_downloader) in invoices_iterator:
                # we do this check for a second time, because
                invoice_date = invoice_dict["invoice_date"]
                if not start_date <= invoice_date <= end_date:
                    LOGGER.info(
                        f"Skipping invoice because date '{invoice_date}' is outside requested range"
                    )
                    continue

                original_download_url = invoice_dict["original_download_url"]
                if self.df_download_url_skip_duplicates and (
                    original_download_url in seen_download_urls
                ):
                    LOGGER.info(
                        f"Skipping file because url '{original_download_url}' was already seen in this run"
                    )
                    continue

                seen_download_urls.add(original_download_url)

                try:
                    discovered_file = DiscoveredFile.build_unique(
                        self.run,
                        invoice_dict["reference_code"],
                        document_type=self.invoice_document_type,
                        file_format=self.invoice_file_format,
                        original_download_url=invoice_dict["original_download_url"],
                        original_filename=invoice_dict["original_filename"],
                        document_properties={
                            "customer_number": invoice_dict["customer_number"],
                            "invoice_number": invoice_dict["invoice_number"],
                            "total_amount": invoice_dict["total_amount"],
                            "invoice_date": invoice_dict["invoice_date"].isoformat(),
                            "restaurant_name": invoice_dict["restaurant_name"],
                            "vendor_name": invoice_dict["vendor_name"],
                        },
                    )
                except DiscoveredFile.AlreadyExists:
                    LOGGER.info(
                        f'Discovered file already exists with reference code: {invoice_dict["reference_code"]}'
                    )
                    continue

                try:
                    download.download_discovered_file(discovered_file, file_downloader)
                    discovered_files.append(discovered_file)
                except PdfNotAvailableException as exc:
                    LOGGER.info(exc)
        return discovered_files


class PdfNotAvailableException(Exception):
    pass


class AirgasWebElementClickBasedDownloader(download.WebElementClickBasedDownloader):
    """
    Downloader implementation that downloads by clicking a WebElement.
    """

    def __init__(self, driver: WebDriver, element: WebElement, **kwargs):
        super().__init__(element, **kwargs)
        self.driver = driver
        self.error_text = None

    def pre_download_action(self):
        is_option_opened = self.driver.find_elements_by_css_selector(
            "td.options i.kabobMenu-display"
        )
        if is_option_opened:
            self.element.find_element_by_css_selector("td").click()

        self.element.find_element_by_css_selector("td.options i.invoiceOption").click()

    def get_download_element(self):
        download_element = self.element.find_element(
            By.CSS_SELECTOR,
            "td.options i.invoiceOption li a.js-invoice-file",
        )
        return download_element

    def _perform_download_action(self):
        self.pre_download_action()
        self.get_download_element().click()

        error_text_elements = self.driver.find_elements_by_css_selector(
            "div.fancybox-overlay div.fancybox-opened div.paragraph-wysiwyg"
        )
        if error_text_elements:
            error_text = error_text_elements[0].text
            handle_popup(
                self.driver,
                value='div.fancybox-overlay div.fancybox-opened a[title="OK"]',
                retry_attempts=1,
            )
            raise PdfNotAvailableException(error_text)
