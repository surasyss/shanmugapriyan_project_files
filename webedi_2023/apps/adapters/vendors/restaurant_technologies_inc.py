import os
from datetime import datetime, date
from typing import List
import time

from selenium.common.exceptions import NoSuchElementException
from selenium.webdriver.remote.webelement import WebElement
from apps.adapters.base import PasswordBasedLoginPage, VendorDocumentDownloadInterface
from apps.adapters.framework import download
from apps.adapters.helpers.webdriver_helper import (
    get_url,
    explicit_wait_till_visibility,
    has_invoices,
    WEB_DRIVER_EXCEPTIONS,
)

from apps.runs.models import Run, DiscoveredFile, DocumentType, FileFormat
from integrator import LOGGER
from spices.datetime_utils import date_from_string

# Billing Center Page Locators
BILLING_CENTER_PAGE = {
    "BILLING_RESTAURANT_LIST": 'select[name="ctl00$ContentPlaceHolder1$ddlLocations"]>option',
    "BILLING_TABLE_CHECK": "#gvInvoiceList",
}

# Billing History Page Locators
BILLING_HISTORY_PAGE = {
    "SEARCH_BUTTON": "#btnSearchStoreAndDate",
    "SELECT_DATE_DROPDOWN": "#reportrange",
    "TABLE_ROWS": "#gvInvoiceList>tbody>tr",
    "START_DATE": 'input[name="ctl00$ContentPlaceHolder1$txtStart"]',
    "VIEW_ALL": "#lnkViewAll",
    "CUSTOMER_NUMBER": "#lblCustNumber",
}


class RestaurantTechnologiesIncLoginPage(PasswordBasedLoginPage):
    """Restaurant Technologies Inc Login Page Web Elements"""

    SELECTOR_USERNAME_TEXTBOX = 'input[name="txtUserName"]'
    SELECTOR_PASSWORD_TEXTBOX = 'input[name="txtPassword"]'
    SELECTOR_LOGIN_BUTTON = 'input[name="btnLogin"]'
    SELECTOR_ERROR_MESSAGE_TEXT = "div.loginError span"


class RestaurantTechnologiesIncBillingHistoryPage:
    """Billing History Page class for Restaurant Technologies Inc"""

    def __init__(self, driver, download_location: str):
        self.driver = driver
        self.download_location = download_location
        self.vendor = "RESTAURANT TECHNOLOGIES INC"

    def get_search_button(self):
        """Load report button"""
        return self.driver.find_element_by_css_selector(
            BILLING_HISTORY_PAGE["SEARCH_BUTTON"]
        )

    def get_view_all_link(self):
        """select view table extension text"""
        return self.driver.find_element_by_css_selector(
            BILLING_HISTORY_PAGE["VIEW_ALL"]
        )

    def get_start_date_input(self):
        """Set the start date"""
        return self.driver.find_element_by_css_selector(
            BILLING_HISTORY_PAGE["START_DATE"]
        )

    def processing_date_field(self, start_date):
        """Clear date and send key value"""
        # clear value of date input
        self.get_start_date_input().clear()
        time.sleep(0.5)
        # set the starting date
        self.get_start_date_input().send_keys(start_date.strftime("%m/%d/%Y"))

    def get_table_rows(self) -> List[WebElement]:
        """Return the billing history table rows"""
        return self.driver.find_elements_by_css_selector(
            BILLING_HISTORY_PAGE["TABLE_ROWS"]
        )

    def get_table_data(
        self, run: Run, from_date: date, restaurant_name: str
    ) -> List[DiscoveredFile]:
        """
        Extracts invoice details from Table
        :param run: Run Object
        :param from_date: Start date of the invoices to be downloaded
        :param restaurant_name: restaurant name get from selection option
        :return: Returns the list of Discovered File
        """
        discovered_files = []
        # click view all text link
        try:
            self.get_view_all_link().click()
        except NoSuchElementException:
            LOGGER.info(f"view all text end of the row in table Not found")

        if not has_invoices(self.driver, value=BILLING_HISTORY_PAGE["TABLE_ROWS"]):
            return discovered_files

        # iterate table rows
        for row in self.get_table_rows()[:-1]:
            # invoice date
            invoice_date = date_from_string(
                row.find_element_by_css_selector("td:nth-child(2)").text, "%m/%d/%Y"
            )

            if invoice_date < from_date:
                return discovered_files

            # invoice number
            invoice_number = row.find_element_by_css_selector("td:nth-child(1)").text

            # total amount
            total_amount = row.find_element_by_css_selector("td:nth-child(3)").text

            # click download button
            row.find_element_by_css_selector("td a").click()

            self.driver.switch_to_window(self.driver.window_handles[1])

            # customer number
            customer_number = self.driver.find_element_by_css_selector(
                BILLING_HISTORY_PAGE["CUSTOMER_NUMBER"]
            ).text

            reference_code = f"{customer_number}_{invoice_number}_{invoice_date}"

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
                    original_download_url=self.driver.current_url,
                    original_filename=f"{reference_code}.pdf",
                    document_properties=document_properties,
                )
            except DiscoveredFile.AlreadyExists:
                LOGGER.info(
                    f"Discovered file already exists with reference code : {reference_code}"
                )
                self.driver.close()
                self.driver.switch_to_window(self.driver.window_handles[0])
                continue  # skip if seen before

            LOGGER.info(
                "Invoice details row data: %s", str(discovered_file.document_properties)
            )

            # discover file download
            discovered_files.append(discovered_file)

            self.driver.close()
            self.driver.switch_to_window(self.driver.window_handles[0])

        return discovered_files

    def download_invoice_by_url(self, discovered_files):
        """
        Download the File in PDF format
        :param discovered_files: DiscoveredFile variable
        """
        # rename is required, if we have download multiple files hence
        # we need to rename the file as for certain conditions for uploading to s3
        for discovered_file in discovered_files:
            get_url(self.driver, discovered_file.original_download_url)
            _downloader = download.DriverExecuteCDPCmdBasedDownloader(
                self.driver,
                cmd="Page.printToPDF",
                cmd_args={"printBackground": True},
                # pass the download dir, since we're passing a pattern below
                local_filepath=f"{self.download_location}/BillingHistoryDetail.pdf",
                rename_to=os.path.join(
                    self.download_location, discovered_file.original_filename
                ),
                file_exists_check_kwargs=dict(timeout=50),
            )
            download.download_discovered_file(discovered_file, _downloader)

    def get_select_location_length(self):
        """Get restaurant location count"""
        return len(
            self.driver.find_elements_by_css_selector(
                BILLING_CENTER_PAGE["BILLING_RESTAURANT_LIST"]
            )
        )

    def select_location(self, option):
        """Get all restaurant location and length"""
        return self.driver.find_elements_by_css_selector(
            BILLING_CENTER_PAGE["BILLING_RESTAURANT_LIST"]
        )[option]

    def check_table_element(self):
        """check table element"""
        return self.driver.find_element_by_css_selector(
            BILLING_CENTER_PAGE["BILLING_TABLE_CHECK"]
        )

    def processing_restaurant_select_option(self, run, start_date):
        """Processing location with table"""
        discovered_files_list = []
        for option in range(self.get_select_location_length()):
            select_option = self.select_location(option)
            explicit_wait_till_visibility(
                self.driver, select_option, msg="wait for option element"
            )
            restaurant_name = select_option.text

            # select option
            select_option.click()

            # next search button
            self.get_search_button().click()

            discovered_files_list.extend(
                self.get_table_data(run, start_date, restaurant_name)
            )

        return discovered_files_list


class RestaurantTechnologiesIncRunner(VendorDocumentDownloadInterface):
    """Runner Class for Restaurant Technologies Inc"""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.login_page = RestaurantTechnologiesIncLoginPage(self.driver)
        self.billing_history_page = RestaurantTechnologiesIncBillingHistoryPage(
            self.driver, self.download_location
        )

    def _login(self):
        """
        Login using credentials
        :return: Nothing
        """
        login_url = "http://www.rtitom.com/LogIn.aspx?ReturnUrl=%2f"
        get_url(self.driver, login_url)
        self.login_page.login(self.run.job.username, self.run.job.password)

        # navigate to bill history page
        get_url(self.driver, "http://www.rtitom.com/MyAccount/BillingHistory.aspx")

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
        discovered_files_list = []
        LOGGER.info("Extracting data from table...")
        start_date = datetime.strptime(
            self.run.request_parameters["start_date"], "%Y-%m-%d"
        ).date()
        try:
            # processing date field
            self.billing_history_page.processing_date_field(start_date)

            # processing table with select restaurant
            discovered_files_list = (
                self.billing_history_page.processing_restaurant_select_option(
                    self.run, start_date
                )
            )

            # download discovered pdf
            self.billing_history_page.download_invoice_by_url(discovered_files_list)
            LOGGER.info(
                f"Downloaded invoice by download link available: {len(discovered_files_list)}"
            )

        except WEB_DRIVER_EXCEPTIONS as excep:
            LOGGER.info(excep)

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
