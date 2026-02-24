import os
from datetime import date, datetime
from typing import List

from selenium.webdriver.remote.webelement import WebElement

from apps.adapters.base import PasswordBasedLoginPage, VendorDocumentDownloadInterface
from apps.adapters.framework import download
from apps.adapters.helpers.webdriver_helper import (
    scroll_down_to_element,
    wait_for_element,
    has_invoices,
    get_url,
)
from apps.adapters.vendors import LOGGER
from apps.runs.models import Run, DiscoveredFile, DocumentType, FileFormat
from spices.datetime_utils import date_from_string

# Home Page Locators
HOME_PAGE_LOCATORS = {
    "HOMEPAGE_SELECT_ALL_CHECKBOX": 'div[class="k-grid-header-wrap"]>table>thead>tr>th>input[type="checkbox"]',
    "HOMEPAGE_TABLE_ROWS": 'div[class="k-grid-content"]>div>table>tbody>tr',
    "HOMEPAGE_DOWNLOAD_BUTTON": "button.downloadButton",
}

# Easy Import Page Locators
EASY_IMPORT_PAGE_LOCATORS = {
    "EASY_IMPORT_FILE_FORMAT_DROPDOWN": 'form[id="eiForm"]>fieldset>div[class="input"]',
    "EASY_IMPORT_FILE_FORMAT_DROPDOWN_OPTION_CSV_DETAIL": '//li[text()="CSV Detail"]',
    "EASY_IMPORT_FILE_FORMAT_DROPDOWN_OPTION_PDF": '//li[text()="PDF"]',
    "EASY_IMPORT_DOWNLOAD_BUTTON": 'input[id="dnldBnt"]',
}


class BillTrustLoginPage(PasswordBasedLoginPage):
    SELECTOR_USERNAME_TEXTBOX = 'input[id="EUserName"]'
    SELECTOR_PASSWORD_TEXTBOX = 'input[id="EPassword"]'
    SELECTOR_LOGIN_BUTTON = 'form[id="siForm"]>div>input[value="Sign In"]'
    SELECTOR_ERROR_MESSAGE_TEXT = (
        'div[id="siForm-errors"] span[data-msgid^="error"], form#sqForm'
    )


class BillTrustHomePage:
    """Home page action methods come here."""

    def __init__(self, driver, download_location: str):
        self.driver = driver
        self.download_location = download_location
        self.vendor_name = "Regal Wine Co."

    def get_select_all_checkbox(self) -> WebElement:
        """Returns Homepage Select All Checkbox WebElement"""
        return self.driver.find_element_by_css_selector(
            HOME_PAGE_LOCATORS["HOMEPAGE_SELECT_ALL_CHECKBOX"]
        )

    def get_table_rows(self):
        """Returns Homepage Table Row WebElement"""
        return self.driver.find_elements_by_css_selector(
            HOME_PAGE_LOCATORS["HOMEPAGE_TABLE_ROWS"]
        )

    def get_download_button(self) -> WebElement:
        """Returns Download Button WebElement"""
        return self.driver.find_element_by_css_selector(
            HOME_PAGE_LOCATORS["HOMEPAGE_DOWNLOAD_BUTTON"]
        )

    def get_invoice_table_data(self, run: Run, from_date: date) -> List[DiscoveredFile]:
        """
        Extracts invoice details from Table
        :param run: Run Object
        :param from_date: Start date of the invoices to be downloaded
        :return: Returns the list of Discovered Files
        """
        LOGGER.info("Extracting invoice details data from the invoice table.")
        discovered_files = []
        pdf_links_list = []

        if not has_invoices(
            self.driver, value=HOME_PAGE_LOCATORS["HOMEPAGE_TABLE_ROWS"]
        ):
            return discovered_files

        rows = self.get_table_rows()
        index = 12
        for row in rows:
            # This is to scroll the Invoice table
            # If not scrolled the data captured is empty strings
            if row.find_elements_by_tag_name("td")[5].text == "":
                scroll_down_to_element(self.driver, rows[index])
                index += 12

            invoice_date = date_from_string(
                row.find_elements_by_tag_name("td")[5].text, "%m/%d/%y"
            )
            if invoice_date < from_date:
                return discovered_files

            invoice_number = row.find_elements_by_tag_name("td")[4].text
            if not invoice_number:
                continue

            pdf_link = row.find_element_by_tag_name("a").get_attribute("href")
            if pdf_link == "javascript:" or pdf_link in pdf_links_list:
                continue

            pdf_links_list.append(pdf_link)
            reference_code = row.get_attribute("data-id")

            document_properties = {
                "customer_number": None,
                "invoice_number": invoice_number,
                "invoice_date": str(invoice_date),
                "due_date": str(
                    date_from_string(
                        row.find_elements_by_tag_name("td")[6].text.strip(), "%m/%d/%y"
                    )
                ),
                "total_amount": row.find_elements_by_tag_name("td")[8].text,
                "vendor_name": self.vendor_name,
                "restaurant_name": row.find_elements_by_tag_name("td")[3].text,
            }
            try:
                # pylint: disable=no-member
                discovered_file = DiscoveredFile.build_unique(
                    run,
                    reference_code,
                    document_type=DocumentType.INVOICE.ident,
                    file_format=FileFormat.PDF.ident,
                    original_download_url=pdf_link,
                    original_filename=f"invoice_{invoice_number}.pdf",
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


class BillTrustEasyImportPage:
    """Home page action methods come here."""

    def __init__(self, driver, download_location):
        self.driver = driver
        self.download_location = download_location

    def get_file_format_dropdown(self) -> WebElement:
        """Returns File Format DropDown WebElement"""
        return self.driver.find_element_by_css_selector(
            EASY_IMPORT_PAGE_LOCATORS["EASY_IMPORT_FILE_FORMAT_DROPDOWN"]
        )

    def get_file_format_dropdown_option_csv_detail(self) -> WebElement:
        """Returns File Format DropDown Option 'CSV Detail' WebElement"""
        return self.driver.find_element_by_xpath(
            EASY_IMPORT_PAGE_LOCATORS[
                "EASY_IMPORT_FILE_FORMAT_DROPDOWN_OPTION_CSV_DETAIL"
            ]
        )

    def get_file_format_dropdown_option_pdf(self) -> WebElement:
        """Returns File Format DropDown Option 'CSV Detail' WebElement"""
        return self.driver.find_element_by_xpath(
            EASY_IMPORT_PAGE_LOCATORS["EASY_IMPORT_FILE_FORMAT_DROPDOWN_OPTION_PDF"]
        )

    def get_download_button(self) -> WebElement:
        """Returns Download Button WebElement"""
        return self.driver.find_element_by_css_selector(
            EASY_IMPORT_PAGE_LOCATORS["EASY_IMPORT_DOWNLOAD_BUTTON"]
        )

    def download_documents_by_link(self, discovered_files: List[DiscoveredFile]):
        """Download all discovered files and set appropriate attributes on them"""
        for discovered_file in discovered_files:
            _downloader = download.DriverBasedUrlGetDownloader(
                self.driver,
                download_url=discovered_file.original_download_url,
                local_filepath=os.path.join(
                    self.download_location, discovered_file.original_filename
                ),
            )
            download.download_discovered_file(discovered_file, _downloader)


class BillTrustRunner(VendorDocumentDownloadInterface):
    """Runner Class for Bill Trust"""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.login_page = BillTrustLoginPage(self.driver)
        self.home_page = BillTrustHomePage(self.driver, self.download_location)
        self.easy_import_page = BillTrustEasyImportPage(
            self.driver, self.download_location
        )

    def _login(self):
        """
        Login to Southern Wine Online
        :return: Nothing
        """
        login_url = "https://secure.billtrust.com/regalbillpay/ig/signin"
        get_url(self.driver, url=login_url)
        self.login_page.login(self.run.job.username, self.run.job.password)
        wait_for_element(
            self.driver,
            value=HOME_PAGE_LOCATORS["HOMEPAGE_SELECT_ALL_CHECKBOX"],
            msg="Select All Checkbox",
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
        # Fetching all invoice table date & storing it in memory
        discovered_files_list = self.home_page.get_invoice_table_data(
            self.run, start_date
        )

        LOGGER.info(
            f"Total Invoices within date range and download link available: {len(discovered_files_list)}"
        )

        # Download all the invoices
        self.easy_import_page.download_documents_by_link(discovered_files_list)

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

            discovered_files += self._download_documents()
        finally:
            self._quit_driver()

        return discovered_files

    def login_flow(self, run: Run):
        self._login()
