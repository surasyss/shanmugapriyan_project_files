import os
import datetime
from typing import List

from selenium.webdriver.common.by import By

from apps.adapters.base import VendorDocumentDownloadInterface, PasswordBasedLoginPage
from apps.adapters.framework import download
from apps.adapters.helpers.webdriver_helper import (
    explicit_wait_till_clickable,
    get_url,
    wait_for_element,
    has_invoices,
)
from apps.adapters.vendors import LOGGER
from apps.runs.models import Run, DiscoveredFile, DocumentType, FileFormat
from spices.datetime_utils import date_from_string

# Home Page Locators
HOME_PAGE_LOCATORS = {"VIEW_BILL_HISTORY": "#ViewBillingHistoryLink"}

# Invoices Page Locators
INVOICE_PAGE_LOCATORS = {
    "DROP_DOWN": 'button[data-toggle="dropdown"]',
    "ACCOUNTS_DROP_DOWN": "a.opt span",
    "INVOICE_TABLE_ROWS": "#BillHistoryTable tbody tr",
    "INVOICE_GROUP_ID": ".ce-leftJustify > div:nth-child(3) > div:nth-child(1)",
}


class SlemcoLoginPage(PasswordBasedLoginPage):
    """
    Slemco login module
    """

    SELECTOR_USERNAME_TEXTBOX = "#LoginUsernameTextBox"
    SELECTOR_PASSWORD_TEXTBOX = "#LoginPasswordTextBox"
    SELECTOR_LOGIN_BUTTON = "#LoginSubmitButton"
    SELECTOR_ERROR_MESSAGE_TEXT = 'span[role="alert"]'


class SlemcoHomePage:
    """Slemco Home page action methods"""

    def __init__(self, driver):
        self.driver = driver

    def go_to_invoices_page(self):
        wait_for_element(
            self.driver,
            value=HOME_PAGE_LOCATORS["VIEW_BILL_HISTORY"],
            msg="View Billing History",
        )
        get_url(self.driver, "https://slemco.smarthub.coop/#billHistory:")


class SlemcoInvoicesPage:
    """Slemco Invoices page action methods come here."""

    vendor_name = "SLEMCO"

    def __init__(self, driver):
        self.driver = driver

    def get_drop_down(self):
        """Get the drop down web element"""
        return self.driver.find_element_by_css_selector(
            INVOICE_PAGE_LOCATORS["DROP_DOWN"]
        )

    def get_account_drop_down_options(self):
        return self.driver.find_elements_by_css_selector(
            INVOICE_PAGE_LOCATORS["ACCOUNTS_DROP_DOWN"]
        )

    def get_invoice_table_rows(self):
        return self.driver.find_elements_by_css_selector(
            INVOICE_PAGE_LOCATORS["INVOICE_TABLE_ROWS"]
        )

    def get_invoice_group_id(self):
        return self.driver.find_element_by_css_selector(
            INVOICE_PAGE_LOCATORS["INVOICE_GROUP_ID"]
        )

    def get_invoice_table_data(
        self, run: Run, from_date, download_location, account_number
    ) -> List[DiscoveredFile]:
        """
        Extracts invoice details from Table
        :param download_location: Download file path
        :param from_date: Invoice start date
        :param run: Run Object
        :param account_number: Account number
        :return: Returns the list of Discovered Files
        """
        discovered_files = []

        if not has_invoices(
            self.driver, value=INVOICE_PAGE_LOCATORS["INVOICE_TABLE_ROWS"]
        ):
            return discovered_files

        restaurant_name = self.driver.find_element_by_css_selector(
            'span[id^="desc"]'
        ).text
        group_id = self.get_invoice_group_id().text
        invoice_group_id = group_id.split(" ")[2] if group_id.strip() else ""

        for index, row in enumerate(self.get_invoice_table_rows()):

            invoice_date = row.find_elements_by_tag_name("td div")[0].text
            if invoice_date == "":
                continue

            invoice_date = date_from_string(invoice_date, "%m/%d/%Y")

            if invoice_date < from_date:
                LOGGER.info(
                    f"Skipping invoices because date '{invoice_date}' is outside requested range"
                )
                return discovered_files

            reference_code = (
                f"{account_number}-{invoice_group_id}-"
                + f"{invoice_date}".replace("-", "")
            )

            pdf_link = (
                "#BillHistoryTable > tbody > tr:nth-child("
                + str(index + 1)
                + ") > td:nth-child(2) > div:nth-child(1) > a:nth-child(2)"
            )

            document_properties = {
                "customer_number": account_number,
                "invoice_number": None,
                "invoice_date": f"{invoice_date}",
                "total_amount": row.find_elements_by_tag_name("td")[4].text,
                "vendor_name": self.vendor_name,
                "restaurant_name": restaurant_name,
            }
            try:
                # pylint: disable=no-member
                discovered_file = DiscoveredFile.build_unique(
                    run,
                    reference_code,
                    document_type=DocumentType.INVOICE.ident,
                    file_format=FileFormat.PDF.ident,
                    original_download_url=pdf_link,
                    original_filename=f"{reference_code}.pdf",
                    document_properties=document_properties,
                )
            except DiscoveredFile.AlreadyExists:
                LOGGER.info(
                    f"Discovered file already exists with reference code : {reference_code}"
                )
                continue  # skip if seen before
            self.download_documents_by_link(download_location, discovered_file)
            discovered_files.append(discovered_file)
            LOGGER.info(
                f"Invoice details row data: {discovered_file.document_properties}"
            )
        return discovered_files

    def download_documents_by_link(self, download_location: str, discovered_file):
        """
        Downloads the invoice by click the view bill button
        :param download_location: Download path
        :param discovered_file: Discovered file
        :return: Nothing
        """

        view_bill_button = explicit_wait_till_clickable(
            self.driver,
            (By.CSS_SELECTOR, discovered_file.original_download_url),
            msg="Clicking the view bill button......",
        )

        inv_date_list = str(discovered_file.document_properties["invoice_date"]).split(
            "-"
        )

        if inv_date_list[2].startswith("0"):
            inv_date_list[2] = inv_date_list[2].replace("0", "")

        invoice_date = f"{inv_date_list[0]}_{inv_date_list[1]}_{inv_date_list[2]}_"

        pdf_filename = f'{invoice_date}{discovered_file.document_properties["customer_number"]}.pdf'

        _downloader = download.DriverExecuteScriptBasedDownloader(
            self.driver,
            script="arguments[0].click();",
            script_args=(view_bill_button,),
            local_filepath=os.path.join(download_location, pdf_filename),
            rename_to=os.path.join(
                download_location, discovered_file.original_filename
            ),
            file_exists_check_kwargs=dict(timeout=50),
        )

        download.download_discovered_file(discovered_file, _downloader)


class SlemcoRunner(VendorDocumentDownloadInterface):
    """Runner Class for Slemco"""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.login_page = SlemcoLoginPage(self.driver)
        self.home_page = SlemcoHomePage(self.driver)
        self.invoices_page = SlemcoInvoicesPage(self.driver)

    def _login(self):
        """
        Login to Slemco
        :return: Nothing
        """
        login_url = "https://slemco.smarthub.coop/Login.html#"
        get_url(self.driver, login_url)
        self.login_page.login(self.run.job.username, self.run.job.password)

    def _download_documents(self, account_number) -> List[DiscoveredFile]:
        """
        Chooses the documents to be downloaded based on the document type
        :return: Returns the list of Discovered Files
        """
        document_type = self.run.job.requested_document_type
        if document_type == "invoice":
            return self._download_invoices(account_number)

        raise NotImplementedError(
            f"Requested Document Type is not supported: {document_type}"
        )

    def _download_invoices(self, account_number) -> List[DiscoveredFile]:
        """
        Downloads the Invoices
        :return: Returns the list of the Discovered Files
        """
        start_date = datetime.datetime.strptime(
            self.run.request_parameters["start_date"], "%Y-%m-%d"
        ).date()
        # Fetching all invoice table date & storing it in memory
        discovered_files_list = self.invoices_page.get_invoice_table_data(
            self.run, start_date, self.download_location, account_number
        )
        LOGGER.info(
            f"Total Invoices within date range and download link available: {len(discovered_files_list)}"
        )
        return discovered_files_list

    def start_documents_download_flow(self, run: Run) -> List[DiscoveredFile]:
        """
        Initiates the Document Download Workflow
        :param run: Run Object
        :return: Returns the list of Discovered Files.
        """
        LOGGER.info(f"[tag:WAV_TPX_SDDF10] Starting documents download flow for Slemco")
        discovered_files = []
        try:
            LOGGER.info(f"[tag:WAV_TPX_SDDF20] Logging in")
            self._login()
            LOGGER.debug(f"[tag:WAV_TPX_SDDF30] Go to invoices page")
            self.home_page.go_to_invoices_page()

            wait_for_element(
                self.driver,
                value=INVOICE_PAGE_LOCATORS["DROP_DOWN"],
                msg="Accounts Drop Down.....",
            )
            LOGGER.debug(
                f"[tag:WAV_TPX_SDDF40] Clicking the drop down to get account list"
            )
            self.invoices_page.get_drop_down().click()

            LOGGER.debug(f"[tag:WAV_TPX_SDDF50] Get the list of accounts")
            accounts = self.invoices_page.get_account_drop_down_options()

            for index, account in enumerate(accounts):
                LOGGER.debug(
                    f"[tag:WAV_TPX_SDDF60] Clicking the specific account to go to invoices page."
                )
                if index > 0:
                    self.invoices_page.get_drop_down().click()
                account = self.invoices_page.get_account_drop_down_options()[index]
                account_number = str(account.text).split(" ")[0]
                account.click()
                discovered_files += self._download_documents(account_number)
        finally:
            self._quit_driver()
        return discovered_files

    def login_flow(self, run: Run):
        self._login()
