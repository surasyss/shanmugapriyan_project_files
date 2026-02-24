from datetime import datetime
from typing import List
from retry.api import retry

from selenium.common.exceptions import (
    WebDriverException,
    StaleElementReferenceException,
)

from apps.adapters import LOGGER
from apps.adapters.base import VendorDocumentDownloadInterface, PasswordBasedLoginPage
from apps.adapters.framework import download
from apps.adapters.helpers.webdriver_helper import get_url, has_invoices
from apps.runs.models import Run, DiscoveredFile, DocumentType, FileFormat

# Login Page Locators
LOGIN_PAGE_LOCATORS = {
    "EMAIL": "input#ctl00_ContentPlaceholder1_UserLogin_UsernameTextBox",
    "PASSWORD": "input#ctl00_ContentPlaceholder1_UserLogin_PasswordTextBox",
    "LOGIN_BUTTON": "input#ctl00_ContentPlaceholder1_UserLogin_LoginButton",
    "ERROR": 'span[id$="_ErrorMessageLabel"]',
}

# Home Page Locators
HOME_PAGE_LOCATORS = {
    "ACCOUNTS": 'a[id$="_LoginLink"]',
    "ORDERS": "a#ctl00_TabSetNavigation_lnkOrderHistory",
    "INVOICE_HISTORY": "a#ctl00_TabSetNavigation_lnkInvoiceHistory",
    "SWITCH_ACCOUNT": "a#ctl00_lnkLoginAction1",
}

# Invoice History Locators
INVOICE_HISTORY_LOCATORS = {
    "ACCOUNT_NUMBER": "span#ctl00_ContentPlaceholder1_AccountNumberLabel",
    "ACCOUNT_NAME": "span#ctl00_ContentPlaceholder1_AccountNameLabel",
    "TABLE_ROWS": 'tr[id^="ctl00_ContentPlaceholder1_InvoiceHistoryListView_ctrl"]',
    "INVOICE_DATE": 'span[id$="_InvoiceDateLabel"]',
    "INVOICE_NUMBER": 'a[id$="_InvoiceNumberLinkButton"]',
    "TOTAL": 'span[id$="OrderTotalLabel"]',
}


class WBMasonLoginPage(PasswordBasedLoginPage):
    """Login Page Web Elements"""

    SELECTOR_USERNAME_TEXTBOX = LOGIN_PAGE_LOCATORS["EMAIL"]
    SELECTOR_PASSWORD_TEXTBOX = LOGIN_PAGE_LOCATORS["PASSWORD"]
    SELECTOR_LOGIN_BUTTON = LOGIN_PAGE_LOCATORS["LOGIN_BUTTON"]
    SELECTOR_ERROR_MESSAGE_TEXT = LOGIN_PAGE_LOCATORS["ERROR"]


class WBMasonHomePage:
    """Home Page Class for WB Mason"""

    def __init__(self, driver):
        self.driver = driver

    def get_accounts_element(self):
        return self.driver.find_elements_by_css_selector(HOME_PAGE_LOCATORS["ACCOUNTS"])

    def get_orders_element(self):
        return self.driver.find_element_by_css_selector(HOME_PAGE_LOCATORS["ORDERS"])

    def get_invoice_history_page(self):
        return self.driver.find_element_by_css_selector(
            HOME_PAGE_LOCATORS["INVOICE_HISTORY"]
        )

    def switch_account(self):
        return self.driver.find_element_by_css_selector(
            HOME_PAGE_LOCATORS["SWITCH_ACCOUNT"]
        )


class WBMasonInvoicesPage:
    """Invoice Page Class for WB Mason"""

    def __init__(self, driver, download_location):
        self.driver = driver
        self.download_location = download_location
        self.home_page = WBMasonHomePage(self.driver)
        self.vendor_name = "WB Mason"

    def get_account_number_element(self):
        return self.driver.find_element_by_css_selector(
            INVOICE_HISTORY_LOCATORS["ACCOUNT_NUMBER"]
        )

    def get_account_name_element(self):
        return self.driver.find_element_by_css_selector(
            INVOICE_HISTORY_LOCATORS["ACCOUNT_NAME"]
        )

    def get_invoice_table_rows(self):
        return self.driver.find_elements_by_css_selector(
            INVOICE_HISTORY_LOCATORS["TABLE_ROWS"]
        )

    def get_order_total(self):
        return self.driver.find_element_by_css_selector(
            INVOICE_HISTORY_LOCATORS["TOTAL"]
        )

    @staticmethod
    def get_nth_child(table_row, index: int):
        return table_row.find_element_by_css_selector(f"td:nth-child({index})")

    def get_actual_invoices_data(self, run: Run, from_date) -> List[DiscoveredFile]:
        """Extracts invoice details"""
        discovered_files = []

        get_url(self.driver, url="https://www.wbmason.com/InvoiceHistory.aspx")

        if not has_invoices(self.driver, value=INVOICE_HISTORY_LOCATORS["TABLE_ROWS"]):
            return discovered_files

        account_number = self.get_account_number_element().text
        account_name = self.get_account_name_element().text

        for index, row in enumerate(self.get_invoice_table_rows()):
            invoice_date = datetime.strptime(
                row.find_element_by_css_selector(
                    INVOICE_HISTORY_LOCATORS["INVOICE_DATE"]
                ).text,
                "%m/%d/%Y",
            ).date()

            if invoice_date < from_date:
                LOGGER.info(
                    f"Skipping remaining invoices because date '{invoice_date}' is outside requested range"
                )
                return discovered_files

            invoice_number = row.find_element_by_css_selector(
                INVOICE_HISTORY_LOCATORS["INVOICE_NUMBER"]
            ).text
            reference_code = f"{account_number}_{invoice_number}"

            try:
                # pylint: disable=no-member
                discovered_file = DiscoveredFile.build_unique(
                    run,
                    reference_code,
                    document_type=DocumentType.INVOICE.ident,
                    file_format=FileFormat.PDF.ident,
                    original_download_url=reference_code,
                    original_filename=f"WBMasonInvoice_{invoice_number}.pdf",
                    document_properties={
                        "customer_number": account_number,
                        "invoice_number": invoice_number,
                        "invoice_date": f"{invoice_date}",
                        "total_amount": None,
                        "vendor_name": self.vendor_name,
                        "restaurant_name": account_name,
                    },
                )
            except DiscoveredFile.AlreadyExists:
                LOGGER.info(
                    f"Discovered file already exists with reference code : {reference_code}"
                )
                continue

            discovered_files.append(discovered_file)
            LOGGER.info(f"Invoice details data: {discovered_file.document_properties}")
            self.download_invoice_by_script(discovered_file, index)

        return discovered_files

    def download_invoice_by_script(self, discovered_file, row_index):
        _downloader = WBMasonDownloader(
            self.driver,
            script="arguments[0].click();",
            script_args=(row_index,),
            local_filepath=f"{self.download_location}/{discovered_file.original_filename}",
            file_exists_check_kwargs=dict(timeout=20),
        )
        download.download_discovered_file(discovered_file, _downloader)


class WBMasonDownloader(download.DriverExecuteScriptBasedDownloader):
    @retry(StaleElementReferenceException, tries=3, delay=2)
    def _perform_download_action(self):
        invoice_history_url = "https://www.wbmason.com/InvoiceHistory.aspx"
        if self.driver.current_url != invoice_history_url:
            get_url(self.driver, invoice_history_url)
        row = self.driver.find_elements_by_css_selector(
            INVOICE_HISTORY_LOCATORS["TABLE_ROWS"]
        )[self.script_args[0]]
        download_element = row.find_element_by_css_selector(
            INVOICE_HISTORY_LOCATORS["INVOICE_NUMBER"]
        )
        self.driver.execute_script(self.script, download_element)


class WBMasonRunner(VendorDocumentDownloadInterface):
    """Runner Class for WBMason"""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.login_page = WBMasonLoginPage(self.driver)
        self.home_page = WBMasonHomePage(self.driver)
        self.invoice_page = WBMasonInvoicesPage(self.driver, self.download_location)

    @retry(WebDriverException, tries=3, delay=2)
    def _login(self):
        """
        Login using credentials
        :return: Nothing
        """
        login_url = "https://www.wbmason.com/login2.aspx"
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
        LOGGER.info("Extracting data from invoice page...")
        start_date = datetime.strptime(
            self.run.request_parameters["start_date"], "%Y-%m-%d"
        ).date()
        discovered_files = self.invoice_page.get_actual_invoices_data(
            self.run, start_date
        )
        LOGGER.info(
            f"Total Invoices within date range and download links available: {len(discovered_files)}"
        )
        return discovered_files

    def start_documents_download_flow(self, run: Run) -> List[DiscoveredFile]:
        """
        Initiates the Document Download Workflow
        :param run: Run Object
        :return: Returns the list of Discovered Files
        """
        discovered_files = []
        try:
            self._login()
            accounts = self.home_page.get_accounts_element()
            if accounts:
                for index, _ in enumerate(accounts):
                    if index > 0:
                        get_url(
                            self.driver,
                            url="https://www.wbmason.com/SelectAccount.aspx",
                        )
                    self.home_page.get_accounts_element()[index].click()

                    discovered_files += self._download_documents()
            else:
                discovered_files += self._download_documents()
        finally:
            self._quit_driver()

        return discovered_files

    def login_flow(self, run: Run):
        self._login()
