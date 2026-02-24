import os
from datetime import date, datetime
from typing import List

from selenium.webdriver.remote.webelement import WebElement
from selenium.webdriver.common.by import By
from selenium.webdriver.support.select import Select
from selenium.common.exceptions import WebDriverException

from apps.adapters.base import VendorDocumentDownloadInterface, PasswordBasedLoginPage
from apps.adapters.framework import download
from apps.adapters.helpers.webdriver_helper import (
    explicit_wait_till_visibility,
    IGNORED_EXCEPTIONS,
    wait_for_element,
)
from apps.adapters.vendors import LOGGER
from apps.runs.models import Run, DiscoveredFile, FileFormat
from spices.datetime_utils import date_from_string
from spices.documents import DocumentType

# Home Page Locators
HOME_PAGE_LOCATORS = {
    "LOADER": "div.rsx-spinner-wrapper svg.loading-circle",
    "ACCOUNT_DROPDOWN": 'select[id="AccountsID"]',
    "ACCOUNT_DROPDOWN_OPTIONS": 'select[id="AccountsID"] option',
    "TABLES": "div.tblWrapper table.table tbody",
}


class TigerNaturalGasLoginPage(PasswordBasedLoginPage):
    """Login page Locators"""

    SELECTOR_USERNAME_TEXTBOX = 'input[id="Email"]'
    SELECTOR_PASSWORD_TEXTBOX = 'input[id="Password"]'
    SELECTOR_LOGIN_BUTTON = "div.form-group input.btn"
    SELECTOR_ERROR_MESSAGE_TEXT = "div.validation-summary-errors"


class TigerNaturalGasHomePage:
    """Tiger Natural Gas home page action methods."""

    def __init__(self, driver, download_location):
        self.driver = driver
        self.download_location = download_location
        self.vendor_name = "Tiger Natural Gas"

    def get_account_dropdown(self) -> WebElement:
        """Return account drop down web element"""
        return self.driver.find_element_by_css_selector(
            HOME_PAGE_LOCATORS["ACCOUNT_DROPDOWN"]
        )

    def get_account_dropdown_options(self) -> List[WebElement]:
        """Return restaurant account list in account drop down"""
        return self.driver.find_elements_by_css_selector(
            HOME_PAGE_LOCATORS["ACCOUNT_DROPDOWN_OPTIONS"]
        )

    def get_account_dropdown_options_list(self) -> List:
        """Return the list of Dropdown text for restaurant account"""
        account_list = []
        for account in self.get_account_dropdown_options():
            account_list.append(account.text)
        return account_list

    def get_invoice_table(self) -> WebElement:
        return self.driver.find_elements_by_css_selector(HOME_PAGE_LOCATORS["TABLES"])[
            1
        ]

    def get_account_information_table(self) -> WebElement:
        return self.driver.find_elements_by_css_selector(HOME_PAGE_LOCATORS["TABLES"])[
            0
        ]

    def get_invoice_table_data(
        self, run: Run, from_date: date, customer_id: str
    ) -> List[DiscoveredFile]:
        """
        Extracts invoice details from Table
        :param run: Run Object
        :param from_date: Start date of the invoices to be downloaded
        :param customer_id: Customer Id
        :return: Returns the list of Discovered File
        """

        discovered_files = []

        invoice_table_rows = self.get_invoice_table().find_elements_by_css_selector(
            "tr"
        )
        restaurant_name = (
            self.get_account_information_table()
            .find_elements_by_css_selector("tr")[0]
            .text
        )

        if "Customer Name:" in restaurant_name:
            restaurant_name = restaurant_name.split("Customer Name:")[1].strip()

        if len(invoice_table_rows) < 1:
            return discovered_files

        for row in invoice_table_rows:

            explicit_wait_till_visibility(
                self.driver,
                row,
                20,
                msg="Wait for invoice table to load",
                ignored_exceptions=IGNORED_EXCEPTIONS,
            )

            invoice_date = date_from_string(
                row.find_elements_by_tag_name("td")[0].text, "%m/%d/%Y"
            )

            if invoice_date < from_date:
                LOGGER.info(
                    f"Skipping invoices because date '{invoice_date}' is outside requested range"
                )
                return discovered_files

            invoice_number = row.find_elements_by_tag_name("td")[1].text
            reference_code = f"{customer_id}_{invoice_number}"

            document_properties = {
                "invoice_number": invoice_number,
                "customer_number": customer_id,
                "invoice_date": row.find_elements_by_tag_name("td")[0].text,
                "total_amount": row.find_elements_by_tag_name("td")[2].text,
                "vendor_name": self.vendor_name,
                "restaurant_name": restaurant_name,
            }
            try:
                # pylint: disable=no-member
                discovered_file = DiscoveredFile.build_unique(
                    run,
                    reference_code,
                    document_type=DocumentType.INVOICE.ident,
                    file_format=FileFormat.PDF.ident,
                    original_download_url=row.find_element_by_css_selector(
                        "td a"
                    ).get_attribute("href"),
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

    def download_invoice_by_url(self, discovered_files: list):
        """
        Download the File in PDF format
        :param discovered_files: DiscoveredFile variable
        :param download_location: Location to store invoice
        """
        for discovered_file in discovered_files:
            _downloader = download.DriverBasedUrlGetDownloader(
                self.driver,
                download_url=discovered_file.original_download_url,
                local_filepath=f"{self.download_location}/Tiger_Invoice.pdf",
                rename_to=os.path.join(
                    self.download_location, discovered_file.original_filename
                ),
                file_exists_check_kwargs=dict(timeout=30),
            )
            download.download_discovered_file(discovered_file, _downloader)


class TigerNaturalGasRunner(VendorDocumentDownloadInterface):
    """Runner Class for Tiger Natural Gas Online"""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.login_page = TigerNaturalGasLoginPage(self.driver)
        self.home_page = TigerNaturalGasHomePage(self.driver, self.download_location)

    def _login(self):
        """
        Login to Tiger Natural Gas
        :return: Nothing
        """
        login_url = "https://customerportal.tigernaturalgas.com/Account/Login"
        LOGGER.info(f"Navigating to {login_url}")
        self.driver.get(login_url)
        self.login_page.login(self.run.job.username, self.run.job.password)
        wait_for_element(
            self.driver, value="form#logoutForm", retry_attempts=2, msg="Log Out"
        )

    def _download_documents(self, customer_id) -> List[DiscoveredFile]:
        """
        Chooses the documents to be downloaded based on the document type
        :return: Returns the list of Discovered Files
        """
        document_type = self.run.job.requested_document_type
        if document_type == "invoice":
            return self._download_invoices(customer_id)

        raise NotImplementedError(
            f"Requested Document Type is not supported: {document_type}"
        )

    def _download_invoices(self, customer_id) -> List[DiscoveredFile]:
        """
        Downloads the Invoices
        :return: Returns the list of the Discovered Files
        """

        LOGGER.info("Download invoice process begins.")
        start_date = datetime.strptime(
            self.run.request_parameters["start_date"], "%Y-%m-%d"
        ).date()

        # Fetching all invoice table date & storing it in memory
        discovered_files_list = self.home_page.get_invoice_table_data(
            self.run, start_date, customer_id
        )

        LOGGER.info(
            f"Total Invoices within date range and download link available: {len(discovered_files_list)}"
        )
        self.home_page.download_invoice_by_url(discovered_files_list)

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
                wait_for_element(
                    self.driver,
                    value=HOME_PAGE_LOCATORS["ACCOUNT_DROPDOWN"],
                    retry_attempts=2,
                    msg="Accounts Dropdown",
                )

                accounts = self.home_page.get_account_dropdown_options_list()
                for account in accounts[1:]:
                    select = Select(self.home_page.get_account_dropdown())
                    customer_id = account
                    select.select_by_visible_text(account)
                    discovered_files += self._download_documents(customer_id)

            except WebDriverException as excep:
                LOGGER.info(f"Accounts Dropdown not found: {excep}")

                customer_id = self.driver.find_element(
                    By.XPATH,
                    "//td[contains(text(),'Customer Number:')]/following-sibling::td",
                )
                discovered_files += self._download_documents(customer_id.text)
        finally:
            self._quit_driver()

        return discovered_files

    def login_flow(self, run: Run):
        self._login()
