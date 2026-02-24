import os
from datetime import datetime
from typing import List
import re
from selenium.webdriver.remote.webelement import WebElement
from selenium.common.exceptions import WebDriverException
from apps.adapters.base import VendorDocumentDownloadInterface, PasswordBasedLoginPage
from apps.adapters.helpers.webdriver_helper import wait_for_element, get_url
from apps.adapters.framework import download
from apps.adapters.vendors import LOGGER
from apps.runs.models import Run, DiscoveredFile, DocumentType, FileFormat
from spices.datetime_utils import date_from_string


# Home Page Locators
HOME_PAGE_LOCATORS = {
    "ACCEPT_COOKIES": "#ensAllow",
    "ACCOUNT_LIST": "select[name='chargeAccount'] > option",
}

# Invoices Page Locators
INVOICE_TABLE_ELEMENT = {
    "INVOICE_TABLE_ROWS": 'table[class="responsive-table responsive enhanced"] > tbody > tr',
}


class SherwinWilliamsLoginPage(PasswordBasedLoginPage):
    """Sherwin williams Login Page Web Elements."""

    SELECTOR_USERNAME_TEXTBOX = 'div[id="CDC_Login"] input[name="username"]'
    SELECTOR_PASSWORD_TEXTBOX = 'div[id="CDC_Login"] input[name="password"]'
    SELECTOR_LOGIN_BUTTON = 'div[id="CDC_Login"] input.gigya-input-submit'
    SELECTOR_ERROR_MESSAGE_TEXT = 'div[id="CDC_Login"] div.gigya-form-error-msg'


class SherwinWilliamsHomePage:
    """Sherwin Williams Home Page action methods come here."""

    def __init__(self, driver):
        self.driver = driver

    def make_customer_dictionary(self, each_account):
        """Update the customer details and url elements."""
        current_url = self.driver.current_url
        account_dictionary = {}
        account_dictionary.update(
            {"customer_number": each_account.text.split(" ", 1)[0].replace("-", "")}
        )
        account_dictionary.update(
            {
                "customer_name": each_account.text.split(" ", 1)[1]
                .replace("-", "")
                .strip()
            }
        )
        account_dictionary.update(
            {"store_id": re.search(r"storeId=\d+", current_url).group()}
        )
        account_dictionary.update(
            {"catalog_id": re.search(r"catalogId=\d+", current_url).group()}
        )
        return account_dictionary

    def home_account_list(self) -> [WebElement]:
        """Return the list of account."""
        return self.driver.find_elements_by_css_selector(
            HOME_PAGE_LOCATORS["ACCOUNT_LIST"]
        )

    @staticmethod
    def built_url(each_account):
        """Return the built view invoice page url."""
        return (
            f'https://www.sherwin-williams.com/InvoiceListView?{each_account["store_id"]}&langId=-1'
            f'&{each_account["catalog_id"]}&availableAccount={each_account["customer_number"]}'
        )

    def home_page_details(self) -> [dict]:
        """Return the customer details extract from the current url."""
        wait_for_element(
            self.driver, value=HOME_PAGE_LOCATORS["ACCOUNT_LIST"], msg="account list"
        )
        available_charge_accounts = list(
            map(self.make_customer_dictionary, self.home_account_list())
        )
        return available_charge_accounts


class SherwinWilliamsInvoicesPage:
    """Sherwin Williams Invoices page action methods come here."""

    def __init__(self, driver, download_location: str):
        super().__init__()
        self.driver = driver
        self.download_location = download_location
        self.vendor_name = "Sherwin Williams"

    def get_invoice_table_rows(self) -> [WebElement]:
        """Get invoice table row list."""
        return self.driver.find_elements_by_css_selector(
            INVOICE_TABLE_ELEMENT["INVOICE_TABLE_ROWS"]
        )

    def get_table_data(self, run: Run, from_date, each_account):
        """Extracts invoice details from Table
        :return: Returns the list of Discovered File
        """
        discovered_files = []
        wait_for_element(
            self.driver,
            value=INVOICE_TABLE_ELEMENT["INVOICE_TABLE_ROWS"],
            msg="invoice table row",
        )
        for row in self.get_invoice_table_rows():

            invoice_date = date_from_string(
                row.find_elements_by_css_selector("td")[3].text, "%m-%d-%Y"
            )

            if invoice_date < from_date:
                return discovered_files

            invoice_number = row.find_element_by_css_selector("td > a").text

            reference_code = (
                f'{each_account["customer_number"]}_{invoice_number}_{invoice_date}'
            )

            try:
                # pylint: disable=no-member
                discovered_file = DiscoveredFile.build_unique(
                    run,
                    reference_code,
                    document_type=DocumentType.INVOICE.ident,
                    file_format=FileFormat.PDF.ident,
                    original_download_url=row.find_element_by_css_selector(
                        "td > a"
                    ).get_attribute("href"),
                    original_filename=f"{reference_code}.pdf",
                    document_properties={
                        "customer_number": f'{each_account["customer_number"]}',
                        "invoice_number": f"{invoice_number}",
                        "invoice_date": f"{invoice_date}",
                        "total_amount": f'{row.find_elements_by_css_selector("td")[6].text}',
                        "vendor_name": self.vendor_name,
                        "restaurant_name": f'{each_account["customer_name"]}',
                    },
                )
            except DiscoveredFile.AlreadyExists:
                LOGGER.info(
                    f"Discovered file already exists with reference code : {reference_code}"
                )
                continue  # skip if seen before

            discovered_files.append(discovered_file)
            self.download_invoice_by_url(discovered_file)
            LOGGER.info(
                f"Invoice details row data: {discovered_file.document_properties}"
            )
        return discovered_files

    def download_invoice_by_url(self, discovered_file):
        """Download the File in PDF format
        :param discovered_file:
        """
        LOGGER.info(f"Navigate to: {discovered_file.original_download_url}")
        _downloader = download.DriverBasedUrlGetDownloader(
            self.driver,
            download_url=discovered_file.original_download_url,
            local_filepath=os.path.join(
                self.download_location,
                f'Account_{discovered_file.document_properties["customer_number"]}.pdf',
            ),
            rename_to=os.path.join(
                self.download_location, discovered_file.original_filename
            ),
            file_exists_check_kwargs=dict(timeout=20),
        )
        download.download_discovered_file(discovered_file, _downloader)


class SherwinWilliamsRunner(VendorDocumentDownloadInterface):
    """Runner Class for sherwin williams."""

    is_angular = False

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.login_page = SherwinWilliamsLoginPage(self.driver)
        self.home_page = SherwinWilliamsHomePage(self.driver)
        self.invoices_page = SherwinWilliamsInvoicesPage(
            self.driver, self.download_location
        )

    def accept_page_cookies(self) -> WebElement:
        """Accept cookies web element."""
        wait_for_element(
            self.driver,
            value=HOME_PAGE_LOCATORS["ACCEPT_COOKIES"],
            msg="accept cookies",
            retry_attempts=2,
        )
        return self.driver.find_element_by_css_selector(
            HOME_PAGE_LOCATORS["ACCEPT_COOKIES"]
        )

    def _login(self):
        """
        Login to sherwin williams
        :return: Nothing
        """
        login_url = "https://www.sherwin-williams.com/login"
        get_url(self.driver, login_url)

        try:
            self.accept_page_cookies().click()
        except WebDriverException as excep:
            LOGGER.info(f"No accept cookies prompt found: {excep}")

        self.login_page.login(self.run.job.username, self.run.job.password)

    def _download_invoices(self) -> List[DiscoveredFile]:
        """
        Downloads the Invoices
        :return: Returns the list of the Discovered Files
        """
        document_type = self.run.job.requested_document_type
        discovered_files_list = []
        if document_type == "invoice":
            LOGGER.info("Extracting data from table...")
            start_date = datetime.strptime(
                self.run.request_parameters["start_date"], "%Y-%m-%d"
            ).date()

            for each_account in self.home_page.home_page_details():

                # get invoice table page for each account
                get_url(self.driver, self.home_page.built_url(each_account))

                discovered_files_list.extend(
                    self.invoices_page.get_table_data(
                        self.run, start_date, each_account
                    )
                )
                LOGGER.info(
                    f"Total Invoices within date range and download link available:"
                    f" {len(discovered_files_list)}"
                )
            return discovered_files_list

        raise NotImplementedError(
            f"Requested Document Type is not supported: {document_type}"
        )

    def start_documents_download_flow(self, run: Run) -> List[DiscoveredFile]:
        """
        Initiates the Document Download Workflow
        :param run: Run Object
        :return: Returns the list of Discovered Files
        """
        try:
            self._login()
            discovered_files = self._download_invoices()
            return discovered_files
        finally:
            self._quit_driver()

    def login_flow(self, run: Run):
        self._login()
