import os
import re

from datetime import datetime, date
from typing import List
from retry.api import retry

from selenium.common.exceptions import (
    NoSuchElementException,
    WebDriverException,
    TimeoutException,
)
from selenium.webdriver.common.by import By
from selenium.webdriver.remote.webelement import WebElement
from apps.adapters.base import PasswordBasedLoginPage, VendorDocumentDownloadInterface
from apps.adapters.framework import download
from apps.adapters.helpers.webdriver_helper import (
    get_url,
    wait_for_ajax,
    wait_for_element,
    explicit_wait_till_visibility,
    explicit_wait_till_url_changes,
    scroll_down,
    has_invoices,
    handle_popup,
    explicit_wait_till_clickable,
    execute_script_click,
    wait_for_loaders,
    WEB_DRIVER_EXCEPTIONS,
)
from apps.runs.models import Run, DiscoveredFile, DocumentType, FileFormat
from integrator import LOGGER
from spices.datetime_utils import date_from_string

# Home Page Locators
HOME_PAGE_LOCATORS = {
    "ACCOUNT_LOCATOR": '#accountListItems>li>a[class^="accountListItem"]',
}

# Billing History Page Locators
BILLING_HISTORY_PAGE = {
    "TABLE_ROWS": "table > tbody.account-list-tbody > tr",
    "HISTORY_TABLE_CONTAINER": "#billingHistoryContainer",
    "HISTORY_DROP_DOWN_MENU": "div#bph-filter-dropdown-wrapper div#divFilterDropdownHeader",
    "HISTORY_DROP_DOWN_OPTION": "#itemBillCharges",
    "VIEW_ALL_TABLE": "#href-view-24month-history",
    "RESTAURANT_NAME": "#spnFirstPremiseAddress",
}


class PgeLoginPage(PasswordBasedLoginPage):
    """Fintech Login Page Web Elements"""

    SELECTOR_USERNAME_TEXTBOX = 'input[name="username"]'
    SELECTOR_PASSWORD_TEXTBOX = 'input[name="password"]'
    SELECTOR_LOGIN_BUTTON = "#home_login_submit"
    SELECTOR_ERROR_MESSAGE_TEXT = (
        'tr[class="loginError"][style=""] div[id="lblAuthErrorMessage"]'
    )

    @retry(WEB_DRIVER_EXCEPTIONS, tries=3, delay=2)
    def _perform_login(self, username: str):
        wait_for_loaders(
            self.driver, value="div.blockUI.blockOverlay", retry_attempts=1
        )
        explicit_wait_till_clickable(
            self.driver,
            locator=(By.CSS_SELECTOR, self.SELECTOR_LOGIN_BUTTON),
            msg="Login Submit Button",
        )
        super()._perform_login(username)


class PgECompanyBillingHistoryPage:
    """Billing History Page class for PgECompany"""

    def __init__(self, driver, download_location: str, home_page):
        self.driver = driver
        self.download_location = download_location
        self.home_page = home_page
        self.vendor = "PG&E COMPANY"

    def get_table_rows(self) -> List[WebElement]:
        """Return the billing history table rows"""
        return self.driver.find_elements_by_css_selector(
            BILLING_HISTORY_PAGE["TABLE_ROWS"]
        )

    def get_table_data(
        self, run: Run, from_date: date, bill_url
    ) -> List[DiscoveredFile]:
        """
        Extracts invoice details from Table
        :param run: Run Object
        :param from_date: Start date of the invoices to be downloaded
        :param bill_url: get account details in list form
        :return: Returns the list of Discovered File
        """
        discovered_files = []

        if not has_invoices(self.driver, value=BILLING_HISTORY_PAGE["TABLE_ROWS"]):
            return discovered_files

        # Get restaurant_name
        restaurant_name = self.driver.find_element_by_css_selector(
            BILLING_HISTORY_PAGE["RESTAURANT_NAME"]
        ).text.strip()

        for row in self.get_table_rows():
            invoice_date = date_from_string(
                row.find_element_by_css_selector(
                    "td h4 span:nth-child(2), td h3 span:nth-child(2)"
                ).text,
                "%m/%d/%y",
            )
            if invoice_date < from_date:
                return discovered_files

            reference_code = f'{bill_url["account_number"]}_{invoice_date}'

            # total amount
            total_amount = row.find_element_by_css_selector("td:nth-child(2)").text

            document_properties = {
                "customer_number": bill_url["account_number"],
                "invoice_number": None,
                "invoice_date": f"{invoice_date}",
                "total_amount": total_amount,
                "restaurant_name": restaurant_name,
                "vendor_name": self.vendor,
            }
            try:
                # pylint: disable=no-member
                discovered_file = DiscoveredFile.build_unique(
                    run,
                    reference_code=reference_code,
                    document_type=DocumentType.INVOICE.ident,
                    file_format=FileFormat.PDF.ident,
                    original_download_url="",
                    original_filename=f"{reference_code}.pdf",
                    document_properties=document_properties,
                )
            except DiscoveredFile.AlreadyExists:
                LOGGER.info(
                    f"Discovered file already exists with reference code : {reference_code}"
                )
                continue  # skip if seen before

            try:
                download_url_element = row.find_element_by_css_selector(
                    "td>div>div>p>a"
                )
                self.download_invoice_by_url(discovered_file, download_url_element)
            except (WebDriverException, NoSuchElementException):
                LOGGER.info(
                    "PDF not found in row element or PDF viewer link not available"
                )
                continue

            discovered_files.append(discovered_file)
            LOGGER.info(
                "Invoice details row data: %s", str(discovered_file.document_properties)
            )

        return discovered_files

    @staticmethod
    def get_account_last_digit(discovered_file):
        """Get last 4 digit of the account number"""
        return re.search(
            r"(?P<acc_digit>\d{4})-\d+",
            discovered_file.document_properties["customer_number"],
        ).groupdict()["acc_digit"]

    @staticmethod
    def get_date_convert_number(discovered_file):
        """Get split and reassign date format for pattern date, month, Year"""
        temp_date = discovered_file.document_properties["invoice_date"].split("-")
        return temp_date[1] + "" + temp_date[-1] + "" + temp_date[0]

    @classmethod
    def prepare_pattern(cls, discovered_file):
        """Return account number and date aggregation"""
        return (
            cls.get_account_last_digit(discovered_file)
            + "custbill"
            + cls.get_date_convert_number(discovered_file)
        )

    def download_invoice_by_url(self, discovered_file, download_url_element):
        """
        Download the File in PDF format
        :param discovered_file: DiscoveredFile variable
        :param download_url_element: download reference element
        """
        # rename is required, if we have download multiple files hence
        # we need to rename the file as for certain conditions for uploading to s3
        _downloader = download.DriverExecuteScriptBasedDownloader(
            self.driver,
            script="arguments[0].click();",
            script_args=(download_url_element,),
            # pass the download dir, since we're passing a pattern below
            local_filepath=rf"{self.download_location}/{self.prepare_pattern(discovered_file)}.pdf",
            rename_to=os.path.join(
                self.download_location, discovered_file.original_filename
            ),
            file_exists_check_kwargs=dict(timeout=50),
        )
        download.download_discovered_file(discovered_file, _downloader)

    def get_bill_history_container(self):
        """Get billing history container block"""
        wait_for_element(
            self.driver,
            value=BILLING_HISTORY_PAGE["HISTORY_TABLE_CONTAINER"],
            msg="wait for whole table",
            retry_attempts=1,
        )
        return self.driver.find_element_by_css_selector(
            BILLING_HISTORY_PAGE["HISTORY_TABLE_CONTAINER"]
        )

    def get_view_all_history_link(self):
        """Get view all text link"""
        return self.driver.find_element_by_css_selector(
            BILLING_HISTORY_PAGE["VIEW_ALL_TABLE"]
        )

    def get_bill_history_drop_down(self):
        """Get bill history drop down button"""
        return self.driver.find_element_by_css_selector(
            BILLING_HISTORY_PAGE["HISTORY_DROP_DOWN_MENU"]
        )

    def get_bill_history_drop_down_option(self):
        """Select drop down option"""
        return self.driver.find_element_by_css_selector(
            BILLING_HISTORY_PAGE["HISTORY_DROP_DOWN_OPTION"]
        )

    def select_bill_history_dropdown(self):
        wait_for_ajax(self.driver, timeout=40)
        explicit_wait_till_visibility(
            self.driver,
            self.get_bill_history_container(),
            timeout=30,
            msg="wait for history block",
        )
        scroll_down(self.driver)
        self.click_element(
            self.get_view_all_history_link(),
            BILLING_HISTORY_PAGE["VIEW_ALL_TABLE"],
            msg="View all history",
        )
        self.click_element(
            self.get_bill_history_drop_down(),
            BILLING_HISTORY_PAGE["HISTORY_DROP_DOWN_MENU"],
            msg="Filter Dropdown",
        )
        self.click_element(
            self.get_bill_history_drop_down_option(),
            BILLING_HISTORY_PAGE["HISTORY_DROP_DOWN_OPTION"],
            msg="Bill Charges",
        )

    def click_element(self, element, wait_locator, msg: str = "wait for the element"):
        explicit_wait_till_clickable(
            self.driver, (By.CSS_SELECTOR, wait_locator), msg=msg
        )
        execute_script_click(self.driver, element)

    @retry(TimeoutException, tries=3, delay=2)
    def navigate_to_bill_page(self, bill_url):
        # navigate url
        get_url(self.driver, bill_url["account_bill_url"])
        wait_for_ajax(self.driver, timeout=30)

    def bill_history_process(self, run, start_date):
        """Bill history processing"""
        discovered_files_list = []
        # iterate account list with details
        for bill_url in self.home_page.prepare_account_details():
            # wait for url change
            explicit_wait_till_url_changes(
                self.driver, bill_url["account_bill_url"], timeout=40
            )
            self.navigate_to_bill_page(bill_url)

            wait_for_ajax(self.driver, timeout=50)

            # select drop down button
            try:
                self.select_bill_history_dropdown()
            except (NoSuchElementException, WebDriverException):
                LOGGER.info("No table found in this page")
                continue

            # discovered account list
            discovered_files_list.extend(self.get_table_data(run, start_date, bill_url))

        return discovered_files_list


class PgECompanyHomePage:
    """Home Page Class for PgECompany"""

    def __init__(self, driver):
        self.driver = driver

    @staticmethod
    def make_bil_url(account_number):
        """make navigate url"""
        return f"https://m.pge.com/index.html?WT.pgeac=Nav_yourBillRes#myaccount/billing/history/{account_number}"

    def account_locators_dict(self, locators):
        """Select account number, restaurant_name, account_bill_url"""
        account_number = re.sub(r"-[A-Za-z\s]+", "", locators.text).strip()
        return {
            "account_number": account_number,
            "account_bill_url": self.make_bil_url(account_number),
        }

    def get_account_locators(self):
        """Get home page Locators"""
        return self.driver.find_elements_by_css_selector(
            HOME_PAGE_LOCATORS["ACCOUNT_LOCATOR"]
        )

    def get_account_drop_down_button(self):
        """Get dropdown button element"""
        for index in range(3):
            try:
                wait_for_element(
                    self.driver,
                    value="#accountsDropDownButton",
                    msg="wait for account drop down",
                    timeout=30,
                    retry_attempts=2,
                )
                return self.driver.find_element_by_css_selector(
                    "#accountsDropDownButton"
                )
            except WebDriverException as excep:
                LOGGER.warning(f"{excep} found in {self.driver.current_url}")
                if index == 2:
                    raise
                get_url(
                    self.driver,
                    "https://m.pge.com/?WT.pgeac=Nav_yourAccountRes#myaccount/dashboard/",
                )

    def prepare_account_details(self):
        """prepare account locators and restaurant_name"""
        self.driver.execute_script(
            "arguments[0].click();", self.get_account_drop_down_button()
        )
        return list(map(self.account_locators_dict, self.get_account_locators()))


class PgECompanyRunner(VendorDocumentDownloadInterface):
    """Runner Class for PgECompany"""

    # uses_proxy = True

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.login_page = PgeLoginPage(self.driver)
        self.home_page = PgECompanyHomePage(self.driver)
        self.billing_history_page = PgECompanyBillingHistoryPage(
            self.driver, self.download_location, self.home_page
        )

    def _login(self):
        """
        Login using credentials
        :return: Nothing
        """
        login_url = "https://m.pge.com/#login"
        get_url(self.driver, login_url)
        wait_for_loaders(
            self.driver, value="div.blockUI.blockOverlay", retry_attempts=1
        )

        # access invisible element access
        scroll_down(self.driver)
        try:
            wait_for_element(
                self.driver,
                value=PgeLoginPage.SELECTOR_LOGIN_BUTTON,
                msg="wait for login button",
            )
        except WebDriverException:
            LOGGER.info("server loading problem, please try again")

        handle_popup(
            self.driver, value="button#onetrust-accept-btn-handler", retry_attempts=1
        )
        self.login_page.login(self.run.job.username, self.run.job.password)

    def _download_documents(self) -> List[DiscoveredFile]:
        """
        Chooses the documents to be downloaded based on the document type
        :return: Returns the list of Discovered Files
        """
        document_type = self.run.job.requested_document_type
        if document_type == "invoice":
            return self._download_invoices()

        raise NotImplementedError(
            f"Requested Document Type is not supported: {document_type}"
        )

    def _download_invoices(self) -> List[DiscoveredFile]:
        """
        Downloads the Invoices
        :return: Returns the list of the Discovered Files
        """
        LOGGER.info("Extracting data from table...")
        start_date = datetime.strptime(
            self.run.request_parameters["start_date"], "%Y-%m-%d"
        ).date()

        discovered_files_list = self.billing_history_page.bill_history_process(
            self.run, start_date
        )

        LOGGER.info(
            f"Downloaded invoice by download link available: {len(discovered_files_list)}"
        )
        return discovered_files_list

    def start_documents_download_flow(self, run: Run) -> List[DiscoveredFile]:
        """
        Initiates the Document Download Workflow
        :param run: Run Object
        :return: Returns the list of Discovered Files
        """
        discovered_files = []
        try:
            self._login()
            discovered_files.extend(self._download_documents())
        finally:
            self._quit_driver()

        return discovered_files

    def login_flow(self, run: Run):
        self._login()
