import os
import re
from datetime import date
from typing import List, Optional

from selenium.common.exceptions import (
    StaleElementReferenceException,
    NoSuchElementException,
)
from selenium.webdriver.chrome.webdriver import WebDriver

from integrator import LOGGER

from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC

from apps.adapters.framework.download import (
    DriverBasedUrlGetDownloader,
    BaseDownloader,
    download_discovered_file,
)
from apps.adapters.framework.context import ExecutionContext
from apps.adapters.framework.registry import connectors
from apps.adapters.framework.steps.primitives import SequentialSteps
from apps.adapters.framework.operations.vendor import BaseVendorConnector
from apps.adapters.framework.steps.web import (
    NavigateToUrl,
    SubmitLoginPassword,
    NavigateToUrlFromElement,
    ExplicitWait,
)
from apps.adapters.helpers.webdriver_helper import (
    explicit_wait_till_visibility,
    get_url,
    close_extra_handles,
    has_invoices,
)
from apps.runs.models import FileFormat, DiscoveredFile
from spices.datetime_utils import date_from_string

_LOGIN_URL = "https://atmosenergy.com/accountcenter/logon/login.html"
_BILLING_HISTORY_URL = "https://atmosenergy.com/accountcenter/finance/FinancialTransaction.html?activeTab=2"


class AuthenticateAgain:
    """Authenticate Again"""

    def __init__(self, link):
        self.link = link

    def __call__(self, execution_context: ExecutionContext):
        if execution_context.driver.current_url == self.link:
            LOGGER.info("Authenticating again...")
            SubmitLoginPassword(
                username_textbox=AtmosConnector.Selectors.LOGIN__USERNAME_TEXTBOX,
                password_textbox=AtmosConnector.Selectors.LOGIN__PASSWORD_TEXTBOX,
                login_button=AtmosConnector.Selectors.LOGIN__LOGIN_BUTTON,
                error_message=AtmosConnector.Selectors.LOGIN__ERROR_MESSAGE_TEXT,
            )(execution_context)


@connectors.add("atmos_energy")
class AtmosConnector(BaseVendorConnector):
    vendor_name = "Atmos Energy"
    invoice_file_format = FileFormat.PDF.ident  # pylint: disable=no-member
    df_download_url_skip_duplicates = True

    class Selectors:
        HOME__ACCOUNT_ROWS = (By.CSS_SELECTOR, "div.grpBodyCell div.line")
        HOME__ACCOUNT_LINK = (
            By.CSS_SELECTOR,
            "div.noInput.hide-s a.btnCommon.btnCompact",
        )
        HOME__ACCOUNT_NUMBER = (By.CSS_SELECTOR, "span.emphasisLarge")

        LOGIN__USERNAME_TEXTBOX = (By.CSS_SELECTOR, 'input[id="username"]')
        LOGIN__PASSWORD_TEXTBOX = (By.CSS_SELECTOR, 'input[id="password"]')
        LOGIN__LOGIN_BUTTON = (By.CSS_SELECTOR, 'input[id="authenticate_button_Login"]')
        LOGIN__ERROR_MESSAGE_TEXT = (By.CSS_SELECTOR, "form ul.errorMessage li span")

        BILLING_HISTORY__VIEW_ALL = (
            By.CSS_SELECTOR,
            'div[id="bilTab"] a[id="viewAll"]',
        )
        BILLING_HISTORY__TABLE_ROWS = (
            By.CSS_SELECTOR,
            'table[id="BillingHistoryTable"] tbody tr',
        )

        ACCOUNT_CENTER__BILLING_AND_USAGE = (By.CSS_SELECTOR, 'a[id="viewbills"]')
        ACCOUNT_CENTER__ACCOUNT_RESTAURANT_VALUE = (By.CSS_SELECTOR, "div.grpBodyCell")
        ACCOUNT_CENTER__RESTAURANT_NAME = (By.CSS_SELECTOR, "li.custName")
        SINGLE_TYPE_ACCOUNT = (By.CSS_SELECTOR, "#bodyWrap>script:nth-child(3)")

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
            AuthenticateAgain(
                link="https://atmosenergy.com/accountcenter/logon/authenticate.html"
            ),
            ExplicitWait(
                until=EC.visibility_of_element_located(
                    locator=Selectors.HOME__ACCOUNT_ROWS
                )
            ),
        ]
    )

    # account page navigation
    _step_navigate_to_invoices_list_page__after_account_selection = (
        NavigateToUrlFromElement(link=Selectors.ACCOUNT_CENTER__BILLING_AND_USAGE)
    )

    def _iter_customer_number_selections(self, customer_numbers: Optional[List[str]]):
        elements = []
        customer_num_elem = self.driver.find_elements(
            *self.Selectors.HOME__ACCOUNT_LINK
        )
        if customer_num_elem:
            for customer_number_elem in customer_num_elem:
                customer_url = customer_number_elem.get_attribute("href")
                customer_number = self._extract_customer_number(
                    None, None, customer_number_elem
                )
                elements.append((customer_number, customer_url))

            # we have to split this into a second for loop because the customer number elements (except the first)
            # become stale as soon as we navigate to the first customer number's page
            for (customer_number, customer_url) in elements:
                setattr(self, "customer_url", customer_url)
                self.navigate_to_account_page()
                yield customer_number, None
        else:
            get_url(
                self.driver,
                _BILLING_HISTORY_URL,
            )
            yield None, None

    def get_table_rows(self):
        table_rows = self.driver.find_elements(
            *self.Selectors.BILLING_HISTORY__TABLE_ROWS
        )
        return table_rows

    def navigate_to_account_page(self):
        customer_url = getattr(self, "customer_url")
        if customer_url:
            get_url(self.driver, customer_url)
            explicit_wait_till_visibility(
                self.driver,
                self.driver.find_element(
                    *self.Selectors.ACCOUNT_CENTER__BILLING_AND_USAGE
                ),
                msg="Billing and usage",
            )

    def _iter_invoice_row_elements(self, start_date: date, end_date: date):
        if has_invoices(
            self.driver,
            value=self.Selectors.BILLING_HISTORY__TABLE_ROWS[1],
            msg="Invoice Row",
            retry_attempts=1,
        ):
            view_all_invoices = self.driver.find_elements(
                *self.Selectors.BILLING_HISTORY__VIEW_ALL
            )
            if view_all_invoices:
                LOGGER.info("Clicking View All...")
                view_all_invoices[0].click()

        table_rows = self.get_table_rows()
        for index, _ in enumerate(table_rows):
            row = self.get_table_rows()[index]
            try:
                invoice_date = self._extract_invoice_date(row)
            except (StaleElementReferenceException, NoSuchElementException):
                LOGGER.info(
                    "Invoice row element becomes stale. Finding element again..."
                )
                if not self.driver.current_url == _BILLING_HISTORY_URL:
                    self.navigate_to_account_page()
                    get_url(self.driver, _BILLING_HISTORY_URL)
                row = self.get_table_rows()[index]
                invoice_date = self._extract_invoice_date(row)

            if not start_date <= invoice_date <= end_date:
                LOGGER.info(
                    f"Skipping remaining invoices because date '{invoice_date}' is outside requested range"
                )
                break
            yield row

    def _construct_downloader(
        self, invoice_row_element, **invoice_fields
    ) -> BaseDownloader:
        return AtmosDriverBasedUrlGetDownloader(
            self.driver,
            download_url=invoice_fields["original_download_url"],
            local_filepath=os.path.join(self.download_location, "my.pdf"),
            rename_to=os.path.join(
                self.download_location, invoice_fields["original_filename"]
            ),
            file_exists_check_kwargs=dict(timeout=20),
            post_download_action=self.post_download_action,
        )

    def post_download_action(self):
        close_extra_handles(self.driver)
        if (
            self.driver.current_url
            == "https://atmosenergy.com/accountcenter/successerror/successErrorMessage.html"
        ):
            LOGGER.info(self.driver.find_element(By.CSS_SELECTOR, "div#main").text)
            self.driver.back()
            raise TimeoutError

    def _extract_invoice_date(self, invoice_row_element) -> date:
        return date_from_string(
            invoice_row_element.find_elements_by_css_selector("td")[0].text, "%b %d, %Y"
        )

    def _extract_customer_number(
        self, invoice_row_element, customer_number, customer_number_element
    ) -> str:
        if customer_number:
            return customer_number
        try:
            customer_number_url = customer_number_element.get_attribute("href")
            customer_number = customer_number_url.split("accountNumber=")[1]
        except AttributeError:
            LOGGER.info("Get Account number in single account")
            customer_number = self._clean_customer_number_value(
                self.get_single_format_account_number
            )
        return customer_number

    def _extract_invoice_number(self, invoice_row_element, **invoice_fields) -> str:
        return f'ATMOS-{invoice_fields["invoice_date"]}'

    def _extract_total_amount(self, invoice_row_element, **invoice_fields) -> str:
        return invoice_row_element.find_elements_by_css_selector("td")[1].text

    def _extract_vendor_name(self, invoice_row_element, **invoice_fields) -> str:
        return "Atmos Energy"

    def _extract_restaurant_name(self, invoice_row_element, **invoice_fields) -> str:
        return self.driver.find_element(
            *self.Selectors.ACCOUNT_CENTER__RESTAURANT_NAME
        ).text

    def _extract_reference_code(self, invoice_row_element, **invoice_fields) -> str:
        customer_number = invoice_fields["customer_number"]
        invoice_date = invoice_fields["invoice_date"]
        return f"{customer_number}_{invoice_date}"

    def _extract_original_download_url(
        self, invoice_row_element, **invoice_fields
    ) -> str:
        download_id = invoice_row_element.find_element_by_css_selector(
            "span.viewPdf"
        ).get_attribute("id")
        original_download_url = f"https://atmosenergy.com/accountcenter/urlfetch/viewPdf.html?printDoc={download_id}"
        return original_download_url

    def _extract_original_filename(self, invoice_row_element, **invoice_fields) -> str:
        reference_code = self._extract_reference_code(
            invoice_row_element, **invoice_fields
        )
        return f"{reference_code}.pdf"

    @staticmethod
    def _clean_customer_number_value(single_type_num):
        return (
            re.compile(r'ca="(?P<number>\d+)')
            .search(single_type_num)
            .groupdict()["number"]
        )

    @property
    def get_single_format_account_number(self):
        return self.driver.find_element(
            *self.Selectors.SINGLE_TYPE_ACCOUNT
        ).get_attribute("innerText")

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
                    download_discovered_file(discovered_file, file_downloader)
                    discovered_files.append(discovered_file)
                except PdfNotAvailableException as exc:
                    LOGGER.info(exc)
                    close_extra_handles(self.driver)
                    self.driver.back()

        return discovered_files


class AtmosDriverBasedUrlGetDownloader(DriverBasedUrlGetDownloader):
    def __init__(self, driver: WebDriver, download_url: str, **kwargs):
        self.pdf_available = True
        super().__init__(driver, download_url, **kwargs)

    def _perform_download_action(self):
        """Perform the download action"""
        if self.pdf_available:
            super()._perform_download_action()
            if "successErrorMessage" in self.driver.current_url:
                error_text = self.driver.find_element(
                    By.CSS_SELECTOR, "p.extender"
                ).text
                self.pdf_available = False
                raise PdfNotAvailableException(error_text)


class PdfNotAvailableException(Exception):
    pass
