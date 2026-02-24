import os
import time
from datetime import datetime
from typing import List

from retry.api import retry
from selenium.common.exceptions import JavascriptException, TimeoutException
from selenium.webdriver.remote.webelement import WebElement
from selenium.webdriver.common.by import By

from apps.adapters.base import VendorDocumentDownloadInterface, PasswordBasedLoginPage
from apps.adapters.framework import download
from apps.adapters.helpers.webdriver_helper import (
    get_url,
    wait_for_element,
    wait_for_ajax,
    WEB_DRIVER_EXCEPTIONS,
    has_invoices,
)
from apps.adapters.vendors import LOGGER
from apps.runs.models import Run, DiscoveredFile, DocumentType, FileFormat
from spices.datetime_utils import date_from_string

# Home Page Locators
HOME_PAGE_LOCATORS = {
    "TRANSACTION_HIS_LINK": 'li[id="transactionhistorySpUrl"] > a',
    "CUSTOMER_NUMBER": 'div[id="wmtContent"] > table[class="table hidden-sm hidden-xs"] > tbody > tr > td',
}

# Invoices Page Locators
INVOICE_PAGE_LOCATORS = {
    "TABLE_ROWS": 'ul[id="transactionHistoryLineItems"] > li[class="list-group-item has-amount"]',
    "PDF_LINKS": 'div[class="cxm-lgi-export"] > a.cxm-settlement-statement',
    "SIGNED_PDF_LINKS": 'div[class="cxm-lgi-export"] > a.cxm-settlement-statement[title="Signed"]',
    "UNSIGNED_PDF_LINKS": 'div[class="cxm-lgi-export"] > a.cxm-settlement-statement:not([title="Signed"])',
    "TOTAL_AMOUNT": 'div[class="cxm-lgi-amount "]',
}


class ShamRockFoodsCompanyLoginPage(PasswordBasedLoginPage):
    """
    Sham Rock Foods Company login module
    """

    SELECTOR_USERNAME_TEXTBOX = "#Username"
    SELECTOR_PASSWORD_TEXTBOX = "#Password"
    SELECTOR_LOGIN_BUTTON = "#loginSubmit"
    SELECTOR_ERROR_MESSAGE_TEXT = "div.alert.cxm-pg-alert.alert-danger.alert-visible"


class ShamRockFoodsCompanyHomePage:
    """Sham Rock Foods Company Home page action methods come here."""

    def __init__(self, driver):
        self.driver = driver

    def transaction_history(self) -> WebElement:
        """
        Return the transaction history page web element.
        """
        return self.driver.find_element_by_css_selector(
            HOME_PAGE_LOCATORS["TRANSACTION_HIS_LINK"]
        )

    def get_customer_number(self) -> [WebElement]:
        return self.driver.find_elements_by_css_selector(
            HOME_PAGE_LOCATORS["CUSTOMER_NUMBER"]
        )

    def customer_number(self) -> str:
        customer_number = self.get_customer_number()
        if customer_number:
            return customer_number[1].text.split(" ")[-1]
        return None


class ShamRockFoodsCompanyInvoicesPage:
    """Sham Rock Foods Company Invoices page action methods come here."""

    def __init__(self, driver, download_location: str):
        self.driver = driver
        self.vendor_name = "Sham Rock Foods Company Inc."
        self.download_location = download_location

    def _get_table_rows(self) -> [WebElement]:
        """Return the table of rows of the web elements"""
        return self.driver.find_elements_by_css_selector(
            INVOICE_PAGE_LOCATORS["TABLE_ROWS"]
        )

    @staticmethod
    def _get_invoice_date(transaction_typ: str, row: WebElement):
        """Return the invoice date"""
        if transaction_typ in ["Credit", "Debit"]:
            invoice_date_css = 'class="cxm-lgi-process-date  refno"'
        else:
            invoice_date_css = 'class="cxm-lgi-process-date  "'
        invoice_date = row.find_element_by_css_selector(
            'div[class="cxm-lgi-line4 "] > div[' + invoice_date_css + "]"
        ).text
        invoice_date = date_from_string(invoice_date, "%A, %B %d, %Y")
        return invoice_date

    @staticmethod
    def _get_signed_pdf_link(row: WebElement) -> WebElement:
        """Return signed PDF link of web element"""
        try:
            return row.find_element_by_css_selector(
                INVOICE_PAGE_LOCATORS["SIGNED_PDF_LINKS"]
            )
        except WEB_DRIVER_EXCEPTIONS:
            return None

    @staticmethod
    def _get_unsigned_pdf_link(row: WebElement) -> WebElement:
        """Return unsigned PDF link of web element"""
        try:
            return row.find_element_by_css_selector(
                INVOICE_PAGE_LOCATORS["UNSIGNED_PDF_LINKS"]
            )
        except WEB_DRIVER_EXCEPTIONS:
            return None

    def _get_pdf_link(self, row: WebElement, invoice_number: str) -> str:
        """Return the PDF link in string format"""
        black_pdf_link = self._get_unsigned_pdf_link(row)
        red_pdf_link = self._get_signed_pdf_link(row)
        if black_pdf_link:
            return black_pdf_link.get_attribute("href")
        elif red_pdf_link:
            if len(invoice_number) > 10:
                return red_pdf_link.get_attribute("href")
            else:
                LOGGER.info(
                    f"[tag:AAVSCSIGGPL10] Length of invoice_number [{invoice_number}]: {len(invoice_number)}."
                    f" Hence skipping it."
                )
                return None
        else:
            LOGGER.info(
                f"[tag:AAVSCSIGGPL20] PDF link not available for invoice_number: {invoice_number}"
            )
            return None

    @staticmethod
    def _get_invoice_total(row: WebElement) -> WebElement:
        """Return the total amount web element"""
        return row.find_element_by_css_selector(INVOICE_PAGE_LOCATORS["TOTAL_AMOUNT"])

    @staticmethod
    def _get_restaurant_name() -> str:
        return "DAVE'S HOT CHICKEN - PAC BEACH"

    def uncheck_trasactiontype(self, transac_type):
        checkbox_list = self.driver.find_elements(
            By.CSS_SELECTOR,
            f"label[class='checked'][data-criteria='{transac_type}'] " f"span.fa-check",
        )
        if checkbox_list:
            checkbox_list[0].click()

    def get_invoice_table_data(
        self, run: Run, from_date, customer_num: str
    ) -> List[DiscoveredFile]:
        """
        Extracts invoice details from Table
        :param from_date: Invoice start date
        :param customer_num: Customer number
        :param run: Run Object
        :return: Returns the list of Discovered Files
        """
        discovered_files = []
        pdf_links_list = []

        try:
            wait_for_ajax(self.driver, msg="Ajax Table")
        except (JavascriptException, TimeoutException) as excep:
            LOGGER.info(excep)

        self.uncheck_trasactiontype("statement")
        self.uncheck_trasactiontype("payment")

        if not has_invoices(
            self.driver,
            value="ul[id='transactionHistoryLineItems'] > li > div[class='cxm-lgi-export']",
            retry_attempts=3,
            msg="Invoice Rows",
        ):
            return discovered_files

        for row in self._get_table_rows():
            transaction_filter = str(row.find_element_by_tag_name("p").text).split("\n")
            if transaction_filter[0] not in ["Payment", "Statement"]:

                invoice_number = transaction_filter[1]
                invoice_date = self._get_invoice_date(transaction_filter[0], row)
                if invoice_date < from_date:
                    LOGGER.info(
                        f"Skipping invoices because date '{invoice_date}' is outside requested range"
                    )
                    return discovered_files

                pdf_link = self._get_pdf_link(row, invoice_number)
                if pdf_link is None:
                    continue

                total_amount = self._get_invoice_total(row).text
                reference_code = (
                    f'{invoice_number}_{str(invoice_date).replace("-", "")}_'
                    f'{pdf_link.split("=")[1]}'.strip()
                )

                if pdf_link in pdf_links_list:
                    continue

                pdf_links_list.append(pdf_link)

                document_properties = {
                    "customer_number": customer_num,
                    "invoice_number": invoice_number,
                    "invoice_date": f"{invoice_date}",
                    "restaurant_name": self._get_restaurant_name(),
                    "total_amount": total_amount,
                    "vendor_name": self.vendor_name,
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
                discovered_files.append(discovered_file)
                LOGGER.info(
                    f"Invoice details row data: {discovered_file.document_properties}"
                )
        return discovered_files

    def download_documents_by_link(self, discovered_files: List[DiscoveredFile]):
        """Download all discovered files and set appropriate attributes on them"""
        try:
            for discovered_file in discovered_files:
                _downloader = download.DriverBasedUrlGetDownloader(
                    self.driver,
                    download_url=discovered_file.original_download_url,
                    local_filepath=os.path.join(
                        self.download_location, "TransactionRecord.pdf"
                    ),
                    rename_to=os.path.join(
                        self.download_location, discovered_file.original_filename
                    ),
                    file_exists_check_kwargs=dict(timeout=20),
                )
                download.download_discovered_file(discovered_file, _downloader)
        except (TypeError, FileNotFoundError):
            LOGGER.error("There is problem in the invoice download module......")


class ShamRockCompanyRunner(VendorDocumentDownloadInterface):
    """Runner Class for Sham Rock Company"""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.login_page = ShamRockFoodsCompanyLoginPage(self.driver)
        self.home_page = ShamRockFoodsCompanyHomePage(self.driver)
        self.customer_num = None
        self.invoices_page = ShamRockFoodsCompanyInvoicesPage(
            self.driver, self.download_location
        )

    @retry(Exception, tries=3, delay=2)
    def _login(self):
        """
        Login to Southern California Edison
        :return: Nothing
        """
        login_url = "https://m.myshamrock.com/Login"
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

        LOGGER.info("Download invoice process begins.")
        start_date = datetime.strptime(
            self.run.request_parameters["start_date"], "%Y-%m-%d"
        ).date()
        # Fetching all invoice table date & storing it in memory
        discovered_files_list = self.invoices_page.get_invoice_table_data(
            self.run, start_date, self.customer_num
        )
        #
        LOGGER.info(
            f"Total Invoices within date range and download link available: {len(discovered_files_list)}"
        )
        #
        # # Download all the invoices
        self.invoices_page.download_documents_by_link(discovered_files_list)

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
            self.customer_num = self.home_page.customer_number()
            for index in range(3):
                try:
                    get_url(self.driver, "https://m.myshamrock.com/transactionhistory")
                    LOGGER.info("Navigating to transaction history page...")
                    break
                except WEB_DRIVER_EXCEPTIONS as excep:
                    LOGGER.warning(excep)
                    if index == 2:
                        raise
                    get_url(self.driver, "https://m.myshamrock.com/")

            time.sleep(2)
            discovered_files += self._download_documents()
        finally:
            self._quit_driver()

        return discovered_files

    def login_flow(self, run: Run):
        self._login()
