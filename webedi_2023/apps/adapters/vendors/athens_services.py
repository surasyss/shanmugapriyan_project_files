import os
import re
from datetime import date, datetime
from typing import List
from selenium.webdriver.remote.webelement import WebElement
from apps.adapters.base import PasswordBasedLoginPage, VendorDocumentDownloadInterface
from apps.adapters.framework import download
from apps.adapters.helpers.webdriver_helper import (
    get_url,
    explicit_wait_till_visibility,
    IGNORED_EXCEPTIONS,
)
from apps.runs.models import Run, DiscoveredFile, DocumentType, FileFormat
from integrator import LOGGER
from spices.datetime_utils import date_from_string

# Home Page Locators
HOME_PAGE_LOCATORS = {
    "GET_ACCOUNTING_ROWS_CLICK": 'div[id="billingAccordion"]>h3',
}

# Billing History Page Locator
BILLING_HISTORY_PAGE = {
    "TABLE_ROWS": 'table[id="tblDetail{}"]> tbody> tr',
}


class AthensServicesLoginPage(PasswordBasedLoginPage):
    """Athens Services Login Page Web Elements"""

    SELECTOR_USERNAME_TEXTBOX = 'input[id="txtSigninEmail"]'
    SELECTOR_PASSWORD_TEXTBOX = 'input[id="txtPassword"]'
    SELECTOR_LOGIN_BUTTON = 'input[id="btnSignin"]'
    SELECTOR_ERROR_MESSAGE_TEXT = 'form[id="frmSignin"]>div>div[id="msgSignin"] p'


class AthensServicesHomePage:
    """Home Page Class for Athens Services"""

    def __init__(self, driver):
        self.driver = driver

    def get_account_rows_list_click(self) -> List[WebElement]:
        """Return the account rows"""
        return self.driver.find_elements_by_css_selector(
            HOME_PAGE_LOCATORS["GET_ACCOUNTING_ROWS_CLICK"]
        )


class AthensServicesBillingHistoryPage:
    """Billing History Page class for Athens Services"""

    def __init__(self, driver, download_location: str):
        super().__init__()
        self.driver = driver
        self.download_location = download_location
        self.vendor = "Athens services"
        self.home_page = AthensServicesHomePage(self.driver)

    def get_table_rows(self, acc_sno) -> List[WebElement]:
        """Return the billing history table rows"""
        return self.driver.find_elements_by_css_selector(
            BILLING_HISTORY_PAGE["TABLE_ROWS"].format(acc_sno)
        )

    def get_table_data(self, run: Run, from_date: date) -> List[DiscoveredFile]:
        """
        Extracts invoice details from Table
        :param run: Run Object
        :param from_date: start days of the download pdf
        :return: Returns the list of Discovered File
        """
        discovered_files, invoice_date = [], None
        for _acc_sno, account_number in enumerate(
            self.home_page.get_account_rows_list_click()
        ):
            account_number.click()
            for row in self.get_table_rows(_acc_sno):
                explicit_wait_till_visibility(
                    self.driver, row, timeout=10, ignored_exceptions=IGNORED_EXCEPTIONS
                )
                invoice_date = date_from_string(
                    row.find_elements_by_css_selector("td")[0].text, "%d-%b-%Y"
                )
                if invoice_date < from_date:
                    break
                invoice_number = row.find_elements_by_css_selector("td")[2].text
                customer_number = account_number.get_attribute("name")
                reference_code = f"{customer_number}_{invoice_number}_{invoice_date}"
                download_id = row.find_element_by_css_selector("td a").get_attribute(
                    "href"
                )
                inv_amount = row.find_elements_by_css_selector("td")[4].text
                # restaurant name
                restaurant_name = re.search(
                    r":\s*(?P<r_name>[\w+\s]+),", account_number.text
                ).groupdict()["r_name"]

                document_properties = {
                    "customer_number": customer_number,
                    "invoice_date": f"{invoice_date}",
                    "invoice_number": f"{invoice_number}",
                    "total_amount": f"{inv_amount}",
                    "restaurant_name": restaurant_name,
                    "vendor_name": self.vendor,
                }
                try:
                    discovered_file = DiscoveredFile.build_unique(
                        run,
                        reference_code,
                        document_type=DocumentType.INVOICE.ident,  # pylint: disable=no-member
                        file_format=FileFormat.PDF.ident,  # pylint: disable=no-member
                        original_download_url=f"{download_id}",
                        original_filename=f"{reference_code}.pdf",
                        document_properties=document_properties,
                    )
                except DiscoveredFile.AlreadyExists:
                    LOGGER.info(
                        f"Discovered file already exists with reference code : {reference_code}"
                    )
                    continue  # skip if seen before

                LOGGER.info(
                    "Invoice details row data: %s",
                    str(discovered_file.document_properties),
                )
                discovered_files.append(discovered_file)
        return discovered_files

    def download_invoice_by_url(self, discovered_files: list):
        """
        Download the File in PDF format
        :param discovered_files: DiscoveredFile variable
        """
        for discovered_file in discovered_files:
            try:
                _downloader = download.DriverBasedUrlGetDownloader(
                    self.driver,
                    download_url=discovered_file.original_download_url,
                    local_filepath=os.path.join(self.download_location, "Display.pdf"),
                    rename_to=os.path.join(
                        self.download_location, discovered_file.original_filename
                    ),
                    file_exists_check_kwargs=dict(timeout=20),
                )
                download.download_discovered_file(discovered_file, _downloader)
            except FileNotFoundError:
                LOGGER.info(
                    f"[df_id: {discovered_file.id}] FileNotFound error for {discovered_file.original_filename}"
                )


class AthensServicesRunner(VendorDocumentDownloadInterface):
    """Runner Class for Athens Services"""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.login_page = AthensServicesLoginPage(self.driver)
        self.home_page = AthensServicesHomePage(self.driver)
        self.billing_history_page = AthensServicesBillingHistoryPage(
            self.driver, self.download_location
        )

    def _login(self):
        """
        Login using credentials
        :return: Nothing
        """
        login_url = "https://billing.athensservices.com/webpak/signin.jsp"
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
        LOGGER.info("Extracting data from table...")
        start_date = datetime.strptime(
            self.run.request_parameters["start_date"], "%Y-%m-%d"
        ).date()
        discovered_files_list = self.billing_history_page.get_table_data(
            self.run, start_date
        )
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
            discovered_files.extend(self._download_documents())
            self.billing_history_page.download_invoice_by_url(discovered_files)
        finally:
            self._quit_driver()

        return discovered_files

    def login_flow(self, run: Run):
        self._login()
