import os
import re
from datetime import datetime, date
from typing import List

from selenium.common.exceptions import NoSuchElementException
from selenium.webdriver.remote.webelement import WebElement
from apps.adapters.base import PasswordBasedLoginPage, VendorDocumentDownloadInterface
from apps.adapters.framework import download
from apps.adapters.helpers.webdriver_helper import get_url, scroll_down, has_invoices
from apps.runs.models import Run, DiscoveredFile, DocumentType, FileFormat
from integrator import LOGGER
from spices.datetime_utils import date_from_string


# Billing History Page Locators
BILLING_HISTORY_PAGE = {
    "ACCOUNT_LIST": "#divAccountList>ul>li",
    "TABLE_ROWS": "#Content_dvRecentActivity>table>tbody>tr",
}

# Bills Page Locators
BILLS_PAGE = {
    "BILLING_STATEMENT_NUMBER": '#BillingBills>div>table>tbody> tr[class$="billsRow"]',
    "SUMMARY_NAV": "#nav_summary",
}


class IpfoneLoginPage(PasswordBasedLoginPage):
    """Restaurant Technologies Inc Login Page Web Elements"""

    SELECTOR_USERNAME_TEXTBOX = 'input[name="ctl00$Content$tbUsername"]'
    SELECTOR_PASSWORD_TEXTBOX = 'input[name="ctl00$Content$tbPass"]'
    SELECTOR_LOGIN_BUTTON = 'input[name="ctl00$Content$btLogin"]'
    SELECTOR_ERROR_MESSAGE_TEXT = "#MessageBoxError_MessageBoxContainer"


class IpfoneBillingHistoryPage:
    """Billing History Page class for Ipfone"""

    def __init__(self, driver, download_location: str):
        self.driver = driver
        self.download_location = download_location
        self.vendor = "IPfone"

    def get_table_rows(self) -> List[WebElement]:
        """Return the billing history table rows"""
        return self.driver.find_elements_by_css_selector(
            BILLING_HISTORY_PAGE["TABLE_ROWS"]
        )

    def account_list(self):
        """Return account rows"""
        return self.driver.find_elements_by_css_selector(
            BILLING_HISTORY_PAGE["ACCOUNT_LIST"]
        )

    @staticmethod
    def get_invoice_number(inv_list, invoice_date):
        """get matching invoice number of date"""
        return (
            "".join(
                [
                    match["s_number"]
                    for match in inv_list
                    if match["s_date"] == invoice_date
                ]
            )
            or None
        )

    def get_table_data(
        self, run: Run, from_date: date, statement_data: List
    ) -> List[DiscoveredFile]:
        """
        Extracts invoice details from Table
        :param run: Run Object
        :param from_date: Start date of the invoices to be downloaded
        :param statement_data: Statement number for match and set invoice number
        :return: Returns the list of Discovered File
        """
        discovered_files = []
        scroll_down(self.driver)

        if not has_invoices(self.driver, value=BILLING_HISTORY_PAGE["TABLE_ROWS"]):
            return discovered_files

        # iterate table rows
        for row in self.get_table_rows()[1:]:

            if not re.search(
                r"Statement",
                row.find_element_by_css_selector("td:nth-child(1)").text,
                re.IGNORECASE,
            ):
                continue

            # invoice date
            invoice_date = date_from_string(
                row.find_element_by_css_selector("td:nth-child(5)").text, "%m/%d/%Y"
            )

            if invoice_date < from_date:
                return discovered_files

            # total amount
            total_amount = row.find_element_by_css_selector("td:nth-child(2)").text

            # customer number
            customer_number = re.sub(
                r"\(|\).*",
                "",
                row.find_element_by_css_selector("td:nth-child(3)").text,
                re.DOTALL,
            )

            # restaurant name
            restaurant_name = re.sub(
                r"\(\d+\)", "", row.find_element_by_css_selector("td:nth-child(3)").text
            )

            # download url
            try:
                download_url = row.find_element_by_css_selector(
                    "td:nth-child(7) a"
                ).get_attribute("href")
            except NoSuchElementException:
                LOGGER.info("No download url element found")
                continue

            # invoice number
            invoice_number = self.get_invoice_number(statement_data, invoice_date)

            reference_code = f"{customer_number}_{invoice_number}_{invoice_date}"

            # document property
            document_properties = {
                "customer_number": f"{customer_number}",
                "invoice_number": f"{invoice_number}",
                "invoice_date": f"{invoice_date}",
                "total_amount": f"{total_amount}",
                "restaurant_name": f"{restaurant_name}",
                "vendor_name": f"{self.vendor}",
            }

            try:
                # pylint: disable=no-member
                discovered_file = DiscoveredFile.build_unique(
                    run,
                    reference_code=reference_code,
                    document_type=DocumentType.INVOICE.ident,
                    file_format=FileFormat.PDF.ident,
                    original_download_url=download_url,
                    original_filename=f"{reference_code}.pdf",
                    document_properties=document_properties,
                )

                LOGGER.info(
                    "Invoice details row data: %s",
                    str(discovered_file.document_properties),
                )
                # discover file download
                discovered_files.append(discovered_file)

            except DiscoveredFile.AlreadyExists:
                LOGGER.info(
                    f"Discovered file already exists with reference code : {reference_code}"
                )

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
                # pass the download dir, since we're passing a pattern below
                local_filepath=os.path.join(
                    self.download_location,
                    f'Bill_{discovered_file.document_properties["invoice_number"]}.pdf',
                ),
                rename_to=os.path.join(
                    self.download_location, discovered_file.original_filename
                ),
                file_exists_check_kwargs=dict(timeout=50),
            )
            download.download_discovered_file(discovered_file, _downloader)

    def processing_account_list(self, run, start_date, statement_data):
        """Processing accounts list"""
        discovered_files_list = []

        # iter accounts
        for account_list in range(len(self.account_list())):
            self.account_list()[account_list].click()

            discovered_files_list.extend(
                self.get_table_data(run, start_date, statement_data)
            )
        return discovered_files_list


class BillStatement:
    """Statement Bills page"""

    def __init__(self, driver):
        self.driver = driver

    @staticmethod
    def make_bills_property(bills_ele):
        """make statement page items as dict format"""
        return {
            "s_number": bills_ele.find_elements_by_css_selector("td")[1].text,
            "s_date": date_from_string(
                bills_ele.find_elements_by_css_selector("td")[3].text, "%m/%d/%Y"
            ),
        }

    def get_bills_page_number_list(self):
        """Get statement number and steps the empty rows"""
        return self.driver.find_elements_by_css_selector(
            BILLS_PAGE["BILLING_STATEMENT_NUMBER"]
        )

    def get_bills_page_process(self):
        """Get statement and change valid date format"""
        return list(map(self.make_bills_property, self.get_bills_page_number_list()))

    def get_summary_navigation(self):
        """Select navigation menu"""
        return self.driver.find_element_by_css_selector(BILLS_PAGE["SUMMARY_NAV"])

    def get_navigate_view_bill(self):
        """navigate bills page"""
        get_url(self.driver, "https://ipfone.billcenter.net/Bills/default.aspx")


class IpfoneRunner(VendorDocumentDownloadInterface):
    """Runner Class for Ipfone"""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.login_page = IpfoneLoginPage(self.driver)
        self.bills_page = BillStatement(self.driver)
        self.billing_history_page = IpfoneBillingHistoryPage(
            self.driver, self.download_location
        )

    def _login(self):
        """
        Login using credentials
        :return: Nothing
        """
        login_url = "https://ipfone.billcenter.net/"
        get_url(self.driver, login_url)
        self.login_page.login(self.run.job.username, self.run.job.password)

        # navigate to statement page
        self.bills_page.get_navigate_view_bill()

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

        # get invoice numbers with date
        statement_data = self.bills_page.get_bills_page_process()

        # summary page
        self.bills_page.get_summary_navigation().click()

        # processing table with select restaurant
        discovered_files_list = self.billing_history_page.processing_account_list(
            self.run, start_date, statement_data
        )

        # download discovered pdf
        self.billing_history_page.download_invoice_by_url(discovered_files_list)
        LOGGER.info(
            f"Downloaded invoice by download link available: {len(discovered_files_list)}"
        )

        # return discovered_files_list
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
        finally:
            self._quit_driver()

        return discovered_files

    def login_flow(self, run: Run):
        self._login()
