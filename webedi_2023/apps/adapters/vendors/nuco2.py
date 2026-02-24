import os
import time
from datetime import datetime
from decimal import Decimal
from typing import List

from selenium.common.exceptions import NoSuchElementException, TimeoutException
from selenium.webdriver import ActionChains
from selenium.webdriver.common.by import By
from selenium.webdriver.remote.webelement import WebElement

from apps.adapters import LOGGER
from apps.adapters.base import VendorDocumentDownloadInterface, PasswordBasedLoginPage
from apps.adapters.framework import download
from apps.adapters.helpers.webdriver_helper import (
    get_url,
    wait_for_ajax,
    handle_popup,
    scroll_down_to_element,
    explicit_wait_till_clickable,
)
from apps.runs.models import Run, DiscoveredFile, DocumentType, FileFormat

LOGIN_PAGE_LOCATORS = {
    "EMAIL": "input#Login",
    "PASSWORD": "input#Password",
    "LOGIN_BUTTON": "button#login-button",
    "ERROR": "div.alert.alert-warning",
}

HOME_PAGE_LOCATORS = {
    "HIDE_ACCOUNT_GROUPING": "button.grouping.show-hide",
    "INVOICE_DATE_HEADER": "span.statement-date",
    "TOTAL_PAGES": "ul.pagination li:last-child",
}

INVOICE_HISTORY_LOCATORS = {
    "INVOICES_DROPDOWN": "div.dropdown a.invoice-selector",
    "ALL_BILLS": "ul.invoice-selector-dropdown li a.all",
    "INVOICE_NUMBER": "div.invoice-header span.biller-controlled",
    "INVOICE_DATE": "span.statement-date",
    "TOTAL_AMOUNT": "span.invoice-amount",
    "RESTAURANT_NAME": "a#account-dropdown-button",
    "ACCOUNT_NUMBER": "div.account-display-first-line",
    "INVOICE_DOWNLOAD_URL": "iframe#bill-view-frame",
    "INVOICE_ROW": "div[id^='invoice-row']",
    "INVOICE_TABLE": "div.invoices-table div.mobile-item-cards",
}

INVOICE_DOWNLOAD_LOCATORS = {
    "VIEW_BILL": "button.view.btn.btn-as-link",
    "CLOSE_BILL": 'button[onclick="closeBill()"]',
    "BACKGROUND_FADE": "div.modal-backdrop.fade.in",
    "SESSION_TIMEOUT_MODAL": "div#session-timeout.modal.fade.in",
    "TIMEOUT_OK_BUTTON": "div#session-timeout button.btn-success",
}


class NuCo2LoginPage(PasswordBasedLoginPage):
    """Login Page Web Elements"""

    SELECTOR_USERNAME_TEXTBOX = LOGIN_PAGE_LOCATORS["EMAIL"]
    SELECTOR_PASSWORD_TEXTBOX = LOGIN_PAGE_LOCATORS["PASSWORD"]
    SELECTOR_LOGIN_BUTTON = LOGIN_PAGE_LOCATORS["LOGIN_BUTTON"]
    SELECTOR_ERROR_MESSAGE_TEXT = LOGIN_PAGE_LOCATORS["ERROR"]


class NuCo2HomePage:
    """Home Page Class"""

    def __init__(self, driver):
        self.driver = driver

    def get_invoices_dropdown(self) -> WebElement:
        """Returns the invoices dropdown web element"""
        return self.driver.find_element_by_css_selector(
            INVOICE_HISTORY_LOCATORS["INVOICES_DROPDOWN"]
        )

    def select_all_bills(self) -> WebElement:
        """Returns the all invoices web element in dropdown"""
        return self.driver.find_element_by_css_selector(
            INVOICE_HISTORY_LOCATORS["ALL_BILLS"]
        )


class NuCo2InvoicesPage:
    """Invoice Page Class"""

    def __init__(self, driver, download_location):
        self.driver = driver
        self.download_location = download_location

    @staticmethod
    def get_invoice_number(row) -> WebElement:
        """Returns the invoice number web element"""
        return row.find_element_by_css_selector(
            INVOICE_HISTORY_LOCATORS["INVOICE_NUMBER"]
        )

    @staticmethod
    def get_invoice_date(row) -> WebElement:
        """Returns the invoice date web element"""
        return row.find_element_by_css_selector(
            INVOICE_HISTORY_LOCATORS["INVOICE_DATE"]
        )

    @staticmethod
    def get_total_amount(row) -> WebElement:
        """Returns the total amount web element"""
        return row.find_element_by_css_selector(
            INVOICE_HISTORY_LOCATORS["TOTAL_AMOUNT"]
        )

    def get_restaurant_name(self) -> WebElement:
        """Returns the restaurant name web element"""
        return self.driver.find_element_by_css_selector(
            INVOICE_HISTORY_LOCATORS["RESTAURANT_NAME"]
        )

    @staticmethod
    def get_account_number(account) -> WebElement:
        """Returns the account number web element"""
        return account.find_element_by_css_selector(
            INVOICE_HISTORY_LOCATORS["ACCOUNT_NUMBER"]
        )

    def get_download_url(self) -> WebElement:
        """Returns the pdf download link web element"""
        return self.driver.find_element_by_css_selector(
            INVOICE_HISTORY_LOCATORS["INVOICE_DOWNLOAD_URL"]
        )

    @staticmethod
    def get_all_invoice_rows(invoice_table) -> List[WebElement]:
        """Returns all invoice rows web element"""
        return invoice_table.find_elements_by_css_selector(
            INVOICE_HISTORY_LOCATORS["INVOICE_ROW"]
        )

    @staticmethod
    def view_invoice(row) -> WebElement:
        """Returns the web element to view pdf"""
        return row.find_element_by_css_selector(INVOICE_DOWNLOAD_LOCATORS["VIEW_BILL"])

    def close_bill(self) -> WebElement:
        """Returns the web element to close pdf window"""
        return self.driver.find_element_by_css_selector(
            INVOICE_DOWNLOAD_LOCATORS["CLOSE_BILL"]
        )

    def hide_account_grouping(self) -> WebElement:
        return self.driver.find_element_by_css_selector(
            HOME_PAGE_LOCATORS["HIDE_ACCOUNT_GROUPING"]
        )

    def wait_for_ajax_loader(self, msg: str = None):
        try:
            wait_for_ajax(self.driver, timeout=10, msg=msg)
        except TimeoutException:
            LOGGER.info("No ajax calls found")

    def sort_by_invoice_date(self):
        for _ in range(2):
            self.driver.find_element_by_css_selector(
                HOME_PAGE_LOCATORS["INVOICE_DATE_HEADER"]
            ).click()
            self.wait_for_ajax_loader(msg="Sorting by invoice date")

    def total_pages(self) -> WebElement:
        return self.driver.find_element_by_css_selector(
            HOME_PAGE_LOCATORS["TOTAL_PAGES"]
        )

    def get_invoice_table(self) -> WebElement:
        return self.driver.find_element_by_css_selector(
            INVOICE_HISTORY_LOCATORS["INVOICE_TABLE"]
        )

    def get_next_page(self, current_page) -> WebElement:
        return self.driver.find_element_by_css_selector(
            f'ul.pagination li a[data-page="{current_page}"]'
        )

    def scroll_to_element_position(self, element):
        x_position = element.location.get("x")
        y_position = element.location.get("y")
        self.driver.execute_script(f"window.scrollTo({x_position}, {y_position});")

    def check_and_handle_session_timeout(self, login_time):
        time_since_login = (time.time() - login_time) / 60
        if time_since_login > 15.0:
            session_timeout = self.driver.find_elements_by_css_selector(
                INVOICE_DOWNLOAD_LOCATORS["SESSION_TIMEOUT_MODAL"]
            )
            if session_timeout:
                LOGGER.info(session_timeout[0].find_element_by_css_selector("p").text)
                handle_popup(
                    self.driver,
                    value=INVOICE_DOWNLOAD_LOCATORS["TIMEOUT_OK_BUTTON"],
                    retry_attempts=1,
                    msg="Timeout",
                )

    def collect_invoices_data(self, from_date, login_time):
        collected_invoices_data = {}
        restaurant_name = self.get_restaurant_name().text
        try:
            total_pages = self.total_pages().text
        except NoSuchElementException:
            total_pages = "1"

        self.hide_account_grouping().click()
        self.wait_for_ajax_loader(msg="Hiding account groups")

        self.sort_by_invoice_date()

        current_page = 1

        while current_page <= int(total_pages):
            invoice_list = []
            for _, row_id in enumerate(self.get_invoice_ids()):
                explicit_wait_till_clickable(
                    self.driver,
                    (By.CSS_SELECTOR, f"div#invoice-row-{row_id}"),
                    timeout=10,
                    msg="Invoice Row",
                )
                row_locator = (
                    INVOICE_HISTORY_LOCATORS["INVOICE_TABLE"]
                    + " "
                    + f"div#invoice-row-{row_id}"
                )
                row = self.driver.find_element_by_css_selector(row_locator)
                # self.scroll_to_element_position(row)
                ActionChains(self.driver).move_to_element(row).perform()

                invoice_date_text = NuCo2InvoicesPage.get_invoice_date(row).text
                invoice_date = datetime.strptime(
                    invoice_date_text.strip(), "%d/%m/%Y"
                ).date()

                if invoice_date < from_date:
                    LOGGER.info(
                        f"Skipping remaining invoices because date "
                        f"'{invoice_date}' is outside requested range"
                    )
                    return collected_invoices_data

                total_amount = NuCo2InvoicesPage.get_total_amount(row).text
                total_amount = total_amount.replace(",", "")
                invoice_number = NuCo2InvoicesPage.get_invoice_number(row).text

                if invoice_number in invoice_list:
                    collected_invoices_data[invoice_number]["total_amount"] += Decimal(
                        total_amount
                    )
                    continue

                LOGGER.info(
                    f"invoice_number : {invoice_number}, total_amount:{total_amount}"
                )
                self.check_and_handle_session_timeout(login_time)
                NuCo2InvoicesPage.view_invoice(row).click()
                self.wait_for_ajax_loader(msg="View Invoice")

                iframe = self.get_download_url()
                if not self.is_invoice_generated(iframe, invoice_number):
                    handle_popup(
                        self.driver,
                        value=INVOICE_DOWNLOAD_LOCATORS["CLOSE_BILL"],
                        retry_attempts=1,
                        msg="Close Bill",
                    )
                    continue

                invoice_list.append(invoice_number)
                download_url = iframe.get_attribute("src")

                handle_popup(
                    self.driver,
                    value=INVOICE_DOWNLOAD_LOCATORS["CLOSE_BILL"],
                    retry_attempts=1,
                    msg="Close Bill",
                )
                collected_invoices_data.update(
                    {
                        invoice_number: {
                            "invoice_date": invoice_date,
                            "total_amount": Decimal(total_amount),
                            "download_url": download_url,
                            "restaurant_name": restaurant_name,
                            "row_id": row_id,
                        }
                    }
                )

            current_page += 1
            if current_page > int(total_pages):
                break

            _next_page = self.get_next_page(current_page)
            scroll_down_to_element(self.driver, _next_page)
            self.check_and_handle_session_timeout(login_time)
            _next_page.click()
            self.wait_for_ajax_loader(msg=f"Navigating to page: {current_page}")

        return collected_invoices_data

    def get_invoice_ids(self):
        invoice_id_list = []
        for row in NuCo2InvoicesPage.get_all_invoice_rows(self.get_invoice_table()):
            invoice_id_list.append(row.get_attribute("data-id"))
        return invoice_id_list

    def get_discovered_files(
        self, run: Run, collected_invoices_data
    ) -> List[DiscoveredFile]:
        """Extracts invoice details"""
        discovered_files = []
        for invoice_number, value in collected_invoices_data.items():
            plain_date = str(value["invoice_date"]).replace("-", "")
            reference_code = f"{invoice_number}_{plain_date}"

            try:
                # pylint: disable=no-member
                discovered_file = DiscoveredFile.build_unique(
                    run,
                    reference_code,
                    document_type=DocumentType.INVOICE.ident,
                    file_format=FileFormat.PDF.ident,
                    original_download_url=value["download_url"],
                    original_filename=f"{reference_code}.pdf",
                    document_properties={
                        "customer_number": None,
                        "invoice_number": invoice_number,
                        "invoice_date": f'{value["invoice_date"]}',
                        "total_amount": f'{value["total_amount"]}',
                        "restaurant_name": value["restaurant_name"],
                        "vendor_name": "NuCo2",
                    },
                )
            except DiscoveredFile.AlreadyExists:
                LOGGER.info(
                    f"Discovered file already exists with reference code : {reference_code}"
                )
                continue

            discovered_files.append(discovered_file)
            LOGGER.info(f"Invoice details data: {discovered_file.document_properties}")

            self.download_invoice_by_url(discovered_file, value["row_id"])
        return discovered_files

    def download_invoice_by_url(self, discovered_file, row_id):
        """Downloads invoice by discovered file url."""
        _downloader = download.DriverBasedUrlGetDownloader(
            self.driver,
            download_url=discovered_file.original_download_url,
            local_filepath=os.path.join(self.download_location, f"Invoice{row_id}.pdf"),
            rename_to=os.path.join(
                self.download_location, discovered_file.original_filename
            ),
            file_exists_check_kwargs=dict(timeout=60),
        )
        download.download_discovered_file(discovered_file, _downloader)

    def is_invoice_generated(self, iframe, invoice_number):
        """As its name states this method validates whether invoice is generated or not in PDF format."""
        ret_value = True
        self.driver.switch_to.frame(iframe)
        try:
            _elem = self.driver.find_element_by_css_selector("span#ErrorLabel")
            if _elem.text == "Invoice PDF is not available.":
                LOGGER.info(f"PDF invoice is yet not generated for : {invoice_number}")
                ret_value = False
        except NoSuchElementException:
            LOGGER.info(f"PDF invoice is generated for : {invoice_number}")
        self.driver.switch_to.default_content()
        return ret_value


class NuCO2Runner(VendorDocumentDownloadInterface):
    """Runner Class"""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.login_page = NuCo2LoginPage(self.driver)
        self.home_page = NuCo2HomePage(self.driver)
        self.invoice_page = NuCo2InvoicesPage(self.driver, self.download_location)
        self.login_time = None

    def _login(self):
        """
        Login using credentials
        :return: Nothing
        """
        login_url = "https://www.billeriq.com/ebpp/NuCO2/Login"
        get_url(self.driver, login_url)
        self.login_page.login(self.run.job.username, self.run.job.password)

    def navigate_to_invoices_page(self):
        """Navigate to all invoices page"""
        self.home_page.get_invoices_dropdown().click()
        self.home_page.select_all_bills().click()
        self.invoice_page.wait_for_ajax_loader(msg="All Invoices")

    def _download_documents(self, login_time):
        """
        Chooses the documents to be downloaded based on the document type
        :return: Returns the list of Discovered Files
        """
        document_type = self.run.job.requested_document_type
        if document_type == "invoice":
            return self._download_invoices(login_time)

        raise NotImplementedError(
            f"Requested Document Type is not supported: {document_type}"
        )

    def _download_invoices(self, login_time):
        """
        Downloads the Invoices
        :return: Returns the list of the Discovered Files
        """
        LOGGER.info("Extracting data from invoice page...")
        start_date = datetime.strptime(
            self.run.request_parameters["start_date"], "%Y-%m-%d"
        ).date()
        collected_invoices_data = self.invoice_page.collect_invoices_data(
            start_date, login_time
        )
        discovered_files = self.invoice_page.get_discovered_files(
            self.run, collected_invoices_data
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
            self.login_time = time.time()
            self.navigate_to_invoices_page()
            discovered_files += self._download_documents(self.login_time)
        finally:
            self._quit_driver()
        return discovered_files

    def login_flow(self, run: Run):
        self._login()
