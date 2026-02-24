import os
from datetime import datetime
from typing import List

from retry.api import retry
from selenium.webdriver.common.by import By
from selenium.common.exceptions import WebDriverException
from selenium.webdriver.remote.webelement import WebElement
from spices.datetime_utils import date_from_string

from apps.adapters.base import VendorDocumentDownloadInterface, PasswordBasedLoginPage
from apps.adapters.framework import download
from apps.adapters.helpers.webdriver_helper import (
    get_url,
    select_dropdown_option_by_visible_text,
    wait_for_element,
)
from apps.adapters.vendors import LOGGER
from apps.runs.models import Run, DiscoveredFile, DocumentType, FileFormat

# Invoices Page Locators
INVOICE_PAGE_LOCATORS = {
    "SELECT_DROPDOWN": "section.account__section form select#OrderDate",
    "SEARCH_ORDER_HISTORY_BUTTON": 'input[value="Search Order History"]',
    "DOWNLOAD_LINK": 'a[href*="download"]',
    "INVOICE_NUMBER": "a.control-label, span.control-label",
    "INVOICE_DATE": "span.order-info",
    "RESTAURANT_NAME": "address",
    "TOTAL_AMOUNT": "label.price",
    "TOTAL_INVOICES_LIST": "div.item-listing",
}


class TheWebstaurantStoreLoginPage(PasswordBasedLoginPage):
    """
    The Webstaurant Store login module
    """

    SELECTOR_USERNAME_TEXTBOX = "input#email"
    SELECTOR_PASSWORD_TEXTBOX = "input#password"
    SELECTOR_LOGIN_BUTTON = "input#the_login_button"
    SELECTOR_ERROR_MESSAGE_TEXT = "div.alert-info"


class TheWebstaurantStoreInvoicesPage:
    """The Webstaurant Store Invoices page action methods come here."""

    def __init__(self, driver):
        self.driver = driver
        self.vendor_name = "THE WEBSTAURANT STORE"

    def select_order_date_drop_down(self) -> WebElement:
        """Get the order date drop down web element"""
        return self.driver.find_element_by_css_selector(
            INVOICE_PAGE_LOCATORS["SELECT_DROPDOWN"]
        )

    def get_search_order_history_btn(self) -> WebElement:
        """Get the search order history button web element"""
        return self.driver.find_element_by_css_selector(
            INVOICE_PAGE_LOCATORS["SEARCH_ORDER_HISTORY_BUTTON"]
        )

    def select_order_date(self, option_text: str):
        wait_for_element(
            self.driver,
            value=INVOICE_PAGE_LOCATORS["SELECT_DROPDOWN"],
            msg="Filter By Order Date Dropdown",
            retry_attempts=3,
        )
        select_dropdown_option_by_visible_text(
            self.select_order_date_drop_down(), option_text
        )

    def go_to_invoices_page(self):
        """
        Go to Invoices Page
        :return:
        """
        wait_for_element(
            self.driver,
            value=INVOICE_PAGE_LOCATORS["SEARCH_ORDER_HISTORY_BUTTON"],
            msg="Search Order History Link",
        )
        LOGGER.info("Clicking on Invoice Link.")
        self.get_search_order_history_btn().click()

    @staticmethod
    def _get_download_invoice(item) -> WebElement:
        """Get the download invoice web element"""
        return item.find_element_by_css_selector(INVOICE_PAGE_LOCATORS["DOWNLOAD_LINK"])

    @staticmethod
    def _get_invoice_date(item) -> WebElement:
        """Get the invoice date web element"""
        return item.find_element_by_css_selector(INVOICE_PAGE_LOCATORS["INVOICE_DATE"])

    @staticmethod
    def _get_total_amount(item) -> WebElement:
        """Get the invoice total amount web element"""
        return item.find_element_by_css_selector(INVOICE_PAGE_LOCATORS["TOTAL_AMOUNT"])

    @staticmethod
    def _get_restaurant_name(item) -> [WebElement]:
        """Get the list of restaurant names of web elements"""
        return item.find_element_by_css_selector(
            INVOICE_PAGE_LOCATORS["RESTAURANT_NAME"]
        )

    @staticmethod
    def _get_invoice_number(item) -> [WebElement]:
        """Get the list of restaurant names of web elements"""
        return item.find_element_by_css_selector(
            INVOICE_PAGE_LOCATORS["INVOICE_NUMBER"]
        )

    def get_total_invoices_list(self):
        return self.driver.find_elements_by_css_selector(
            INVOICE_PAGE_LOCATORS["TOTAL_INVOICES_LIST"]
        )

    def get_invoice_table_data(self, run: Run, from_date) -> List[DiscoveredFile]:
        """
        Extracts invoice details from Table
        :param from_date: Invoice start date
        :param run: Run Object
        :return: Returns the list of Discovered Files
        """
        discovered_files = []
        item_list = self.get_total_invoices_list()[1:]

        for _, item in enumerate(item_list):

            invoice_number = TheWebstaurantStoreInvoicesPage._get_invoice_number(
                item
            ).text.replace("Order #", "")
            invoice_date = TheWebstaurantStoreInvoicesPage._get_invoice_date(item).text
            invoice_date = date_from_string(invoice_date.split("\n")[0], "%B %d, %Y")

            if invoice_date < from_date:
                return discovered_files

            pdf_link = TheWebstaurantStoreInvoicesPage._get_download_invoice(
                item
            ).get_attribute("href")
            total_amount = TheWebstaurantStoreInvoicesPage._get_total_amount(item).text
            restaurant_name = TheWebstaurantStoreInvoicesPage._get_restaurant_name(
                item
            ).text.split("\n")[0]

            inv_date = str(invoice_date).replace("-", "").strip()
            reference_code = f"{invoice_number.strip()}_{inv_date}"

            document_properties = {
                "customer_number": None,
                "invoice_number": invoice_number,
                "invoice_date": f"{invoice_date}",
                "restaurant_name": restaurant_name,
                "total_amount": total_amount,
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

    def download_documents_by_link(
        self, download_location: str, discovered_files: List[DiscoveredFile]
    ):
        """
        Downloads the invoice & renames it with the actual invoice Number with date
        :param download_location:
        :param discovered_files: List of Discovered files
        :return: Nothing
        """

        for discovered_file in discovered_files:
            pdf_filename = (
                "invoice_" + discovered_file.document_properties["invoice_number"]
            )
            _downloader = download.DriverBasedUrlGetDownloader(
                self.driver,
                download_url=discovered_file.original_download_url,
                local_filepath=f"{download_location}/{pdf_filename}.pdf",
                rename_to=os.path.join(
                    download_location, discovered_file.original_filename
                ),
                file_exists_check_kwargs=dict(timeout=20),
            )
            download.download_discovered_file(discovered_file, _downloader)


class TheWebstaurantStoreRunner(VendorDocumentDownloadInterface):
    """Runner Class for The Webstaurant Store"""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.login_page = TheWebstaurantStoreLoginPage(self.driver)
        self.invoices_page = TheWebstaurantStoreInvoicesPage(self.driver)

    @retry(WebDriverException, tries=3, delay=2)
    def _login(self):
        """
        Login to The Webstaurant Store
        :return: Nothing
        """
        login_url = "https://www.webstaurantstore.com/myaccount/"
        get_url(self.driver, login_url)
        self.login_page.login(self.run.job.username, self.run.job.password)
        wait_for_element(
            self.driver,
            by_selector=By.XPATH,
            value="//a[contains(text(),'View Orders')]",
            msg="View Orders",
        )

    def _goto_download_page(self, document_type: str):
        """
        Go to download page based on the document type
        :param document_type: Specifies the type of the document eg. Invoice/Statement etc.
        :return:
        """
        if document_type == "invoice":
            self.invoices_page.go_to_invoices_page()
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
        self.invoices_page.download_documents_by_link(
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
            orders_page_url = "https://www.webstaurantstore.com/myaccount/orders/"

            for index in range(5):
                try:
                    get_url(self.driver, orders_page_url)
                    if self.driver.current_url != orders_page_url:
                        continue
                    self.invoices_page.select_order_date("in the past 30 Days")
                    break

                except WebDriverException as excep:
                    LOGGER.warning(f"{excep} found in {self.driver.current_url}")
                    if index == 4:
                        raise

            self._goto_download_page(self.run.job.requested_document_type)
            discovered_files += self._download_documents()
        finally:
            self._quit_driver()

        return discovered_files

    def login_flow(self, run: Run):
        self._login()
