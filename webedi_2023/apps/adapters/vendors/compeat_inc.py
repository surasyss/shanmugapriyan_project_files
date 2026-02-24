import os
from datetime import datetime, date
from typing import List
import time
from selenium.webdriver.remote.webelement import WebElement
from selenium.common.exceptions import (
    NoSuchElementException,
    StaleElementReferenceException,
)

from apps.adapters.base import PasswordBasedLoginPage, VendorDocumentDownloadInterface
from apps.adapters.framework import download
from apps.adapters.helpers.webdriver_helper import (
    explicit_wait_till_visibility,
    get_url,
    ActionChains,
)
from apps.runs.models import Run, DiscoveredFile, DocumentType, FileFormat
from integrator import LOGGER
from spices.datetime_utils import date_from_string, date_from_isoformat
import re

# Home Page Locators
HOME_PAGE_LOCATORS = {
    "UPDATE_MSG": "button.wm-visual-design-button",
    "UPDATE_FRAME": "div.wm-visual-design-canvas",
}

# Account Center Page Locators
ACCOUNT_CENTER_PAGE = {
    "MENU_OPTION": 'div[id="mst-waffle"]',
    "TABLE_START_DATE": 'input[id="ctl00_cphMain_ctlDateRangeSelector_txtStartDate_txtDate"]',
    "TABLE_ROW": 'table[id="ctl00_cphMain_grd"]>tbody>tr',
    "WALK_ME_BUTTON": "div.walkme-custom-balloon-close-button",
    "TABLE_PAGES": "tr.grdP td table tbody tr td",
}

# Account page details Locators
ACCOUNT_DETAILS_PAGE = {
    "INVOICE_DETAINS": '//a[text()="Accounts Payable"]',
    "SHOW_BUTTON": 'input[id="ctl00_cphMain_cmdShow"]',
}

# Billing History Page Locators
BILLING_HISTORY_PAGE = {
    "TABLE_ROW": "#ctl00_cphMain_grd > tbody:nth-child(2) > tr",
    "BILL_HISTORY_ROW": 'table[id="ctl00_cphMain_grd"]>tbody',
}


class CompeatIncLoginPage(PasswordBasedLoginPage):
    """Compeat Inc Login Page Web Elements"""

    SELECTOR_USERNAME_TEXTBOX = 'input[id="txtUserName"]'
    SELECTOR_PASSWORD_TEXTBOX = 'input[id="txtPassword"]'
    SELECTOR_LOGIN_BUTTON = 'button[id="SignOn"]'
    SELECTOR_ERROR_MESSAGE_TEXT = " div.ptl-LoginPage_Card p.ptl-LoginPage_ErrorMessage"


# This crawler is not being used anywhere as its not enabled(ie connector is still backlog).
# reason being its de-prioritized for time-being.


class CompeatIncHomePage:
    """Home Page Class for Compeat Inc"""

    def __init__(self, driver):
        self.driver = driver

    def get_account_href(self):
        """Return the account number list"""
        # select for export page from home page
        _menu = self.driver.find_element_by_css_selector(
            ACCOUNT_CENTER_PAGE["MENU_OPTION"]
        )
        sub_menu = self.driver.find_elements_by_xpath(
            ACCOUNT_CENTER_PAGE["SUB_MENU_OPTION"]
        )[0]
        ActionChains(self.driver).double_click(_menu).click(sub_menu).perform()
        self.driver.implicitly_wait(20)

    def notification_window(self):
        """notification window"""
        return self.driver.find_element_by_css_selector(
            HOME_PAGE_LOCATORS["UPDATE_FRAME"]
        )

    @staticmethod
    def click_notification(window_open):
        """click update notification"""
        window_open.find_element_by_css_selector(
            HOME_PAGE_LOCATORS["UPDATE_MSG"]
        ).click()


class CompeatIncAccountCenterPage:
    """Account Center Page class for Compeat Inc"""

    def __init__(self, driver):
        self.driver = driver

    def get_table_row_filter(self):
        """get table rows"""
        return self.driver.find_elements_by_css_selector(
            ACCOUNT_CENTER_PAGE["TABLE_ROW"]
        )

    def show_button_click(self):
        """select show button click"""
        self.driver.find_element_by_css_selector(
            ACCOUNT_DETAILS_PAGE["SHOW_BUTTON"]
        ).click()


class CompeatIncBillingHistoryPage:
    """Billing History Page class for Compeat Inc"""

    def __init__(self, driver, download_location: str):
        self.driver = driver
        self.download_location = download_location
        self.account_center_page = CompeatIncAccountCenterPage(self.driver)

    def get_inner_table(self):
        return self.driver.find_element_by_css_selector(
            BILLING_HISTORY_PAGE["BILL_HISTORY_ROW"]
        )

    def get_table_rows(self) -> List[WebElement]:
        """Return the billing history table rows"""
        return self.get_inner_table().find_elements_by_css_selector(
            BILLING_HISTORY_PAGE["TABLE_ROW"]
        )[1:]

    @staticmethod
    def get_inner_table_click(table_element, shift_count):
        table_element.find_elements_by_css_selector("td a")[shift_count].click()

    def get_table_data(self, run: Run, from_date: date) -> List[DiscoveredFile]:
        """
        Extracts invoice details from Table
        :param run: Run Object
        :param from_date: Start date of the invoices to be downloaded
        :return: Returns the list of Discovered File
        """
        discovered_files, al_num, download_id = (
            [],
            int(len(self.account_center_page.get_table_row_filter())) - 1,
            "",
        )
        for index in range(al_num)[2:]:
            try:
                explicit_wait_till_visibility(
                    self.driver,
                    self.account_center_page.get_table_row_filter()[index],
                    timeout=20,
                    msg="check",
                )
                self.account_center_page.get_table_row_filter()[
                    index
                ].find_elements_by_css_selector("td a")[0].click()
                time.sleep(2)
                self.driver.implicitly_wait(20)
                self.driver.execute_script(
                    "window.scrollTo(0, document.body.scrollHeight);"
                )
                # inner table rows
                for row in self.get_table_rows():
                    explicit_wait_till_visibility(
                        self.driver, row, timeout=10, msg="waiting for row table data"
                    )
                    try:
                        download_id = row.find_elements_by_css_selector("td a")[
                            1
                        ].get_attribute("href")
                    except IndexError:
                        continue
                    explicit_wait_till_visibility(
                        self.driver, row, timeout=20, msg="wait for main account data"
                    )
                    try:
                        invoice_number = row.find_elements_by_css_selector("td")[3].text
                    except IndexError:
                        invoice_number = "-"
                    invoice_date = date_from_string(
                        row.find_elements_by_css_selector("td")[6].text, "%m/%d/%Y"
                    )
                    total_amount = row.find_elements_by_css_selector("td")[8].text
                    vendor_name = row.find_elements_by_css_selector("td")[7].text
                    if invoice_date < from_date:
                        continue
                    # this code should be unique, as duplications will not be considered, to prevent duplicate files.
                    reference_code = re.sub(
                        r"https://plateiq.pics/\S+/|\.pdf",
                        "",
                        download_id,
                        re.IGNORECASE,
                    )
                    reference_code = f"{invoice_number}_{invoice_date}_{reference_code}"

                    # pylint: disable=no-member
                    if DiscoveredFile.get_unique(run, reference_code):
                        continue
                    # pylint: disable=no-member
                    discovered_file = DiscoveredFile(
                        run=run, document_type=DocumentType.INVOICE.ident
                    )
                    discovered_file.file_format = FileFormat.PDF.ident
                    discovered_file.original_filename = f"{reference_code}.pdf"
                    discovered_file.original_download_url = download_id
                    discovered_file.document_properties = {
                        "invoice_number": f"{invoice_number}",
                        "invoice_date": f"{invoice_date}",
                        "total_amount": f"{total_amount}",
                        "vendor_name": vendor_name,
                    }
                    LOGGER.info(
                        "Invoice details row data: %s",
                        str(discovered_file.document_properties),
                    )
                    discovered_files.append(discovered_file)
                self.driver.execute_script("history.back();")
            except StaleElementReferenceException:
                pass
        self.driver.execute_script("history.back();")
        return discovered_files

    def download_invoice_by_url(self, discovered_files):
        """
        Download the File in PDF format
        :param discovered_files: DiscoveredFile variable
        """
        # rename is required, if we have download multiple files hence
        # we need to rename the file as for certain conditions for uploading to s3
        for discovered_file in discovered_files:
            _downloader = download.DriverBasedUrlGetDownloader(
                self.driver,
                download_url=discovered_file.original_download_url,
                local_filepath=os.path.join(self.download_location),
                rename_to=os.path.join(
                    self.download_location, discovered_file.original_filename
                ),
                file_exists_check_kwargs=dict(timeout=50),
            )
            download.download_discovered_file(discovered_file, _downloader)


class CompeatIncRunner(VendorDocumentDownloadInterface):
    """Runner Class for Compeat Inc"""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.login_page = CompeatIncLoginPage(self.driver)
        self.home_page = CompeatIncHomePage(self.driver)
        self.account_center_page = CompeatIncAccountCenterPage(self.driver)
        self.billing_history_page = CompeatIncBillingHistoryPage(
            self.driver, self.download_location
        )

    def _login(self):
        """
        Login using credentials
        :return: Nothing
        """
        login_url = "https://portal.compeat.com/"
        get_url(self.driver, login_url)
        self.login_page.login(self.run.job.username, self.run.job.password)

    def navigate_to_account_center(self):
        """Navigate to the account center page"""
        # select for export page from home page
        # _menu = self.driver.find_element_by_css_selector(ACCOUNT_CENTER_PAGE['MENU_OPTION'])
        # sub_menu = self.driver.find_elements_by_xpath(ACCOUNT_CENTER_PAGE['SUB_MENU_OPTION'])[0]
        # ActionChains(self.driver).double_click(_menu).click(sub_menu).perform()
        # self.driver.implicitly_wait(20)
        get_url(self.driver, "https://radar.ctuit.com/CtuitNet/AP/Batches.aspx")

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

    def set_start_date(self):
        start_date = date_from_isoformat(
            self.run.request_parameters["start_date"]
        ).strftime("%m/%d/%Y")
        set_date = self.driver.find_element_by_css_selector(
            ACCOUNT_CENTER_PAGE["TABLE_START_DATE"]
        )
        set_date.clear()
        set_date.send_keys(start_date)

    def handle_walk_me_pop_up(self):
        try:
            self.driver.find_element_by_css_selector(
                ACCOUNT_CENTER_PAGE["WALK_ME_BUTTON"]
            ).click()
        except NoSuchElementException:
            pass

    def _download_invoices(self) -> List[DiscoveredFile]:
        """
        Downloads the Invoices
        :return: Returns the list of the Discovered Files
        """
        LOGGER.info("Extracting data from table...")
        discovered_files_list = []
        self.handle_walk_me_pop_up()
        # set starting date to the input field
        self.set_start_date()
        # show button click
        self.driver.implicitly_wait(20)
        self.account_center_page.show_button_click()
        self.driver.implicitly_wait(20)
        self.driver.refresh()
        start_date = datetime.strptime(
            self.run.request_parameters["start_date"], "%Y-%m-%d"
        ).date()
        # get shift pages
        shift_page = self.account_center_page.get_table_row_filter()[0]
        # shift pagination in table
        for shift_count in range(
            int(len(shift_page.find_elements_by_css_selector("td a"))) + 1
        ):
            try:
                self.driver.implicitly_wait(20)
                discovered_files_list.extend(
                    self.billing_history_page.get_table_data(self.run, start_date)
                )
                # get inner table element
                table_element = self.billing_history_page.get_inner_table()
                # click pagination rows
                self.billing_history_page.get_inner_table_click(
                    table_element, shift_count
                )
                time.sleep(5)
            except (NoSuchElementException, StaleElementReferenceException):
                pass

        LOGGER.info(
            f"Total Invoices within date range and download link available: {len(discovered_files_list)}"
        )
        LOGGER.info(
            f"Downloaded invoice by download link available: {len(discovered_files_list)}"
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
            self.driver.implicitly_wait(20)
            try:
                window_open = explicit_wait_till_visibility(
                    self.driver, self.home_page.notification_window(), timeout=30
                )
                self.home_page.click_notification(window_open)
            except NoSuchElementException:
                pass
            self.driver.implicitly_wait(20)
            self.navigate_to_account_center()
            self.driver.implicitly_wait(20)
            discovered_files.extend(self._download_documents())
            self.billing_history_page.download_invoice_by_url(discovered_files)
        finally:
            self._quit_driver()

        return discovered_files

    def login_flow(self, run: Run):
        self._login()
