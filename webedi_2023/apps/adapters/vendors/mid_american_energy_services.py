import os
import datetime
from typing import List

from selenium.webdriver.remote.webelement import WebElement

from apps.adapters.base import VendorDocumentDownloadInterface, PasswordBasedLoginPage
from apps.adapters.framework import download
from apps.adapters.helpers.webdriver_helper import (
    get_url,
    wait_for_element,
    has_invoices,
    wait_for_loaders,
)
from apps.adapters.vendors import LOGGER
from apps.runs.models import Run, DiscoveredFile, DocumentType, FileFormat
from spices.datetime_utils import date_from_string


# Home Page Locators
HOME_PAGE_LOCATORS = {"BILL_PAY": 'a[data-parent="Bills"]'}

# Invoices Page Locators
INVOICE_PAGE_LOCATORS = {
    "CUSTOMERS_DROP_DOWN": "#CustomerSelectContainer",
    "CUSTOMERS_DROP_DOWN_VALUES": "#select2-Customers-container",
    "INVOICE_TABLE_ROWS": 'table[class^="pq-grid-table"]>tbody>tr.pq-grid-row',
    "LOADER": "div.loader",
}


class MidAmericanEnergyServicesLoginPage(PasswordBasedLoginPage):
    """
    Mid American Energy Services login module
    """

    SELECTOR_USERNAME_TEXTBOX = "#UserName"
    SELECTOR_PASSWORD_TEXTBOX = "#Password"
    SELECTOR_LOGIN_BUTTON = 'input[value="Log in"]'
    SELECTOR_ERROR_MESSAGE_TEXT = "div.alert.alert-danger > div > ul > li"


class MidAmericanEnergyServicesHomePage:
    def __init__(self, driver):
        self.driver = driver

    def go_to_invoice_page(self):
        wait_for_element(
            self.driver, value=HOME_PAGE_LOCATORS["BILL_PAY"], msg="Bill Pay"
        )
        get_url(self.driver, "https://www.midamericanenergyservices.com/EMA/Bills/Main")


class MidAmericanEnergyServicesInvoicesPage:
    """Mid-American Energy Services Invoices page action methods come here."""

    vendor_name = "MidAmerican Energy Services"

    def __init__(self, driver):
        self.driver = driver

    def get_account_dropdown(self) -> WebElement:
        return self.driver.find_element_by_css_selector(
            INVOICE_PAGE_LOCATORS["CUSTOMERS_DROP_DOWN"]
        )

    def get_account_dropdown_options(self):
        return self.driver.find_elements_by_css_selector(
            INVOICE_PAGE_LOCATORS["CUSTOMERS_DROP_DOWN_VALUES"]
        )

    def get_invoice_table_rows(self):
        return self.driver.find_elements_by_css_selector(
            INVOICE_PAGE_LOCATORS["INVOICE_TABLE_ROWS"]
        )

    def get_invoice_table_data(
        self, run: Run, from_date, restaurant_name: str
    ) -> List[DiscoveredFile]:
        """
        Extracts invoice details from Table
        :param from_date: Invoice start date
        :param run: Run Object
        :return: Returns the list of Discovered Files
        """
        discovered_files = []

        if not has_invoices(
            self.driver, value=INVOICE_PAGE_LOCATORS["INVOICE_TABLE_ROWS"]
        ):
            return discovered_files

        for row in self.get_invoice_table_rows():
            pdf_link = row.find_elements_by_tag_name("td")[7].text
            if pdf_link in ("Unavailable", ""):
                continue

            invoice_date_element = row.find_elements_by_tag_name("td")[6]
            invoice_date = date_from_string(invoice_date_element.text, "%m/%d/%Y")

            if invoice_date < from_date:
                return discovered_files

            invoice_number = row.find_elements_by_tag_name("td")[2].text
            account_number = row.find_elements_by_tag_name("td")[1].text
            reference_code = (
                f"{account_number}_{invoice_number}_"
                + f"{invoice_date}".replace("-", "")
            )
            # restaurant_name = row.find_elements_by_tag_name('td')[4].text
            pdf_link = (
                "https://www.midamericanenergyservices.com/EMA/bills/RenderElectricInvoice?id="
                + invoice_number
            )
            document_properties = {
                "customer_number": account_number,
                "invoice_number": invoice_number,
                "invoice_date": f"{invoice_date}",
                "total_amount": None,
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

    def download_documents_by_link(self, download_location: str, discovered_files):
        """
        Downloads the invoice by click the view bill button
        :param download_location: Download path
        :param discovered_files: Discovered files
        :return: Nothing
        """
        for discovered_file in discovered_files:
            _downloader = download.DriverBasedUrlGetDownloader(
                self.driver,
                download_url=discovered_file.original_download_url,
                local_filepath=os.path.join(
                    download_location, "RenderElectricInvoice.pdf"
                ),
                rename_to=os.path.join(
                    download_location, discovered_file.original_filename
                ),
                file_exists_check_kwargs=dict(timeout=50),
            )
            download.download_discovered_file(discovered_file, _downloader)


class MidAmericanEnergyServicesRunner(VendorDocumentDownloadInterface):
    """Runner Class for Mid-American Energy Services"""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.login_page = MidAmericanEnergyServicesLoginPage(self.driver)
        self.home_page = MidAmericanEnergyServicesHomePage(self.driver)
        self.invoices_page = MidAmericanEnergyServicesInvoicesPage(self.driver)

    def _login(self):
        """
        Login to Mid-American Energy Services
        :return: Nothing
        """
        login_url = "https://www.midamericanenergyservices.com/EMA/"
        get_url(self.driver, login_url)
        self.login_page.login(self.run.job.username, self.run.job.password)

    def _download_documents(self, restaurant_name: str) -> List[DiscoveredFile]:
        """
        Chooses the documents to be downloaded based on the document type
        :return: Returns the list of Discovered Files
        """
        document_type = self.run.job.requested_document_type
        if document_type == "invoice":
            return self._download_invoices(restaurant_name)

        raise NotImplementedError(
            f"Requested Document Type is not supported: {document_type}"
        )

    def _download_invoices(self, restaurant_name: str) -> List[DiscoveredFile]:
        """
        Downloads the Invoices
        :return: Returns the list of the Discovered Files
        """
        start_date = datetime.datetime.strptime(
            self.run.request_parameters["start_date"], "%Y-%m-%d"
        ).date()
        # Fetching all invoice table date & storing it in memory
        discovered_files_list = self.invoices_page.get_invoice_table_data(
            self.run, start_date, restaurant_name
        )
        LOGGER.info(
            f"Total Invoices within date range and download link available: {len(discovered_files_list)}"
        )
        self.invoices_page.download_documents_by_link(
            self.download_location, discovered_files_list
        )
        return discovered_files_list

    def start_documents_download_flow(self, run: Run) -> List[DiscoveredFile]:
        """
        Initiates the Document Download Workflow
        :param run: Run Object
        :return: Returns the list of Discovered Files.
        """
        LOGGER.info(f"[tag:WAV_TPX_SDDF10] Starting documents download flow")
        discovered_files = []
        try:
            LOGGER.info(f"[tag:WAV_TPX_SDDF20] Logging in")
            self._login()
            self.home_page.go_to_invoice_page()

            LOGGER.debug(
                f'[tag:WAV_TPX_SDDF30] Clicking "Customers drop down" to visible the customers.'
            )
            self.invoices_page.get_account_dropdown().click()
            LOGGER.debug(
                f"[tag:WAV_TPX_SDDF40] Get the list of customers from drop down"
            )
            customers = self.invoices_page.get_account_dropdown_options()

            for index, _ in enumerate(customers):
                LOGGER.debug(
                    f'[tag:WAV_TPX_SDDF30] Clicking specific "Customer" to go to invoices page'
                )
                self.invoices_page.get_account_dropdown_options()[index].click()
                wait_for_loaders(
                    self.driver, value=INVOICE_PAGE_LOCATORS["LOADER"], timeout=10
                )
                self.home_page.go_to_invoice_page()
                discovered_files += self._download_documents(
                    self.invoices_page.get_account_dropdown_options()[index].text
                )

        finally:
            self._quit_driver()
        return discovered_files

    def login_flow(self, run: Run):
        self._login()
