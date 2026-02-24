import os
import re
from datetime import date, datetime
from typing import List
from retry.api import retry

from selenium.common.exceptions import WebDriverException
from selenium.webdriver.common.by import By
from selenium.webdriver.remote.webelement import WebElement

from apps.adapters.base import VendorDocumentDownloadInterface, PasswordBasedLoginPage
from apps.adapters.framework import download
from apps.adapters.helpers.helper import sleep
from apps.adapters.helpers.webdriver_helper import (
    wait_for_element,
    get_url,
    set_implicit_timeout,
    execute_script_click,
    explicit_wait_till_clickable,
)
from apps.adapters.vendors import LOGGER
from apps.runs.models import Run, DiscoveredFile, DocumentType, FileFormat
from spices.datetime_utils import date_from_string

# Home Page Locators
HOME_PAGE_LOCATORS = {
    "LOCATION_TEXT": 'table[id$="pt_pglCustLoc"] .dropDownMenu-Container span',
    "LOCATION_DROPDOWN": 'table[id$="pt_pglCustLoc"] .dropDownMenu-Container tr',
    "LOCATION_DROPDOWN_MENU": 'table[id$="pt_pglCustLoc"] .dropDownMenu-Container div.dropDownMenu-UtilityMenu',
    "LOCATION_DROPDOWN_OPTIONS": 'table[id$="pt_pglCustLoc"] .dropDownMenu-Container div.dropDownMenu-UtilityMenu a.dceCustomerLink',
    "AGREE": "//button[contains(text(),'Agree')]",
    "REMIND_ME_LATER": "#cil3",
}

# Invoices Page Locators
INVOICE_PAGE_LOCATORS = {
    "LOCATION_TEXT": 'table[id$="pt_pglCustLoc"] .dropDownMenu-Container span',
    "LOCATION_DROPDOWN": 'table[id$="pt_pglCustLoc"] .dropDownMenu-Container',
    "ACCOUNT_NAME": 'table[id$="pt_pglCustLoc"] .dropDownMenu-Container a.dceCustomerLocation span',
    "LOCATION_DROPDOWN_MENU": 'table[id$="pt_pglCustLoc"] .dropDownMenu-Container div.dropDownMenu-UtilityMenu',
    "LOCATION_DROPDOWN_OPTIONS": 'table[id$="pt_pglCustLoc"] .dropDownMenu-Container div.dropDownMenu-UtilityMenu a.dceCustomerLink',
    "VIEW_INVOICES_LINK": '//a[text()="View Invoices"]',
    "INVOICE_FORMAT_DROPDOWN": "a.jqTransformSelectOpen",
    "INVOICE_FORMAT_DROPDOWN_OPTIONS": "div.jqTransformSelectWrapper li a",
    "DOWNLOAD_INVOICES_BUTTON": '//button[text()="Download Invoices"]',
    "INVOICE_TABLE_ROWS": "div.productsList.af_listView div.orderListViewItem.af_listItem",
    "LOAD_MORE_ITEMS": '//a[text()="Load More Items"]',
    "START_DATE": "input[id*='stDate']",
    "SEARCH_BUTTON": '//button[text()="Search"]',
}


class UsFoodsLoginPage(PasswordBasedLoginPage):
    SELECTOR_USERNAME_TEXTBOX = 'input[name="it9"]'
    SELECTOR_PASSWORD_TEXTBOX = 'input[name="it1"]'
    SELECTOR_LOGIN_BUTTON = 'button[id="cb1"]'
    SELECTOR_ERROR_MESSAGE_TEXT = "div span.dceAlertFieldTextBold13px"


class UsFoodsHomePage:
    """US Foods Home page action methods come here."""

    def __init__(self, driver):
        self.driver = driver

    def get_location(self) -> WebElement:
        return self.driver.find_element_by_css_selector(
            HOME_PAGE_LOCATORS["LOCATION_TEXT"]
        )

    def get_location_dropdown(self) -> WebElement:
        return self.driver.find_element_by_css_selector(
            HOME_PAGE_LOCATORS["LOCATION_DROPDOWN"]
        )

    def get_location_dropdown_options(self) -> [WebElement]:
        return self.driver.find_elements_by_css_selector(
            HOME_PAGE_LOCATORS["LOCATION_DROPDOWN_OPTIONS"]
        )

    def _has_single_account(self):
        try:
            set_implicit_timeout(self.driver, 5)
            wait_for_element(
                self.driver,
                value='table[id$="pt_pglCustLoc"] .dropDownMenu-Container.dceSearchContainer',
                msg="Location text",
                timeout=10,
                retry_attempts=1,
            )
            LOGGER.info(f"Found multiple accounts.")
            return None
        except WebDriverException:
            location = self.get_location().text
            LOGGER.info(f"Found single account: {location}")
            return location
        finally:
            set_implicit_timeout(self.driver, 15)

    def _has_department(self) -> bool:
        location = self.get_location_dropdown().text
        if len(location.split("(")) > 2:
            LOGGER.info(f"Found departments: {location}")
            return True

        LOGGER.info(f"Found no Departments")
        return False

    def _get_multiple_locations(self) -> []:
        self.get_location_dropdown().click()
        wait_for_element(
            self.driver,
            value=HOME_PAGE_LOCATORS["LOCATION_DROPDOWN_MENU"],
            msg="Location dropdown Menu",
        )
        location_list = []
        for _index, location in enumerate(self.get_location_dropdown_options()):
            if location.text != "":
                location_list.append({"index": _index, "location_text": location.text})
        return location_list

    def get_locations(self) -> list:
        for index in range(3):
            try:
                wait_for_element(
                    self.driver,
                    value=INVOICE_PAGE_LOCATORS["LOCATION_DROPDOWN"],
                    msg="Account Locations",
                    retry_attempts=3,
                )
                break
            except WebDriverException as excep:
                LOGGER.warning(f"{excep} found in {self.driver.current_url}")
                if index == 2:
                    raise
                domain = self.driver.current_url.split(".com")[0]
                get_url(
                    self.driver,
                    f"{domain}.com/order/faces/oracle/webcenter/portalapp/pages/invoice/invoiceInquiry.jspx",
                )

        # For Single Location
        location = self._has_single_account()
        if location:
            return [location]

        # For multiple locations without departments
        return self._get_multiple_locations()


class UsFoodsInvoicesPage:
    """US Foods Invoices page action methods come here."""

    def __init__(self, driver):
        self.driver = driver
        self.vendor_name = "US Foods"
        self.reference_code_list = []

    def get_download_invoices_link(self) -> WebElement:
        return self.driver.find_element_by_xpath(
            INVOICE_PAGE_LOCATORS["DOWNLOAD_INVOICES_BUTTON"]
        )

    def get_invoice_format_dropdown(self) -> WebElement:
        return self.driver.find_element_by_css_selector(
            INVOICE_PAGE_LOCATORS["INVOICE_FORMAT_DROPDOWN"]
        )

    def get_invoice_format_dropdown_options(self) -> List[WebElement]:
        return self.driver.find_elements_by_css_selector(
            INVOICE_PAGE_LOCATORS["INVOICE_FORMAT_DROPDOWN_OPTIONS"]
        )

    def get_download_invoices_button(self) -> WebElement:
        return self.driver.find_element_by_xpath(
            INVOICE_PAGE_LOCATORS["DOWNLOAD_INVOICES_BUTTON"]
        )

    def get_invoice_table_rows(self) -> List[WebElement]:
        return self.driver.find_elements_by_css_selector(
            INVOICE_PAGE_LOCATORS["INVOICE_TABLE_ROWS"]
        )

    def get_location_dropdown(self) -> WebElement:
        return self.driver.find_element_by_css_selector(
            INVOICE_PAGE_LOCATORS["LOCATION_DROPDOWN"]
        )

    def get_nth_location_dropdown_options(self, index: int) -> WebElement:
        return self.driver.find_elements_by_css_selector(
            HOME_PAGE_LOCATORS["LOCATION_DROPDOWN_OPTIONS"]
        )[index]

    def get_start_date(self) -> WebElement:
        return self.driver.find_element_by_css_selector(
            INVOICE_PAGE_LOCATORS["START_DATE"]
        )

    def get_search_button(self) -> WebElement:
        return self.driver.find_element_by_xpath(INVOICE_PAGE_LOCATORS["SEARCH_BUTTON"])

    def get_load_more_items_link(self):
        return self.driver.find_element_by_xpath(
            INVOICE_PAGE_LOCATORS["LOAD_MORE_ITEMS"]
        )

    def load_more(self):
        try:
            execute_script_click(self.driver, self.get_load_more_items_link())
            sleep(1, msg="Load More link")
            wait_for_element(
                self.driver,
                by_selector=By.XPATH,
                value=INVOICE_PAGE_LOCATORS["LOAD_MORE_ITEMS"],
                retry_attempts=1,
                msg="Load More link",
            )
            LOGGER.info(f"Clicking on Load More link")
            self.load_more()
        except WebDriverException:
            LOGGER.info(f"All invoices are loaded now.")

    def goto_invoice_page(self):
        domain = self.driver.current_url.split(".com")[0]
        get_url(
            self.driver,
            f"{domain}.com/order/faces/oracle/webcenter/portalapp/pages/invoice/invoiceInquiry.jspx",
        )
        wait_for_element(
            self.driver,
            by_selector=By.XPATH,
            value=INVOICE_PAGE_LOCATORS["DOWNLOAD_INVOICES_BUTTON"],
            msg="Download Invoices Link",
            raise_exception=False,
            retry_attempts=3,
        )

    def select_location_by_index(self, index: int):
        wait_for_element(
            self.driver,
            value=INVOICE_PAGE_LOCATORS["LOCATION_DROPDOWN"],
            msg="Location dropdown",
        )
        self.get_location_dropdown().click()
        wait_for_element(
            self.driver,
            value=INVOICE_PAGE_LOCATORS["LOCATION_DROPDOWN_MENU"],
            msg="Location dropdown Opts",
        )
        execute_script_click(self.driver, self.get_nth_location_dropdown_options(index))
        sleep(5)

    def select_invoice_format(self, text: str):
        wait_for_element(
            self.driver,
            value=INVOICE_PAGE_LOCATORS["INVOICE_FORMAT_DROPDOWN"],
            msg="Invoice Format dropdown",
        )
        execute_script_click(self.driver, self.get_invoice_format_dropdown())
        sleep(2)
        wait_for_element(
            self.driver,
            value=INVOICE_PAGE_LOCATORS["INVOICE_FORMAT_DROPDOWN_OPTIONS"],
            msg="Invoice Format dropdown options",
        )
        invoice_formats = self.get_invoice_format_dropdown_options()
        for invoice_format in invoice_formats:
            if invoice_format.text.lower() == text.lower():
                LOGGER.info(f'Selecting "{text}" from Invoice format dropdown')
                execute_script_click(self.driver, invoice_format)
                sleep(1)
                break

    def select_nth_checkbox(self, index: int):
        for _ in range(5):
            try:
                set_implicit_timeout(self.driver, timeout=5)
                table_rows = self.get_invoice_table_rows()
                if index < len(table_rows):
                    invoice_checkbox = table_rows[index].find_element_by_css_selector(
                        "table.af_selectBooleanCheckbox a.jqTransformCheckbox"
                    )
                    execute_script_click(self.driver, invoice_checkbox)
                    self.get_invoice_table_rows()[index].find_element_by_css_selector(
                        "table.af_selectBooleanCheckbox a.jqTransformCheckbox.jqTransformChecked"
                    )
                    LOGGER.info(f"Invoice row {index} checkbox selected.")
                    break
            except WebDriverException:
                LOGGER.warning(f"Invoice row was not selected. Trying again...")
            finally:
                set_implicit_timeout(self.driver, timeout=15)

    def get_selected_location(self):
        return self.driver.find_element_by_css_selector(
            INVOICE_PAGE_LOCATORS["ACCOUNT_NAME"]
        )

    def _get_account_name_customer_id(self):
        try:
            location = self.get_selected_location().text
        except WebDriverException:
            LOGGER.info(f"It has single account ")
            location = self.driver.find_element_by_css_selector(
                INVOICE_PAGE_LOCATORS["LOCATION_TEXT"]
            ).text

        account_name = location.split("(")[0].strip()
        customer_id = re.search(r"\(([0-9]{4,})\)", location).group(1)
        return account_name, customer_id

    def select_start_end_date(self, from_date: date):
        start_date_in_box = self.get_start_date().get_attribute("value")
        start_date = date_from_string(start_date_in_box, "%m/%d/%Y")
        if start_date > from_date:
            self.get_start_date().clear()
            sleep(1, msg="wait for start date element")
            explicit_wait_till_clickable(
                self.driver,
                (By.CSS_SELECTOR, "input[id*='stDate']"),
                timeout=10,
                msg="Start Date Input Box",
            )
            LOGGER.info(f"Typing {from_date} in start date input box.")
            self.get_start_date().send_keys(from_date.strftime("%m/%d/%Y"))
            self.get_search_button().click()
            explicit_wait_till_clickable(
                self.driver,
                locator=(By.XPATH, INVOICE_PAGE_LOCATORS["SEARCH_BUTTON"]),
                msg="Search button",
            )

    def get_invoice_table_data(self, run: Run, from_date: date):
        """
        Extracts invoice details from Table
        :param run: Run Object
        :param from_date: Start date of the invoices to be downloaded
        :return: Returns the list of Discovered Files
        """
        LOGGER.info("Extracting Invoice table data.")

        discovered_files = []
        invoice_row_index = []

        self.select_start_end_date(from_date)

        if len(self.get_invoice_table_rows()) < 1:
            LOGGER.info("Invoice table found empty.")
            return discovered_files, invoice_row_index

        self.load_more()
        account_name, customer_id = self._get_account_name_customer_id()

        for index, row in enumerate(self.get_invoice_table_rows()):
            row_cell_elements = row.find_elements_by_css_selector(
                "td table.af_panelGroupLayout"
            )
            row_values = [cell.text for cell in row_cell_elements]

            invoice_date_cell = row_values[1]
            invoice_date = date_from_string(invoice_date_cell, "%m/%d/%Y")

            if invoice_date < from_date:
                LOGGER.info(
                    f"Skipping remaining invoices because date '{invoice_date}' is outside requested range"
                )
                return discovered_files, invoice_row_index

            invoice_number = row_values[3]
            reference_code = f"{customer_id}_{invoice_number}"
            document_type = row_values[2]

            # Adding this special check since US Foods is listing same invoice under different departments
            if reference_code in self.reference_code_list:
                LOGGER.info(
                    f"Skipping invoice because reference code '{reference_code}' already seen in this run."
                )
                continue

            if document_type.lower() not in [
                "invoice",
                "will call invoice",
                "vendor ship",
                "chef store",
            ]:
                continue

            try:
                # pylint: disable=no-member
                discovered_file = DiscoveredFile.build_unique(
                    run,
                    reference_code,
                    document_type=DocumentType.INVOICE.ident,
                    file_format=FileFormat.XML.ident,
                    original_download_url="",
                    original_filename=f"{reference_code}.xml",
                    document_properties={
                        "invoice_number": invoice_number,
                        "invoice_date": str(invoice_date),
                        "total_amount": row_values[5],
                        "vendor_name": self.vendor_name,
                        "restaurant_name": account_name,
                        "customer_number": customer_id,
                    },
                )
            except DiscoveredFile.AlreadyExists:
                LOGGER.info(
                    f"Discovered file already exists with reference code : {reference_code}"
                )
                continue  # skip if seen before
            discovered_files.append(discovered_file)
            invoice_row_index.append(index)
            self.reference_code_list.append(reference_code)
            LOGGER.info(
                "Invoice details row data: %s", str(discovered_file.document_properties)
            )

        return discovered_files, invoice_row_index


class UsFoodsRunner(VendorDocumentDownloadInterface):
    """Runner Class for US Foods"""

    uses_proxy = False

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.login_page = UsFoodsLoginPage(self.driver)
        self.home_page = UsFoodsHomePage(self.driver)
        self.invoices_page = UsFoodsInvoicesPage(self.driver)

    @retry(WebDriverException, tries=3, delay=2)
    def _login(self):
        """
        Login to US Foods
        :return: Nothing
        """
        login_url = "https://www3.usfoods.com/order/faces/oracle/webcenter/portalapp/pages/login.jspx"
        get_url(self.driver, login_url)
        self.login_page.login(self.run.job.username, self.run.job.password)

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
        (
            discovered_files_list,
            invoice_row_index,
        ) = self.invoices_page.get_invoice_table_data(self.run, start_date)

        LOGGER.info(
            f"Total Invoices within date range and download link available: {len(discovered_files_list)}"
        )

        # Download all the invoices
        if len(discovered_files_list) != 0:
            self.download_all_documents(
                self.download_location,
                discovered_files_list,
                invoice_row_index,
                start_date,
            )
        return discovered_files_list

    def download_all_documents(
        self,
        download_location: str,
        discovered_files: List[DiscoveredFile],
        invoice_row_index: list,
        start_date: date,
    ):
        """
        Downloads the invoice & renames it with the actual invoice Number
        :param start_date:
        :param download_location:
        :param discovered_files: List of Discovered files
        :param invoice_row_index: List of invoice row indexes
        :return: Nothing
        """
        for index, discovered_file in enumerate(discovered_files):
            self.invoices_page.goto_invoice_page()
            self.invoices_page.select_start_end_date(start_date)
            self.invoices_page.load_more()
            # Selecting the invoices
            invoice_row = invoice_row_index[index]
            self.invoices_page.select_nth_checkbox(invoice_row)
            self.invoices_page.select_invoice_format("xml")
            download_invoices_button = self.invoices_page.get_download_invoices_button()
            _downloader = download.DriverExecuteScriptBasedDownloader(
                self.driver,
                script="arguments[0].click();",
                script_args=(download_invoices_button,),
                local_filepath=os.path.join(download_location, "invoiceDetails.xml"),
                rename_to=os.path.join(
                    self.download_location, discovered_file.original_filename
                ),
                file_exists_check_kwargs=dict(timeout=20),
            )
            download.download_discovered_file(discovered_file, _downloader)

    def accept_terms_of_use(self):
        agree_button = self.driver.find_elements(By.XPATH, HOME_PAGE_LOCATORS["AGREE"])
        remind_me_later = self.driver.find_elements(
            By.CSS_SELECTOR, HOME_PAGE_LOCATORS["REMIND_ME_LATER"]
        )
        if agree_button:
            LOGGER.info("Found Terms of Use. Clicking on Agree...")
            agree_button[0].click()
        if remind_me_later:
            LOGGER.info("Found New Order Application. Clicking on remind me later...")
            remind_me_later[0].click()

    def start_documents_download_flow(self, run: Run) -> List[DiscoveredFile]:
        """
        Initiates the Document Download Workflow
        :param run: Run Object
        :return: Returns the list of Discovered Files
        """
        discovered_files = []
        try:
            self._login()
            self.accept_terms_of_use()
            wait_for_element(
                self.driver,
                value=INVOICE_PAGE_LOCATORS["LOCATION_DROPDOWN"],
                msg="Account Locations Dropdown",
                retry_attempts=3,
            )
            self._goto_download_page(self.run.job.requested_document_type)
            locations = self.home_page.get_locations()
            LOGGER.info(f"Found locations: {locations}")

            for location in locations:
                LOGGER.info(f"Selecting {location} from the dropdown.")
                if len(locations) > 1:
                    self.invoices_page.select_location_by_index(location["index"])
                discovered_files += self._download_documents()
        finally:
            self._quit_driver()

        return discovered_files

    def login_flow(self, run: Run):
        self._login()
