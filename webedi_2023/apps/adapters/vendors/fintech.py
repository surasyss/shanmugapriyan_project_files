import os
from datetime import datetime, date
from typing import List

from selenium.common.exceptions import ElementClickInterceptedException
from selenium.webdriver.common.by import By
from selenium.webdriver.remote.webelement import WebElement
from apps.adapters.base import PasswordBasedLoginPage, VendorDocumentDownloadInterface
from apps.adapters.framework import download
from apps.adapters.helpers.webdriver_helper import (
    get_url,
    has_invoices,
    handle_popup,
    explicit_wait_till_clickable,
)
from apps.runs.models import Run, DiscoveredFile, DocumentType, FileFormat
from integrator import LOGGER
from spices.datetime_utils import date_from_string

# Home Page Locators
HOME_PAGE_LOCATORS = {"NOTIFICATION": 'div[id="notificationModal"]'}

# Billing History Page Locators
BILLING_HISTORY_PAGE = {
    "LOAD_REPORT_BUTTON": 'div[name="btnFormSubmitFromCalendar"]',
    "SELECT_DATE_DROPDOWN": 'div[id="reportrange"]',
    "TABLE_ROWS": 'table[id="report_table"] > tbody > tr',
    "START_DATE": 'input[name="daterangepicker_start"]',
    "REPORT_RANGE": 'div[id="reportrange"]',
    "SELECT_ALL_COMPANY": '//li[text()="All"]',
    "DESC_ORDER_DATE": '//th[text()="Invoice Date"]',
}


class FintechLoginPage(PasswordBasedLoginPage):
    """Fintech Login Page Web Elements"""

    SELECTOR_USERNAME_TEXTBOX = 'input[id="user"]'
    SELECTOR_PASSWORD_TEXTBOX = 'input[id="password"]'
    SELECTOR_LOGIN_BUTTON = 'input[name="sSubmit"]'
    SELECTOR_ERROR_MESSAGE_TEXT = "form.nav__login p.error"


class FintechBillingHistoryPage:
    """Billing History Page class for Fintech"""

    def __init__(self, driver, download_location: str):
        self.driver = driver
        self.download_location = download_location
        self.vendor = "Fintech"

    def get_load_report_button(self):
        """load report button"""
        return self.driver.find_element_by_css_selector(
            BILLING_HISTORY_PAGE["LOAD_REPORT_BUTTON"]
        )

    def get_table_date_click(self):
        """date table drop down window"""
        self.driver.find_element_by_css_selector(
            BILLING_HISTORY_PAGE["SELECT_DATE_DROPDOWN"]
        ).click()

    def get_report_link(self):
        """drop down report link"""
        self.driver.find_element_by_css_selector(
            BILLING_HISTORY_PAGE["REPORT_RANGE"]
        ).click()

    def get_start_date_input(self):
        """set start date for input box"""
        return self.driver.find_element_by_css_selector(
            BILLING_HISTORY_PAGE["START_DATE"]
        )

    def get_all_company_txt(self):
        """select all company text in WebElement"""
        self.driver.find_element_by_xpath(
            BILLING_HISTORY_PAGE["SELECT_ALL_COMPANY"]
        ).click()

    def set_date_to_date_filter_table(self, start_date):
        explicit_wait_till_clickable(
            self.driver,
            (By.CSS_SELECTOR, BILLING_HISTORY_PAGE["REPORT_RANGE"]),
            timeout=10,
            msg="Date Range",
        )
        # drop down report link
        self.get_report_link()
        # clear date field
        self.get_start_date_input().clear()
        # set start date and click
        self.get_start_date_input().send_keys(start_date.strftime("%m/%d/%Y"))
        # select all company text
        self.get_all_company_txt()
        # click reports button
        self.get_load_report_button().click()

    def get_table_rows(self) -> List[WebElement]:
        """Return the billing history table rows"""
        return self.driver.find_elements_by_css_selector(
            BILLING_HISTORY_PAGE["TABLE_ROWS"]
        )

    def change_desc_invoice_date(self):
        """change invoice date order as desc order"""
        return self.driver.find_element_by_xpath(
            BILLING_HISTORY_PAGE["DESC_ORDER_DATE"]
        )

    def get_table_data(self, run: Run, from_date: date) -> List[DiscoveredFile]:
        """
        Extracts invoice details from Table
        :param run: Run Object
        :param from_date: Start date of the invoices to be downloaded
        :return: Returns the list of Discovered File
        """

        discovered_files = []
        # change invoice order as descent order
        self.change_desc_invoice_date().click()

        if not has_invoices(self.driver, value=BILLING_HISTORY_PAGE["TABLE_ROWS"]):
            return discovered_files

        for row in self.get_table_rows():
            invoice_date = date_from_string(
                row.find_elements_by_css_selector("td")[6].text, "%m/%d/%Y"
            )
            if invoice_date < from_date:
                return discovered_files
            store_number = row.find_elements_by_css_selector("td")[2].text
            invoice_number = row.find_elements_by_css_selector("td")[5].text
            restaurant_name = row.find_elements_by_css_selector("td")[1].text
            reference_code = f"{store_number}_{invoice_number}_{invoice_date}"
            total_amount = row.find_elements_by_css_selector("td")[9].text
            try:
                download_element = row.find_elements_by_css_selector("td a")[2]
                main_page = self.driver.window_handles[0]
                download_element.click()
                self.driver.switch_to.window(self.driver.window_handles[1])
                document_properties = {
                    "customer_number": f"{store_number}",
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
                    continue  # skip if seen before

                # discover file download
                self.download_invoice_by_url(discovered_file)
                discovered_files.append(discovered_file)
                LOGGER.info(
                    "Invoice details row data: %s",
                    str(discovered_file.document_properties),
                )
                self.driver.close()
                self.driver.switch_to.window(main_page)
            except ElementClickInterceptedException:
                self.driver.execute_script(
                    "window.scrollTo(0,document.documentElement.scrollHeight);"
                )
        return discovered_files

    def download_invoice_by_url(self, discovered_file):
        """
        Download the File in PDF format
        :param discovered_file: DiscoveredFile variable
        """
        # rename is required, if we have download multiple files hence
        # we need to rename the file as for certain conditions for uploading to s3
        _downloader = download.DriverExecuteCDPCmdBasedDownloader(
            self.driver,
            cmd="Page.printToPDF",
            cmd_args={"printBackground": True},
            # pass the download dir, since we're passing a pattern below
            local_filepath=f"{self.download_location}/invoice.pdf",
            rename_to=os.path.join(
                self.download_location, discovered_file.original_filename
            ),
            file_exists_check_kwargs=dict(timeout=50),
        )

        download.download_discovered_file(discovered_file, _downloader)


class FintechRunner(VendorDocumentDownloadInterface):
    """Runner Class for Fintech"""

    # uses_proxy = True

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.login_page = FintechLoginPage(self.driver)
        self.billing_history_page = FintechBillingHistoryPage(
            self.driver, self.download_location
        )

    def _login(self):
        """
        Login using credentials
        :return: Nothing
        """
        login_url = "https://fintech.com/login/"
        get_url(self.driver, login_url)
        self.login_page.login(self.run.job.username, self.run.job.password)

    def _download_documents(self) -> List[DiscoveredFile]:
        """
        Chooses the documents to be downloaded based on the document type
        :return: Returns the list of Discovered Files.
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

        # Navigate to invoice details page
        get_url(
            self.driver,
            "https://www.fintech.net/fms/reports/retailer_invoice_information_detailed.asp",
        )

        start_date = datetime.strptime(
            self.run.request_parameters["start_date"], "%Y-%m-%d"
        ).date()
        self.billing_history_page.set_date_to_date_filter_table(start_date)

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
            handle_popup(
                self.driver,
                value=HOME_PAGE_LOCATORS["NOTIFICATION"],
                msg="Notification page",
            )
            discovered_files.extend(self._download_documents())
        finally:
            self._quit_driver()

        return discovered_files

    def login_flow(self, run: Run):
        self._login()
