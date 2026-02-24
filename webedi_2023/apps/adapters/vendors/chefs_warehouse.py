import datetime
import os
from typing import List

from selenium.webdriver.common.by import By
from selenium.webdriver.remote.webelement import WebElement

from apps.adapters import LOGGER
from apps.adapters.base import VendorDocumentDownloadInterface, PasswordBasedLoginPage
from apps.adapters.framework import download
from apps.adapters.helpers.webdriver_helper import (
    get_url,
    wait_for_element,
    wait_for_loaders,
)
from apps.runs.models import Run, DiscoveredFile, DocumentType, FileFormat

# Login Page Locators
LOGIN_PAGE_LOCATORS = {
    "EMAIL": "input#loginInput",
    "PASSWORD": "input#loginPassword",
    "SUBMIT": 'button[onclick="return login();"]',
    "ERROR": "div.messages.page-messages div.alert.alert-danger",
}

# Home Page Locators
HOME_PAGE_LOCATORS = {
    "ORDER_MANAGEMENT": "ul.profile-navigation a#order-history-btn",
    "ORDER_HISTORY": "div#orderHistoryTable",
    "ADDRESS_BOOK": "div.my-profile a#address-book-btn",
}

# Invoice Page Locators
INVOICE_PAGE_LOCATORS = {
    "TABLE": "table > tbody",
    "TABLE_ROW": "tr",
    "INVOICE_DETAIL": "td > a.detail-link",
    "INVOICE_NUMBER": '//strong[text()="Invoice Number"]/following-sibling::span',
    "INVOICE_DATE": '//strong[text()="Order Date"]/following-sibling::span',
    "ORDER_NUMBER": '//strong[text()="CW Order Number"]/following-sibling::span',
    "WEB_ORDER_NUMBER": '//strong[text()="Web Order Number"]/following-sibling::span',
    "TOTAL_AMOUNT": '//dt[text()="Total:"]/following-sibling::dd',
    "RESTAURANT_NAME": '//label[text()="Company Name"]/following-sibling::*',
    "DROPDOWN_BUTTON": "button.selectpicker",
    "SEARCH_BUTTON": "a.search-orders-button",
    "INVOICED_OPTION": 'a[data-normalized-text*="Invoiced"]',
    "LOADER": "a.search-orders-button i.fa-spinner",
}


class TheChefsWarehouseLoginPage(PasswordBasedLoginPage):
    """Login Page Web Elements"""

    SELECTOR_USERNAME_TEXTBOX = LOGIN_PAGE_LOCATORS["EMAIL"]
    SELECTOR_PASSWORD_TEXTBOX = LOGIN_PAGE_LOCATORS["PASSWORD"]
    SELECTOR_LOGIN_BUTTON = LOGIN_PAGE_LOCATORS["SUBMIT"]
    SELECTOR_ERROR_MESSAGE_TEXT = LOGIN_PAGE_LOCATORS["ERROR"]


class TheChefsWarehouseHomePage:
    """Home Page Class"""

    def __init__(self, driver):
        self.driver = driver

    def get_order_management(self) -> WebElement:
        """Returns order management element."""
        return self.driver.find_element_by_css_selector(
            HOME_PAGE_LOCATORS["ORDER_MANAGEMENT"]
        )

    def get_order_history(self) -> WebElement:
        """Returns order history element."""
        return self.driver.find_element_by_css_selector(
            HOME_PAGE_LOCATORS["ORDER_HISTORY"]
        )

    def get_address_book(self) -> WebElement:
        """Returns address book element."""
        return self.driver.find_element_by_css_selector(
            HOME_PAGE_LOCATORS["ADDRESS_BOOK"]
        )


class TheChefsWarehouseInvoicesPage:
    def __init__(self, driver):
        self.driver = driver
        self.home_page = TheChefsWarehouseHomePage(self.driver)
        self.vendor_name = "The Chefs' Warehouse"

    @staticmethod
    def get_table_element(order_history):
        return order_history.find_element_by_css_selector(
            INVOICE_PAGE_LOCATORS["TABLE"]
        )

    @staticmethod
    def get_table_rows_element(orders_table):
        return orders_table.find_elements_by_css_selector(
            INVOICE_PAGE_LOCATORS["TABLE_ROW"]
        )

    @staticmethod
    def get_invoice_details(table_row):
        return table_row.find_element_by_css_selector(
            INVOICE_PAGE_LOCATORS["INVOICE_DETAIL"]
        )

    def get_restaurant_name(self):
        self.home_page.get_address_book().click()
        return self.driver.find_element_by_xpath(
            INVOICE_PAGE_LOCATORS["RESTAURANT_NAME"]
        )

    def get_table_rows(self):
        order_history = self.home_page.get_order_history()
        orders_table = TheChefsWarehouseInvoicesPage.get_table_element(order_history)
        rows = TheChefsWarehouseInvoicesPage.get_table_rows_element(orders_table)
        return rows

    def get_select_dropdown_button(self):
        return self.driver.find_element_by_css_selector(
            INVOICE_PAGE_LOCATORS["DROPDOWN_BUTTON"]
        )

    def get_search_button(self):
        return self.driver.find_element_by_css_selector(
            INVOICE_PAGE_LOCATORS["SEARCH_BUTTON"]
        )

    def get_invoiced_option(self):
        return self.driver.find_element_by_css_selector(
            INVOICE_PAGE_LOCATORS["INVOICED_OPTION"]
        )

    def get_invoice_number(self):
        return self.driver.find_element_by_xpath(
            INVOICE_PAGE_LOCATORS["INVOICE_NUMBER"]
        )

    def get_order_number(self):
        return self.driver.find_element_by_xpath(INVOICE_PAGE_LOCATORS["ORDER_NUMBER"])

    def get_web_order_number(self):
        return self.driver.find_element_by_xpath(
            INVOICE_PAGE_LOCATORS["WEB_ORDER_NUMBER"]
        )

    def get_invoice_date(self):
        return self.driver.find_element_by_xpath(INVOICE_PAGE_LOCATORS["INVOICE_DATE"])

    def get_total_amount(self):
        return self.driver.find_element_by_xpath(INVOICE_PAGE_LOCATORS["TOTAL_AMOUNT"])

    def select_dropdown_invoiced_option(self):
        self.get_select_dropdown_button().click()
        self.get_invoiced_option().click()
        self.get_search_button().click()

        wait_for_loaders(
            self.driver,
            value=INVOICE_PAGE_LOCATORS["LOADER"],
            retry_attempts=1,
            timeout=5,
        )

    def get_invoice_data(
        self, run: Run, from_date, download_location: str
    ) -> List[DiscoveredFile]:
        """Extracts invoice details"""
        discovered_files = []
        restaurant_name = self.get_restaurant_name().text

        self.home_page.get_order_management().click()
        self.select_dropdown_invoiced_option()

        rows = self.get_table_rows()
        for idx, _ in enumerate(rows):
            web_order_element = TheChefsWarehouseInvoicesPage.get_invoice_details(
                rows[idx]
            )
            # scroll_down_to_element(self.driver, web_order_element)
            web_order_element.click()
            wait_for_element(
                self.driver,
                by_selector=By.XPATH,
                value=INVOICE_PAGE_LOCATORS["INVOICE_NUMBER"],
                msg="Invoice Number",
            )

            order_number = self.get_order_number().text
            web_order_number = self.get_web_order_number().text
            invoice_date = datetime.datetime.strptime(
                self.get_invoice_date().text, "%m/%d/%Y"
            ).date()

            if invoice_date < from_date:
                return discovered_files

            reference_code = f"{web_order_number}_{order_number}_{invoice_date}"

            try:
                # pylint: disable=no-member
                discovered_file = DiscoveredFile.build_unique(
                    run,
                    reference_code,
                    document_type=DocumentType.INVOICE.ident,
                    file_format=FileFormat.PDF.ident,
                    original_download_url="window.print();",
                    original_filename=f"{reference_code}.pdf",
                    document_properties={
                        "customer_number": order_number,
                        "invoice_number": self.get_invoice_number().text,
                        "invoice_date": f"{invoice_date}",
                        "total_amount": self.get_total_amount().text,
                        "vendor_name": self.vendor_name,
                        "restaurant_name": restaurant_name,
                    },
                )
            except DiscoveredFile.AlreadyExists:
                LOGGER.info(
                    f"Discovered file already exists with reference code : {reference_code}"
                )
                self.driver.back()
                continue

            discovered_files.append(discovered_file)
            LOGGER.info(
                f"Invoice details row data: {discovered_file.document_properties}"
            )

            self.download_invoice_by_script(download_location, discovered_file)
            self.driver.back()
        return discovered_files

    def download_invoice_by_script(self, download_location, discovered_file):
        """
        Download the webpage in PDF format
        :param discovered_file:
        :param download_location: path to download file
        """
        _downloader = download.DriverExecuteCDPCmdBasedDownloader(
            self.driver,
            cmd="Page.printToPDF",
            cmd_args={"printBackground": True},
            local_filepath=f"{download_location}/invoice.pdf",
            rename_to=os.path.join(
                download_location, discovered_file.original_filename
            ),
            file_exists_check_kwargs=dict(timeout=20),
        )
        download.download_discovered_file(discovered_file, _downloader)


class ChefsWarehouseRunner(VendorDocumentDownloadInterface):
    """Runner Class"""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.login_page = TheChefsWarehouseLoginPage(self.driver)
        self.home_page = TheChefsWarehouseHomePage(self.driver)
        self.invoice_page = TheChefsWarehouseInvoicesPage(self.driver)

    def _login(self):
        """
        Login using credentials
        :return: Nothing
        """
        login_url = "https://www.chefswarehouse.com/registration/login.jsp"
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
        LOGGER.info("Extracting data from invoice page...")
        start_date = datetime.datetime.strptime(
            self.run.request_parameters["start_date"], "%Y-%m-%d"
        ).date()
        discovered_files_list = self.invoice_page.get_invoice_data(
            self.run, start_date, self.download_location
        )
        LOGGER.info(
            f"Total Invoices within date range and download links available: {len(discovered_files_list)}"
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
            discovered_files = self._download_documents()
        finally:
            self._quit_driver()

        return discovered_files

    def login_flow(self, run: Run):
        self._login()
