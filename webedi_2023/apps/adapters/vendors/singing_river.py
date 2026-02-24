import os
from datetime import datetime
import time
from typing import List
from selenium.webdriver.remote.webelement import WebElement
from selenium.common.exceptions import NoSuchElementException
from apps.adapters.base import VendorDocumentDownloadInterface, PasswordBasedLoginPage
from apps.adapters.helpers.webdriver_helper import (
    wait_for_element,
    get_url,
    has_invoices,
)
from apps.adapters.framework import download
from apps.adapters.vendors import LOGGER
from apps.runs.models import Run, DiscoveredFile, DocumentType, FileFormat
from spices.datetime_utils import date_from_string

# Home Page Locators
HOME_PAGE_LOCATORS = {
    "TERMS_AND_CONDITION": "button.btn-success",
    "ACCOUNT_DROP_DOWN": "div[class^='btn-group'] button",
    "ACCOUNT_LIST": "div.dropdown-menu.open ul li",
}

# Invoices Page Locators
INVOICE_TABLE_ELEMENT = {
    "INVOICE_TABLE_ROWS": "#BillHistoryTable tbody tr",
    "RESTAURANT_NAME": "li.billingAndPaymentsTabs.disabled.active a span strong",
}


class SingingRiverLoginPage(PasswordBasedLoginPage):
    """Singing River Login Page Web Elements."""

    SELECTOR_USERNAME_TEXTBOX = "#LoginUsernameTextBox"
    SELECTOR_PASSWORD_TEXTBOX = "#LoginPasswordTextBox"
    SELECTOR_LOGIN_BUTTON = "#LoginSubmitButton"
    SELECTOR_ERROR_MESSAGE_TEXT = "div.form-group span.help-block.ce-warningMessage"


class SingingRiverHomePage:
    """Singing River Home Page action methods come here."""

    def __init__(self, driver):
        self.driver = driver

    def terms_and_condition(self):
        """Check if the terms and conditions page exists or not;
        if it does, click the accept button."""
        wait_for_element(
            self.driver,
            value=HOME_PAGE_LOCATORS["TERMS_AND_CONDITION"],
            msg="click drop down",
            raise_exception=False,
        )

        try:
            terms_and_condition = self.driver.find_element_by_css_selector(
                HOME_PAGE_LOCATORS["TERMS_AND_CONDITION"]
            )
            terms_and_condition.click()
        except NoSuchElementException:
            LOGGER.info(f"The term and condition page is not shown.")

    def home_page_details(self):
        """Return the customer details extract from the current url."""
        billing_invoice = (
            "https://singingriver.smarthub.coop/#billHistory:VVNFUl9JRDpjaW5nYWxsc0BiZ2Zvb2QuY29tOg=="
            "!YWNjdE5icj02MTA3NDAwNCZjdXN0TmFtZT1CJkcgQ0FQSVRBTCAmIEdVTEYgQ09BU1QgVkVOVFVSRVMgTEwmc3lzd"
            "GVtT2ZSZWNvcmQ9VVRJTElUWQ=="
        )
        get_url(self.driver, billing_invoice)

    def account_drop_down(self) -> [WebElement]:
        """Return drop down button web element."""
        wait_for_element(
            self.driver,
            value=HOME_PAGE_LOCATORS["ACCOUNT_DROP_DOWN"],
            msg="click drop down",
        )
        return self.driver.find_element_by_css_selector(
            HOME_PAGE_LOCATORS["ACCOUNT_DROP_DOWN"]
        )

    def account_list(self) -> [WebElement]:
        """Click drop down button and return list of accounts."""
        wait_for_element(
            self.driver, value=HOME_PAGE_LOCATORS["ACCOUNT_LIST"], msg="account list"
        )
        return self.driver.find_elements_by_css_selector(
            HOME_PAGE_LOCATORS["ACCOUNT_LIST"]
        )


class SingingRiverInvoicesPage:
    """Singing River Invoices page action methods come here."""

    def __init__(self, driver, download_location: str):
        super().__init__()
        self.driver = driver
        self.download_location = download_location
        self.vendor_name = "Singing River"

    def get_restaurant_name(self) -> WebElement:
        """Return restaurant name we element."""
        return self.driver.find_element_by_css_selector(
            INVOICE_TABLE_ELEMENT["RESTAURANT_NAME"]
        )

    def get_invoice_table_rows(self) -> [WebElement]:
        """Get invoice table row list."""
        return self.driver.find_elements_by_css_selector(
            INVOICE_TABLE_ELEMENT["INVOICE_TABLE_ROWS"]
        )

    def get_table_data(self, run: Run, from_date, account_number):
        """Extracts invoice details from Table
        :return: Returns the list of Discovered File
        """
        discovered_files = []
        wait_for_element(
            self.driver,
            value=INVOICE_TABLE_ELEMENT["INVOICE_TABLE_ROWS"],
            msg="invoice table row",
        )

        if not has_invoices(
            self.driver, value=INVOICE_TABLE_ELEMENT["INVOICE_TABLE_ROWS"]
        ):
            return discovered_files

        for row in self.get_invoice_table_rows():

            if not row.text:
                continue

            invoice_date = date_from_string(
                row.find_elements_by_css_selector("td")[0].text, "%m/%d/%Y"
            )

            if invoice_date < from_date:
                return discovered_files

            reference_code = f"{account_number}_{invoice_date}".replace("-", "")
            pattern = f"{invoice_date}_{account_number}".replace("-", "_")

            # changed the pattern for invoice
            download_pattern = (
                pattern[:8] + pattern[9:] if pattern[8] == "0" else pattern
            )

            document_properties = {
                "customer_number": f"{account_number}",
                "invoice_number": None,
                "invoice_date": f"{invoice_date}",
                "total_amount": f'{row.find_elements_by_css_selector("td")[4].text}',
                "vendor_name": self.vendor_name,
                "restaurant_name": f"{self.get_restaurant_name().text}",
            }

            try:
                # pylint: disable=no-member
                discovered_file = DiscoveredFile.build_unique(
                    run,
                    reference_code,
                    document_type=DocumentType.INVOICE.ident,
                    file_format=FileFormat.PDF.ident,
                    original_download_url=row.find_elements_by_css_selector("td")[1],
                    original_filename=f"{reference_code}.pdf",
                    document_properties=document_properties,
                )
            except DiscoveredFile.AlreadyExists:
                LOGGER.info(
                    f"Discovered file already exists with reference code : {reference_code}"
                )
                continue  # skip if seen before

            discovered_files.append(discovered_file)
            self.download_invoice_by_url(discovered_file, download_pattern)
            LOGGER.info(
                f"Invoice details row data: {discovered_file.document_properties}"
            )
        return discovered_files

    def download_invoice_by_url(self, discovered_file, download_pattern):
        """Download the File in PDF format
        :param download_pattern:
        :param discovered_file:
        """
        LOGGER.info(f"Navigate to: {discovered_file.original_download_url}")
        _downloader = download.DriverExecuteScriptBasedDownloader(
            self.driver,
            script="arguments[0].click();",
            script_args=(discovered_file.original_download_url,),
            local_filepath=os.path.join(
                self.download_location, f"{download_pattern}.pdf"
            ),
            rename_to=os.path.join(
                self.download_location, discovered_file.original_filename
            ),
            file_exists_check_kwargs=dict(timeout=20),
        )
        download.download_discovered_file(discovered_file, _downloader)


class SingingRiverRunner(VendorDocumentDownloadInterface):
    """Runner Class for Singing River."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.login_page = SingingRiverLoginPage(self.driver)
        self.home_page = SingingRiverHomePage(self.driver)
        self.invoices_page = SingingRiverInvoicesPage(
            self.driver, self.download_location
        )

    def _login(self):
        """
        Login to Singing River
        :return: Nothing
        """
        login_url = "https://singingriver.smarthub.coop/Login.html"
        get_url(self.driver, login_url)
        self.login_page.login(self.run.job.username, self.run.job.password)
        self.home_page.terms_and_condition()
        self.home_page.home_page_details()

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
            self.home_page.account_drop_down().click()

            for each_account in range(0, len(self.home_page.account_list())):

                if each_account != 0:
                    self.home_page.account_drop_down().click()

                # get account number before close drop down
                account_number = (
                    self.home_page.account_list()[each_account]
                    .text.split("-")[0]
                    .strip()
                )
                self.home_page.account_list()[each_account].click()
                time.sleep(5)

                discovered_files_list.extend(
                    self.invoices_page.get_table_data(
                        self.run, start_date, account_number
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
