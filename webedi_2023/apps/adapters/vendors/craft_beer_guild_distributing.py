import os
import re
from datetime import datetime, date
from typing import List

from selenium.common.exceptions import NoSuchElementException
from selenium.webdriver.remote.webelement import WebElement
from apps.adapters.base import PasswordBasedLoginPage, VendorDocumentDownloadInterface
from apps.adapters.framework import download
from apps.adapters.helpers.webdriver_helper import (
    get_url,
    explicit_wait_till_visibility,
    has_invoices,
    wait_for_element,
    wait_for_loaders,
)
from apps.runs.models import Run, DiscoveredFile, DocumentType, FileFormat
from integrator import LOGGER
from spices.datetime_utils import date_from_string


# Billing History Page Locators
BILLING_HISTORY_PAGE = {
    "BILLING_RETAILER_TABLE": 'table[ng-model="historySelection"]>tbody>tr',
    "BILLING_TABLE_CHECK": 'table[ng-model="historySelection"]',
}

HOME_PAGE = {
    "RETAILER_PICKERS": 'span[class="ng-star-inserted"] a.mat-button',
    "RETAILER_PICKERS_URLS": "a.mat-list-item",
}

LOGIN_PAGE = {
    "SELECTOR_EMAIL_BUTTON": 'input[name="HomeRealmByEmail"]',
    "SELECTOR_EMAIL_TEXTBOX": 'input[name="Email"]',
}


class CraftBeerGuildDistributingHomePage:
    """Craft Beer Guild Distributing home page"""

    def __init__(self, driver):
        self.driver = driver

    def prepare_history_property(self, retailer):
        """Get retailers url, account name and account number"""
        explicit_wait_till_visibility(
            self.driver, retailer, msg="waiting element for pickers", timeout=20
        )
        acc_num = re.sub(re.compile(r".*\(|\)", re.DOTALL), "", retailer.text)
        return {
            "url": retailer.get_attribute("href") + "/order-history",
            "name": retailer.text,
            "acc_number": acc_num,
        }

    def get_retailer_picker(self):
        """Get retailer pickers"""
        return self.driver.find_element_by_css_selector(HOME_PAGE["RETAILER_PICKERS"])

    def get_retailer_orders_url(self):
        """Get retails urls"""
        retailers_links = list(
            map(
                self.prepare_history_property,
                self.driver.find_elements_by_css_selector(
                    HOME_PAGE["RETAILER_PICKERS_URLS"]
                ),
            )
        )
        return retailers_links

    def home_page_prepare_data(self):
        """Return retailers data with url"""
        try:
            # click selection button
            self.get_retailer_picker().click()
            return self.get_retailer_orders_url()
        except NoSuchElementException as excep:
            LOGGER.warning(f"Retailer accounts not found - {excep}")
            return []

    @property
    def home_wholesaler_element(self):
        """Return wholesaler element"""
        return self.driver.find_elements_by_css_selector(
            'div[class^="distributor-card-stack"]>a'
        )

    def select_wholesaler_urls(self, wholesaler_elements):
        """Return wholesaler urls"""
        wait_for_element(
            self.driver,
            value='div[class^="distributor-card-stack"]>a',
            msg="wait for wholesaler",
        )
        return [wholesaler.get_attribute("href") for wholesaler in wholesaler_elements]


class CraftBeerGuildDistributingIncLoginPage(PasswordBasedLoginPage):
    """Craft Beer Guild Distributing Login Page Web Elements"""

    SELECTOR_USERNAME_TEXTBOX = 'input[name="UserName"]'
    SELECTOR_PASSWORD_TEXTBOX = 'input[name="Password"]'
    SELECTOR_LOGIN_BUTTON = "#submitButton"
    SELECTOR_ERROR_MESSAGE_TEXT = "#errorText"

    def get_email_button(self):
        """Get login email button"""
        return self.driver.find_element_by_css_selector(
            LOGIN_PAGE["SELECTOR_EMAIL_BUTTON"]
        )

    def get_email_verification(self, username):
        """Get login email text box"""
        # send value
        self.driver.find_element_by_css_selector(
            LOGIN_PAGE["SELECTOR_EMAIL_TEXTBOX"]
        ).send_keys(username)
        # click email button
        self.get_email_button().click()


class CraftBeerGuildDistributingBillingHistoryPage:
    """Billing History Page class for Craft Beer Guild Distributing"""

    def __init__(self, driver, download_location: str):
        self.driver = driver
        self.download_location = download_location
        self.vendor = "Craft Beer Guild Distributing"

    def get_table_rows(self) -> List[WebElement]:
        """Return the billing history table rows"""
        return self.driver.find_elements_by_css_selector(
            BILLING_HISTORY_PAGE["BILLING_RETAILER_TABLE"]
        )

    def get_table_data(
        self, run: Run, from_date: date, retailer_dict: dict
    ) -> List[DiscoveredFile]:
        """
        Extracts invoice details from Table
        :param run: Run Object
        :param from_date: Start date of the invoices to be downloaded
        :param retailer_dict: retailer_dict for binding url, name and account number
        :return: Returns the list of Discovered File
        """
        discovered_files, collected_invoices = [], []

        if not has_invoices(
            self.driver, value=BILLING_HISTORY_PAGE["BILLING_RETAILER_TABLE"]
        ):
            return discovered_files

        # iterate table rows
        for row in self.get_table_rows():
            explicit_wait_till_visibility(
                self.driver, row, msg="waiting for row", timeout=20
            )

            # invoice date
            date_string = (
                row.find_element_by_css_selector("td:nth-child(6)").text
                or row.find_element_by_css_selector("td:nth-child(5)").text
            )

            invoice_date = date_from_string(date_string, "%b %d, %Y")
            if invoice_date < from_date:
                LOGGER.info(
                    f"Skipping remaining invoices because date '{invoice_date}' is outside requested range"
                )
                return discovered_files

            # invoice number
            invoice_number = row.find_element_by_css_selector("td:nth-child(4)").text

            # total amount
            total_amount = row.find_element_by_css_selector("td:nth-child(7)").text

            this_invoice = f"{invoice_number}_{invoice_date}_{total_amount}"
            if this_invoice in collected_invoices:
                LOGGER.info(
                    f"Skipping this invoice because '{this_invoice}' was already seen in this run"
                )
                continue
            collected_invoices.append(this_invoice)

            try:
                # download link
                download_link = row.find_element_by_css_selector(
                    "td:nth-child(1)>a"
                ).get_attribute("href")
            except NoSuchElementException:
                LOGGER.info("Invoice download element not found")
                continue

            reference_code = (
                f'{retailer_dict["acc_number"]}_{invoice_number}_{invoice_date}'
            )

            document_properties = {
                "customer_number": f'{retailer_dict["acc_number"]}',
                "invoice_number": f"{invoice_number}",
                "invoice_date": f"{invoice_date}",
                "total_amount": f"{total_amount}",
                "restaurant_name": f'{retailer_dict["name"]}',
                "vendor_name": f"{self.vendor}",
            }

            try:
                # pylint: disable=no-member
                discovered_file = DiscoveredFile.build_unique(
                    run,
                    reference_code=reference_code,
                    document_type=DocumentType.INVOICE.ident,
                    file_format=FileFormat.PDF.ident,
                    original_download_url=download_link,
                    original_filename=f"{reference_code}.pdf",
                    document_properties=document_properties,
                )
            except DiscoveredFile.AlreadyExists:
                LOGGER.info(
                    f"Discovered file already exists with reference code : {reference_code}"
                )
                continue  # skip if seen before

            LOGGER.info(
                "Invoice details row data: %s", str(discovered_file.document_properties)
            )

            # discover file download
            discovered_files.append(discovered_file)

        return discovered_files

    def download_invoice_by_url(self, discovered_files):
        """
        Download the File in PDF format
        :param discovered_files: DiscoveredFile variable
        """
        # rename is required, if we have download multiple files hence
        # we need to rename the file as for certain conditions for uploading to s3
        for discovered_file in discovered_files:
            _downloader = download.DriverBasedUrlGetDownloader(
                self.driver,
                download_url=discovered_file.original_download_url,
                local_filepath=self.download_location,
                rename_to=os.path.join(
                    self.download_location, discovered_file.original_filename
                ),
                file_exists_check_kwargs=dict(
                    timeout=20, pattern=rf"Invoice-B_[0-9-]+.pdf$"
                ),
            )
            download.download_discovered_file(discovered_file, _downloader)

    def get_all_retailers_discovered_file(
        self, run, start_date, _get_retailer_order_url
    ):
        """Get all retailers discovered files"""
        discovered_files_list, seen_retailer_order_url = [], []
        for index, retailer_dict in enumerate(_get_retailer_order_url):
            retailer_url = retailer_dict["url"]

            if retailer_url in seen_retailer_order_url:
                LOGGER.info(
                    f"Skipping this retailer because '{retailer_url}' was already seen in this run"
                )
                continue
            seen_retailer_order_url.append(retailer_url)

            get_url(self.driver, retailer_url)
            wait_for_loaders(
                self.driver, value="div.loading-container", timeout=10, retry_attempts=1
            )
            discovered_files_list.extend(
                self.get_table_data(run, start_date, retailer_dict)
            )
        return discovered_files_list


class CraftBeerGuildDistributingRunner(VendorDocumentDownloadInterface):
    """Runner Class for Craft Beer Guild Distributing"""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.login_page = CraftBeerGuildDistributingIncLoginPage(self.driver)
        self.home_page = CraftBeerGuildDistributingHomePage(self.driver)
        self.billing_history_page = CraftBeerGuildDistributingBillingHistoryPage(
            self.driver, self.download_location
        )

    def _login(self):
        """
        Login using credentials
        :return: Nothing
        """
        login_url = "https://apps.vtinfo.com/retailer-portal/login"
        get_url(self.driver, login_url)
        # login pre page processing
        self.login_page.get_email_verification(self.run.job.username)
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
        LOGGER.info("Extracting data from table...")
        start_date = datetime.strptime(
            self.run.request_parameters["start_date"], "%Y-%m-%d"
        ).date()

        # click retailers pickers and get all pickers urls
        _get_retailer_order_url = self.home_page.home_page_prepare_data()

        if not _get_retailer_order_url:
            return []

        # processing table with select restaurant
        discovered_files_list = (
            self.billing_history_page.get_all_retailers_discovered_file(
                self.run, start_date, _get_retailer_order_url
            )
        )

        # download discovered url files
        self.billing_history_page.download_invoice_by_url(discovered_files_list)

        LOGGER.info(
            f"Downloaded invoice by download link available: {len(discovered_files_list)}"
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
            wholesaler_elements = self.home_page.home_wholesaler_element
            if wholesaler_elements:
                for _wholesaler_url in self.home_page.select_wholesaler_urls(
                    wholesaler_elements
                ):
                    get_url(self.driver, _wholesaler_url)
                    discovered_files.extend(self._download_documents())
            else:
                discovered_files.extend(self._download_documents())
        finally:
            self._quit_driver()

        return discovered_files

    def login_flow(self, run: Run):
        self._login()
