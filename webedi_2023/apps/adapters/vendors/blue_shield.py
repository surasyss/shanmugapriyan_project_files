import os
from datetime import date, datetime
from typing import List

from retry import retry
from selenium.common.exceptions import WebDriverException
from selenium.webdriver.remote.webelement import WebElement

from apps.adapters.base import VendorDocumentDownloadInterface, PasswordBasedLoginPage
from apps.adapters.framework import download
from apps.adapters.helpers.helper import sleep
from apps.adapters.helpers.webdriver_helper import (
    explicit_wait_till_visibility,
    select_dropdown_option_by_value,
)
from apps.adapters.vendors import LOGGER
from apps.runs.models import Run, DiscoveredFile, DocumentType, FileFormat
from spices.datetime_utils import date_from_string

# Home Page Locators
HOME_PAGE_LOCATORS = {"HOME_INVOICES_LINK": 'li[id="odbills"]>a'}

# Invoices Page Locators
INVOICE_PAGE_LOCATORS = {
    "INVOICES_DATE_FILTER_DROPDOWN": 'select[name="resultTable_length"]',
    "INVOICES_DATE_FILTER_DROPDOWN_OPTIONS": 'select[name="resultTable_length"]/option',
    "INVOICE_TABLE_ROWS": 'table[id="resultTable"]>tbody>tr',
}

# Invoice Details Page Locators
INVOICE_DETAILS_PAGE_LOCATORS = {
    "INVOICE_DETAILS_REPORT_CONTENT": 'div[id="content"]',
    "INVOICE_DETAILS_SAVE_LINK": 'div[id="content"]>embed',
    "INVOICE_DETAILS_SAVE_AS_PDF": 'cr-icon-button[id="download"]',
    "INVOICE_DETAILS_SAVE_AS_EXCEL": '//a[@alt="Excel"]',
}

VIEW_PRINT_PAGE_LOCATORS = {
    "GROUP_ID_LOC": 'select[name="groupId"]',
    "GROUP_IDS": 'select[name="groupId"] option',
    "DUE_DATE_START_MONTH": 'select[id="dueDate_month"]',
    "DUE_DATE_START_YEAR": 'select[id="dueDate_year"]',
    "DUE_DATE_END_MONTH": 'select[id="dueDate_secondary_month"]',
    "DUE_DATE_END_YEAR": 'select[id="dueDate_secondary_year"]',
    "SEARCH_BUTTON_LOC": 'input[onclick="displayResults(this.form);"]',
}


class BlueShieldLoginPage(PasswordBasedLoginPage):
    SELECTOR_USERNAME_TEXTBOX = 'input[id="username"]'
    SELECTOR_PASSWORD_TEXTBOX = 'input[id="password"]'
    SELECTOR_LOGIN_BUTTON = 'button[onclick="return postOk();"]'
    SELECTOR_ERROR_MESSAGE_TEXT = "div.warning div.error"


class BlueShieldHomePage:
    """Blue Shield Home page action methods come here."""

    def __init__(self, driver):
        self.driver = driver
        self.blue_shield_bill_page = BlueShieldViewPrintPage(self.driver)

    def get_invoices_link(self) -> WebElement:
        """Returns Invoices Link WebElement"""
        return self.driver.find_element_by_css_selector(
            HOME_PAGE_LOCATORS["HOME_INVOICES_LINK"]
        )

    def navigate_to_view_print_bill_page(self):
        """Navigates to the View/Print Bill Page"""
        view_bill_page_url = (
            "https://employers.bcbst.com/secure/restricted/apps/BlueAccessDocumentSearch/search/"
            "displaySearchCriteria.do?searchApp=ODBills"
        )
        LOGGER.info(f"Navigating to {view_bill_page_url}")
        self.driver.get(view_bill_page_url)
        explicit_wait_till_visibility(
            self.driver,
            self.blue_shield_bill_page.get_search_button_link(),
            msg="Wait for Search button",
        )


class BlueShieldViewPrintPage:
    def __init__(self, driver):
        self.driver = driver

    def get_group_id_link(self) -> WebElement:
        """Returns the Web Element for Group Id Select link"""
        return self.driver.find_element_by_css_selector(
            VIEW_PRINT_PAGE_LOCATORS["GROUP_ID_LOC"]
        )

    def get_group_ids(self) -> List[WebElement]:
        """Returns the Web Elements of the select group id options"""
        return self.driver.find_elements_by_css_selector(
            VIEW_PRINT_PAGE_LOCATORS["GROUP_IDS"]
        )

    def get_search_button_link(self) -> WebElement:
        """Return the Web Element for the Search button"""
        return self.driver.find_element_by_css_selector(
            VIEW_PRINT_PAGE_LOCATORS["SEARCH_BUTTON_LOC"]
        )

    def group_id_select_by_value(self, group_id):
        """Select group id based on the group id value"""
        options = self.get_group_ids()
        for option in options:
            if group_id == option.get_attribute("value"):
                select_dropdown_option_by_value(
                    self.get_group_id_link(), option.get_attribute("value")
                )


class BlueShieldInvoicesPage:
    """Blue shield Invoices page action methods come here."""

    def __init__(self, driver, download_location):
        self.driver = driver
        self.download_location = download_location
        self.invoice_details_page = BlueShieldInvoiceDetailsPage(self.driver)

    @staticmethod
    def get_vendor_name() -> str:
        """Returns Vendor Name"""
        return "Blue Shield"

    def get_invoices_date_filter_dropdown(self) -> WebElement:
        """Returns Invoices Date Filter DropDown WebElement"""
        return self.driver.find_element_by_css_selector(
            INVOICE_PAGE_LOCATORS["INVOICES_DATE_FILTER_DROPDOWN"]
        )

    def get_invoices_table_rows(self):
        """Returns Invoices Table Rows WebElement"""
        return self.driver.find_elements_by_css_selector(
            INVOICE_PAGE_LOCATORS["INVOICE_TABLE_ROWS"]
        )

    def get_invoice_table_data(self, run: Run, from_date: date) -> List[DiscoveredFile]:
        """
        Extracts invoice details from Table
        :param run: Run Object
        :param from_date: date Object
        :return: Returns the list of Discovered Files
        """
        sleep(1, "for invoice table to load.")
        explicit_wait_till_visibility(self.driver, self.get_invoices_table_rows()[1])
        LOGGER.info("Extracting Invoice table date.")

        discovered_files = []
        rows = self.get_invoices_table_rows()
        for row in rows[0:]:
            invoice_date = date_from_string(
                row.find_elements_by_tag_name("td")[3].text, "%m/%d/%Y"
            )
            if invoice_date < from_date:
                return discovered_files

            group_id = row.find_elements_by_tag_name("td")[0].text
            sub_group_id = row.find_elements_by_tag_name("td")[1].text
            due_date = date_from_string(
                row.find_elements_by_tag_name("td")[2].text, "%m/%d/%Y"
            )
            statement_number = row.find_elements_by_tag_name("td")[5].text
            pdf_link = row.find_elements_by_tag_name("a")[0].get_attribute("href")

            reference_code = f"{group_id}_{sub_group_id}_{statement_number}"

            document_properties = {
                "customer_number": f"{group_id}_{sub_group_id}",
                "invoice_number": statement_number,
                "group_id": group_id,
                "sub_group_id": sub_group_id,
                "invoice_date": f"{invoice_date}",
                "due_date": f"{due_date}",
                "vendor_name": self.get_vendor_name(),
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


class BlueShieldInvoiceDetailsPage:
    """Blue shield Print Invoices page action methods come here."""

    def __init__(self, driver):
        self.driver = driver

    @retry((FileNotFoundError, WebDriverException), tries=3, delay=2)
    def download_documents_by_link(
        self, download_location: str, discovered_files, username
    ):
        """
        Downloads the invoice & renames it with the actual invoice Number
        Retries the downloading 3 times in case of exceptions
        :param download_location:
        :param discovered_files: Discovered files
        :param username: Username
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
                    local_filepath=download_location,  # pass the download dir, since we're passing a pattern below
                    rename_to=os.path.join(
                        download_location, discovered_file.original_filename
                    ),
                    file_exists_check_kwargs=dict(
                        timeout=20, pattern=f"(.*)_{username.upper()}_(.*).pdf$"
                    ),
                )
                download.download_discovered_file(discovered_file, _downloader)

                # Every download file opens a new tab. Following code is closing the tabs after file download
                self.driver.switch_to.window(self.driver.window_handles[1])
                self.driver.close()
                self.driver.switch_to.window(self.driver.window_handles[0])
        except (FileNotFoundError, WebDriverException) as exc:
            LOGGER.error(str(exc), exc_info=True)
            raise


class BlueShieldRunner(VendorDocumentDownloadInterface):
    """Runner Class for Blue Shine Online"""

    # uses_proxy = True

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.login_page = BlueShieldLoginPage(self.driver)
        self.home_page = BlueShieldHomePage(self.driver)
        self.view_print_page = BlueShieldViewPrintPage(self.driver)
        self.invoices_page = BlueShieldInvoicesPage(self.driver, self.download_location)
        self.invoice_details_page = BlueShieldInvoiceDetailsPage(self.driver)

    def _login(self):
        """
        Login to Blue Shield
        :return: Nothing
        """
        login_url = "https://www.bcbst.com/log-in/employer/"
        LOGGER.info(f"Navigating to {login_url}")
        self.driver.get(login_url)
        self.login_page.login(self.run.job.username, self.run.job.password)
        explicit_wait_till_visibility(self.driver, self.home_page.get_invoices_link())

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

    def _get_table_rows_visible_select_value(self):
        options = list(
            self.invoices_page.get_invoices_date_filter_dropdown().find_elements_by_tag_name(
                "option"
            )
        )
        option_value = "10"
        for elem in options:
            option_value = elem.get_attribute("value")
        return option_value

    def _download_invoices(self) -> List[DiscoveredFile]:
        """
        Downloads the Invoices
        :return: Returns the list of the Discovered Files
        """
        explicit_wait_till_visibility(
            self.driver, self.invoices_page.get_invoices_date_filter_dropdown()
        )

        LOGGER.info("Download invoice process begins.")

        option = self._get_table_rows_visible_select_value()
        LOGGER.info(f"Selecting {option} option from the dropdown.")
        select_dropdown_option_by_value(
            self.invoices_page.get_invoices_date_filter_dropdown(), option
        )
        discovered_files_list = []
        start_date = datetime.strptime(
            self.run.request_parameters["start_date"], "%Y-%m-%d"
        ).date()
        # Fetching all invoice table date & storing it in memory
        discovered_files_list += self.invoices_page.get_invoice_table_data(
            self.run, start_date
        )

        # Downloading the invoice from the links
        self.invoice_details_page.download_documents_by_link(
            self.download_location, discovered_files_list, self.run.job.username
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
            self.home_page.navigate_to_view_print_bill_page()
            account_list = self.view_print_page.get_group_ids()
            for account in account_list:
                self.view_print_page.group_id_select_by_value(
                    account.get_attribute("value")
                )
                LOGGER.info("Clicking on view / print Page Search button.")
                self.view_print_page.get_search_button_link().click()
                explicit_wait_till_visibility(
                    self.driver, self.invoices_page.get_invoices_date_filter_dropdown()
                )
                discovered_files += self._download_documents()
        finally:
            self._quit_driver()

        return discovered_files

    def login_flow(self, run: Run):
        self._login()
