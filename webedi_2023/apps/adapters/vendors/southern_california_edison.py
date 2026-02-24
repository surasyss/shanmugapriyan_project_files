import os
from datetime import datetime
from typing import List

from retry import retry
from selenium.common.exceptions import (
    WebDriverException,
    StaleElementReferenceException,
    ElementNotInteractableException,
    NoSuchElementException,
)
from selenium.webdriver.common.by import By
from selenium.webdriver.remote.webelement import WebElement

from apps.adapters.base import VendorDocumentDownloadInterface, PasswordBasedLoginPage
from apps.adapters.framework import download
from apps.adapters.helpers.webdriver_helper import (
    explicit_wait_till_clickable,
    explicit_wait_till_visibility,
    get_url,
    wait_for_element,
    handle_popup,
    wait_for_loaders,
    WEB_DRIVER_EXCEPTIONS,
    has_invoices,
)
from apps.adapters.vendors import LOGGER
from apps.runs.models import Run, DiscoveredFile, DocumentType, FileFormat
from spices.datetime_utils import date_from_string

# Home Page Locators
HOME_PAGE_LOCATORS = {
    "HOME_ACCOUNTS_LINK": 'a[class="customerAccountComponent__sceSmLink__Kl5GO '
    'customerAccountComponent__sceDetailsLink__1nr2s"]',
    "GET_FEEDBACK_BUTTON": 'button[class="fsrButton fsrButton__inviteDecline fsrDeclineButton"]',
    "LOADER": "div[class*='appSpinner']",
}

# Invoices Page Locators
INVOICE_PAGE_LOCATORS = {
    "RESTAURANT_NAME": "section.singleComponent__bnpSingleAcc__1QqzV div[class*='singleComponent__sceSection'] "
    "div[class^='singleComponent__sceTextAlign'] span",
    "ACCOUNT_NUMBER": "section.singleComponent__bnpSingleAcc__1QqzV div[class*='singleComponent__sceSection'] "
    "div.singleComponent__sceTextAlign__BQh6- div p",
    "GET_YEARS": 'div[class="accordionComponent__sceAccordionHistory__3V6rG"] > span',
    "MORE_BUTTON": 'a[class="billingHistoryComponent__viewLink__1QTKH"]',
    "INVOICE_TABLE_ROWS": 'div[id="content"] > section > div[class="row gridComponent__contentContainer__3v0n4"]',
}


class SouthernCaliforniaEdisonLoginPage(PasswordBasedLoginPage):
    """
    Southern California Edison login module
    """

    SELECTOR_USERNAME_TEXTBOX = 'input[id="userName"]'
    SELECTOR_PASSWORD_TEXTBOX = 'input[id="password"]'
    SELECTOR_LOGIN_BUTTON = 'button[id="HomeLoginButton"]'
    SELECTOR_ERROR_MESSAGE_TEXT = (
        "span.globalErrorBlock__sceAlertText__3Cpzf, a[href='/apps/maintenance']"
    )


class SouthernCaliforniaEdisonHomePage:
    """Southern California Edison Home page action methods come here."""

    def __init__(self, driver):
        self.driver = driver

    def get_loader(self) -> WebElement:
        """Returns Loader WebElement"""
        return self.driver.find_element_by_css_selector(HOME_PAGE_LOCATORS["LOADER"])

    def get_accounts_links(self) -> List[WebElement]:
        """Returns Invoices Link WebElement"""
        return self.driver.find_elements_by_css_selector(
            HOME_PAGE_LOCATORS["HOME_ACCOUNTS_LINK"]
        )

    def get_nth_account_link(self, index: int) -> WebElement:
        """Returns Invoices Link WebElement"""
        return self.driver.find_elements_by_css_selector(
            HOME_PAGE_LOCATORS["HOME_ACCOUNTS_LINK"]
        )[index]

    def get_feedback_dialog(self) -> WebElement:
        """Get feedback window button css web element...."""
        return self.driver.find_element_by_css_selector(
            HOME_PAGE_LOCATORS["GET_FEEDBACK_BUTTON"]
        )

    def go_to_invoices_page(self, index: int):
        """
        Go to Invoices Page
        :return:
        """
        for retries in range(3):
            try:
                # Fetch 1st element
                wait_for_element(
                    self.driver,
                    value=HOME_PAGE_LOCATORS["HOME_ACCOUNTS_LINK"],
                    msg="Invoice Link",
                )
                handle_popup(
                    self.driver,
                    value=HOME_PAGE_LOCATORS["GET_FEEDBACK_BUTTON"],
                    retry_attempts=1,
                )
                LOGGER.info("Clicking on Invoice Link.")
                self.get_nth_account_link(index).click()
                handle_popup(
                    self.driver,
                    value=HOME_PAGE_LOCATORS["GET_FEEDBACK_BUTTON"],
                    retry_attempts=1,
                )
                break
            except WebDriverException as excep:
                LOGGER.info(excep)
                if retries == 2:
                    raise
                get_url(self.driver, "https://www.sce.com/mysce/myaccount")

    def wait_for_loaders(self):
        wait_for_loaders(self.driver, value=HOME_PAGE_LOCATORS["LOADER"])


class SouthernCaliforniaEdisonInvoicesPage:
    """Southern California Edison Invoices page action methods come here."""

    def __init__(self, driver):
        self.driver = driver
        self.vendor_name = "Southern California Edison"

    def _get_restaurant_names(self) -> List[WebElement]:
        """
        Get restaurant names
        :return: List of restaurant names
        """
        return self.driver.find_elements_by_css_selector(
            INVOICE_PAGE_LOCATORS["RESTAURANT_NAME"]
        )

    def _get_restaurant_name(self):
        """
        Get restaurant name from two rows
        :return: Restaurant name
        """
        restaurant_names = self._get_restaurant_names()
        combine_res_name = restaurant_names[0].get_attribute("title")
        if len(restaurant_names) == 2:
            combine_res_name = (
                restaurant_names[0].get_attribute("title")
                + "/"
                + restaurant_names[1].get_attribute("title")
            )
        return combine_res_name

    def _get_account_number(self) -> WebElement:
        """
        Get account number web element
        :return: Account web element
        """
        return self.driver.find_element_by_css_selector(
            INVOICE_PAGE_LOCATORS["ACCOUNT_NUMBER"]
        )

    def _get_invoice_history_tables(self) -> List[WebElement]:
        """
        Get invoice history table
        :return: List of years web element
        """
        return self.driver.find_elements_by_css_selector(
            INVOICE_PAGE_LOCATORS["GET_YEARS"]
        )

    def _get_view_more_button(self) -> WebElement:
        """
        Get the view more button web element
        :return: View more button web element
        """
        return self.driver.find_element_by_css_selector(
            INVOICE_PAGE_LOCATORS["MORE_BUTTON"]
        )

    def _open_latest_year_invoice_table(self, account_number):
        for retries in range(3):
            try:
                # Fetching 1st element returned
                wait_for_element(
                    self.driver,
                    value=INVOICE_PAGE_LOCATORS["GET_YEARS"],
                    msg="Recent Year Bill & Payment History",
                    retry_attempts=3,
                )
                handle_popup(
                    self.driver,
                    value=HOME_PAGE_LOCATORS["GET_FEEDBACK_BUTTON"],
                    retry_attempts=1,
                )
                self._get_invoice_history_tables()[0].click()
                break
            except WebDriverException as excep:
                LOGGER.warning(f"{excep} found in {self.driver.current_url}")
                if retries == 2:
                    raise
                get_url(
                    self.driver,
                    f"https://www.sce.com/mysce/billsnpayments#viewAccount/{account_number}",
                )

    def _get_invoice_rows(self) -> List[WebElement]:
        """
        Get the invoice rows of web elements
        :return: List of web elements
        """
        return self.driver.find_elements_by_css_selector(
            INVOICE_PAGE_LOCATORS["INVOICE_TABLE_ROWS"]
        )

    @staticmethod
    def _get_invoice_pdf_link(index_inv: int) -> str:
        """
        Get the pdf link locator
        :param index_inv: Row number in index
        :return: PDF link locator
        """
        return (
            "section div#row"
            + str(index_inv)
            + ".row.gridComponent__contentContainer__3v0n4 div "
            "a#viewbill.billingHistoryComponent__sceSmBillingLink__L66XR"
        )

    def get_invoice_table_data(self, run: Run, from_date) -> List[DiscoveredFile]:
        """
        Extracts invoice details from Table
        :param from_date: Invoice start date
        :param run: Run Object
        :return: Returns the list of Discovered Files
        """
        discovered_files = []
        pdf_links_list = []

        if not has_invoices(
            self.driver,
            value=INVOICE_PAGE_LOCATORS["GET_YEARS"],
            retry_attempts=1,
        ):
            return discovered_files

        account_number = self._get_account_number().text
        self._open_latest_year_invoice_table(account_number)

        for index, row in enumerate(self._get_invoice_rows()):
            if "View Bill" not in row.text:
                continue

            columns_values = row.text.split("\n")
            invoice_date = date_from_string(columns_values[0], "%b %d, %Y")
            if invoice_date < from_date:
                LOGGER.info(
                    f"Skipping invoice because date '{invoice_date}' is outside requested range"
                )
                return discovered_files

            pdf_link = self._get_invoice_pdf_link(index)

            reference_code = f"{account_number}_{invoice_date}"

            if pdf_link in pdf_links_list:
                continue

            pdf_links_list.append(pdf_link)

            document_properties = {
                "customer_number": account_number,
                "invoice_date": f"{invoice_date}",
                "restaurant_name": self._get_restaurant_name(),
                "total_amount": columns_values[1],
                "vendor_name": self.vendor_name,
            }
            try:
                # pylint: disable=no-member
                discovered_file = DiscoveredFile.build_unique(
                    run,
                    reference_code,
                    document_type=DocumentType.INVOICE.ident,
                    file_format=FileFormat.PDF.ident,
                    original_download_url=pdf_link,
                    original_filename=f"{reference_code}.pdf",
                    document_properties=document_properties,
                )
            except DiscoveredFile.AlreadyExists:
                LOGGER.info(
                    f"Discovered file already exists with reference code : {reference_code}"
                )
                continue  # skip if seen before
            discovered_files.append(discovered_file)
            LOGGER.info(
                f"Invoice details row data: {discovered_file.document_properties}"
            )

        return discovered_files


class SouthernCaliforniaEdisonInvoiceDetailsPage:
    """Southern California Edison Print Invoices page action methods come here."""

    def __init__(self, driver):
        self.driver = driver

    @retry((FileNotFoundError, WebDriverException), tries=3, delay=2)
    def download_documents_by_link(
        self, download_location: str, discovered_files: List[DiscoveredFile]
    ):
        """
        Downloads the invoice & renames it with the actual invoice Number
        Retries the downloading 3 times in case of exceptions
        :param download_location:
        :param discovered_files: List of Discovered files
        :return: Nothing
        """
        for discovered_file in discovered_files:
            LOGGER.info(f"Navigate to: {discovered_file.original_download_url}")
            try:
                view_bill_button = explicit_wait_till_clickable(
                    self.driver,
                    (By.CSS_SELECTOR, discovered_file.original_download_url),
                )

                _downloader = download.DriverExecuteScriptBasedDownloader(
                    self.driver,
                    script="arguments[0].click();",
                    script_args=(view_bill_button,),
                    local_filepath=download_location,  # pass the download dir, since we're passing a pattern below
                    rename_to=os.path.join(
                        download_location, discovered_file.original_filename
                    ),
                    file_exists_check_kwargs=dict(
                        timeout=20, pattern=r"^[a-z0-9-]+.pdf$"
                    ),
                )
                download.download_discovered_file(discovered_file, _downloader)
            except WEB_DRIVER_EXCEPTIONS:
                LOGGER.info(" Bill is not available at this time ....")


class SouthernCaliforniaEdisonRunner(VendorDocumentDownloadInterface):
    """Runner Class for Southern California Edison"""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.login_page = SouthernCaliforniaEdisonLoginPage(self.driver)
        self.home_page = SouthernCaliforniaEdisonHomePage(self.driver)
        self.invoices_page = SouthernCaliforniaEdisonInvoicesPage(self.driver)
        self.invoice_details_page = SouthernCaliforniaEdisonInvoiceDetailsPage(
            self.driver
        )

    @retry(
        (StaleElementReferenceException, ElementNotInteractableException),
        tries=3,
        delay=1,
    )
    def _login(self):
        """
        Login to Southern California Edison
        :return: Nothing
        """
        login_url = "https://www.sce.com/"
        get_url(self.driver, login_url)
        self.login_page.login(self.run.job.username, self.run.job.password)
        handle_popup(self.driver, value=HOME_PAGE_LOCATORS["GET_FEEDBACK_BUTTON"])
        self.home_page.wait_for_loaders()

    def _goto_download_page(self, document_type: str, index: int):
        """
        Go to download page based on the document type
        :param document_type: Specifies the type of the document eg. Invoice/Statement etc.
        :return:
        """
        if document_type == "invoice":
            self.home_page.go_to_invoices_page(index)
        else:
            raise NotImplementedError(
                f"Requested Document Type is not supported: {document_type}"
            )

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

        LOGGER.info("Download invoice process begins.")
        start_date = datetime.strptime(
            self.run.request_parameters["start_date"], "%Y-%m-%d"
        ).date()
        # Fetching all invoice table date & storing it in memory
        discovered_files_list = self.invoices_page.get_invoice_table_data(
            self.run, start_date
        )

        LOGGER.info(
            f"Total Invoices within date range and download link available: {len(discovered_files_list)}"
        )

        # Download all the invoices
        self.invoice_details_page.download_documents_by_link(
            self.download_location, discovered_files_list
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
            try:
                explicit_wait_till_visibility(
                    self.driver,
                    self.driver.find_element(
                        By.CSS_SELECTOR, HOME_PAGE_LOCATORS["HOME_ACCOUNTS_LINK"]
                    ),
                    msg="Accounts",
                )
                accounts = self.home_page.get_accounts_links()
                LOGGER.info(f"Total accounts found: {len(accounts)}")
                if accounts:
                    for index, _ in enumerate(accounts):
                        self._goto_download_page(
                            self.run.job.requested_document_type, index
                        )
                        discovered_files += self._download_documents()
                        get_url(self.driver, "https://www.sce.com/mysce/myaccount")
                        self.home_page.wait_for_loaders()

            except NoSuchElementException:
                get_url(self.driver, "https://www.sce.com/mysce/billsnpayments")
                handle_popup(
                    self.driver, value=HOME_PAGE_LOCATORS["GET_FEEDBACK_BUTTON"]
                )
                discovered_files += self._download_documents()

        finally:
            self._quit_driver()

        return discovered_files

    def login_flow(self, run: Run):
        self._login()
