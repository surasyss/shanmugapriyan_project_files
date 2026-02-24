import os
from datetime import date, datetime
from typing import List

from apps.adapters.framework import download
from apps.adapters.helpers.webdriver_helper import (
    explicit_wait_till_invisibility,
    wait_for_element,
    has_invoices,
)
from apps.adapters.vendors import LOGGER
from apps.adapters.base import VendorDocumentDownloadInterface, PasswordBasedLoginPage

from apps.runs.models import Run, DiscoveredFile, DocumentType, FileFormat
from spices.datetime_utils import date_from_string

# Pay My Bills Page Locators
INVOICE_TABLE = "div.invoices-table "
INVOICE_HEADERS = INVOICE_TABLE + "div.invoices-header "
INVOICE_BODY = INVOICE_TABLE + "div.invoices-body "
INVOICE_NAVIGATION = "nav.invoices-nav "
PAY_MY_BILLS_LOCATORS = {
    "INVOICE_SELECTOR_DROPDOWN": INVOICE_NAVIGATION
    + "div.tabs div.dropdown a.invoice-selector",
    "INVOICE_SELECTOR_DROPDOWN_OPTION_ALL": INVOICE_NAVIGATION
    + "div.tabs div.dropdown ul.invoice-selector-dropdown li a.all",
    "HEADER_INVOICE_DATE": INVOICE_HEADERS + "span.statement-date",
    "HEADER_DUE_DATE": INVOICE_HEADERS + "span.due-date",
    "HEADER_INVOICE_ID": INVOICE_HEADERS + "span.biller-controlled",
    "HEADER_PAY_THIS_AMOUNT": INVOICE_HEADERS + "span.invoice-amount",
    "HEADER_PAYMENT_AMOUNT": INVOICE_HEADERS + "span.payment-amount",
    "INVOICE_DATE": "div.item-header span.statement-date",
    "DUE_DATE": "div.item-header span.due-date",
    "INVOICE_ID": "div.item-header span.biller-controlled",
    "INVOICE_AMOUNT": "div.item-header span.invoice-amount",
    "PAYMENT_AMOUNT": "PaymentAmount",
    "ACCOUNT": INVOICE_BODY + "div.account",
    "ACCOUNT_NAME": "div.site-header div.account-nav a.btn",
    "INVOICE_ROWS": INVOICE_BODY + "div.mobile-item-cards div.item.invoice",
    "ACCOUNT_NUMBER": INVOICE_BODY
    + "div.account-header div.account-display-first-line",
    "LOADER": "waitmessage",
}


class CintasLoginPage(PasswordBasedLoginPage):
    """Login page which uses a username / password combination to log a user in"""

    SELECTOR_USERNAME_TEXTBOX = 'input[id="Login"]'
    SELECTOR_PASSWORD_TEXTBOX = 'input[id="Password"]'
    SELECTOR_LOGIN_BUTTON = "button.btn.btn-success.m-mobile"
    SELECTOR_ERROR_MESSAGE_TEXT = "div.alert p"


class CintasPayMyBillsPage:
    """Pay My Bills page"""

    def __init__(self, driver, download_location: str):
        self.driver = driver
        self.download_location = download_location
        self.vendor_name = "Cintas"

    def get_invoice_selector_dropdown(self):
        return self.driver.find_element_by_css_selector(
            PAY_MY_BILLS_LOCATORS["INVOICE_SELECTOR_DROPDOWN"]
        )

    def get_invoice_selector_dropdown_option_all(self):
        return self.driver.find_element_by_css_selector(
            PAY_MY_BILLS_LOCATORS["INVOICE_SELECTOR_DROPDOWN_OPTION_ALL"]
        )

    def get_header_invoice_date(self):
        return self.driver.find_element_by_css_selector(
            PAY_MY_BILLS_LOCATORS["HEADER_INVOICE_DATE"]
        )

    def get_accounts(self):
        return self.driver.find_elements_by_css_selector(
            PAY_MY_BILLS_LOCATORS["ACCOUNT"]
        )

    def get_account_name(self):
        return self.driver.find_element_by_css_selector(
            PAY_MY_BILLS_LOCATORS["ACCOUNT_NAME"]
        )

    def get_account_number(self):
        return self.driver.find_elements_by_css_selector(
            PAY_MY_BILLS_LOCATORS["ACCOUNT_NUMBER"]
        )

    def get_loader(self):
        return self.driver.find_element_by_id(PAY_MY_BILLS_LOCATORS["LOADER"])

    def get_invoice_table_data(self, run: Run, from_date: date) -> List[DiscoveredFile]:
        """
        Extracts invoice details from Table
        :param run: Run
        :param from_date: Start date for the invoice to be downloaded
        :return Returns the list of Discovered Files
        """
        discovered_files = []

        explicit_wait_till_invisibility(
            self.driver, self.get_loader(), msg="Pay My Bill Page Loader"
        )
        LOGGER.info("Extracting Invoice table data.")

        accounts = self.get_accounts()
        for account in accounts:
            account_number = account.find_element_by_css_selector(
                PAY_MY_BILLS_LOCATORS["ACCOUNT_NUMBER"]
            ).text.split(" ")[2]
            rows = account.find_elements_by_css_selector(
                PAY_MY_BILLS_LOCATORS["INVOICE_ROWS"]
            )

            for row in rows:
                invoice_date = date_from_string(
                    row.find_element_by_css_selector(
                        PAY_MY_BILLS_LOCATORS["INVOICE_DATE"]
                    ).text,
                    "%m/%d/%Y",
                )
                invoice_number = row.find_element_by_css_selector(
                    PAY_MY_BILLS_LOCATORS["INVOICE_ID"]
                ).text

                if invoice_date < from_date:
                    return discovered_files

                # invoice_number = 0 means non-invoice document
                if not invoice_number or invoice_number.strip() == "0":
                    continue

                reference_code = row.get_attribute("data-id")
                pdf_link = (
                    "https://53.billerdirectexpress.com/ebpp/Cintas/apps/ViewPDFBill.aspx?ID="
                    + reference_code
                )
                document_properties = {
                    "invoice_number": invoice_number,
                    "invoice_date": str(invoice_date),
                    "due_date": str(
                        date_from_string(
                            row.find_element_by_css_selector(
                                PAY_MY_BILLS_LOCATORS["DUE_DATE"]
                            ).text,
                            "%m/%d/%Y",
                        )
                    ),
                    "total_amount": row.find_element_by_css_selector(
                        PAY_MY_BILLS_LOCATORS["INVOICE_AMOUNT"]
                    ).text,
                    "payment_amount": row.find_element_by_name(
                        PAY_MY_BILLS_LOCATORS["PAYMENT_AMOUNT"]
                    ).get_attribute("value"),
                    "vendor_name": self.vendor_name,
                    "restaurant_name": self.get_account_name().text,
                    "customer_number": account_number,
                }
                try:
                    # pylint: disable=no-member
                    discovered_file = DiscoveredFile.build_unique(
                        run,
                        reference_code,
                        document_type=DocumentType.INVOICE.ident,
                        file_format=FileFormat.PDF.ident,
                        original_download_url=pdf_link,
                        original_filename=f"Invoice{reference_code}.pdf",
                        document_properties=document_properties,
                    )
                except DiscoveredFile.AlreadyExists:
                    LOGGER.info(
                        f"Discovered file already exists with reference code : {reference_code}"
                    )
                    continue  # skip if seen before

                self.download_documents_by_link(discovered_file)
                discovered_files.append(discovered_file)
                LOGGER.info(
                    "Invoice details row data: %s",
                    str(discovered_file.document_properties),
                )

        return discovered_files

    def download_documents_by_link(self, discovered_file: DiscoveredFile):
        """Download all discovered files and set appropriate attributes on them"""
        _downloader = download.DriverBasedUrlGetDownloader(
            self.driver,
            download_url=discovered_file.original_download_url,
            local_filepath=os.path.join(
                self.download_location, discovered_file.original_filename
            ),
        )
        download.download_discovered_file(discovered_file, _downloader)


class CintasRunner(VendorDocumentDownloadInterface):
    """Runner Class for Cintas"""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.login_page = CintasLoginPage(self.driver)
        self.pay_my_bill_page = CintasPayMyBillsPage(
            self.driver, self.download_location
        )

    def _login(self):
        """
        Login to Southern Wine Online
        :return: Nothing
        """
        login_url = "https://53.billerdirectexpress.com/ebpp/Cintas/Login/"
        LOGGER.info("Navigating to %s.", login_url)
        self.driver.get(login_url)
        self.login_page.login(self.run.job.username, self.run.job.password)
        wait_for_element(
            self.driver,
            value=PAY_MY_BILLS_LOCATORS["INVOICE_SELECTOR_DROPDOWN"],
            msg="Invoice Selector Dropdown",
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
        LOGGER.info("Extracting data from table...")

        # Open All Invoices
        self.pay_my_bill_page.get_invoice_selector_dropdown().click()
        wait_for_element(
            self.driver,
            value=PAY_MY_BILLS_LOCATORS["INVOICE_SELECTOR_DROPDOWN_OPTION_ALL"],
            msg="Invoice Selector DropDown Options All",
        )
        self.pay_my_bill_page.get_invoice_selector_dropdown_option_all().click()
        explicit_wait_till_invisibility(
            self.driver,
            self.pay_my_bill_page.get_loader(),
            msg="Pay My Bill Page Loader",
        )

        if not has_invoices(
            self.driver,
            value=PAY_MY_BILLS_LOCATORS["INVOICE_ROWS"],
            msg="Checking for invoice rows...",
        ):
            return []

        # Ordering by Invoice Date Desc
        self.pay_my_bill_page.get_header_invoice_date().click()
        explicit_wait_till_invisibility(
            self.driver,
            self.pay_my_bill_page.get_loader(),
            msg="Pay My Bill Page Loader",
        )
        self.pay_my_bill_page.get_header_invoice_date().click()
        explicit_wait_till_invisibility(
            self.driver,
            self.pay_my_bill_page.get_loader(),
            msg="Pay My Bill Page Loader",
        )

        start_date = datetime.strptime(
            self.run.request_parameters["start_date"], "%Y-%m-%d"
        ).date()
        # Fetching all invoice table date & storing it in memory
        discovered_files_list = self.pay_my_bill_page.get_invoice_table_data(
            self.run, start_date
        )
        LOGGER.info(
            f"Total Invoices within date range and download link available: {len(discovered_files_list)}"
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
            discovered_files += self._download_documents()
        finally:
            self._quit_driver()

        return discovered_files

    def login_flow(self, run: Run):
        self._login()
