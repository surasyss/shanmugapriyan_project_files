import os
from datetime import datetime, date
from typing import List

from selenium.webdriver.remote.webelement import WebElement

from apps.adapters.base import PasswordBasedLoginPage, VendorDocumentDownloadInterface
from apps.adapters.framework import download
from apps.adapters.helpers.webdriver_helper import (
    explicit_wait_till_visibility,
    get_url,
)
from apps.runs.models import Run, DiscoveredFile, DocumentType, FileFormat
from integrator import LOGGER
from spices.datetime_utils import date_from_string

# Home Page Locators
HOME_PAGE_LOCATORS = {
    "ACCOUNT_LINK": "a.ButtonContent",
    "CURRENT_BALANCE": "span.AccountBalance",
}

# Account summary Locators
ACCOUNT_SUMMARY_LOCATORS = {
    "BILL_HISTORY": "Bill History",
    "RESTAURANT_NAME": "div.Entity h2",
    "ACCOUNT_NUMBER": "div.Entity p.MarginNone",
    "BILL_HISTORY_HEADER": "div[id=Content]",
    "INVOICE_LINKS": "div.ColumnLayout a.LinkNewWindow",
    "INVOICE_LINK": "a.LinkNewWindow",
    "INVOICE_ROWS": "div.ColumnLayout",
}


class WaterDistrictLoginPage(PasswordBasedLoginPage):
    """Water District Login Page Web Elements"""

    SELECTOR_USERNAME_TEXTBOX = 'input[id="Username"]'
    SELECTOR_PASSWORD_TEXTBOX = 'input[id="Password"]'
    SELECTOR_LOGIN_BUTTON = "input.ButtonPrimary"
    SELECTOR_ERROR_MESSAGE_TEXT = "div.HighlightError ul li"


class WaterDistrictHomePage:
    """Water District Home page action methods come here."""

    def __init__(self, driver):
        self.driver = driver

    def get_account_link(self) -> List[WebElement]:
        """Return the account link element"""
        return self.driver.find_elements_by_css_selector(
            HOME_PAGE_LOCATORS["ACCOUNT_LINK"]
        )

    def get_account_links(self) -> List:
        """Return Account links list"""
        accounts = self.get_account_link()
        account_links = []
        for account in accounts:
            account_links.append(account.get_attribute("href"))
        return account_links


class WaterDistrictAccountSummaryPage:
    """Water District Account summary page action methods come here."""

    def __init__(self, driver, download_location):
        self.driver = driver
        self.download_location = download_location
        self.vendor_name = "Las Vegas Valley Water District"

    def get_bill_history_link(self) -> WebElement:
        """Return Web Element for Bill History"""
        return self.driver.find_elements_by_link_text(
            ACCOUNT_SUMMARY_LOCATORS["BILL_HISTORY"]
        )

    def get_bill_history_tab(self) -> WebElement:
        """Return Bill History Header Web element"""
        return self.driver.find_element_by_css_selector(
            ACCOUNT_SUMMARY_LOCATORS["BILL_HISTORY_HEADER"]
        )

    def navigate_to_bill_history(self):
        """Navigates to the Account Billing summary page"""
        billing_summary_url = "https://myaccount.lvvwd.com/bill-history.cfml"
        get_url(self.driver, billing_summary_url)
        explicit_wait_till_visibility(
            self.driver, self.get_bill_history_tab(), msg="Bill History Header"
        )

    def get_restaurant_name(self) -> WebElement:
        """Return Restaurant name Web Element"""
        return self.driver.find_element_by_css_selector(
            ACCOUNT_SUMMARY_LOCATORS["RESTAURANT_NAME"]
        )

    def get_account_number(self) -> WebElement:
        """Return Account Number Web Element"""
        return self.driver.find_element_by_css_selector(
            ACCOUNT_SUMMARY_LOCATORS["ACCOUNT_NUMBER"]
        )

    def get_invoice_rows(self) -> List[WebElement]:
        """Return invoice row web element list"""
        return self.driver.find_elements_by_css_selector(
            ACCOUNT_SUMMARY_LOCATORS["INVOICE_ROWS"]
        )

    def get_invoice_links(self) -> List[WebElement]:
        """Return invoice links web element list"""
        return self.driver.find_elements_by_css_selector(
            ACCOUNT_SUMMARY_LOCATORS["INVOICE_LINKS"]
        )

    def save_invoices_link(self) -> List:
        """Save the invoice lists links of Account Summary Page"""
        invoice_download_links = []
        for invoice_link in self.get_invoice_links():
            invoice_download_links.append(f'{invoice_link.get_attribute("href")}')
        return invoice_download_links

    def get_view_link(self) -> WebElement:
        """Return the  invoice downloadable link"""
        return self.driver.find_element_by_css_selector("form[method=POST]")

    def get_invoice_table_data(self, run: Run, from_date: date) -> List[DiscoveredFile]:
        """
        Extracts invoice details from Table
        :param run: Run Object
        :param from_date: Start date of the invoices to be downloaded
        :return: Returns the list of Discovered File
        """
        discovered_files = []

        for invoice_row in self.get_invoice_rows():  # pylint: disable=unused-variable
            invoice_date = date_from_string(invoice_row.text.split("\n")[0], "%m/%d/%Y")

            if invoice_date < from_date:
                return discovered_files
            account_number = self.get_account_number().text.split(": ")[1]
            reference_code = f"{account_number}_{invoice_date}"

            pdf_link = invoice_row.find_element_by_css_selector(
                ACCOUNT_SUMMARY_LOCATORS["INVOICE_LINK"]
            ).get_attribute("href")

            document_properties = {
                "invoice_number": reference_code,
                "customer_number": account_number,
                "invoice_date": f"{invoice_date}",
                "total_amount": invoice_row.text.split("\n")[1],
                "vendor_name": self.vendor_name,
                "restaurant_name": self.get_restaurant_name().text,
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
                "Invoice details row data: %s", str(discovered_file.document_properties)
            )
        return discovered_files

    def download_invoice_by_click(self, discovered_files):
        """
        Download the File in PDF format
        :param discovered_files: DiscoveredFiles variable
        """
        for discovered_file in discovered_files:
            get_url(self.driver, discovered_file.original_download_url)
            explicit_wait_till_visibility(
                self.driver, self.get_view_link(), msg="View Link"
            )

            _downloader = download.DriverBasedUrlGetDownloader(
                self.driver,
                download_url=self.get_view_link().get_attribute("action"),
                local_filepath=f"{self.download_location}/Statement.pdf",
                rename_to=os.path.join(
                    self.download_location, discovered_file.original_filename
                ),
                file_exists_check_kwargs=dict(timeout=20),
            )
            download.download_discovered_file(discovered_file, _downloader)


class WaterDistrictRunner(VendorDocumentDownloadInterface):
    """Runner Class for Water District Vendor"""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.login_page = WaterDistrictLoginPage(self.driver)
        self.home_page = WaterDistrictHomePage(self.driver)
        self.account_summary = WaterDistrictAccountSummaryPage(
            self.driver, self.download_location
        )

    def _login(self):
        """
        Login using credentials
        :return: Nothing
        """
        login_url = "https://myaccount.lvvwd.com/"
        get_url(self.driver, login_url)
        self.login_page.login(self.run.job.username, self.run.job.password)
        explicit_wait_till_visibility(
            self.driver, self.home_page.get_account_link()[0], msg="Account Summary"
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
        LOGGER.info("Extracting data from table...")
        start_date = datetime.strptime(
            self.run.request_parameters["start_date"], "%Y-%m-%d"
        ).date()

        discovered_files_list = self.account_summary.get_invoice_table_data(
            self.run, start_date
        )
        LOGGER.info(
            f"Total Invoices within date range and download link available: {len(discovered_files_list)}"
        )

        LOGGER.info(
            f"Downloading invoice with download link available: {len(discovered_files_list)}"
        )
        self.account_summary.download_invoice_by_click(discovered_files_list)

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
            for account in self.home_page.get_account_links():
                get_url(self.driver, account)
                explicit_wait_till_visibility(
                    self.driver,
                    self.account_summary.get_account_number(),
                    msg="Account summary page to load",
                )
                self.account_summary.navigate_to_bill_history()
                discovered_files += self._download_documents()
        finally:
            self._quit_driver()

        return discovered_files

    def login_flow(self, run: Run):
        self._login()
