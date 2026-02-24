import os
from datetime import date
from typing import List
from retry.api import retry

from selenium.webdriver.common.by import By
from selenium.common.exceptions import (
    WebDriverException,
    StaleElementReferenceException,
)
from selenium.webdriver.remote.webelement import WebElement
from selenium.webdriver.support.select import Select

from apps.adapters.base import VendorDocumentDownloadInterface, PasswordBasedLoginPage
from apps.adapters.framework import download
from apps.adapters.helpers.webdriver_helper import (
    get_url,
    wait_for_element,
    handle_popup,
)
from apps.adapters.vendors import LOGGER
from apps.runs.models import Run, DiscoveredFile, DocumentType, FileFormat
from spices.datetime_utils import date_from_string

# Home Page Locators
HOME_PAGE_LOCATORS = {
    "RECEIPTS_LINK": "nav>div.navigation--wrapper>ul.navigation--main>li.item.receipts",
    "DIALOGUE_CONTAINER": 'div[id="mgs-popup"]',
    "DIALOGUE_CONTAINER_CLOSE_BUTTON": 'div[id="mgs-popup"] button.action-close',
    "CLICK_COLLECT_BUTTON": "div.shopping-types div.shopping-types-inner a.btn-create-list",
}

# Receipts Page Locators
RECEIPTS_PAGE_LOCATORS = {
    "RECEIPT_DATE_DROPDOWN": 'select[id="select-receipt-date"]',
    "REQUEST_BUTTON": 'button[id="btn-request-receipt"]',
    "TABLE_ROWS": "div.products-list > ol.product-items > li.product-item > div.row",
}


class RestaurantDepotLoginPage(PasswordBasedLoginPage):
    SELECTOR_USERNAME_TEXTBOX = 'input[id="email"]'
    SELECTOR_PASSWORD_TEXTBOX = 'input[id="pass"]'
    SELECTOR_LOGIN_BUTTON = 'button[id="send2"]'
    SELECTOR_ERROR_MESSAGE_TEXT = "div.message-error div, div#email-error"


class RestaurantDepotHomePage:
    """Home page action methods come here."""

    def __init__(self, driver, download_location: str):
        self.driver = driver
        self.download_location = download_location
        self.vendor_name = "Regal Wine Co."

    def get_receipts_link(self) -> WebElement:
        """Returns Receipts Link WebElement"""
        return self.driver.find_element_by_css_selector(
            HOME_PAGE_LOCATORS["RECEIPTS_LINK"]
        )

    def get_dialogue_container(self) -> WebElement:
        return self.driver.find_element_by_css_selector(
            HOME_PAGE_LOCATORS["DIALOGUE_CONTAINER"]
        )

    def get_dialogue_container_close_button(self) -> WebElement:
        return self.driver.find_element_by_css_selector(
            HOME_PAGE_LOCATORS["DIALOGUE_CONTAINER_CLOSE_BUTTON"]
        )

    def get_click_collect_button(self) -> WebElement:
        return self.driver.find_element_by_css_selector(
            HOME_PAGE_LOCATORS["CLICK_COLLECT_BUTTON"]
        )


class RestaurantDepotReceiptsPage:
    """Receipts page action methods come here."""

    def __init__(self, driver):
        self.driver = driver
        self.csv_webelement_dict = {}
        self.last_sixty_days_invoices = (
            "https://member.restaurantdepot.com/receipts/index/index/days/60"
        )

    @staticmethod
    def get_vendor_name() -> str:
        """Returns Vendor Name"""
        return "Restaurant Depot"

    def get_receipts_date_dropdown(self) -> WebElement:
        """Returns Receipts Date Dropdown WebElement"""
        return self.driver.find_element_by_css_selector(
            RECEIPTS_PAGE_LOCATORS["RECEIPT_DATE_DROPDOWN"]
        )

    def get_request_button(self) -> WebElement:
        """Returns Request Button WebElement"""
        return self.driver.find_element_by_css_selector(
            RECEIPTS_PAGE_LOCATORS["REQUEST_BUTTON"]
        )

    def get_table_rows(self) -> List[WebElement]:
        """Returns Table Rows WebElement"""
        return self.driver.find_elements_by_css_selector(
            RECEIPTS_PAGE_LOCATORS["TABLE_ROWS"]
        )

    def select_receipt_date_by_value(self, value: str):
        """Selects Receipt Date by Value"""
        Select(self.get_receipts_date_dropdown()).select_by_value(value)

    def navigate_to_last_sixty_days_invoices(self):
        for retries in range(5):
            try:
                get_url(
                    self.driver,
                    self.last_sixty_days_invoices,
                )
                wait_for_element(
                    self.driver,
                    value=RECEIPTS_PAGE_LOCATORS["RECEIPT_DATE_DROPDOWN"],
                    retry_attempts=1,
                    msg="Receipts Date DropDown",
                )
                break
            except WebDriverException:
                if self.driver.current_url != self.last_sixty_days_invoices:
                    LOGGER.info(
                        f"Receipts date dropdown not found in {self.driver.current_url}. "
                        f"Reloading Receipts page..."
                    )

                if (
                    retries == 4
                    and self.driver.current_url == self.last_sixty_days_invoices
                ):
                    LOGGER.info(
                        f"Receipts date dropdown not found. Check for table rows..."
                    )

    def get_invoice_table_data(
        self, run: Run, start_date: date, download_location
    ) -> List[DiscoveredFile]:
        """
        Extracts invoice details from Table
        :param run: Run Object
        :param start_date: minimum range for invoice date
        :param download_location: invoices download directory
        :return: Returns the list of Discovered Files
        """
        self.navigate_to_last_sixty_days_invoices()

        LOGGER.info(
            "[tag:WEWVRD1] Extracting invoice details data from the invoice table."
        )
        discovered_files, reference_codes = [], []

        rows = self.get_table_rows()

        if not rows:
            LOGGER.info("No Invoice found")

        for index, row in enumerate(rows):
            location_id = ""
            for retries in range(3):
                try:
                    row = self.get_table_rows()[index]
                    location_id = row.find_element_by_css_selector(
                        "div.date-col a.veiw-receipt"
                    ).get_attribute("data-branch")
                    break
                except StaleElementReferenceException as excep:
                    LOGGER.warning(f"{excep} found in {self.driver.current_url}")
                    if retries == 2:
                        raise
                    if self.driver.current_url != self.last_sixty_days_invoices:
                        get_url(self.driver, self.last_sixty_days_invoices)

            invoice_number = row.find_element_by_css_selector(
                "div.date-col a.veiw-receipt"
            ).get_attribute("data-receipt-id")

            invoice_date = date_from_string(
                row.find_element_by_css_selector("div.date-col").text, "%Y/%m/%d"
            )

            if invoice_date < start_date:
                LOGGER.info(
                    f"Skipping remaining invoices because date '{invoice_date}' is outside requested range"
                )
                continue

            reference_code = f"{location_id}_{invoice_number}_{invoice_date}"

            # checking for duplicate reference code, as there exists identical invoice rows
            if reference_code in reference_codes:
                continue

            # collecting all reference codes
            reference_codes.append(reference_code)

            document_properties = {
                "customer_number": None,
                "invoice_number": invoice_number,
                "invoice_date": str(invoice_date),
                "due_date": "",
                "total_amount": row.find_element_by_css_selector("div.total-col").text,
                "vendor_name": self.get_vendor_name(),
                "restaurant_name": row.find_element_by_css_selector(
                    "div.location-col"
                ).text,
            }
            try:
                # pylint: disable=no-member
                discovered_file = DiscoveredFile.build_unique(
                    run,
                    reference_code,
                    document_type=DocumentType.INVOICE.ident,
                    file_format=FileFormat.CSV.ident,
                    original_download_url=reference_code,
                    original_filename=f"Receipt_{invoice_number}.csv",
                    document_properties=document_properties,
                )
            except DiscoveredFile.AlreadyExists:
                LOGGER.info(
                    f"Discovered file already exists with reference code : {reference_code}"
                )
                continue  # skip if seen before

            self.download_documents_by_click(download_location, discovered_file, index)
            discovered_files.append(discovered_file)
            LOGGER.info(
                "[tag:WEWVRD2] Invoice details row data: %s",
                str(discovered_file.document_properties),
            )

        return discovered_files

    def download_documents_by_click(
        self, download_location: str, discovered_file: DiscoveredFile, index: int
    ):
        """Download all discovered files and set appropriate attributes on them"""
        for retries in range(3):
            try:
                _downloader = download.WebElementClickBasedDownloader(
                    element=self.get_table_rows()[index].find_element_by_css_selector(
                        "div.action-col li>a.download-receipt"
                    ),
                    local_filepath=os.path.join(
                        download_location, discovered_file.original_filename
                    ),
                    file_exists_check_kwargs=dict(timeout=60),
                )
                download.download_discovered_file(discovered_file, _downloader)
                break
            except StaleElementReferenceException as excep:
                LOGGER.warning(f"{excep} found in {self.driver.current_url}")

                if retries == 2:
                    raise
                self.navigate_to_last_sixty_days_invoices()


class RestaurantDepotRunner(VendorDocumentDownloadInterface):
    """Runner Class for Restaurant Depot"""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.login_page = RestaurantDepotLoginPage(self.driver)
        self.home_page = RestaurantDepotHomePage(self.driver, self.download_location)
        self.receipts_page = RestaurantDepotReceiptsPage(self.driver)

    @retry(WebDriverException, tries=3, delay=2)
    def _login(self):
        """
        Login to Restaurant Depot
        :return: Nothing
        """
        login_url = "https://member.restaurantdepot.com/"
        for index in range(5):
            try:
                get_url(self.driver, login_url)
                self.login_page.login(self.run.job.username, self.run.job.password)

                if self.driver.find_elements(
                    By.CSS_SELECTOR, self.login_page.SELECTOR_USERNAME_TEXTBOX
                ):
                    continue
                break
            except WebDriverException as excep:
                LOGGER.info(f"{excep} found in {self.driver.current_url}")
                if index == 4:
                    raise

    def post_login_action(self):
        for index in range(3):
            try:
                handle_popup(
                    self.driver,
                    value=HOME_PAGE_LOCATORS["CLICK_COLLECT_BUTTON"],
                    msg="Click & Collect page",
                    retry_attempts=1,
                )
                wait_for_element(
                    self.driver,
                    value=HOME_PAGE_LOCATORS["RECEIPTS_LINK"],
                    msg="Receipts Link",
                )
                handle_popup(
                    self.driver,
                    value=HOME_PAGE_LOCATORS["DIALOGUE_CONTAINER_CLOSE_BUTTON"],
                    retry_attempts=1,
                )
                break
            except WebDriverException as excep:
                LOGGER.warning(f"{excep} found in {self.driver.current_url}")
                if index == 2:
                    raise
                get_url(self.driver, "https://member.restaurantdepot.com/")

    def _download_documents(self) -> List[DiscoveredFile]:
        """
        Chooses the documents to be downloaded based on the document type
        :return: Returns the list of Discovered Files
        """
        document_type = self.run.job.requested_document_type
        if document_type == "invoice":
            return self._download_invoices()

        raise NotImplementedError(
            f"[tag:WEWVRD7] Requested Document Type is not supported: {document_type}"
        )

    def _download_invoices(self) -> List[DiscoveredFile]:
        """
        Downloads the Invoices
        :return: Returns the list of the Discovered Files
        """
        LOGGER.info("[tag:WEWVRD8] Extracting data from table...")
        # Fetching all invoice table date & storing it in memory
        start_date = date_from_string(
            self.run.request_parameters["start_date"], "%Y-%m-%d"
        )
        discovered_files_list = self.receipts_page.get_invoice_table_data(
            self.run, start_date, self.download_location
        )
        LOGGER.info(
            f"[tag:WEWVRD9] Total Invoices within date range and download link available: "
            f"{len(discovered_files_list)}"
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
            self.post_login_action()
            get_url(self.driver, "https://member.restaurantdepot.com/receipts")

            discovered_files += self._download_documents()
        finally:
            self._quit_driver()

        return discovered_files

    def login_flow(self, run: Run):
        self._login()
