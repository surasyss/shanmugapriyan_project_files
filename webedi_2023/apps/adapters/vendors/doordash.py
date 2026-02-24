import os
from typing import List

from selenium.webdriver.remote.webelement import WebElement

from apps.adapters import LOGGER
from apps.adapters.base import PasswordBasedLoginPage, VendorDocumentDownloadInterface
from apps.adapters.framework import download
from apps.adapters.helpers.helper import (
    wait_until_file_exists,
    extract_zip_file,
    delete_files,
)
from apps.adapters.helpers.webdriver_helper import (
    explicit_wait_till_visibility,
    explicit_wait_till_invisibility,
    IGNORED_EXCEPTIONS,
)
from apps.runs.models import Run, DiscoveredFile, DocumentType, FileFormat

TIMEOUT = 40
# Home Page Locators
HOME_PAGE_LOCATORS = {"DELIVERIES_LINK": 'a[href="/merchant/deliveries/list"]'}

# Receipts Page Locators
DELIVERIES_PAGE_MAIN = "div.sc-iwsKbI.sc-gzVnrw "
DELIVERIES_PAGE_MODEL = "div.sc-eXEjpC.bbpjKa "
DELIVERIES_PAGE_LOCATORS = {
    "FROM_TO_DATE_TEXTBOXS": DELIVERIES_PAGE_MAIN + "input.sc-doWzTn",
    "SUBMIT_BUTTON": '//button[@class="sc-erOsFi gxfewO"]//div[@class="sc-fMiknA hpxNZA"][text()="Submit"]',
    "DOWNLOAD_CSV_BUTTON": '//button[@class="sc-erOsFi gxfewO"]//div[@class="sc-fMiknA hpxNZA"][text()="Download CSV"]',
    "PAGINATION_LABEL": DELIVERIES_PAGE_MAIN
    + "section.panel div.panel-heading span.sc-ccLTTT.sc-ifAKCX",
    "PAGINATION_ARROWS": DELIVERIES_PAGE_MAIN
    + "section.panel div.panel-heading div.sc-hARARD.ciLzbd",
    "TABLE_ROWS": DELIVERIES_PAGE_MAIN + "div.sc-eNPDpu.jUaLWW table.table>tbody>tr",
    "MONTHS_LABEL": DELIVERIES_PAGE_MODEL
    + "div.sc-bZQynM.eHDGLZ span.sc-ifAKCX.hwtskg",
    "DOWNLOAD_BUTTONS": DELIVERIES_PAGE_MODEL
    + "div.sc-ccSCjj.sc-dnqmqq button.sc-erOsFi.fRChKJ",
    "LOADER": "div.sc-ccSCjj.sc-dnqmqq button.sc-erOsFi.fRChKJ div.sc-dVhcbM.kCAXQA",
}


class DoorDashLoginPage(PasswordBasedLoginPage):
    SELECTOR_USERNAME_TEXTBOX = 'input[data-anchor-id="IdentityLoginPageEmailField"]'
    SELECTOR_PASSWORD_TEXTBOX = 'input[data-anchor-id="IdentityLoginPagePasswordField"]'
    SELECTOR_LOGIN_BUTTON = 'button[data-anchor-id="IdentityLoginSigninButton"]'
    SELECTOR_ERROR_MESSAGE_TEXT = "div.card div.login-error span"


class DoorDashHomePage:
    """Home page action methods come here."""

    def __init__(self, driver, download_location: str):
        self.driver = driver
        self.download_location = download_location

    def get_deliveries_link(self) -> WebElement:
        """Returns Deliveries Link WebElement"""
        return self.driver.find_element_by_css_selector(
            HOME_PAGE_LOCATORS["DELIVERIES_LINK"]
        )


class DoorDashDeliveriesPage:
    """Receipts page action methods come here."""

    def __init__(self, driver):
        self.driver = driver

    @staticmethod
    def get_vendor_name() -> str:
        """Returns Vendor Name"""
        return "DoorDash"

    def get_from_date_textbox(self) -> WebElement:
        """Returns From Date Textbox WebElement"""
        return self.driver.find_elements_by_css_selector(
            DELIVERIES_PAGE_LOCATORS["FROM_TO_DATE_TEXTBOXS"]
        )[0]

    def get_to_date_textbox(self) -> WebElement:
        """Returns To Date Textbox WebElement"""
        return self.driver.find_elements_by_css_selector(
            DELIVERIES_PAGE_LOCATORS["FROM_TO_DATE_TEXTBOXS"]
        )[1]

    def get_submit_button(self) -> WebElement:
        """Returns Submit Button WebElement"""
        return self.driver.find_element_by_xpath(
            DELIVERIES_PAGE_LOCATORS["SUBMIT_BUTTON"]
        )

    def get_download_csv_button(self) -> WebElement:
        """Returns Download CSV Button WebElement"""
        return self.driver.find_element_by_xpath(
            DELIVERIES_PAGE_LOCATORS["DOWNLOAD_CSV_BUTTON"]
        )

    def get_pagination_label(self) -> WebElement:
        """Returns Pagination Label WebElement"""
        return self.driver.find_element_by_css_selector(
            DELIVERIES_PAGE_LOCATORS["PAGINATION_LABEL"]
        )

    def get_pagination_right_arrow(self) -> WebElement:
        """Returns Pagination Right Arrow WebElement"""
        return self.driver.find_elements_by_css_selector(
            DELIVERIES_PAGE_LOCATORS["PAGINATION_ARROWS"]
        )[1]

    def get_table_rows(self) -> List[WebElement]:
        """Returns Request Button WebElement"""
        return self.driver.find_elements_by_css_selector(
            DELIVERIES_PAGE_LOCATORS["TABLE_ROWS"]
        )

    def get_months_label(self) -> List[WebElement]:
        """Returns Request Button WebElement"""
        return self.driver.find_elements_by_css_selector(
            DELIVERIES_PAGE_LOCATORS["MONTHS_LABEL"]
        )

    def get_download_button_by_index(self, index) -> WebElement:
        """Returns Request Button WebElement"""
        return self.driver.find_elements_by_css_selector(
            DELIVERIES_PAGE_LOCATORS["DOWNLOAD_BUTTONS"]
        )[index]

    def get_loader(self) -> WebElement:
        """Returns Loader WebElement"""
        return self.driver.find_element_by_css_selector(
            DELIVERIES_PAGE_LOCATORS["LOADER"]
        )


class DoorDashRunner(VendorDocumentDownloadInterface):
    """Runner Class for Doordash"""

    # uses_proxy = True

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.login_page = DoorDashLoginPage(self.driver)
        self.home_page = DoorDashHomePage(self.driver, self.download_location)
        self.deliveries_page = DoorDashDeliveriesPage(self.driver)
        self.vendor_name = "DoorDash"
        self.restaurant_name = "Danville Harvest"
        self.customer_id = "314969"

    def _login(self):
        """
        Login to Restaurant Depot
        :return: Nothing
        """
        login_url = "https://www.doordash.com/merchant/"
        LOGGER.info("[tag:WEWVDD1] Navigating to %s", login_url)
        self.driver.get(login_url)
        self.login_page.login(self.run.job.username, self.run.job.password)
        explicit_wait_till_visibility(
            self.driver,
            self.home_page.get_deliveries_link(),
            timeout=TIMEOUT,
            ignored_exceptions=IGNORED_EXCEPTIONS,
        )

    def _go_to_deliveries_page(self):
        self.home_page.get_deliveries_link().click()
        explicit_wait_till_visibility(
            self.driver,
            self.deliveries_page.get_pagination_label(),
            timeout=TIMEOUT,
            ignored_exceptions=IGNORED_EXCEPTIONS,
        )

    def _search_invoices_in_date_range(self, from_date: str, to_date: str):
        from_date_script = (
            f'document.querySelectorAll("{DELIVERIES_PAGE_LOCATORS["FROM_TO_DATE_TEXTBOXS"]}")[0].'
            f"value={from_date}"
        )
        to_date_script = (
            f'document.querySelectorAll("{DELIVERIES_PAGE_LOCATORS["FROM_TO_DATE_TEXTBOXS"]}")[1].'
            f"value={to_date}"
        )

        self.driver.execute_script(from_date_script)
        self.driver.execute_script(to_date_script)
        # self.deliveries_page.get_from_date_textbox().send_keys(from_date)
        # self.deliveries_page.get_to_date_textbox().send_keys(to_date)
        self.deliveries_page.get_submit_button().click()
        explicit_wait_till_visibility(
            self.driver,
            self.deliveries_page.get_pagination_label(),
            timeout=TIMEOUT,
            ignored_exceptions=IGNORED_EXCEPTIONS,
        )
        LOGGER.info(f"{self.deliveries_page.get_pagination_label().text}")

    def _download_documents(self, run: Run) -> List[DiscoveredFile]:
        """
        Chooses the documents to be downloaded based on the document type
        :return: Returns the list of Discovered Files
        """
        document_type = self.run.job.requested_document_type
        if document_type == "invoice":
            return self._download_invoices(run)

        raise NotImplementedError(
            f"[tag:WEWVDD2] Requested Document Type is not supported: {document_type}"
        )

    def _download_invoices(self, run: Run) -> List[DiscoveredFile]:
        """
        Downloads the Invoices
        :return: Returns the list of the Discovered Files
        """
        self.deliveries_page.get_download_csv_button().click()
        explicit_wait_till_visibility(
            self.driver,
            self.deliveries_page.get_download_button_by_index(0),
            timeout=TIMEOUT,
            ignored_exceptions=IGNORED_EXCEPTIONS,
        )

        self.deliveries_page.get_download_button_by_index(0).click()
        explicit_wait_till_invisibility(
            self.driver,
            self.deliveries_page.get_loader(),
            timeout=TIMEOUT,
            ignored_exceptions=IGNORED_EXCEPTIONS,
        )

        downloaded_file = wait_until_file_exists(
            file_path=self.download_location,
            timeout=TIMEOUT,
            pattern="transaction_report(.*).zip",
        )
        extracted_files = extract_zip_file(downloaded_file)
        delete_files(self.download_location, "(.*).zip")

        discovered_files_list = []

        for extracted_file in extracted_files:
            reference_code = extracted_file.replace(".csv", "")
            document_properties = {
                "invoice_number": None,
                "invoice_date": None,
                "due_date": None,
                "total_amount": None,
                "payment_amount": None,
                "vendor_name": self.vendor_name,
                "restaurant_name": self.restaurant_name,
                "customer_number": self.customer_id,
            }
            try:
                # pylint: disable=no-member
                discovered_file = DiscoveredFile.build_unique(
                    run,
                    reference_code,
                    document_type=DocumentType.INVOICE.ident,
                    file_format=FileFormat.CSV.ident,
                    original_download_url="NA",
                    original_filename=extracted_file,
                    document_properties=document_properties,
                )
            except DiscoveredFile.AlreadyExists:
                LOGGER.info(
                    f"Discovered file already exists with reference code : {reference_code}"
                )
                continue  # skip if seen before
            filepath = os.path.join(
                self.download_location, discovered_file.original_filename
            )
            _downloader = download.NoOpDownloader(local_filepath=filepath)
            download.download_discovered_file(discovered_file, _downloader)

            discovered_files_list.append(discovered_file)

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
            self._go_to_deliveries_page()

            discovered_files += self._download_documents(run)
        finally:
            self._quit_driver()

        return discovered_files

    def login_flow(self, run: Run):
        self._login()
