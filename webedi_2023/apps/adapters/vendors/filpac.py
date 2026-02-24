import os
from datetime import datetime, date
from typing import List
import re

from selenium.webdriver.remote.webelement import WebElement
from apps.adapters.base import PasswordBasedLoginPage, VendorDocumentDownloadInterface
from apps.adapters.framework import download
from apps.adapters.helpers.webdriver_helper import (
    get_url,
    wait_for_element,
    has_invoices,
    Select,
)
from apps.runs.models import Run, DiscoveredFile, DocumentType, FileFormat
from integrator import LOGGER
from spices.datetime_utils import date_from_string

# Billing History Page Locators
BILLING_HISTORY_PAGE = {
    "TABLE_ROWS": '#ctl00_MainContent_invoiceGridView>tbody>tr[class="TableContent"]'
}

# Home Page Locators
HOME_PAGE_LOCATORS = {
    "CUSTOMERS_LINK": "#ctl00_selectNewCustomerLink",
    "CUSTOMER_ACCOUNTS": "#ctl00_selectNewCustomerWindow_tmpl_selectNewCust>option",
    "SELECT_ACCOUNT": "#ctl00_selectNewCustomerWindow_tmpl_selectNewCust",
    "CUSTOMER_SUBMIT_BUTTON": "#ctl00_selectNewCustomerWindow_tmpl_submitButton",
}


class FilpacLoginPage(PasswordBasedLoginPage):
    """Filpac Login Page Web Elements"""

    SELECTOR_USERNAME_TEXTBOX = (
        'input[name="ctl00$MainContent$loginControl$LoginUI$UserName"]'
    )
    SELECTOR_PASSWORD_TEXTBOX = (
        'input[name="ctl00$MainContent$loginControl$LoginUI$Password"]'
    )
    SELECTOR_LOGIN_BUTTON = (
        'input[name="ctl00$MainContent$loginControl$LoginUI$LoginButton"]'
    )
    SELECTOR_ERROR_MESSAGE_TEXT = (
        "#ctl00_MainContent_loginControl_LoginUI > tbody > tr > td >table > tbody > "
        "tr:nth-child(5)> td "
    )


class FilpacBillHistoryPage:
    """Billing History Page class for Filpac"""

    def __init__(self, driver, download_location: str):
        self.driver = driver
        self.download_location = download_location
        self.vendor = "FILPAC"

    def get_table_rows(self) -> List[WebElement]:
        """Return the billing history table rows"""
        return self.driver.find_elements_by_css_selector(
            BILLING_HISTORY_PAGE["TABLE_ROWS"]
        )

    def get_table_data(
        self, run: Run, from_date: date, account_detail: dict
    ) -> List[DiscoveredFile]:
        """
        Extracts invoice details from Table
        :param run: Run Object
        :param from_date: Start date of the invoices to be downloaded
        :param account_detail: get account details
        :return: Returns the list of Discovered File
        """
        discovered_files = []
        if not has_invoices(self.driver, value=BILLING_HISTORY_PAGE["TABLE_ROWS"]):
            return discovered_files

        for row in self.get_table_rows():
            # invoice date
            invoice_date = date_from_string(
                row.find_elements_by_css_selector("td")[2].text, "%m/%d/%Y"
            )

            if invoice_date < from_date:
                return discovered_files

            # invoice number
            invoice_number = row.find_elements_by_css_selector("td")[0].text

            reference_code = re.sub(
                r"\.",
                "",
                f'{account_detail["account_number"]}_{invoice_number}_{invoice_date}',
            )

            document_properties = {
                "customer_number": f'{account_detail["account_number"]}',
                "invoice_number": f"{invoice_number}",
                "invoice_date": f"{invoice_date}",
                "total_amount": None,
                "restaurant_name": f'{re.sub(r".*-", "", account_detail["restaurant_name"]).strip()}',
                "vendor_name": f"{self.vendor}",
            }
            try:
                # pylint: disable=no-member
                discovered_file = DiscoveredFile.build_unique(
                    run,
                    reference_code=reference_code,
                    document_type=DocumentType.INVOICE.ident,
                    file_format=FileFormat.PDF.ident,
                    original_download_url=row.find_elements_by_css_selector("td a")[0],
                    original_filename=f"{reference_code}.pdf",
                    document_properties=document_properties,
                )
            except DiscoveredFile.AlreadyExists:
                LOGGER.info(
                    f"Discovered file already exists with reference code : {reference_code}"
                )
                continue  # skip if seen before

            # download element
            self.download_invoice_by_url(row, discovered_file)
            discovered_files.append(discovered_file)

            LOGGER.info(
                "Invoice details row data: %s", str(discovered_file.document_properties)
            )

        return discovered_files

    def download_invoice_by_url(self, row, discovered_file):
        """
        Download the File in PDF format
        :param discovered_file: DiscoveredFile variable
        :param row: DiscoveredFile row elements
        """
        # rename is required, if we have download multiple files hence
        # we need to rename the file as for certain conditions for uploading to s3
        _downloader = download.DriverExecuteScriptBasedDownloader(
            self.driver,
            script="arguments[0].click();",
            script_args=(row.find_elements_by_css_selector("td a")[0],),
            # pass the download dir, since we're passing a pattern below
            local_filepath=f"{self.download_location}/CustomerInvoice.pdf",
            rename_to=os.path.join(
                self.download_location, discovered_file.original_filename
            ),
            file_exists_check_kwargs=dict(timeout=80),
        )
        download.download_discovered_file(discovered_file, _downloader)


class FilpacHomePage:
    """Home Page Class for Filpac"""

    def __init__(self, driver, bill_history_page):
        self.driver = driver
        self.bill_history_page = bill_history_page

    def get_select_option_value(self) -> List:
        """ " Return option all values"""
        return [
            {
                "account_number": customer_num.get_attribute("value"),
                "restaurant_name": customer_num.text,
            }
            for customer_num in self.driver.find_elements_by_css_selector(
                HOME_PAGE_LOCATORS["CUSTOMER_ACCOUNTS"]
            )
        ]

    def navigate_invoice_url(self):
        """Navigate to invoice url"""
        get_url(self.driver, "https://customerportal.filpac.net/Main/invoices.aspx")

    def get_select_drop_down(self) -> WebElement:
        """Return new customer select dropdown"""
        return self.driver.find_element_by_css_selector(
            HOME_PAGE_LOCATORS["SELECT_ACCOUNT"]
        )

    def get_new_customer_submit_button(self) -> WebElement:
        """Return new customer submit button"""
        return self.driver.find_element_by_css_selector(
            HOME_PAGE_LOCATORS["CUSTOMER_SUBMIT_BUTTON"]
        )

    def get_new_customer_link(self) -> WebElement:
        """Return new customer element"""
        wait_for_element(
            self.driver,
            value=HOME_PAGE_LOCATORS["CUSTOMERS_LINK"],
            msg="wait for customer click",
            timeout=30,
        )
        return self.driver.find_element_by_css_selector(
            HOME_PAGE_LOCATORS["CUSTOMERS_LINK"]
        )

    def home_page_customer_processing(self, run, start_date):
        """Return collected discovered file"""
        collect_discover_files = []

        # click new customer
        self.get_new_customer_link().click()

        # iterate new customer list
        for customer_num in self.get_select_option_value():

            wait_for_element(
                self.driver,
                value=HOME_PAGE_LOCATORS["SELECT_ACCOUNT"],
                msg="wait for new customer element",
                timeout=30,
            )
            # Select dropdown and set value
            Select(self.get_select_drop_down()).select_by_value(
                customer_num["account_number"]
            )

            # Click submit button
            self.get_new_customer_submit_button().click()

            # navigate invoice history page
            self.navigate_invoice_url()

            # history table data stored in list
            collect_discover_files.extend(
                self.bill_history_page.get_table_data(run, start_date, customer_num)
            )

            # browser back button
            self.driver.back()

            # wait for next customer link
            self.get_new_customer_link().click()

        return collect_discover_files


class FilpacRunner(VendorDocumentDownloadInterface):
    """Runner Class for Filpac"""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.login_page = FilpacLoginPage(self.driver)
        self.bill_history_page = FilpacBillHistoryPage(
            self.driver, self.download_location
        )
        self.home_page = FilpacHomePage(self.driver, self.bill_history_page)

    def _login(self):
        """
        Login using credentials
        :return: Nothing
        """
        login_url = "https://customerportal.filpac.net/enterpass.aspx"
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
        discovered_files_list = self.home_page.home_page_customer_processing(
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
        finally:
            self._quit_driver()

        return discovered_files

    def login_flow(self, run: Run):
        self._login()
