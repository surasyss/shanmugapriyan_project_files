import datetime
import os
from typing import List
from retry.api import retry
from datetime import date

from selenium.webdriver.remote.webelement import WebElement
from selenium.common.exceptions import TimeoutException, JavascriptException

from apps.adapters.base import (
    VendorDocumentDownloadInterface,
    PasswordBasedLoginPage,
    get_end_invoice_date,
)
from apps.adapters.framework import download
from apps.adapters.helpers.webdriver_helper import (
    get_url,
    select_dropdown_option_by_value,
    WEB_DRIVER_EXCEPTIONS,
    wait_for_ajax,
    explicit_wait_till_invisibility,
    explicit_wait_till_visibility,
    has_invoices,
)
from apps.adapters.vendors import LOGGER
from apps.runs.models import Run, DiscoveredFile, DocumentType, FileFormat
from spices.datetime_utils import date_from_string

# Home Page Locators
HOME_PAGE_LOCATORS = {
    "SELECT_ACCOUNT_TAB": 'select[id="SelectAccount"]',
    "INVOICES_LOC": 'a[id="nav-invoice"]',
}

# Invoices Page Locators
INVOICE_PAGE_LOCATORS = {
    "INVOICE_TABLE": 'table[id="grid"] tr',
    "INVOICE_TABLE_ROW": 'table[id="grid"] > tbody > tr',
    "ACCOUNT_NAME": "section.select-account div.row h3",
}


class AlscoLoginPage(PasswordBasedLoginPage):
    """
    Alsco login module
    """

    SELECTOR_USERNAME_TEXTBOX = 'input[id="UserName"]'
    SELECTOR_PASSWORD_TEXTBOX = 'input[id="Password"]'
    SELECTOR_LOGIN_BUTTON = 'input[name="login"]'
    SELECTOR_ERROR_MESSAGE_TEXT = "div.validation-summary-errors"


class AlscoHomePage:
    """Alsco Home page action methods come here."""

    def __init__(self, driver):
        self.driver = driver

    def select_account_tab(self) -> WebElement:
        """Select the account tab web elements."""
        return self.driver.find_element_by_css_selector(
            HOME_PAGE_LOCATORS["SELECT_ACCOUNT_TAB"]
        )

    def get_option_values(self):
        """Get all the available account option values"""
        option_values = []
        try:
            options = list(
                self.select_account_tab().find_elements_by_tag_name("option")
            )
            for elem in options:
                option_value = elem.get_attribute("value")
                LOGGER.info("Dropdown options: %s", option_value)
                if option_value == "" or int(option_value) <= -1:
                    continue
                option_values.append(option_value)
        except WEB_DRIVER_EXCEPTIONS:
            LOGGER.info(
                "Error in the home page. It does not found the accounts of drop down id."
            )
        LOGGER.info("Returning %s", option_values)
        return option_values


class AlscoInvoicesPage:
    """Alsco Invoices page action methods come here."""

    def __init__(self, driver, download_location):
        self.driver = driver
        self.vendor_name = "ALSCO"
        self.download_location = download_location

    def get_invoice_table_rows(self) -> [WebElement]:
        """Get the invoice table of rows of web elements."""
        return self.driver.find_elements_by_css_selector(
            INVOICE_PAGE_LOCATORS["INVOICE_TABLE_ROW"]
        )

    def get_account_info(self) -> WebElement:
        """Get the account information of the web elements."""
        return self.driver.find_element_by_css_selector(
            INVOICE_PAGE_LOCATORS["ACCOUNT_NAME"]
        )

    @staticmethod
    def format_date(date_string):
        date_string = date_string.replace("-", "/")
        dt, month, year = date_string.split("/")

        if (int(year) == date.today().year and int(dt) > date.today().month) or int(
            dt
        ) > 12:
            return date_from_string(date_string, "%d/%m/%Y")

        return date_from_string(date_string, "%m/%d/%Y")

    def get_invoice_table_data(
        self, run: Run, from_date, end_date
    ) -> List[DiscoveredFile]:
        """
        Extracts invoice details from Table
        :param from_date: Invoice start date
        :param end_date: Invoice end date
        :param run: Run Object
        :return: Returns the list of Discovered Files
        """
        discovered_files = []
        collected_invoices = []
        for row in self.get_invoice_table_rows():
            cols = row.find_elements_by_tag_name("td")
            invoice_date = AlscoInvoicesPage.format_date(cols[1].text)

            if not from_date <= invoice_date <= end_date:
                LOGGER.info(
                    f"Skipping invoice because date '{invoice_date}' is outside requested range"
                )
                return discovered_files

            pdf_link = cols[0].find_element_by_tag_name("a").get_attribute("href")

            _, customer_number, restaurant_name = self.get_account_info().text.split(
                "-", maxsplit=2
            )
            invoice_number = cols[0].text
            total_amount = cols[2].text

            current_invoice = f"{invoice_number}_{invoice_date}_{total_amount}"

            if current_invoice in collected_invoices:
                LOGGER.info(
                    f"Invoice with invoice number {invoice_number} was already found in the run."
                )
                continue
            collected_invoices.append(current_invoice)

            reference_code = customer_number.strip() + "_" + invoice_number

            document_properties = {
                "customer_number": customer_number.strip(),
                "invoice_number": invoice_number,
                "total_amount": total_amount,
                "invoice_date": f"{invoice_date}",
                "restaurant_name": restaurant_name.strip(),
                "vendor_name": self.vendor_name,
            }

            try:
                discovered_file = DiscoveredFile.build_unique(
                    run,
                    reference_code,
                    document_type=DocumentType.INVOICE.ident,  # pylint: disable=no-member
                    file_format=FileFormat.PDF.ident,  # pylint: disable=no-member
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

    @retry(TimeoutException, tries=5, delay=2)
    def download_documents_by_link(self, discovered_files: List[DiscoveredFile]):
        """
        Downloads the invoice & renames it with the actual invoice Number
        :param discovered_files: list of Discovered file
        :return: Nothing
        """
        for discovered_file in discovered_files:
            _downloader = download.DriverBasedUrlGetDownloader(
                self.driver,
                download_url=discovered_file.original_download_url,
                local_filepath=f'{self.download_location}/{discovered_file.document_properties["invoice_number"]}.pdf',
                rename_to=os.path.join(
                    self.download_location, discovered_file.original_filename
                ),
                file_exists_check_kwargs=dict(timeout=40),
            )
            download.download_discovered_file(discovered_file, _downloader)

            try:
                wait_for_ajax(self.driver)
            except JavascriptException as js_excep:
                LOGGER.info(js_excep)


class AlscoRunner(VendorDocumentDownloadInterface):
    """Runner Class for Alsco"""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.login_page = AlscoLoginPage(self.driver)
        self.home_page = AlscoHomePage(self.driver)
        self.invoices_page = AlscoInvoicesPage(self.driver, self.download_location)

    def _login(self):
        """
        Login to cox business
        :return: Nothing
        """
        login_url = "https://atrack.alsco.com/Account/Login"
        get_url(self.driver, login_url)
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
        LOGGER.info("Download invoice process begins.")
        start_date = datetime.datetime.strptime(
            self.run.request_parameters["start_date"], "%Y-%m-%d"
        ).date()
        end_date = get_end_invoice_date(self.run)
        # Fetching all invoice table date & storing it in memory
        discovered_files_list = self.invoices_page.get_invoice_table_data(
            self.run, start_date, end_date
        )
        LOGGER.info(
            f"Total Invoices within date range and download link available: {len(discovered_files_list)}"
        )
        self.invoices_page.download_documents_by_link(discovered_files_list)
        return discovered_files_list

    def start_documents_download_flow(self, run: Run) -> List[DiscoveredFile]:
        """
        Initiates the Document Download Workflow
        :param run: Run Object
        :return: Returns the list of Discovered Files.
        """
        discovered_files = []
        try:
            self._login()

            if "ChangePassword" in self.driver.current_url:
                get_url(self.driver, "https://atrack.alsco.com/")

            for index, opt_val in enumerate(self.home_page.get_option_values()):
                select_dropdown_option_by_value(
                    self.home_page.select_account_tab(), opt_val
                )
                if index > 0:
                    try:
                        self.wait_for_invoice_table()
                    except WEB_DRIVER_EXCEPTIONS:
                        self.driver.back()
                        continue

                if has_invoices(
                    self.driver, value=INVOICE_PAGE_LOCATORS["INVOICE_TABLE_ROW"]
                ):
                    discovered_files += self._download_documents()
        finally:
            self._quit_driver()
        return discovered_files

    def wait_for_invoice_table(self):
        for index in range(3):
            try:
                explicit_wait_till_invisibility(
                    self.driver,
                    self.driver.find_element_by_css_selector(
                        INVOICE_PAGE_LOCATORS["INVOICE_TABLE"]
                    ),
                    timeout=30,
                    msg="Invisibility of Invoice Table",
                )
                explicit_wait_till_visibility(
                    self.driver,
                    self.driver.find_element_by_css_selector(
                        INVOICE_PAGE_LOCATORS["INVOICE_TABLE"]
                    ),
                    timeout=30,
                    msg="Visibility of Invoice Table",
                )
                break
            except WEB_DRIVER_EXCEPTIONS as excep:
                LOGGER.warning(f"{excep} found in {self.driver.current_url}")
                if index == 2:
                    raise

    def login_flow(self, run: Run):
        self._login()
