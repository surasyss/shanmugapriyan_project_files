import os
from datetime import datetime
from typing import List

from selenium.webdriver.common.by import By
from selenium.common.exceptions import WebDriverException
from selenium.webdriver.remote.webelement import WebElement

from apps.adapters.base import VendorDocumentDownloadInterface, PasswordBasedLoginPage
from apps.adapters.helpers.webdriver_helper import (
    WEB_DRIVER_EXCEPTIONS,
    wait_for_element,
    get_url,
    scroll_down,
    wait_for_loaders,
)
from apps.adapters.framework import download
from apps.adapters.vendors import LOGGER
from apps.runs.models import Run, DiscoveredFile, DocumentType, FileFormat
from spices.datetime_utils import date_from_string


# Home page Locators
HOME_PAGE_ELEMENT = {"BILLING": "div.navbar-brand > ul > li > a"}

# Invoices Page Locators
INVOICE_TABLE_ELEMENT = {
    "INVOICE_TABLE_ROWS": "table.granite-table tbody tr[rr5-search-result-header]",
    "SHOW_MORE_RESULTS": "//button[text()='show more results']",
    "DATE_COLUMN_HEADER": "//button[contains(text(),'Date')]",
}


class GranitesPaymentPortalLoginWebPage(PasswordBasedLoginPage):
    """granites payment portal Login Page Web Elements."""

    SELECTOR_USERNAME_TEXTBOX = "#UserName"
    SELECTOR_PASSWORD_TEXTBOX = "#Password"
    SELECTOR_LOGIN_BUTTON = 'button[type="submit"]'
    SELECTOR_ERROR_MESSAGE_TEXT = "div.text-danger.validation-summary-errors > ul > li"


class GranitesPaymentPortalHomePage:
    """granites payment portal home page action methods come here"""

    def __init__(self, driver):
        super().__init__()
        self.driver = driver

    def get_billing(self) -> WebElement:
        """Return invoice billing option web element."""
        for index in range(3):
            try:
                wait_for_element(
                    self.driver,
                    value=HOME_PAGE_ELEMENT["BILLING"],
                    msg="wait for billing",
                )
                return self.driver.find_element_by_css_selector(
                    HOME_PAGE_ELEMENT["BILLING"]
                )
            except WebDriverException as excep:
                LOGGER.warning(f"{excep} found in {self.driver.current_url}")
                get_url(self.driver, "https://rockreports.granitenet.com/dashboard")
                if index == 2:
                    raise


class GranitesPaymentPortalInvoicesPage:
    """granites payment portal Invoices page action methods come here"""

    def __init__(self, driver, download_location: str):
        super().__init__()
        self.driver = driver
        self.download_location = download_location
        self.vendor_name = "Granite Telecommunications"

    def show_more_results(self) -> WebElement:
        """Return show more result web element or none"""
        try:
            scroll_down(self.driver)
            wait_for_element(
                self.driver,
                by_selector=By.XPATH,
                value=INVOICE_TABLE_ELEMENT["SHOW_MORE_RESULTS"],
                msg="show more results",
                raise_exception=False,
                retry_attempts=2,
            )
            return self.driver.find_element_by_xpath(
                INVOICE_TABLE_ELEMENT["SHOW_MORE_RESULTS"]
            )
        except WEB_DRIVER_EXCEPTIONS:
            LOGGER.info("button get invisible ....")

    def get_invoice_table_rows(self) -> [WebElement]:
        """Return invoice table row list"""
        for index in range(3):
            try:
                wait_for_element(
                    self.driver,
                    value=INVOICE_TABLE_ELEMENT["INVOICE_TABLE_ROWS"],
                    msg="invoice table row",
                    retry_attempts=3,
                )
                return self.driver.find_elements_by_css_selector(
                    INVOICE_TABLE_ELEMENT["INVOICE_TABLE_ROWS"]
                )
            except WebDriverException as excep:
                LOGGER.warning(f"{excep} found in {self.driver.current_url}")
                if index == 2:
                    raise
                get_url(self.driver, "https://rockreports.granitenet.com/billing")

    def get_table_data(self, run: Run, from_date):
        """Extracts invoice details from Table
        :return: Returns the list of Discovered File
        """
        discovered_files = []

        for idx in range(3):
            try:
                wait_for_element(
                    self.driver,
                    by_selector=By.XPATH,
                    value=INVOICE_TABLE_ELEMENT["DATE_COLUMN_HEADER"],
                    msg="Date Column Header",
                    retry_attempts=2,
                )
                # sort by invoice date
                self.driver.find_element_by_xpath(
                    INVOICE_TABLE_ELEMENT["DATE_COLUMN_HEADER"]
                ).click()
                break
            except WebDriverException:
                LOGGER.info(
                    f"Date column header not found in {self.driver.current_url}"
                )
                if idx == 2:
                    LOGGER.info("Invoice table not found.")
                    return discovered_files
                get_url(self.driver, "https://rockreports.granitenet.com/billing")

        while True:
            if self.show_more_results() is None:
                break
            self.show_more_results().click()

        for index, row in enumerate(self.get_invoice_table_rows()):
            first_date = row.find_element_by_css_selector("td:nth-child(2)").text
            invoice_date = date_from_string(first_date, "%m/%d/%Y")

            if invoice_date < from_date:
                LOGGER.info(
                    f"Skipping remaining invoice because date '{invoice_date}' is outside requested range"
                )
                return discovered_files

            invoice_number_element = row.find_element_by_css_selector("td > a")
            invoice_number = invoice_number_element.text
            original_download_url = invoice_number_element.get_attribute("href")

            account_number = row.find_element_by_css_selector(
                "td:nth-child(4)"
            ).text.strip()
            restaurant_name = row.find_element_by_css_selector(
                "td:nth-child(5)"
            ).text.strip()
            total_amount = row.find_element_by_css_selector("td:nth-child(7)").text
            original_filename = (
                f"{first_date}_{account_number}_{invoice_number}".replace(
                    "/", ""
                ).lstrip("0")
            )

            # make reference_code
            reference_code = f"{account_number}_{invoice_number}_{invoice_date}"

            document_properties = {
                "customer_number": account_number,
                "invoice_number": invoice_number,
                "invoice_date": f"{invoice_date}",
                "total_amount": total_amount,
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
                    original_download_url=original_download_url,
                    original_filename=f"{original_filename}.pdf",
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

    def download_documents_by_link(self, discovered_file):
        """
        Downloads the invoice & renames it with the actual invoice Number
        :param discovered_file: Discovered file
        :return: Nothing
        """
        LOGGER.info(f"Navigate to: {discovered_file.original_download_url}")
        _downloader = download.DriverBasedUrlGetDownloader(
            self.driver,
            download_url=discovered_file.original_download_url,
            local_filepath=os.path.join(
                self.download_location, discovered_file.original_filename
            ),
            file_exists_check_kwargs=dict(timeout=20),
        )
        download.download_discovered_file(discovered_file, _downloader)


class GranitesPaymentPortalRunner(VendorDocumentDownloadInterface):
    """Runner Class for granites payment portal."""

    # uses_proxy = True

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.login_page = GranitesPaymentPortalLoginWebPage(self.driver)
        self.home_page = GranitesPaymentPortalHomePage(self.driver)
        self.invoices_page = GranitesPaymentPortalInvoicesPage(
            self.driver, self.download_location
        )

    def _login(self):
        """
        Login to sherwin williams
        :return: Nothing
        """
        login_url = "https://rockreports.granitenet.com/"
        get_url(self.driver, login_url)
        self.login_page.login(self.run.job.username, self.run.job.password)

    def _download_invoices(self) -> List[DiscoveredFile]:
        """
        Downloads the Invoice json
        :return: Returns the list of the Discovered Files
        """
        LOGGER.info("Extracting data from table...")
        start_date = datetime.strptime(
            self.run.request_parameters["start_date"], "%Y-%m-%d"
        ).date()
        discovered_files_list = self.invoices_page.get_table_data(self.run, start_date)
        for discovered_file in discovered_files_list:
            self.invoices_page.download_documents_by_link(
                discovered_file,
            )
        LOGGER.info(
            f"Total Invoices within date range and download link available: {len(discovered_files_list)}"
        )
        return discovered_files_list

    def start_documents_download_flow(self, run: Run) -> List[DiscoveredFile]:
        """
        Initiates the Document Download Workflow
        :param run: Run Object
        :return: Returns the list of Discovered Files
        """
        try:
            self._login()
            self.home_page.get_billing().click()
            wait_for_loaders(
                self.driver, value="granite-loading[mode='query']", timeout=10
            )
            discovered_files = self._download_invoices()
            return discovered_files
        finally:
            self._quit_driver()

    def login_flow(self, run: Run):
        self._login()
