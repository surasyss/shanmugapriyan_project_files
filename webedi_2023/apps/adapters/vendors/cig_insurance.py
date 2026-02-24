import os
from datetime import date, datetime
from typing import List

from retry import retry
from selenium.common.exceptions import (
    WebDriverException,
    TimeoutException,
    NoSuchElementException,
)
from selenium.webdriver.remote.webelement import WebElement

from apps.adapters.base import VendorDocumentDownloadInterface, PasswordBasedLoginPage
from apps.adapters.framework import download
from apps.adapters.helpers.webdriver_helper import (
    explicit_wait_till_visibility,
    is_element_present,
)
from apps.adapters.vendors import LOGGER
from apps.runs.models import Run, DiscoveredFile, DocumentType, FileFormat
from spices.datetime_utils import date_from_string

# Home Page Locators
HOME_PAGE_LOCATORS = {
    "HOME_INVOICES_LINK": 'a[id="ctl00_ContentPlaceHolder1_grdPolicyHolderPolicies_ctl02_lnkPolicy"]',
}

PAPERLESS_PAGE_LOCATORS = {
    "NO_THANKS_BUTTON": 'input[id="ctl00_MainBody_btnPaperlessNo"]',
}

# Invoices Page Locators
INVOICE_PAGE_LOCATORS = {
    "ACCOUNT_HOLDER_NAME": 'span[id="ctl00_ContentPlaceHolder1_ucBillingInfo_lblAccountHolder"]',
    "ACCOUNT_NUMBER": 'span[id="ctl00_ContentPlaceHolder1_ucBillingInfo_lblAccountNumber"]',
    "ACCOUNT_ADDRESS": 'span[id="ctl00_ContentPlaceHolder1_ucBillingInfo_lblBillingAddress"]',
    "TELEPHONE_NUMBER": 'span[id="ctl00_ContentPlaceHolder1_ucBillingInfo_lblTelephoneNumber"]',
    "BILL_SENT_TO": 'span[id="ctl00_ContentPlaceHolder1_ucBillingInfo_lblBillSentTo"]',
    "CURRENT_ACCOUNT_DUE_DATE": 'span[id="ctl00_ContentPlaceHolder1_ucBillingInfo_lblDueDate"]',
    "CURRENT_ACCOUNT_MINIMUM_DUE": 'span[id="ctl00_ContentPlaceHolder1_ucBillingInfo_lblMinimumDue"]',
    "CURRENT_ACCOUNT_BALANCE": 'span[id="ctl00_ContentPlaceHolder1_ucBillingInfo_lblAccountBalance"]',
    "CURRENT_ACCOUNT_NEXT_BILL_DATE": 'span[id="ctl00_ContentPlaceHolder1_ucBillingInfo_lblNextBillDate"]',
    "CURRENT_ACCOUNT_NON_PAYMENT_NOTICE": 'span[id="ctl00_ContentPlaceHolder1_ucBillingInfo_lblNonPaymentNotice"]',
    "INVOICE_TABLE": "table[id='ctl00_ContentPlaceHolder1_ucBillingInfo_grvaccountdocumentsDetails']",
    "INVOICE_TABLE_ROWS": 'table[id="ctl00_ContentPlaceHolder1_ucBillingInfo_grvaccountdocumentsDetails"]>tbody>tr',
}


class CapitalInsuranceGroupLoginPage(PasswordBasedLoginPage):
    SELECTOR_USERNAME_TEXTBOX = 'input[id="ctl00_MainBody_tbxUserID"]'
    SELECTOR_PASSWORD_TEXTBOX = 'input[id="ctl00_MainBody_tbxPassword"]'
    SELECTOR_LOGIN_BUTTON = 'input[id="ctl00_MainBody_btnLogin"]'
    SELECTOR_ERROR_MESSAGE_TEXT = 'span[id="ctl00_MainBody_lblError"]'


class CapitalInsuranceGroupHomePage:
    """Capital Insurance Group Home page action methods come here."""

    def __init__(self, driver):
        self.driver = driver

    def get_invoices_link(self) -> WebElement:
        """Returns Invoices Link WebElement"""
        return self.driver.find_element_by_css_selector(
            HOME_PAGE_LOCATORS["HOME_INVOICES_LINK"]
        )

    def get_no_thanks_button(self) -> WebElement:
        """Returns No Thanks Button on Paperless Page WebElement"""
        return self.driver.find_element_by_css_selector(
            PAPERLESS_PAGE_LOCATORS["NO_THANKS_BUTTON"]
        )

    def check_for_paperless_page(self):
        try:
            explicit_wait_till_visibility(
                self.driver,
                self.get_no_thanks_button(),
                msg="No thanks button",
                timeout=10,
            )
            self.get_no_thanks_button().click()
            LOGGER.info("Paperless page: Clicked on No Thanks button")
        except (TimeoutException, NoSuchElementException):
            LOGGER.info("Paperless page not found!")
            pass

    def go_to_invoices_page(self):
        """
        Go to Invoices Page
        :return:
        """
        explicit_wait_till_visibility(self.driver, self.get_invoices_link())
        LOGGER.info("Clicking on Invoices Link.")
        self.get_invoices_link().click()
        self.check_for_paperless_page()


class CapitalInsuranceGroupInvoicesPage:
    """Capital Insurance Group Invoices page action methods come here."""

    def __init__(self, driver):
        self.driver = driver
        self.pagination_list = []
        self.page_num = 0
        self.executed_pg_li = []
        self.all_rows_columns_data = []

    def get_account_holder_name(self) -> WebElement:
        """Returns Account Holder name label web element"""
        return self.driver.find_element_by_css_selector(
            INVOICE_PAGE_LOCATORS["ACCOUNT_HOLDER_NAME"]
        )

    def get_account_number(self) -> WebElement:
        """Return Account number label web element"""
        return self.driver.find_element_by_css_selector(
            INVOICE_PAGE_LOCATORS["ACCOUNT_NUMBER"]
        )

    @staticmethod
    def get_vendor_name() -> str:
        """Returns Vendor Name"""
        return "Capital Insurance Group"

    def get_account_address(self) -> WebElement:
        """Returns Account Address Web Element"""
        return self.driver.find_element_by_css_selector(
            INVOICE_PAGE_LOCATORS["ACCOUNT_ADDRESS"]
        )

    def get_telephone_number(self) -> WebElement:
        """Returns the Telephone Number"""
        return self.driver.find_elements_by_css_selector(
            INVOICE_PAGE_LOCATORS["TELEPHONE_NUMBER"]
        )

    def get_bill_sent_to(self) -> WebElement:
        """Returns bill sent to WebElement"""
        return self.driver.find_element_by_css_selector(
            INVOICE_PAGE_LOCATORS["BILL_SENT_TO"]
        )

    def get_current_account_due_date(self) -> WebElement:
        """Returns current account due date WebElement"""
        return self.driver.find_element_by_css_selector(
            INVOICE_PAGE_LOCATORS["CURRENT_ACCOUNT_DUE_DATE"]
        )

    def get_current_account_minimum_due(self) -> WebElement:
        """Returns current account minimum due WebElement"""
        return self.driver.find_element_by_css_selector(
            INVOICE_PAGE_LOCATORS["CURRENT_ACCOUNT_MINIMUM_DUE"]
        )

    def get_current_account_balance(self) -> WebElement:
        """Returns current account balance WebElement"""
        return self.driver.find_element_by_css_selector(
            INVOICE_PAGE_LOCATORS["CURRENT_ACCOUNT_BALANCE"]
        )

    def get_current_account_next_bill_date(self) -> WebElement:
        """Returns current account next bill date WebElement"""
        return self.driver.find_element_by_css_selector(
            INVOICE_PAGE_LOCATORS["CURRENT_ACCOUNT_NEXT_BILL_DATE"]
        )

    def get_current_account_non_payment_notice(self) -> WebElement:
        """Returns current account non payment notice WebElement"""
        return self.driver.find_element_by_css_selector(
            INVOICE_PAGE_LOCATORS["CURRENT_ACCOUNT_NON_PAYMENT_NOTICE"]
        )

    def _pagination_process(self, cell):
        """
        Pagination process handle
        :param cell: Column value
        :return: Nothing
        """
        if int(cell.text) not in self.executed_pg_li:
            pg_view_js = cell.find_element_by_tag_name("a").get_attribute("href")
            if pg_view_js not in self.pagination_list:
                self.pagination_list.append(pg_view_js)

    def get_all_data(self, from_date):
        """
        Scraping all the page of table of the content with url.
        :return: Nothing
        """
        table = self.driver.find_element_by_css_selector(
            INVOICE_PAGE_LOCATORS["INVOICE_TABLE"]
        )
        self.page_num += 1
        self.executed_pg_li.append(self.page_num)
        row_count = 0
        for row in table.find_elements_by_css_selector("tr"):
            columns_data = []
            row_count += 1
            for cell in row.find_elements_by_tag_name("td"):
                if cell.text == "View":
                    view_js = cell.find_element_by_tag_name("a").get_attribute(
                        "onclick"
                    )
                    view_js = view_js.replace(" return false;", "")
                    columns_data.append(view_js)
                elif row_count == 13 and is_element_present(
                    self.driver, row.find_element_by_tag_name("a")
                ):
                    try:
                        self._pagination_process(cell)
                    except ValueError:
                        continue
                elif row_count < 13:
                    columns_data.append(cell.text)

            if columns_data:
                self.all_rows_columns_data.append(columns_data)
        # To handle all the pages
        if not self.pagination_list:
            self.all_rows_columns_data = self.all_rows_columns_data[:-2]
        else:
            inv_created_date = date_from_string(
                self.all_rows_columns_data[-1][-1], "%m/%d/%Y %H:%M:%S %p"
            )
            if inv_created_date > from_date:
                self.driver.execute_script(self.pagination_list[0])
                del self.pagination_list[0]
                self.get_all_data(from_date)

    def get_invoice_table_data(self, run: Run, from_date: date) -> List[DiscoveredFile]:
        """
        Extracts invoice details from Table
        :param from_date: Current date
        :param run: Run Object
        :return: Returns the list of Discovered Files
        """
        discovered_files = []
        pdf_links_list = []
        self.get_all_data(from_date)
        document_num = self.get_account_number().text
        for row in self.all_rows_columns_data:
            ind = self.all_rows_columns_data.index(row)
            inv_created_date = date_from_string(row[4], "%m/%d/%Y %H:%M:%S %p")
            reference_code = document_num + str(inv_created_date) + "_" + str(ind)
            reference_code = reference_code.replace("-", "").strip()
            pdf_link = row[3]
            if inv_created_date < from_date:
                return discovered_files

            if pdf_link in pdf_links_list:
                continue

            pdf_links_list.append(pdf_link)

            document_properties = {
                "vendor_name": self.get_vendor_name(),
                "invoice_date": str(inv_created_date),
                "total_amount": self.get_current_account_balance().text,
                "invoice_number": reference_code,
                "customer_number": document_num,
                "restaurant_name": self.get_account_holder_name().text,
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
                "Invoice details row data: %s", str(discovered_file.document_properties)
            )

        return discovered_files


class CapitalInsuranceGroupInvoiceDetailsPage:
    """Capital Insurance Group Print Invoices page action methods come here."""

    def __init__(self, driver):
        self.driver = driver

    @retry((FileNotFoundError, WebDriverException), tries=3, delay=2)
    def download_documents_by_link(
        self, download_location: str, discovered_files: List[DiscoveredFile]
    ):
        """
        Downloads the invoice & renames it with the actual account Number with random number
        Retries the downloading 3 times in case of exceptions
        :param download_location:
        :param discovered_files: List of Discovered files
        :return: Nothing
        """
        try:
            for discovered_file in discovered_files:
                LOGGER.info(f"Navigate to: {discovered_file.original_download_url}")
                script = (
                    f'window.open("{discovered_file.original_download_url}", "_self")'
                )
                _downloader = download.DriverExecuteScriptBasedDownloader(
                    self.driver,
                    script=script,
                    local_filepath=os.path.join(
                        download_location, "Doc_AccountBill_IN_.Pdf"
                    ),
                    rename_to=os.path.join(
                        download_location, discovered_file.original_filename
                    ),
                    file_exists_check_kwargs=dict(timeout=40),
                )
                download.download_discovered_file(discovered_file, _downloader)

            self.driver.close()
        except (FileNotFoundError, WebDriverException) as exc:
            LOGGER.error(str(exc), exc_info=True)
            raise


class CapitalInsuranceGroupRunner(VendorDocumentDownloadInterface):
    """Runner Class for Capital Insurance Group"""

    # uses_proxy = True

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.login_page = CapitalInsuranceGroupLoginPage(self.driver)
        self.home_page = CapitalInsuranceGroupHomePage(self.driver)
        self.invoices_page = CapitalInsuranceGroupInvoicesPage(self.driver)
        self.invoice_details_page = CapitalInsuranceGroupInvoiceDetailsPage(self.driver)

    @retry(WebDriverException, tries=3, delay=2)
    def _login(self):
        """
        Login to Capital Insurance Group
        :return: Nothing
        """
        login_url = "https://webapp.ciginsurance.com/PolicyInquiry/Login/Login.aspx"
        LOGGER.info(f"Navigating to {login_url}")
        self.driver.get(login_url)
        self.login_page.login(self.run.job.username, self.run.job.password)
        explicit_wait_till_visibility(self.driver, self.home_page.get_invoices_link())

    def _goto_download_page(self, document_type: str):
        """
        Go to download page based on the document type
        :param document_type: Specifies the type of the document eg. Invoice/Statement etc.
        :return:
        """
        if document_type == "invoice":
            self.home_page.go_to_invoices_page()
        else:
            raise NotImplementedError(
                f"Requested Document Type is not supported: {document_type}"
            )

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
            self.run, start_date
        )

        LOGGER.info(
            f"Total Invoices within date range and download link available: {len(discovered_files_list)}"
        )

        # Download all the invoices
        self.invoice_details_page.download_documents_by_link(
            self.download_location, discovered_files_list
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
            self._goto_download_page(self.run.job.requested_document_type)
            discovered_files += self._download_documents()
        finally:
            self._quit_driver()
        return discovered_files

    def login_flow(self, run: Run):
        self._login()
