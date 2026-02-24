import datetime
import re
from typing import List

from selenium.common.exceptions import NoSuchElementException
from selenium.webdriver.remote.webelement import WebElement
from selenium.webdriver.common.action_chains import ActionChains
from spices.datetime_utils import date_from_string

from apps.adapters import LOGGER
from apps.adapters.base import VendorDocumentDownloadInterface
from apps.adapters.framework import download
from apps.adapters.framework.steps.web import handle_login_errors
from apps.adapters.helpers.webdriver_helper import (
    get_url,
    wait_for_element,
    has_invoices,
    explicit_wait_till_visibility,
    WEB_DRIVER_EXCEPTIONS,
)
from apps.runs.models import Run, DiscoveredFile, DocumentType, FileFormat

LOGIN_PAGE_LOCATORS = {
    "USERNAME": "input#userID",
    "CONTINUE": "#continueFromUserLogin",
    "PASSWORD": "input#password",
    "SUBMIT": "#signin",
    "ERROR": "div#errorDescArea",
}

HOME_PAGE_LOCATORS = {
    "SEE_MY_BILL": "li:nth-child(3) div.gn-removetext-decration",
    "FIRST_ACCOUNT_NUMBER": "div span[aria-label='accountNumber']",
    "CHECK_ACCOUNT": "#Selection_Menu_Demo_C div div",
    "LOADING": "#intialSpinner div div.overviewBtnSmall div",
}

INVOICE_PAGE_LOCATORS = {
    "ACCOUNT_DROPDOWN": "#Selection_Menu_Demo_C div div",
    "ACCOUNT_LIST": "#Selection_Menu_Demo_C-listbox button",
    "INVOICE_DATE": "div.MyBillHistory__due-date__18yF1",
    "INVOICE_TOTAL_AMOUNT": "div.MyBillHistory__due-amt__3p-oX",
    "EACH_INVOICE_ROW": "div.HistoryComponent__billing-history-section__1GHNt",
    "DOWNLOAD_DROP_DOWN": "div[data-testid='buttonSelectTest1']",
    "SELECT_DOWNLOAD_OPTION": "#demo-dropdown-buttonSelect1 ul li:nth-child(1)",
}

ERROR_PAGE_LOCATORS = {
    "BAD_REQUEST_ERROR": "div.bad-request-div",
}


class ATTLoginPage:
    """Login Page Web Elements"""

    def __init__(self, driver):
        self.driver = driver

    def get_login_button(self) -> WebElement:
        """Returns Login Button WebElement"""
        return self.driver.find_element_by_css_selector(LOGIN_PAGE_LOCATORS["SUBMIT"])

    def get_continue_button(self) -> WebElement:
        """Returns Continue Button WebElement"""
        return self.driver.find_element_by_css_selector(LOGIN_PAGE_LOCATORS["CONTINUE"])

    def get_user_name_textbox(self) -> WebElement:
        """Returns UserName TextBox WebElement"""
        return self.driver.find_element_by_css_selector(LOGIN_PAGE_LOCATORS["USERNAME"])

    def get_password_textbox(self) -> WebElement:
        """Returns Password TextBox WebElement"""
        wait_for_element(
            self.driver,
            value=LOGIN_PAGE_LOCATORS["PASSWORD"],
            retry_attempts=3,
            msg="Wait for password text box",
        )
        return self.driver.find_element_by_css_selector(LOGIN_PAGE_LOCATORS["PASSWORD"])

    def get_error_message(self):
        """Returns Error message WebElement"""
        return self.driver.find_element_by_css_selector(LOGIN_PAGE_LOCATORS["ERROR"])

    def _perform_login(self, username: str):
        self.driver.implicitly_wait(5)

        LOGGER.info("Clicking on Login button")
        self.get_login_button().click()

        try:
            wait_for_element(
                self.driver,
                value=LOGIN_PAGE_LOCATORS["ERROR"],
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

    def login(self, username: str, password: str):
        """Handle login page flow for AT&T"""

        wait_for_element(
            self.driver, value=LOGIN_PAGE_LOCATORS["USERNAME"], msg="Username textbox"
        )

        masked_username = username[:3] + "x" * (len(username) - 3)
        masked_password = password[:1] + "x" * (len(password) - 1)
        LOGGER.info(
            f"Attempting login into AT&T with "
            f"username: {masked_username}, password: {masked_password}"
        )

        LOGGER.info("Clearing username and password text boxes")
        self.get_user_name_textbox().clear()

        LOGGER.info(f"Typing {masked_username} in username textbox.")
        self.get_user_name_textbox().send_keys(username)

        LOGGER.info(f"Continue to next page sign-in")
        self.get_continue_button().click()

        self.get_password_textbox().clear()
        LOGGER.info(f"Typing {masked_password} in password textbox.")
        self.get_password_textbox().send_keys(password)

        self._perform_login(username)


class ATTHomePage:
    """Home Page Class for AT&T"""

    def __init__(self, driver):
        self.driver = driver

    def get_see_my_bill_button(self) -> WebElement:
        """Return the bill button element"""
        return self.driver.find_element_by_css_selector(
            HOME_PAGE_LOCATORS["SEE_MY_BILL"]
        )

    def check_account(self) -> WebElement:
        """Return the account div element"""
        return self.driver.find_element_by_css_selector(
            HOME_PAGE_LOCATORS["CHECK_ACCOUNT"]
        )

    def get_first_account_number(self) -> WebElement:
        """Return the first account number."""
        return self.driver.find_element_by_css_selector(
            HOME_PAGE_LOCATORS["FIRST_ACCOUNT_NUMBER"]
        )

    def get_bad_request_error_page(self) -> WebElement:
        """Return bad request error page element."""
        return self.driver.find_element_by_css_selector(
            ERROR_PAGE_LOCATORS["BAD_REQUEST_ERROR"]
        )

    def go_to_invoice_page(self):
        """Navigate to invoice home page."""
        for _ in range(5):
            try:
                explicit_wait_till_visibility(
                    self.driver, self.get_see_my_bill_button(), msg="Billing & payments"
                )

                self.get_see_my_bill_button().click()
                LOGGER.info("Navigating to Billing and Payments Page...")
                wait_for_element(
                    self.driver,
                    value=HOME_PAGE_LOCATORS["FIRST_ACCOUNT_NUMBER"],
                    msg="Account number",
                )

                account_number = self.get_first_account_number().text.split(" ")[1]
                invoice_page_url = f"https://www.att.com/acctmgmt/history?selectedAcct={account_number}"
                get_url(self.driver, url=invoice_page_url)
                LOGGER.info("Navigating to Invoice Page...")

                break
            except WEB_DRIVER_EXCEPTIONS as excep:
                get_url(self.driver, url="http://att.com/acctmgmt/accountoverview")
                LOGGER.warning(f"Unexpected Error: {excep}. Retrying...")


class ATTInvoicesPage:
    """Invoices Page Class for AT&T."""

    def __init__(self, driver, download_location: str):
        self.driver = driver
        self.download_location = download_location
        self.home_page = ATTHomePage(self.driver)
        self.vendor_name = "AT&T"

    def get_invoice_rows_element(self):
        """Return invoice row elements."""
        return self.driver.find_elements_by_css_selector(
            INVOICE_PAGE_LOCATORS["EACH_INVOICE_ROW"]
        )

    def get_total_amount(self):
        """Return invoice total element."""
        return self.driver.find_element_by_css_selector(
            INVOICE_PAGE_LOCATORS["INVOICE_TOTAL_AMOUNT"]
        )

    @staticmethod
    def get_invoice_date(row):
        """Return invoice date element."""
        return row.find_element_by_css_selector(INVOICE_PAGE_LOCATORS["INVOICE_DATE"])

    def get_download_button(self):
        """Return download dropdown elements."""
        return self.driver.find_elements_by_css_selector(
            INVOICE_PAGE_LOCATORS["DOWNLOAD_DROP_DOWN"]
        )

    def select_download_option(self):
        """Return select download option elements."""
        return self.driver.find_elements_by_css_selector(
            INVOICE_PAGE_LOCATORS["SELECT_DOWNLOAD_OPTION"]
        )

    def get_account_drop_down(self):
        """Return account dropdown element."""
        return self.driver.find_element_by_css_selector(
            INVOICE_PAGE_LOCATORS["ACCOUNT_DROPDOWN"]
        )

    def get_account_list(self):
        """Return account list elements in the dropdown."""
        return self.driver.find_elements_by_css_selector(
            INVOICE_PAGE_LOCATORS["ACCOUNT_LIST"]
        )

    def get_table_data(
        self, run: Run, account_details_list, from_date
    ) -> List[DiscoveredFile]:
        """
        Extracts invoice details from Table
        :param run: Run Object
        :param account_details_list: account details
        :param from_date: start days of the download pdf
        :return: Returns the list of Discovered File
        """
        discovered_files = []

        invoice_rows = self.get_invoice_rows_element()
        for _row_index, _ in enumerate(invoice_rows):

            has_invoices(self.driver, value=INVOICE_PAGE_LOCATORS["EACH_INVOICE_ROW"])
            each_row = self.get_invoice_rows_element()[_row_index]
            inv_date = ATTInvoicesPage.get_invoice_date(each_row).text.split("-")[-1]

            try:
                invoice_date = date_from_string(inv_date.strip(), "%B %d, %Y")
            except ValueError:
                invoice_date = date_from_string(inv_date.strip(), "%b %d, %Y")

            if invoice_date < from_date:
                break

            invoice_amount = self.get_total_amount().text
            customer_number = account_details_list.split()[1]
            restaurant_name = re.split(r"\n\d+", account_details_list)[0]
            reference_code = f"{customer_number}_{invoice_date}"
            document_pattern = re.split(r"\s\d+,\s", inv_date.strip())
            download_pattern = f"ATTBill_{customer_number[-4:]}_" + "".join(
                document_pattern
            )

            document_properties = {
                "customer_number": customer_number,
                "invoice_date": f"{invoice_date}",
                "invoice_number": "",
                "invoice_index": _row_index,
                "total_amount": f"{invoice_amount}",
                "restaurant_name": restaurant_name,
                "download_pattern": download_pattern,
                "vendor_name": self.vendor_name,
            }

            wait_for_element(
                self.driver,
                value=INVOICE_PAGE_LOCATORS["DOWNLOAD_DROP_DOWN"],
                msg="wait for download dropdown...",
            )

            ActionChains(self.driver).click(
                self.get_download_button()[_row_index]
            ).perform()
            download_element = self.select_download_option()[_row_index]

            try:
                discovered_file = DiscoveredFile.build_unique(
                    run,
                    reference_code,
                    document_type=DocumentType.INVOICE.ident,  # pylint: disable=no-member
                    file_format=FileFormat.PDF.ident,  # pylint: disable=no-member
                    original_download_url=download_element,
                    original_filename=f"{reference_code}.pdf",
                    document_properties=document_properties,
                )
            except DiscoveredFile.AlreadyExists:
                LOGGER.info(
                    f"Discovered file already exists with reference code : {reference_code}"
                )
                continue  # skip if seen before

            LOGGER.info(
                "Invoice details row data: %s",
                str(discovered_file.document_properties),
            )
            discovered_files.append(discovered_file)
        return discovered_files

    def download_invoice_by_element_click(self, discovered_file):
        """
        Download the File in PDF format
        :param discovered_file: DiscoveredFile object
        """
        pattern = discovered_file.document_properties["download_pattern"] + ".pdf"
        _inv_index = discovered_file.document_properties["invoice_index"]
        inv_download_element = self.select_download_option()[_inv_index]

        _downloader = download.WebElementClickBasedDownloader(
            element=inv_download_element,
            local_filepath=self.download_location,
            file_exists_check_kwargs=dict(timeout=20, pattern=pattern),
        )
        download.download_discovered_file(discovered_file, _downloader)


class ATTRunner(VendorDocumentDownloadInterface):
    """Runner Class for AT&T"""

    is_angular = True

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.login_page = ATTLoginPage(self.driver)
        self.home_page = ATTHomePage(self.driver)
        self.invoice_page = ATTInvoicesPage(self.driver, self.download_location)

    def _login(self):
        """
        Login using credentials
        :return: Nothing
        """
        # Using ignore_synchronization, if True,
        # pytractor will not attempt to synchronize with the page before
        #     performing actions
        self.driver.ignore_synchronization = True
        login_url = "https://signin.att.com/"
        get_url(self.driver, login_url)
        self.login_page.login(self.run.job.username, self.run.job.password)

    def _download_documents(self, account_details_list) -> List[DiscoveredFile]:
        """
        Chooses the documents to be downloaded based on the document type
        :return: Returns the list of Discovered Files
        """
        document_type = self.run.job.requested_document_type
        if document_type == "invoice":
            return self._download_invoices(account_details_list)
        raise NotImplementedError(
            f"Requested Document Type is not supported: {document_type}"
        )

    def _download_invoices(self, account_details_list) -> List[DiscoveredFile]:
        """
        Downloads the Invoices
        :return: Returns the list of the Discovered Files
        """
        LOGGER.info("Extracting data from table...")
        start_date = datetime.datetime.strptime(
            self.run.request_parameters["start_date"], "%Y-%m-%d"
        ).date()
        att_discovered_files = self.invoice_page.get_table_data(
            self.run, account_details_list=account_details_list, from_date=start_date
        )
        return att_discovered_files

    def start_documents_download_flow(self, run: Run) -> List[DiscoveredFile]:
        """
        Initiates the Document Download Workflow
        :param run: Run Object
        :return: Returns the list of Discovered Files
        """
        discovered_files = []
        try:
            self._login()

            for retries in range(3):
                try:
                    bad_req_element = self.home_page.get_bad_request_error_page()
                    error_text = bad_req_element.text
                    LOGGER.info(
                        f"Login failed with error: {error_text}. Retrying login: {retries}"
                    )
                    self._login()

                    if retries == 2:
                        handle_login_errors(error_text, self.run.job.username)

                except NoSuchElementException:
                    break

            get_url(self.driver, url="http://att.com/acctmgmt/accountoverview")
            LOGGER.info("Navigate to account overview page...")

            wait_for_element(
                self.driver,
                value=HOME_PAGE_LOCATORS["CHECK_ACCOUNT"],
                msg="Check accounts...",
            )
            no_account_error_text = "You don't have an account linked"
            no_accounts_present = self.home_page.check_account()
            if not no_accounts_present:
                LOGGER.info(no_account_error_text)
                return discovered_files

            self.home_page.go_to_invoice_page()
            self.invoice_page.get_account_drop_down().click()
            for _acc_index, _ in enumerate(self.invoice_page.get_account_list()):

                if _acc_index > 0:
                    # self.get_account_drop_down().click()
                    ActionChains(self.driver).click(
                        self.invoice_page.get_account_drop_down()
                    ).perform()

                account_details_list = self.invoice_page.get_account_list()[
                    _acc_index
                ].text
                wait_for_element(
                    self.driver,
                    value=INVOICE_PAGE_LOCATORS["ACCOUNT_LIST"],
                    msg="wait for account list in dropdown...",
                )
                ActionChains(self.driver).click(
                    self.invoice_page.get_account_list()[_acc_index]
                ).perform()
                wait_for_element(
                    self.driver,
                    value=HOME_PAGE_LOCATORS["LOADING"],
                    msg="wait for loading...",
                    retry_attempts=3,
                    raise_exception=False,
                )
                discovered_files.extend(self._download_documents(account_details_list))
                self.invoice_page.download_invoice_by_element_click(discovered_files[0])
        finally:
            self._quit_driver()

        LOGGER.info(
            f"Total Invoices within date range and download "
            f"links available %s: {len(discovered_files)}"
        )
        return discovered_files

    def login_flow(self, run: Run):
        self._login()
