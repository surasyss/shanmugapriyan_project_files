import os
from datetime import date, datetime
from typing import List
from retry.api import retry

from selenium.common.exceptions import (
    NoSuchElementException,
    TimeoutException,
    WebDriverException,
)
from selenium.webdriver.common.by import By
from selenium.webdriver.remote.webelement import WebElement
from spices.datetime_utils import date_from_string

from apps.adapters.base import VendorDocumentDownloadInterface, PasswordBasedLoginPage
from apps.adapters.framework import download
from apps.adapters.helpers.helper import sleep

from apps.adapters.helpers.webdriver_helper import (
    is_element_present,
    wait_for_element,
    wait_for_loaders,
    hover_over_element,
    get_url,
)
from apps.adapters.vendors import LOGGER
from apps.runs.models import Run, DiscoveredFile, DocumentType, FileFormat

# Home Page Locators
HOME_PAGE_LOCATORS = {
    "LOADER": "div.css-0, div.knexai",
    "LOCATION_BAR_DROPDOWN": 'div[id="location-bar"] div.toscana-row div.toscana-cell',
    "LOCATION_DROPDOWN_OPTIONS": "div.ReactVirtualized__Table div.search-table-grid div.ReactVirtualized__Table__row",
    "LOCATION_DROPDOWN_ARROW": 'div[id="location-bar"] div.toscana-row div.toscana-cell.sc-ugnQR.gYIPPx',
}

# Invoices Page Locators
INVOICE_PAGE_LOCATORS = {
    "LOCATION_BAR_DROPDOWN": 'div[id="location-bar"] div.toscana-row div.toscana-cell',
    "LOCATION_DROPDOWN_OPTIONS": "div.ReactVirtualized__Table div.search-table-grid div.ReactVirtualized__Table__row",
    "LOCATION_SEARCH_TEXTBOX": 'input[placeholder="Search Bill-To Name or Number"]',
    "INVOICE_TABLE_ROWS": "div.ReactVirtualized__Table div.reports-table-grid div.ReactVirtualized__Table__row",
    "INVOICE_LOADER": "div.sc-cIShpX.knexai div.css-1d8ny0s",
    "HEADER_INVOICE_DATE": '//div[@aria-label="Invoice Date"]',
}

# Invoice Details Page Locators
INVOICE_DETAIL_PAGE_LOCATORS = {
    "INVOICE_DETAILS_EXPORT_LINK": '//a[text()="Export"]',
    "INVOICE_DETAIL_LOADER": "div.css-0",
}


class SyscoAccountCenterLoginPage(PasswordBasedLoginPage):
    SELECTOR_USERNAME_TEXTBOX = 'input[id="userName"]'
    SELECTOR_PASSWORD_TEXTBOX = 'input[id="userPassword"]'
    SELECTOR_LOGIN_BUTTON = 'button[id="login-action-button"]'
    SELECTOR_ERROR_MESSAGE_TEXT = "div.aFfFL p"

    def login(self, username: str, password: str):  # pylint: disable=arguments-differ
        wait_for_element(
            self.driver, value=self.SELECTOR_USERNAME_TEXTBOX, msg="Username textbox"
        )

        site_page = self.__class__.__name__
        masked_username = username[:3] + "x" * (len(username) - 3)
        masked_password = password[:1] + "x" * (len(password) - 1)
        LOGGER.info(
            f"Attempting login into {site_page} with username: {masked_username}, password: {masked_password}"
        )

        LOGGER.info("Clearing username text box")
        self.get_user_name_textbox().clear()

        LOGGER.info(f"Typing {masked_username} in username textbox.")
        self.get_user_name_textbox().send_keys(username)

        LOGGER.info("Clicking on Next button")
        self._perform_login(username)

        wait_for_element(
            self.driver, value=self.SELECTOR_PASSWORD_TEXTBOX, msg="Password textbox"
        )
        LOGGER.info("Clearing password text box")
        self.get_password_textbox().clear()

        LOGGER.info(f"Typing {masked_password} in password textbox.")
        self.get_password_textbox().send_keys(password)

        LOGGER.info("Clicking and Checking on Login button")
        self._perform_login(username)


class SyscoAccountCenterHomePage:
    """Sysco Account Center Home page action methods come here."""

    def __init__(self, driver):
        self.driver = driver

    def get_location_bar_dropdown(self) -> WebElement:
        return self.driver.find_elements_by_css_selector(
            HOME_PAGE_LOCATORS["LOCATION_BAR_DROPDOWN"]
        )[1]

    def get_location_dropdown_options(self) -> List[WebElement]:
        return self.driver.find_elements_by_css_selector(
            HOME_PAGE_LOCATORS["LOCATION_DROPDOWN_OPTIONS"]
        )

    def get_location_bar_dropdown_arrow(self) -> WebElement:
        return self.driver.find_element_by_css_selector(
            HOME_PAGE_LOCATORS["LOCATION_DROPDOWN_ARROW"]
        )

    def get_loader(self) -> WebElement:
        return self.driver.find_element_by_css_selector(HOME_PAGE_LOCATORS["LOADER"])

    def have_single_location(self) -> bool:
        """Returns True if only 1 account found else False"""
        try:
            self.get_location_bar_dropdown_arrow()
            return False
        except (NoSuchElementException, TimeoutException):
            LOGGER.info(f"Contains only 1 account.")
            return True

    def get_locations(self) -> list:
        """
        Return a list of all the Locations available
        :return: Returns all Locations list
        """
        for index in range(3):
            try:
                wait_for_element(
                    self.driver,
                    value=f"{HOME_PAGE_LOCATORS['LOCATION_BAR_DROPDOWN']}:nth-child(1)",
                    msg="Location-Bar dropdown",
                )
                break
            except WebDriverException as excep:
                LOGGER.warning(f"{excep} found in {self.driver.current_url}")
                get_url(
                    self.driver,
                    "https://sysco.accountcenter.com/customer/payment/manual",
                )
                wait_for_loaders(
                    self.driver, value=HOME_PAGE_LOCATORS["LOADER"], timeout=10
                )

                if index == 2:
                    raise

        location_list = []
        if self.have_single_location():
            location = self.get_location_bar_dropdown().text
            location_list.append(location.replace("|", " \n"))
        else:
            self.get_location_bar_dropdown().click()
            # Fetching 1st drop down option
            wait_for_element(
                self.driver,
                value=f"{HOME_PAGE_LOCATORS['LOCATION_DROPDOWN_OPTIONS']}",
                msg="Location-Bar dropdown options",
            )
            aria_rowindices = []
            while True:
                dropdown_options = self.get_location_dropdown_options()
                if dropdown_options:
                    last_option_rowindex = dropdown_options[-1].get_attribute(
                        "aria-rowindex"
                    )
                    for location in dropdown_options:
                        if last_option_rowindex in aria_rowindices:
                            return location_list

                        rowindex = location.get_attribute("aria-rowindex")
                        if rowindex not in aria_rowindices:
                            aria_rowindices.append(rowindex)
                            location_list.append(location.text)
                    hover_over_element(self.driver, dropdown_options[-1])
        return location_list


class SyscoAccountCenterInvoicesPage:
    """Sysco Account Center Invoices page action methods come here."""

    def __init__(self, driver, start_day, start_month):
        self.driver = driver
        self.start_day = start_day
        self.start_month = start_month
        self.vendor = "Sysco"
        self.invoice_details_page = SyscoAccountCenterInvoicesDetailsPage(self.driver)

    def get_location_bar_dropdown(self) -> WebElement:
        return self.driver.find_elements_by_css_selector(
            INVOICE_PAGE_LOCATORS["LOCATION_BAR_DROPDOWN"]
        )[1]

    def get_location_dropdown_options(self) -> List[WebElement]:
        return self.driver.find_elements_by_css_selector(
            INVOICE_PAGE_LOCATORS["LOCATION_DROPDOWN_OPTIONS"]
        )

    def get_location_search_textbox(self) -> WebElement:
        return self.driver.find_element_by_css_selector(
            INVOICE_PAGE_LOCATORS["LOCATION_SEARCH_TEXTBOX"]
        )

    def get_loader(self) -> WebElement:
        return self.driver.find_element_by_css_selector(
            INVOICE_PAGE_LOCATORS["INVOICE_LOADER"]
        )

    def get_header_invoice_date(self) -> WebElement:
        return self.driver.find_element_by_xpath(
            INVOICE_PAGE_LOCATORS["HEADER_INVOICE_DATE"]
        )

    def goto_invoice_page(self):
        get_url(self.driver, "https://sysco.accountcenter.com/customer/reports/invoice")
        wait_for_loaders(self.driver, value=HOME_PAGE_LOCATORS["LOADER"], timeout=10)

    def select_date_range(self):
        date_text = self.driver.find_element_by_css_selector(
            ".toscana-container > div:nth-child(2) > "
            "div:nth-child(1) > div:nth-child(2) > "
            "div:nth-child(1) > div:nth-child(2) > "
            "span:nth-child(1)"
        ).text
        search_date = date_from_string(date_text, "%m/%d/%Y")
        if str(search_date.month) != self.start_month:

            self.driver.find_element_by_css_selector(
                ".toscana-container > div:nth-child(2) > div:nth-child(1) > "
                "div:nth-child(2) > div:nth-child(1)"
            ).click()
            self.driver.find_element_by_css_selector(
                'button[class="DayPickerNavigation__prev"]'
            ).click()
            sleep(2)
            calendar_rows = self.driver.find_elements_by_css_selector(
                "div.CalendarMonth:nth-child(2) > " "table:nth-child(2) > tbody > tr"
            )
            for row in calendar_rows:
                columns = row.find_elements_by_tag_name("td")
                for col in columns:
                    if col.text == self.start_day:
                        col.find_element_by_tag_name("button").click()
                        break
            self.driver.find_element_by_css_selector("button.ripple").click()
            wait_for_loaders(
                self.driver, value=HOME_PAGE_LOCATORS["LOADER"], timeout=10
            )

    def select_location_by_account_id(self, account_id: str):
        wait_for_element(
            self.driver,
            value=f"{INVOICE_PAGE_LOCATORS['LOCATION_BAR_DROPDOWN']}:nth-child(1)",
            msg="Location-Bar dropdown",
        )
        selected_dropdown_option = self.get_location_bar_dropdown()
        selected_dropdown_option.click()
        wait_for_element(
            self.driver,
            value=INVOICE_PAGE_LOCATORS["LOCATION_SEARCH_TEXTBOX"],
            msg="LocationBar Search Textbox",
        )
        if selected_dropdown_option.text.split(" | ")[-1] != account_id:
            self.get_location_search_textbox().clear()
            self.get_location_search_textbox().send_keys(account_id)
            self.get_location_dropdown_options()[0].click()
        else:
            self.get_location_bar_dropdown().click()
        wait_for_loaders(self.driver, value=HOME_PAGE_LOCATORS["LOADER"], timeout=10)

    def get_invoices_table_rows(self) -> List[WebElement]:
        """Returns Invoices Table Rows WebElement"""
        return self.driver.find_elements_by_css_selector(
            INVOICE_PAGE_LOCATORS["INVOICE_TABLE_ROWS"]
        )

    def sort_invoice_date_by_descending(self):
        for index in range(5):
            try:
                wait_for_element(
                    self.driver,
                    value=INVOICE_PAGE_LOCATORS["INVOICE_TABLE_ROWS"],
                    timeout=10,
                    msg="Table Rows",
                )
                self.get_header_invoice_date().click()
                self.get_header_invoice_date().click()
                break
            except WebDriverException as excep:
                LOGGER.info(
                    f"Caught exception {excep} in the page {self.driver.current_url}"
                )
                self.goto_invoice_page()
                if index == 4:
                    raise

    def get_invoice_table_data(
        self,
        run: Run,
        from_date: date,
        account_name: str,
        customer_id: str,
        download_location: str,
    ) -> List[DiscoveredFile]:
        """
        Extracts invoice details from Table
        :param run: Run Object
        :param from_date: Start date of the invoices to be downloaded
        :param account_name: Account Name
        :param customer_id: Account Id
        :param download_location: directory for downloading files
        :return: Returns the list of Discovered Files
        """
        LOGGER.info("Extracting Invoice table data.")

        discovered_files = []
        csv_links_list = []
        collected_invoices = []

        rows = self.get_invoices_table_rows()
        LOGGER.info(f"Total invoice rows found: {len(rows)}")

        if not rows:
            LOGGER.info("No invoices found.")
            return discovered_files

        self.sort_invoice_date_by_descending()

        for index, _ in enumerate(rows):

            if index > 0:
                self.sort_invoice_date_by_descending()

            for _ in range(5):
                rows = self.get_invoices_table_rows()
                if rows and index < len(rows):
                    break
                wait_for_element(
                    self.driver,
                    value=INVOICE_PAGE_LOCATORS["INVOICE_TABLE_ROWS"],
                    timeout=10,
                    msg="Table Rows",
                )

            row = rows[index]

            if "Original Amount Total" in row.text:
                continue

            row_cells = row.text.split("\n")
            invoice_date = date_from_string(row_cells[3], "%m/%d/%y")

            if invoice_date < from_date:
                LOGGER.info(
                    f"Skipping remaining invoices because date '{invoice_date}' is outside requested range"
                )
                return discovered_files

            invoice_number_element = row.find_element_by_tag_name("a")
            if not is_element_present(self.driver, invoice_number_element):
                continue

            invoice_detail_page_url = invoice_number_element.get_attribute("href")
            this_invoice = (customer_id, row_cells[2], invoice_date, row_cells[5])
            reference_code = (
                f'{customer_id}_{row_cells[2]}_{invoice_detail_page_url.split("/")[5]}'
            )

            # Added this check since there are repeated invoices present
            if this_invoice in collected_invoices:
                LOGGER.info(
                    f"Skipping file because invoice '{this_invoice}' was already seen in this run"
                )
                continue

            if invoice_detail_page_url in csv_links_list:
                LOGGER.info(
                    f"Skipping file because url '{invoice_detail_page_url}' was already seen in this run"
                )
                continue

            collected_invoices.append(this_invoice)
            csv_links_list.append(invoice_detail_page_url)

            document_properties = {
                "invoice_number": row_cells[2],
                "invoice_date": str(invoice_date),
                "due_date": str(date_from_string(row_cells[4], "%m/%d/%y")),
                "total_amount": row_cells[5],
                "vendor_name": self.vendor,
                "restaurant_name": account_name,
                "customer_number": customer_id,
            }
            try:
                # pylint: disable=no-member
                discovered_file = DiscoveredFile.build_unique(
                    run,
                    reference_code,
                    document_type=DocumentType.INVOICE.ident,
                    file_format=FileFormat.CSV.ident,
                    original_download_url=invoice_detail_page_url,
                    original_filename=f"{reference_code}.csv",
                    document_properties=document_properties,
                )
            except DiscoveredFile.AlreadyExists:
                LOGGER.info(
                    f"Discovered file already exists with reference code : {reference_code}"
                )
                continue  # skip if seen before

            self.download_document_by_link(download_location, discovered_file, row)
            discovered_files.append(discovered_file)
            LOGGER.info(
                "Invoice details row data: %s", str(discovered_file.document_properties)
            )

        return discovered_files

    def download_document_by_link(
        self, download_location: str, discovered_file: DiscoveredFile, row: WebElement
    ):
        """
        Downloads the invoice & renames it with the actual invoice Number
        Retries the downloading 3 times in case of exceptions
        :param download_location: directory for downloading files
        :param discovered_file: Discovered file object
        :param row: invoice row element
        :return: Nothing
        """
        row.find_element_by_tag_name("a").click()
        LOGGER.info(
            f"Navigating to the {discovered_file.document_properties['invoice_number']} invoice detail page..."
        )
        wait_for_loaders(self.driver, value=HOME_PAGE_LOCATORS["LOADER"])

        if self.invoice_details_page.is_export_link_present():
            csv_webelement = self.invoice_details_page.get_export_link()
            csv_link = csv_webelement.get_attribute("href")
            discovered_file.original_filename = csv_webelement.get_attribute("download")
            LOGGER.info(f"Downloading Invoice: {csv_link}")

            _downloader = download.WebElementClickBasedDownloader(
                element=self.invoice_details_page.get_export_link(),
                local_filepath=os.path.join(
                    download_location, discovered_file.original_filename
                ),
                file_exists_check_kwargs=dict(timeout=20),
            )
            download.download_discovered_file(discovered_file, _downloader)

        self.goto_invoice_page()


class SyscoAccountCenterInvoicesDetailsPage:
    """Sysco Account Center invoice details page action methods come here."""

    def __init__(self, driver):
        self.driver = driver

    def get_export_link(self) -> WebElement:
        """Returns Invoices Save Link WebElement"""
        return self.driver.find_element_by_xpath(
            INVOICE_DETAIL_PAGE_LOCATORS["INVOICE_DETAILS_EXPORT_LINK"]
        )

    def is_export_link_present(self) -> bool:
        try:
            wait_for_element(
                self.driver,
                by_selector=By.XPATH,
                retry_attempts=1,
                value=INVOICE_DETAIL_PAGE_LOCATORS["INVOICE_DETAILS_EXPORT_LINK"],
                msg="Export link",
            )
            return True
        except WebDriverException:
            LOGGER.info(f"Export link not found!")
            return False


class SyscoAccountCenterRunner(VendorDocumentDownloadInterface):
    """Runner Class for Sysco Accounter Center"""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.start_day, self.start_month = self.get_start_day()
        self.login_page = SyscoAccountCenterLoginPage(self.driver)
        self.home_page = SyscoAccountCenterHomePage(self.driver)
        self.invoices_page = SyscoAccountCenterInvoicesPage(
            self.driver, self.start_day, self.start_month
        )

    def get_start_day(self):
        start_date = datetime.strptime(
            self.run.request_parameters["start_date"], "%Y-%m-%d"
        ).date()
        start_day = str(start_date.day)
        start_month = str(start_date.month)
        if str(start_day).startswith("0"):
            start_day = str(start_day).replace("0", "")
        return start_day, start_month

    @retry(WebDriverException, tries=3, delay=2)
    def _login(self):
        """
        Login to Sysco Account Center
        :return: Nothing
        """
        login_url = "https://www.syscoaccountcenter.com/ngs/s/NGS_A_Login"
        LOGGER.info(f"Navigating to: {login_url}")
        self.driver.get(login_url)
        self.login_page.login(self.run.job.username, self.run.job.password)
        wait_for_loaders(self.driver, value=HOME_PAGE_LOCATORS["LOADER"], timeout=10)

    def _goto_download_page(self, document_type: str):
        """
        Go to Download page
        :param document_type: Specify the document type eg. Invoice/Statement etc.
        :return: Nothing
        """
        if document_type == "invoice":
            self.invoices_page.goto_invoice_page()
        else:
            raise NotImplementedError(
                f"Requested Document Type is not supported: {document_type}"
            )

    def _download_documents(
        self, account_name: str, customer_id: str
    ) -> List[DiscoveredFile]:
        """
        Chooses the documents to be downloaded based on the document type
        :param account_name: Account Name
        :param customer_id: Account Id
        :return: Returns the list of Discovered Files
        """
        document_type = self.run.job.requested_document_type
        if document_type == "invoice":
            return self._download_invoices(account_name, customer_id)

        raise NotImplementedError(
            f"Requested Document Type is not supported: {document_type}"
        )

    def _download_invoices(
        self, account_name: str, customer_id: str
    ) -> List[DiscoveredFile]:
        """
        Downloads the Invoices
        :param account_name: Account Name
        :param customer_id: Account Id
        :return: Returns the list of the Discovered Files
        """
        LOGGER.info("Download invoice process begins.")

        start_date = datetime.strptime(
            self.run.request_parameters["start_date"], "%Y-%m-%d"
        ).date()
        # Fetching all invoice table date & storing it in memory
        discovered_files_list = self.invoices_page.get_invoice_table_data(
            self.run, start_date, account_name, customer_id, self.download_location
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

            locations = self.home_page.get_locations()
            LOGGER.info(f"Total accounts found: {len(locations)}")
            for location in locations:
                location_name = location.split("\n")[-2].strip()
                account_id = location.split("\n")[-1].strip()

                LOGGER.info(
                    f"Selecting {location_name} | {account_id} from the dropdown."
                )
                self._goto_download_page(self.run.job.requested_document_type)

                if len(locations) > 1:
                    self.invoices_page.select_location_by_account_id(account_id)
                self.invoices_page.select_date_range()

                discovered_files += self._download_documents(location_name, account_id)
        finally:
            self._quit_driver()

        return discovered_files

    def login_flow(self, run: Run):
        self._login()
