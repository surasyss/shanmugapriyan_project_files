import os
from datetime import datetime
from typing import List

from selenium.common.exceptions import WebDriverException
from selenium.webdriver.remote.webelement import WebElement

from apps.adapters.base import VendorDocumentDownloadInterface, PasswordBasedLoginPage
from apps.adapters.framework import download
from apps.adapters.helpers.webdriver_helper import (
    wait_for_element,
    get_url,
    has_invoices,
    WEB_DRIVER_EXCEPTIONS,
    handle_popup,
)
from apps.adapters.vendors import LOGGER
from apps.runs.models import Run, DiscoveredFile, DocumentType, FileFormat
from spices.datetime_utils import date_from_string

# Invoices Page Locators
INVOICE_TABLE_ELEMENTS = {
    "RESTAURANT_NAME": "p.account-address.spacer-top-xs",
    "INVOICE_TABLE_ROWS": 'table > tbody > tr[ng-repeat^="invoice in allInvoices"]',
    "PAST_INVOICE_RADIO_BTN": "table.your-financials-table-2 td:nth-child(2) label.radio span.control-indicator",
}


class PitneyBowesLoginPage(PasswordBasedLoginPage):
    """Pitney Bowes Login Page Web Elements"""

    SELECTOR_USERNAME_TEXTBOX = "#username"
    SELECTOR_PASSWORD_TEXTBOX = "#password"
    SELECTOR_LOGIN_BUTTON = "button.login-button"
    SELECTOR_ERROR_MESSAGE_TEXT = "p.error, div.message--login"


class PitneyBowesHomePage:
    """Pitney Bowes home page action methods come here."""

    def __init__(self, driver):
        self.driver = driver

    def go_to_billing_account_invoices(self):
        """Navigate to billing account invoice page."""
        account_invoice_url = (
            "https://www.pitneybowes.us/signin/youraccount.go?request_locale=en_US#/"
            "financial-bills/billing-account-invoices"
        )
        get_url(self.driver, account_invoice_url)


class PitneyBowesInvoicesPage:
    """Pitney Bowes Invoices page action methods come here."""

    def __init__(self, driver, download_location: str):
        super().__init__()
        self.driver = driver
        self.download_location = download_location
        self.vendor_name = "Pitney Bowes"
        self.home_page = PitneyBowesHomePage(self.driver)

    def get_restaurant_name(self) -> WebElement:
        """Return restaurant name web element"""
        try:
            return self.driver.find_element_by_css_selector(
                INVOICE_TABLE_ELEMENTS["RESTAURANT_NAME"]
            )
        except WEB_DRIVER_EXCEPTIONS:
            LOGGER.info("restaurant name unavailable ...")

    def select_past_invoice_radio_btn(self):
        """Return past invoice radio button"""
        for index in range(3):
            try:
                wait_for_element(
                    self.driver,
                    value=INVOICE_TABLE_ELEMENTS["PAST_INVOICE_RADIO_BTN"],
                    msg="Past Invoice Radio",
                    retry_attempts=2,
                )
                return self.driver.find_element_by_css_selector(
                    INVOICE_TABLE_ELEMENTS["PAST_INVOICE_RADIO_BTN"]
                )
            except WebDriverException as excep:
                LOGGER.warning(f"{excep} in {self.driver.current_url}")
                self.home_page.go_to_billing_account_invoices()
                if index == 2:
                    raise

    def get_invoice_table_rows(self) -> [WebElement]:
        """Return table row elements"""
        return self.driver.find_elements_by_css_selector(
            INVOICE_TABLE_ELEMENTS["INVOICE_TABLE_ROWS"]
        )

    def get_table_data(
        self, run: Run, from_date, invoice_type="current"
    ) -> List[DiscoveredFile]:
        """Extracts invoice details from current and past invoice table
        :return: Returns the list of Discovered FileInvoice table
        """
        discovered_files = []

        if invoice_type == "past":
            # click past invoice radio button
            self.select_past_invoice_radio_btn().click()

        if not has_invoices(
            self.driver, value=INVOICE_TABLE_ELEMENTS["INVOICE_TABLE_ROWS"]
        ):
            return discovered_files

        for row in self.get_invoice_table_rows():
            due_date = date_from_string(
                row.find_elements_by_css_selector("td")[4].text, "%b %d, %Y"
            )

            if due_date < from_date:
                LOGGER.info(
                    f"Skipping invoices because date '{due_date}' is outside requested range"
                )
                return discovered_files

            invoice_number = row.find_elements_by_css_selector("td")[1].text
            customer_number = row.find_elements_by_css_selector("td")[2].text
            reference_code = f"{customer_number}_{invoice_number}_{due_date}"
            restaurant_name = (
                self.get_restaurant_name().text if self.get_restaurant_name() else ""
            )

            document_properties = {
                "customer_number": f"{customer_number}",
                "invoice_number": f"{invoice_number}",
                "invoice_date": f"{due_date}",
                "total_amount": f'{row.find_elements_by_css_selector("td")[5].text}',
                "vendor_name": self.vendor_name,
                "restaurant_name": f"{restaurant_name}".split("\n", 1)[0],
            }

            try:
                # pylint: disable=no-member
                discovered_file = DiscoveredFile.build_unique(
                    run,
                    reference_code,
                    document_type=DocumentType.INVOICE.ident,
                    file_format=FileFormat.PDF.ident,
                    original_download_url="",
                    original_filename=f"{reference_code}.pdf",
                    document_properties=document_properties,
                )
            except DiscoveredFile.AlreadyExists:
                LOGGER.info(
                    f"Discovered file already exists with reference code : {reference_code}"
                )
                continue  # skip if seen before

            download_element = row.find_element_by_css_selector("a > span.newpdficon")

            self.download_invoice_by_click(discovered_file, download_element)
            discovered_files.append(discovered_file)
            LOGGER.info(
                f"Invoice details row data: {discovered_file.document_properties}"
            )
            handle_popup(
                self.driver,
                value="div#surveyclose",
                msg="survey Popup",
                retry_attempts=1,
            )
        return discovered_files

    def download_invoice_by_click(self, discovered_file, download_element):
        """Download the File in PDF format
        :param discovered_file: DiscoveredFile variable
        :param download_element: download web element
        """
        LOGGER.info(f"Navigate to: {discovered_file.original_download_url}")
        file_pattern = rf"[0-9a-z]+-[0-9a-z]+-[0-9a-z]+-[0-9a-z]+-[0-9a-z]+.pdf$"
        _downloader = download.DriverExecuteScriptBasedDownloader(
            self.driver,
            script="arguments[0].click();",
            script_args=(download_element,),
            local_filepath=self.download_location,
            rename_to=os.path.join(
                self.download_location, discovered_file.original_filename
            ),
            file_exists_check_kwargs=dict(timeout=40, pattern=file_pattern),
        )
        download.download_discovered_file(discovered_file, _downloader)


class PitneyBowesRunner(VendorDocumentDownloadInterface):
    """Runner Class for Pitney Bowes"""

    is_angular = True

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.login_page = PitneyBowesLoginPage(self.driver)
        self.home_page = PitneyBowesHomePage(self.driver)
        self.invoices_page = PitneyBowesInvoicesPage(
            self.driver, self.download_location
        )

    def _login(self):
        """
        Login to Pitney Bowes
        :return: Nothing
        """
        login_url = "https://www.pitneybowes.us/signin/logon.go?request_locale=en_US#/account/login"
        get_url(self.driver, login_url)
        self.login_page.login(self.run.job.username, self.run.job.password)

    def _download_invoices(self) -> List[DiscoveredFile]:
        """
        Downloads the Invoices
        :return: Returns the list of the Discovered Files
        """
        document_type = self.run.job.requested_document_type
        if document_type == "invoice":
            LOGGER.info("Extracting data from table...")
            start_date = datetime.strptime(
                self.run.request_parameters["start_date"], "%Y-%m-%d"
            ).date()

            discovered_files_list = self.invoices_page.get_table_data(
                self.run, start_date
            )
            discovered_files_list += self.invoices_page.get_table_data(
                self.run, start_date, invoice_type="past"
            )
            LOGGER.info(
                f"Total Invoices within date range and download link available: {len(discovered_files_list)}"
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
            self.home_page.go_to_billing_account_invoices()
            discovered_files = self._download_invoices()
        finally:
            self._quit_driver()
        return discovered_files

    def login_flow(self, run: Run):
        self._login()
