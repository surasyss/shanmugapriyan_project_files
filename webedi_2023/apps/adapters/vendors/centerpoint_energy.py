import os
import re
from typing import List

from selenium.common.exceptions import (
    NoSuchElementException,
    ElementNotInteractableException,
)
from selenium.webdriver.common.by import By
from selenium.webdriver.remote.webelement import WebElement
from spices.datetime_utils import date_from_string

from apps.adapters import LOGGER
from apps.adapters.base import VendorDocumentDownloadInterface, PasswordBasedLoginPage
from apps.adapters.framework import download
from apps.adapters.helpers.webdriver_helper import (
    get_url,
    scroll_down_to_element,
    handle_popup,
    has_invoices,
)
from apps.runs.models import Run, DiscoveredFile, DocumentType, FileFormat

LOGIN_PAGE_LOCATORS = {
    "SIGN_IN": "a[id$='MAOSignInHref']",
    "USERNAME": "input#signInName",
    "PASSWORD": "input#password",
    "SUBMIT": "button#next.signin-button",
    "ERROR": "div.error[aria-hidden='false']",
}

ACCOUNTS_PAGE_LOCATORS = {
    "EXPAND_ROWS": "button.btn.btn-expand",
    "ACCOUNT_SUMMARY": "div#divAccountSummary",
    "ACCOUNT_ROWS": "div#divSummaryHeading",
    "RESTAURANT_NAME": "span.alias-name-text",
    "ACCOUNT_NUMBER": 'div#divGasBox span[data-bind$="AccountNumberWithCheckDigit"]',
    "SIBLING": "./following-sibling::div",
    "NEXT_PAGE": "a#linkBtnNext",
    "CLOSE_BUTTON": "button.close",
    "VIEW_PROPERTY_DETAILS": "div#divAccountDetails a#hlAccountDet",
}

INVOICE_PAGE_LOCATORS = {
    "TABLE_BODY": "tbody",
    "TABLE_ROW": "tr",
    "PDF_DOWNLOAD_LINK": "a#aPDF",
    "INVOICE_DATE": ":nth-child(2)",
    "TOTAL_AMOUNT": ":nth-child(4)",
}


class CenterPointEnergyLoginPage(PasswordBasedLoginPage):
    """First Login Page Web Elements"""

    SELECTOR_USERNAME_TEXTBOX = LOGIN_PAGE_LOCATORS["USERNAME"]
    SELECTOR_PASSWORD_TEXTBOX = LOGIN_PAGE_LOCATORS["PASSWORD"]
    SELECTOR_LOGIN_BUTTON = LOGIN_PAGE_LOCATORS["SUBMIT"]
    SELECTOR_ERROR_MESSAGE_TEXT = LOGIN_PAGE_LOCATORS["ERROR"]


class CenterPointEnergyMyAccountsPage:
    """My Accounts Page Class"""

    def __init__(self, driver):
        self.driver = driver

    def expand_account_rows(self) -> WebElement:
        """Returns the element to expand account rows."""
        return self.driver.find_element_by_css_selector(
            ACCOUNTS_PAGE_LOCATORS["EXPAND_ROWS"]
        )

    def get_accounts_summary(self) -> WebElement:
        """Returns the accounts container element."""
        return self.driver.find_element_by_css_selector(
            ACCOUNTS_PAGE_LOCATORS["ACCOUNT_SUMMARY"]
        )

    @staticmethod
    def get_account_rows(accounts_container) -> List[WebElement]:
        """Returns the account rows"""
        return accounts_container.find_elements_by_css_selector(
            ACCOUNTS_PAGE_LOCATORS["ACCOUNT_ROWS"]
        )

    @staticmethod
    def get_restaurant_name(account_row):
        return account_row.find_element_by_css_selector(
            ACCOUNTS_PAGE_LOCATORS["RESTAURANT_NAME"]
        )

    @staticmethod
    def get_restaurant_name_sibling(account_row):
        return account_row.find_element_by_xpath(ACCOUNTS_PAGE_LOCATORS["SIBLING"])

    @staticmethod
    def get_account_number(account_url: str, sibling: WebElement):
        try:
            account_number_elem = sibling.find_element_by_css_selector(
                ACCOUNTS_PAGE_LOCATORS["ACCOUNT_NUMBER"]
            )
            return account_number_elem.text.split("-")[0].strip()
        except NoSuchElementException:
            return re.findall(r"\d+", account_url)[-1]

    def get_next_page(self):
        return self.driver.find_element_by_css_selector(
            ACCOUNTS_PAGE_LOCATORS["NEXT_PAGE"]
        )

    @staticmethod
    def get_account_url(account_row: WebElement):
        view_property_details = account_row.find_element_by_css_selector(
            ACCOUNTS_PAGE_LOCATORS["VIEW_PROPERTY_DETAILS"]
        )
        return view_property_details.get_attribute("href")

    def get_multiple_accounts_data(self):
        accounts = []

        while True:
            try:
                self.expand_account_rows().click()
            except ElementNotInteractableException:
                LOGGER.info("Account rows are already expanded")
            except NoSuchElementException:
                LOGGER.info("No accounts found.")
                return accounts

            accounts_container = self.get_accounts_summary()
            account_rows = CenterPointEnergyMyAccountsPage.get_account_rows(
                accounts_container
            )
            for account_row in account_rows:
                sibling = CenterPointEnergyMyAccountsPage.get_restaurant_name_sibling(
                    account_row
                )

                account_url = CenterPointEnergyMyAccountsPage.get_account_url(
                    account_row
                )

                account_data = {
                    "restaurant_name": CenterPointEnergyMyAccountsPage.get_restaurant_name(
                        account_row
                    ).text,
                    "account_number": CenterPointEnergyMyAccountsPage.get_account_number(
                        account_url, sibling
                    ),
                    "account_url": account_url,
                }

                accounts.append(account_data)

            try:
                next_button = self.get_next_page()
                scroll_down_to_element(self.driver, next_button)
                LOGGER.info("Clicking on Next button")
                next_button.click()
            except (NoSuchElementException, ElementNotInteractableException):
                break

        return accounts


class CenterPointEnergyAccountDetailsPage:
    def __init__(self, driver):
        self.driver = driver

    def navigate_to_billing_and_payment_history(self, account_url=None):
        if account_url:
            get_url(self.driver, account_url)
        handle_popup(self.driver, value=ACCOUNTS_PAGE_LOCATORS["CLOSE_BUTTON"])
        get_url(
            self.driver,
            "https://myaccount.centerpointenergy.com/billing/ViewHistoricalBill",
        )


class CenterPointEnergyInvoicesPage:
    def __init__(self, driver, download_location):
        self.driver = driver
        self.download_location = download_location

    def get_table(self):
        return self.driver.find_element_by_css_selector(
            INVOICE_PAGE_LOCATORS["TABLE_BODY"]
        )

    @staticmethod
    def get_table_rows(table):
        return table.find_elements_by_css_selector(INVOICE_PAGE_LOCATORS["TABLE_ROW"])

    @staticmethod
    def get_invoice_date(invoice_row):
        return invoice_row.find_element_by_css_selector(
            INVOICE_PAGE_LOCATORS["INVOICE_DATE"]
        )

    @staticmethod
    def get_total_amount(invoice_row):
        return invoice_row.find_element_by_css_selector(
            INVOICE_PAGE_LOCATORS["TOTAL_AMOUNT"]
        )

    @staticmethod
    def get_pdf_download_script(invoice_row):
        return invoice_row.find_element_by_css_selector(
            INVOICE_PAGE_LOCATORS["PDF_DOWNLOAD_LINK"]
        )

    def get_invoices_data_from_table(self, run: Run, account, from_date):
        discovered_files = []
        account_number = account["account_number"]

        if not has_invoices(self.driver, value=INVOICE_PAGE_LOCATORS["TABLE_BODY"]):
            LOGGER.info(f"No table found for the account {account_number}")
            return discovered_files

        table = self.get_table()

        for invoice_row in CenterPointEnergyInvoicesPage.get_table_rows(table):
            if "PDF" not in invoice_row.text:
                LOGGER.info(
                    f"Downloadable pdf link not available. Hence skipping this row '{invoice_row.text}'"
                )
                continue

            invoice_date = date_from_string(
                CenterPointEnergyInvoicesPage.get_invoice_date(invoice_row).text,
                "%b %d,%Y",
            )

            if invoice_date < from_date:
                LOGGER.info(
                    f"Skipping remaining invoices because date '{invoice_date}' is outside requested range"
                )
                break

            invoice = {
                "invoice_date": invoice_date,
                "total_amount": CenterPointEnergyInvoicesPage.get_total_amount(
                    invoice_row
                ).text,
                "download_script": CenterPointEnergyInvoicesPage.get_pdf_download_script(
                    invoice_row
                ).get_attribute(
                    "onclick"
                ),
            }

            reference_code = (
                f'{account_number}_{invoice["invoice_date"].strftime("%d%m%Y")}'
            )

            try:
                # pylint: disable=no-member
                discovered_file = DiscoveredFile.build_unique(
                    run,
                    reference_code,
                    document_type=DocumentType.INVOICE.ident,
                    file_format=FileFormat.PDF.ident,
                    original_download_url=invoice["download_script"],
                    original_filename=f"CNP_{reference_code}_Bill.pdf",
                    document_properties={
                        "customer_number": account_number,
                        "invoice_number": None,
                        "invoice_date": f'{invoice["invoice_date"]}',
                        "restaurant_name": account.get("restaurant_name"),
                        "total_amount": invoice["total_amount"],
                        "vendor_name": "CENTERPOINT ENERGY",
                    },
                )

                LOGGER.info(
                    f"Invoice details row data: {discovered_file.document_properties}"
                )

            except DiscoveredFile.AlreadyExists:
                LOGGER.info(
                    f"Discovered file already exists with reference code : {reference_code}"
                )
                continue
            self.download_documents_by_script(discovered_file)
            discovered_files.append(discovered_file)

        return discovered_files

    def download_documents_by_script(self, discovered_file):
        """Downloads the invoices by executing script"""
        LOGGER.info(f"Navigate to: {discovered_file.original_download_url}")
        _downloader = download.DriverExecuteScriptBasedDownloader(
            self.driver,
            script=discovered_file.original_download_url,
            local_filepath=f"{self.download_location}/"
            f'CNP-{discovered_file.document_properties["customer_number"]}-Bill.pdf',
            rename_to=os.path.join(
                self.download_location, discovered_file.original_filename
            ),
            file_exists_check_kwargs=dict(timeout=20),
        )
        download.download_discovered_file(discovered_file, _downloader)


class CenterPointEnergyRunner(VendorDocumentDownloadInterface):
    """Runner Class"""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.login_page = CenterPointEnergyLoginPage(self.driver)
        self.home_page = CenterPointEnergyMyAccountsPage(self.driver)
        self.invoice_page = CenterPointEnergyInvoicesPage(
            self.driver, self.download_location
        )
        self.account_details_page = CenterPointEnergyAccountDetailsPage(self.driver)

    def _login(self):
        """
        Login using credentials
        :return: Nothing
        """
        login_url = "https://www.centerpointenergy.com/en-us/"
        get_url(self.driver, login_url)
        self.driver.find_element_by_css_selector(LOGIN_PAGE_LOCATORS["SIGN_IN"]).click()
        self.login_page.login(self.run.job.username, self.run.job.password)

    def _download_documents(self, account) -> List[DiscoveredFile]:
        """
        Chooses the documents to be downloaded based on the document type
        :return: Returns the list of Discovered Files
        """
        document_type = self.run.job.requested_document_type
        if document_type == "invoice":
            return self._download_invoices(account)

        raise NotImplementedError(
            f"Requested Document Type is not supported: {document_type}"
        )

    def _download_invoices(self, account) -> List[DiscoveredFile]:
        """
        Downloads the Invoices
        :return: Returns the list of the Discovered Files
        """
        LOGGER.info("Extracting data from table...")
        start_date = date_from_string(
            self.run.request_parameters["start_date"], "%Y-%m-%d"
        )
        discovered_files_list = self.invoice_page.get_invoices_data_from_table(
            self.run, account, start_date
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
            if "MyAccounts/Index" in self.driver.current_url:
                multiple_accounts_data = self.home_page.get_multiple_accounts_data()
                for account in multiple_accounts_data:
                    LOGGER.info(f"Collecting discovered files for account: {account}")
                    self.account_details_page.navigate_to_billing_and_payment_history(
                        account_url=account["account_url"],
                    )
                    discovered_files += self._download_documents(account)
            else:
                self.account_details_page.navigate_to_billing_and_payment_history()
                account_number = self.driver.find_element(
                    By.CSS_SELECTOR, "label[id='lblAccountNumber']"
                ).text
                discovered_files += self._download_documents(
                    {"account_number": account_number.split("-")[0].strip()}
                )

        finally:
            self._quit_driver()

        LOGGER.info(
            f"Total Invoices within date range and download link available: {len(discovered_files)}"
        )
        return discovered_files

    def login_flow(self, run: Run):
        self._login()
