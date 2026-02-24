import os
from datetime import datetime
from typing import List

from selenium.common.exceptions import NoSuchElementException, WebDriverException
from selenium.webdriver.common.by import By

from apps.adapters import LOGGER
from apps.adapters.base import VendorDocumentDownloadInterface, PasswordBasedLoginPage
from apps.adapters.framework import download
from apps.adapters.helpers.webdriver_helper import (
    get_url,
    handle_popup,
    scroll_down_to_element,
    explicit_wait_till_invisibility,
    wait_for_element,
    wait_for_loaders,
    has_invoices,
)
from apps.runs.models import Run, DiscoveredFile, DocumentType, FileFormat

LOGIN_PAGE_LOCATORS = {
    "USERNAME": "input#user",
    "PASSWORD": "input#passwd",
    "SUBMIT": "button#sign_in",
    "ERROR": "div#validation-errors",
    "POPUP": "button.kcInviteNoBtn, button.kcBtn-remove",
    "SIGNIN": 'a[class*="sign-in"]',
    "ERROR_PAGE": "button#reload-button",
}

CURRENT_BILL_PAGE_LOCATORS = {
    "ACCOUNT_NUMBER": "//span[text()='Account Number:']/following-sibling::span",
    "BILL_DATE": "//span[text()='For Services From:']/following-sibling::span",
    "BILL_TOTAL": "//span[text()='Statement Balance']/following-sibling::span",
    "DOWNLOAD_BUTTON": "button.bsd-billing-view-bill-btn",
    "FOUND_PAST_BILLS": "div.bsd-past-bills",
    "BILL_PAGE_ERROR": "div.bsd-service-error",
    "DIALOG_CLOSE": "button.bsd-dialog-close",
}

PAST_BILL_PAGE_LOCATORS = {
    "PAST_BILLS": "div.bsd-past-bills-items",
    "BILL_DATE": "span",
    "DOWNLOAD_BUTTON": "button",
    "VIEW_MORE": "div.bsd-past-bills a.bsd-past-bills-view-more",
}

ACCOUNT_PAGE_LOCATORS = {
    "POPUP_AFTER_PAGE_LOAD": "input#close, button#tcChat_btnCloseChat_img",
    "ACCOUNTS_DROPDOWN": "div#wt-account-selector button",
    "ACCOUNTS_LIST": "div#bsd-account-select-filter ul#bsd-select-filter-list li.bsd-select-filter-item",
    "ACCOUNTS_NAMES_LIST": "div.bsd-account-selector span.bsd-selector-name, "
    "div.bsd-account-selector p.bsd-selector-name, "
    "div.bsd-account-selector--single span.bsd-selector-title, "
    "div.bsd-account-selector--single p.bsd-selector-title",
    "BACK_TO_BILL": "div.bsd-past-bills-history-link a.bsd-link--button",
    "SUMMARY_DETAILS": "div.bsd-bill-summary-items-info",
    "SPINNER": "div.bcp-page-spinner, div.bcp-page-spinner-container, div.bsd-spinner-container",
}


class ComcastLoginPage(PasswordBasedLoginPage):
    """First Login Page Web Elements"""

    SELECTOR_USERNAME_TEXTBOX = LOGIN_PAGE_LOCATORS["USERNAME"]
    SELECTOR_PASSWORD_TEXTBOX = LOGIN_PAGE_LOCATORS["PASSWORD"]
    SELECTOR_LOGIN_BUTTON = LOGIN_PAGE_LOCATORS["SUBMIT"]
    SELECTOR_ERROR_MESSAGE_TEXT = LOGIN_PAGE_LOCATORS["ERROR"]

    def get_welcome_popup_element(self):
        return self.driver.find_element_by_css_selector(LOGIN_PAGE_LOCATORS["POPUP"])

    def get_signin_element(self):
        return self.driver.find_element_by_css_selector(LOGIN_PAGE_LOCATORS["SIGNIN"])


class ComcastCurrentBillPage:
    def __init__(self, driver, download_location):
        self.driver = driver
        self.download_files = DownloadDiscoveredFile(self.driver, download_location)

    def get_current_bill_date(self):
        return self.driver.find_element_by_xpath(
            CURRENT_BILL_PAGE_LOCATORS["BILL_DATE"]
        )

    def get_current_bill_total(self):
        return self.driver.find_element_by_xpath(
            CURRENT_BILL_PAGE_LOCATORS["BILL_TOTAL"]
        )

    def get_current_bill_download_button(self):
        try:
            return self.driver.find_element_by_css_selector(
                CURRENT_BILL_PAGE_LOCATORS["DOWNLOAD_BUTTON"]
            )
        except NoSuchElementException:
            return None

    def get_current_bill_details(self, run, account_detail, from_date):
        current_bill = {
            "invoice_date": self.get_current_bill_date().text.split("-")[-1].strip(),
            "total_amount": self.get_current_bill_total().text,
            "pdf_download_button": self.get_current_bill_download_button(),
        }
        discovered_file = self.download_files.get_discovered_file(
            run, current_bill, account_detail, from_date
        )
        return [discovered_file]


class ComcastPastBillsPage:
    def __init__(self, driver, download_location):
        self.driver = driver
        self.download_files = DownloadDiscoveredFile(self.driver, download_location)

    def get_past_bills(self):
        return self.driver.find_elements_by_css_selector(
            PAST_BILL_PAGE_LOCATORS["PAST_BILLS"]
        )

    @staticmethod
    def get_past_bill_date(bill):
        return bill.find_element_by_css_selector(PAST_BILL_PAGE_LOCATORS["BILL_DATE"])

    @staticmethod
    def get_past_bill_download_button(bill):
        return bill.find_element_by_css_selector(
            PAST_BILL_PAGE_LOCATORS["DOWNLOAD_BUTTON"]
        )

    def get_back_to_current_bill(self):
        return self.driver.find_element_by_css_selector(
            ACCOUNT_PAGE_LOCATORS["BACK_TO_BILL"]
        )

    def view_more(self):
        return self.driver.find_element_by_css_selector(
            PAST_BILL_PAGE_LOCATORS["VIEW_MORE"]
        )

    def past_bill_body_text(self):
        return self.driver.find_element_by_css_selector(
            "div.bsd-past-bills-panel div.bsd-panel-body"
        )

    def get_past_bills_details(self, run: Run, account_detail, from_date):
        discovered_files = []

        LOGGER.info(f"Navigating to the past bills page...")
        handle_popup(
            self.driver,
            value=ACCOUNT_PAGE_LOCATORS["POPUP_AFTER_PAGE_LOAD"],
            retry_attempts=1,
        )

        for _, bill in enumerate(self.get_past_bills()):
            invoice_date = ComcastPastBillsPage.get_past_bill_date(bill).text.replace(
                "BILLED ", ""
            )

            if (
                formatted_date := datetime.strptime(invoice_date, "%B %d, %Y").date()
            ) < from_date:
                LOGGER.info(
                    f"Skipping invoice because date '{formatted_date}' is outside requested range"
                )
                break

            download_button = ComcastPastBillsPage.get_past_bill_download_button(bill)

            bill_detail = {
                "invoice_date": invoice_date,
                "total_amount": None,
                "pdf_download_button": download_button,
            }
            discovered_file = self.download_files.get_discovered_file(
                run, bill_detail, account_detail, from_date
            )
            discovered_files.append(discovered_file)

        self.get_back_to_current_bill().click()
        LOGGER.info(f"Navigating back to the current bill page...")
        handle_popup(
            self.driver,
            value=ACCOUNT_PAGE_LOCATORS["POPUP_AFTER_PAGE_LOAD"],
            retry_attempts=1,
        )
        return discovered_files


class DownloadDiscoveredFile:
    def __init__(self, driver, download_location):
        self.driver = driver
        self.download_location = download_location

    def get_discovered_file(self, run: Run, bill_detail, account_detail, from_date):
        discovered_file = None

        invoice_date = datetime.strptime(
            bill_detail["invoice_date"], "%B %d, %Y"
        ).date()

        if invoice_date < from_date:
            LOGGER.info(
                f"Skipping invoice because date '{invoice_date}' is outside requested range"
            )
            return discovered_file

        reference_code = (
            f'{account_detail["customer_number"]}-{invoice_date.strftime("%m-%d-%Y")}'
        )

        try:
            # pylint: disable=no-member
            discovered_file = DiscoveredFile.build_unique(
                run,
                reference_code,
                document_type=DocumentType.INVOICE.ident,
                file_format=FileFormat.PDF.ident,
                original_download_url=bill_detail["pdf_download_button"],
                original_filename=f"{reference_code}.pdf",
                document_properties={
                    "customer_number": account_detail["customer_number"],
                    "invoice_number": None,
                    "invoice_date": f"{invoice_date}",
                    "restaurant_name": account_detail["restaurant_name"],
                    "total_amount": bill_detail["total_amount"],
                    "vendor_name": "Comcast",
                },
            )

            LOGGER.info(
                f"Invoice details row data: {discovered_file.document_properties}"
            )
            if discovered_file.original_download_url:
                wait_for_loaders(
                    self.driver,
                    value=ACCOUNT_PAGE_LOCATORS["SPINNER"],
                    timeout=10,
                    retry_attempts=1,
                )
                self.download_documents_by_element_click(discovered_file)
            else:
                LOGGER.info("Pdf statement not yet available. Please check back later.")

        except DiscoveredFile.AlreadyExists:
            LOGGER.info(
                f"Discovered file already exists with reference code : {reference_code}"
            )

        return discovered_file

    def download_documents_by_element_click(self, discovered_file):
        """Downloads the invoices by executing script"""
        LOGGER.info(f"Navigate to: {discovered_file.original_download_url}")
        _downloader = download.WebElementClickBasedDownloader(
            element=discovered_file.original_download_url,
            local_filepath=self.download_location,
            rename_to=f"{os.path.join(self.download_location, discovered_file.content_hash)}.pdf",
            file_exists_check_kwargs=dict(
                timeout=20, pattern=r"Comcast_Business_Invoice_\S+.pdf$"
            ),
        )
        download.download_discovered_file(discovered_file, _downloader)


class ComcastRunner(VendorDocumentDownloadInterface):
    """Runner Class"""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.login_page = ComcastLoginPage(self.driver)
        self.current_bill_page = ComcastCurrentBillPage(
            self.driver, self.download_location
        )
        self.past_bill_page = ComcastPastBillsPage(self.driver, self.download_location)

    def _login(self):
        """
        Login using credentials
        :return: Nothing
        """
        login_url = "https://business.comcast.com/"
        for _ in range(5):
            try:
                get_url(self.driver, login_url)

                try:
                    self.login_page.get_welcome_popup_element().click()
                except NoSuchElementException:
                    LOGGER.info("No popup found")

                self.login_page.get_signin_element().click()
                self.login_page.login(self.run.job.username, self.run.job.password)
                break
            except WebDriverException:
                LOGGER.info("Failed to load login page. Retrying login...")

    def _download_documents(self, account_name) -> List[DiscoveredFile]:
        """
        Chooses the documents to be downloaded based on the document type
        :return: Returns the list of Discovered Files
        """
        document_type = self.run.job.requested_document_type
        if document_type == "invoice":
            return self._download_invoices(account_name)

        raise NotImplementedError(
            f"Requested Document Type is not supported: {document_type}"
        )

    def failed_to_load_login_page(self):
        return self.driver.find_element_by_css_selector(
            LOGIN_PAGE_LOCATORS["ERROR_PAGE"]
        )

    def get_account_elements_list(self, index=None):
        try:
            self.get_account_dropdown().click()
        except NoSuchElementException:
            LOGGER.info("No multiple accounts found.")

        if index is not None:
            for _ in range(5):
                wait_for_element(
                    self.driver,
                    value=ACCOUNT_PAGE_LOCATORS["ACCOUNTS_LIST"],
                    msg="Loading accounts list...",
                    retry_attempts=1,
                    raise_exception=False,
                )
                accounts = self.driver.find_elements_by_css_selector(
                    ACCOUNT_PAGE_LOCATORS["ACCOUNTS_LIST"]
                )
                if index < len(accounts):
                    scroll_down_to_element(self.driver, accounts[index])
                    return accounts[index]

        accounts_elements = self.driver.find_elements_by_css_selector(
            ACCOUNT_PAGE_LOCATORS["ACCOUNTS_NAMES_LIST"]
        )
        return accounts_elements

    def get_account_number(self):
        return self.driver.find_element_by_xpath(
            CURRENT_BILL_PAGE_LOCATORS["ACCOUNT_NUMBER"]
        )

    def get_summary_details(self):
        return self.driver.find_element(
            By.CSS_SELECTOR, ACCOUNT_PAGE_LOCATORS["SUMMARY_DETAILS"]
        )

    def get_accounts_list(self):
        return self.driver.find_element(
            By.CSS_SELECTOR, ACCOUNT_PAGE_LOCATORS["ACCOUNTS_LIST"]
        )

    def found_past_bills(self):
        return self.driver.find_element_by_css_selector(
            CURRENT_BILL_PAGE_LOCATORS["FOUND_PAST_BILLS"]
        )

    def get_account_dropdown(self):
        return self.driver.find_element_by_css_selector(
            ACCOUNT_PAGE_LOCATORS["ACCOUNTS_DROPDOWN"]
        )

    def bill_page_error(self):
        return self.driver.find_element_by_css_selector(
            CURRENT_BILL_PAGE_LOCATORS["BILL_PAGE_ERROR"]
        )

    def get_dialog_close_buttons(self):
        return self.driver.find_elements_by_css_selector(
            CURRENT_BILL_PAGE_LOCATORS["DIALOG_CLOSE"]
        )

    def _download_invoices(self, account_name) -> List[DiscoveredFile]:
        """
        Downloads the Invoices
        :return: Returns the list of the Discovered Files
        """
        start_date = datetime.strptime(
            self.run.request_parameters["start_date"], "%Y-%m-%d"
        ).date()
        account_number = self.get_account_number().text

        account_detail = {
            "customer_number": account_number,
            "restaurant_name": account_name,
        }

        discovered_files = self.current_bill_page.get_current_bill_details(
            self.run, account_detail, start_date
        )

        try:
            wait_for_loaders(
                self.driver,
                value=ACCOUNT_PAGE_LOCATORS["SPINNER"],
                timeout=10,
                retry_attempts=1,
            )
            self.past_bill_page.view_more().click()
            discovered_files += self.past_bill_page.get_past_bills_details(
                self.run, account_detail, start_date
            )
        except NoSuchElementException:
            LOGGER.info(self.past_bill_page.past_bill_body_text().text)

        return discovered_files

    def close_dialogs(self):
        for close_button in self.get_dialog_close_buttons():
            close_button.click()

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
                value=ACCOUNT_PAGE_LOCATORS["POPUP_AFTER_PAGE_LOAD"],
                retry_attempts=1,
            )

            self.driver.get("https://business.comcast.com/account/bill")
            LOGGER.info(f"Navigating to the current bill page...")
            handle_popup(
                self.driver,
                value=ACCOUNT_PAGE_LOCATORS["POPUP_AFTER_PAGE_LOAD"],
                retry_attempts=1,
            )

            account_list_elements = self.get_account_elements_list()
            account_names = [
                accounts_element.text for accounts_element in account_list_elements
            ]
            LOGGER.info(f"Totally {len(account_names)} accounts found: {account_names}")

            for index, account_name in enumerate(account_names):

                if index > 0:
                    self.get_account_elements_list(index).click()
                    explicit_wait_till_invisibility(
                        self.driver,
                        self.get_accounts_list(),
                        msg="Loading next account",
                    )
                    wait_for_loaders(
                        self.driver,
                        value=ACCOUNT_PAGE_LOCATORS["SPINNER"],
                        timeout=10,
                        retry_attempts=1,
                    )

                LOGGER.info(f"Navigating to the {account_name} account page...")
                self.close_dialogs()

                try:
                    if not has_invoices(
                        self.driver,
                        value=CURRENT_BILL_PAGE_LOCATORS["DOWNLOAD_BUTTON"],
                        msg="View Pdf",
                    ):
                        continue
                except NoSuchElementException:
                    LOGGER.info(
                        f"Collecting details from the {account_name} account page..."
                    )

                discovered_files += self._download_documents(account_name)

        finally:
            self._quit_driver()

        LOGGER.info(
            f"Total Invoices within date range and download link available: {len(discovered_files)}"
        )
        return discovered_files

    def login_flow(self, run: Run):
        self._login()
