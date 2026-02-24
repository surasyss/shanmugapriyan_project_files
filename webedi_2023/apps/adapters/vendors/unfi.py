import os
import re
from datetime import datetime
from selenium.common.exceptions import (
    NoSuchElementException,
    TimeoutException,
    WebDriverException,
)
from selenium.webdriver import ActionChains
from selenium.webdriver.remote.webelement import WebElement
from selenium.webdriver.common.by import By

from apps.adapters.base import VendorDocumentDownloadInterface, PasswordBasedLoginPage
from apps.adapters.helpers.helper import sleep
from apps.adapters.helpers.webdriver_helper import (
    wait_for_element,
    get_url,
    wait_for_ajax,
    scroll_down,
    close_extra_handles,
    handle_popup,
)
from apps.adapters.framework import download
from apps.adapters.vendors import LOGGER

from apps.runs.models import Run, DiscoveredFile, DocumentType, FileFormat
from spices.datetime_utils import date_from_string

# Home Page Locators
HOME_PAGE_LOCATORS = {
    "WEB_ORDERS_BOX": "span[aria-owns='dllTransactions_listbox']",
    "SELECT_INVOICE_OPTION": "//li[text()='Invoices']",
    "FILTER_BUTTON": "#A1",
}

# Invoices Page Locators
INVOICE_TABLE_ELEMENTS = {
    "INVOICE_TABLE_ROWS": "#OHgridForInvoiceWest div.k-grid-content table tbody tr",
    "OHGRID_TABLE_ROWS": "#OHgrid div.k-grid-content table tbody tr",
    "REPORT": "td a.k-button.k-button-icontext.k-grid-Report",
    "PAGE_LIST": "#OHgridForInvoiceWest div.k-pager-wrap.k-grid-pager.k-widget ul li",
    "OHGRID_PAGE_LIST": "#OHgrid div.k-pager-wrap.k-grid-pager.k-widget ul li",
    "INVOICE_PAGE_FRONT_BUTTON": '#OHgrid a[title="Go to the first page"]',
    "GO_TO_NEXT_BUTTON": '#OHgrid a[title="Go to the next page"]',
    "GO_TO_NEXT_PAGE": "#OHgridForInvoiceWest > div.k-pager-wrap.k-grid-pager.k-widget > a:nth-child(4) > span",
    "INVOICE_PAGE_BACK_BUTTON": '#OHgrid a[title="Go to the last page"]',
    "RESTAURANT_NAME": "#lblAccountName",
    "ACCOUNT_NUMBER": "label#lblAccountNum",
    "PRINT": "body > div:nth-child(1) > a",
}

# Without Report Button Locators
ANOTHER_INVOICE_ELEMENTS = {
    "INVOICE_DETAILS": "div.k-grid-content > table > tbody > tr:nth-child(3) > td > a",
    "DROP_DOWN_BUTTON": "span.k-select > span",
    "DROP_DOWN_INVOICES": "#ddlInvoiceNumber_listbox > li",
    "INPUT_BOX_VALUE": "#kddl_div > span > span > span.k-input",
    "DROP_DOWN_BOX": "#kddl_div > span > li",
    "ERROR_REQUEST": "#lblShowMessage",
    "DOWNLOAD_BUTTON": "#A1 > span",
}


class UnfiLoginPage(PasswordBasedLoginPage):
    """Unfi Login Page Web Elements."""

    SELECTOR_USERNAME_TEXTBOX = "#userName"
    SELECTOR_PASSWORD_TEXTBOX = "#Password"
    SELECTOR_LOGIN_BUTTON = "#login_btn"
    SELECTOR_ERROR_MESSAGE_TEXT = "span#errorMsg"


class UnfiHomePage:
    """Unfi Home Page action methods come here."""

    def __init__(self, driver):
        self.driver = driver

    def navigate_order_history(self):
        """Navigate to order history web page."""
        get_url(self.driver, "https://customers.unfi.com/Pages/OrderHistory.aspx")


class UnfiInvoicesPage:
    """Unfi Invoices page action methods come here."""

    def __init__(self, driver, download_location: str):
        super().__init__()
        self.driver = driver
        self.download_location = download_location
        self.vendor_name = "UNFI"

    def restaurant_name(self):
        """Return the restaurant name."""
        wait_for_element(
            self.driver,
            value=INVOICE_TABLE_ELEMENTS["RESTAURANT_NAME"],
            msg="get restaurant name",
        )
        return self.driver.find_element_by_css_selector(
            INVOICE_TABLE_ELEMENTS["RESTAURANT_NAME"]
        ).text

    def get_account_number(self):
        """Return the account number"""
        account_number = self.driver.find_element_by_css_selector(
            INVOICE_TABLE_ELEMENTS["ACCOUNT_NUMBER"]
        ).text
        return account_number.replace(",", "").strip()

    def transactions_drop_down(self):
        """Transactions drop down web element."""
        wait_for_element(
            self.driver, value=HOME_PAGE_LOCATORS["WEB_ORDERS_BOX"], msg="web order box"
        )
        view_element = self.driver.find_element_by_css_selector(
            HOME_PAGE_LOCATORS["WEB_ORDERS_BOX"]
        )
        ActionChains(self.driver).move_to_element(view_element).click(
            view_element
        ).perform()

    def invoice_page_front_button(self):
        """All page front button web element."""
        return self.driver.find_element_by_css_selector(
            INVOICE_TABLE_ELEMENTS["INVOICE_PAGE_FRONT_BUTTON"]
        )

    def invoice_page_back_button(self):
        """All page back button web element."""
        return self.driver.find_element_by_css_selector(
            INVOICE_TABLE_ELEMENTS["INVOICE_PAGE_BACK_BUTTON"]
        )

    def total_table_count(self):
        """Return number of table pages."""
        scroll_down(self.driver)
        self.driver.execute_script(
            "arguments[0].click();", self.invoice_page_back_button()
        )
        wait_for_ajax(self.driver)
        total_pages = self.driver.find_elements_by_css_selector(
            INVOICE_TABLE_ELEMENTS["PAGE_LIST"]
        ) or self.driver.find_elements_by_css_selector(
            INVOICE_TABLE_ELEMENTS["OHGRID_PAGE_LIST"]
        )
        total_pages = total_pages[-1].text
        self.driver.execute_script(
            "arguments[0].click();", self.invoice_page_front_button()
        )
        wait_for_ajax(self.driver)
        LOGGER.info(f"Total number of pages : {total_pages}")
        return total_pages

    def go_to_next_page(self):
        """Return next button web element."""
        scroll_down(self.driver)
        try:
            wait_for_element(
                self.driver,
                value=INVOICE_TABLE_ELEMENTS["GO_TO_NEXT_BUTTON"],
                retry_attempts=2,
            )
            self.driver.find_element_by_css_selector(
                INVOICE_TABLE_ELEMENTS["GO_TO_NEXT_BUTTON"]
            ).click()
        except (NoSuchElementException, WebDriverException):
            self.driver.find_element_by_css_selector(
                INVOICE_TABLE_ELEMENTS["GO_TO_NEXT_PAGE"]
            ).click()

    def select_invoice_option(self) -> WebElement:
        """Return drop down list web element."""
        wait_for_element(
            self.driver,
            by_selector=By.XPATH,
            value=HOME_PAGE_LOCATORS["SELECT_INVOICE_OPTION"],
            msg="select invoice option",
        )
        return self.driver.find_element_by_xpath(
            HOME_PAGE_LOCATORS["SELECT_INVOICE_OPTION"]
        )

    def filter_button(self) -> WebElement:
        """Return filter button web element."""
        wait_for_element(
            self.driver, value=HOME_PAGE_LOCATORS["FILTER_BUTTON"], msg="filter button"
        )
        return self.driver.find_element_by_css_selector(
            HOME_PAGE_LOCATORS["FILTER_BUTTON"]
        )

    def invoice_details(self) -> WebElement:
        """Return invoice details web element."""
        wait_for_element(
            self.driver,
            value=ANOTHER_INVOICE_ELEMENTS["INVOICE_DETAILS"],
            msg="invoice details",
        )
        return self.driver.find_element_by_css_selector(
            ANOTHER_INVOICE_ELEMENTS["INVOICE_DETAILS"]
        )

    def invoice_drop_down(self) -> WebElement:
        """Return invoice drop down web element."""
        wait_for_element(
            self.driver,
            value=ANOTHER_INVOICE_ELEMENTS["DROP_DOWN_BUTTON"],
            msg="invoice drop down",
        )
        return self.driver.find_element_by_css_selector(
            ANOTHER_INVOICE_ELEMENTS["DROP_DOWN_BUTTON"]
        )

    def collect_all_invoices(self) -> [WebElement]:
        """Return invoice drop down web element."""
        return self.driver.find_elements_by_css_selector(
            ANOTHER_INVOICE_ELEMENTS["DROP_DOWN_INVOICES"]
        )

    def download_element(self):
        """Return download element web element."""
        return self.driver.find_element_by_css_selector(
            ANOTHER_INVOICE_ELEMENTS["DOWNLOAD_BUTTON"]
        )

    def _handle_popup(self):
        handle_popup(
            self.driver,
            value="div.k-window[style*='display: block;'] div#MigrationMessagePopup span#migrationAskMeLater a",
            msg="myUNFI Portal",
            timeout=10,
        )

    def get_invoice_page_locations(self):
        """Get drop down and click invoice option."""

        self._handle_popup()
        self._handle_popup()

        self.transactions_drop_down()

        self.select_invoice_option().click()

        self.filter_button().click()

    def get_table_rows(self):
        return self.driver.find_elements_by_css_selector(
            INVOICE_TABLE_ELEMENTS["INVOICE_TABLE_ROWS"]
        ) or self.driver.find_elements_by_css_selector(
            INVOICE_TABLE_ELEMENTS["OHGRID_TABLE_ROWS"]
        )

    def get_table_data(self, run: Run, from_date, restaurant_name):
        """Extracts invoice details from Table.
        :return: Returns the list of Discovered File.
        """
        discovered_files = []

        for row in self.get_table_rows():

            if not row.text:
                continue

            # Invoice date
            invoice_date = date_from_string(
                row.find_elements_by_css_selector("td")[6].text, "%m/%d/%Y"
            )

            if invoice_date < from_date:
                return discovered_files, True

            # Invoice number
            invoice_number = row.find_elements_by_css_selector("td")[5].text

            # customer number, total amount
            account_number = self.get_account_number()
            total_amount = row.find_elements_by_css_selector("td")[7].text

            reference_code = f"{account_number}_{invoice_number}_{invoice_date}"

            try:
                # pylint: disable=no-member
                discovered_file = DiscoveredFile.build_unique(
                    run,
                    reference_code,
                    document_type=DocumentType.INVOICE.ident,
                    file_format=FileFormat.PDF.ident,
                    original_download_url="",
                    original_filename=f"{reference_code}.pdf",
                    document_properties={
                        "customer_number": f"{account_number}",
                        "invoice_number": f"{invoice_number}",
                        "invoice_date": f"{invoice_date}",
                        "total_amount": f"{total_amount}",
                        "vendor_name": self.vendor_name,
                        "restaurant_name": f"{restaurant_name}",
                    },
                )
            except DiscoveredFile.AlreadyExists:
                LOGGER.info(
                    f"Discovered file already exists with reference code : {reference_code}"
                )
                continue  # skip if seen before

            try:
                # report element
                row.find_element_by_css_selector(
                    INVOICE_TABLE_ELEMENTS["REPORT"]
                ).click()

                for index in range(5):
                    if len(self.driver.window_handles) > 1:
                        break
                    sleep(2, msg=f"{index}. wait for window handles change")

                # navigate to popup window
                self.driver.switch_to_window(self.driver.window_handles[1])
                wait_for_element(
                    self.driver,
                    value=INVOICE_TABLE_ELEMENTS["PRINT"],
                    retry_attempts=2,
                    raise_exception=False,
                )
                self.download_invoice_by_url(discovered_file)

                # close the popup window
                self.driver.close()

                # switch to invoice table page
                self.driver.switch_to_window(self.driver.window_handles[0])
            except NoSuchElementException:
                LOGGER.info(
                    f"Report not found for this invoice number: "
                    f"{discovered_file.document_properties['invoice_number']}"
                )
            discovered_files.append(discovered_file)
            LOGGER.info(
                f"Invoice details row data: {discovered_file.document_properties}"
            )
        return discovered_files, False

    def get_after_invoice_table(self, run, from_date, restaurant_name):
        discovered_files = []

        get_url(self.driver, "https://customers.unfi.com/Pages/Reports.aspx")
        wait_for_element(
            self.driver,
            value=ANOTHER_INVOICE_ELEMENTS["ERROR_REQUEST"],
            retry_attempts=1,
            raise_exception=False,
        )

        if self.driver.find_elements_by_css_selector(
            ANOTHER_INVOICE_ELEMENTS["ERROR_REQUEST"]
        ):
            get_url(self.driver, "https://customers.unfi.com/Pages/Reports.aspx")

        self.invoice_details().click()
        self.invoice_drop_down().click()

        wait_for_element(
            self.driver,
            value=ANOTHER_INVOICE_ELEMENTS["DROP_DOWN_BOX"],
            retry_attempts=1,
            raise_exception=False,
        )

        all_invoice_data = [each.text for each in self.collect_all_invoices()]
        for _, row in enumerate(all_invoice_data[1:]):
            # Invoice date
            invoice_date = date_from_string(
                re.search(r"\d{4}-\d+-\d+", row).group(), "%Y-%m-%d"
            )

            if invoice_date < from_date:
                return discovered_files

            # Invoice number
            invoice_number = row.split(" ")[0]

            # customer number, total amount
            account_number = self.get_account_number()
            total_amount = row.split(" ")[-1]

            reference_code = f"{account_number}_{invoice_number}_{invoice_date}"

            try:
                # pylint: disable=no-member
                discovered_file = DiscoveredFile.build_unique(
                    run,
                    reference_code,
                    document_type=DocumentType.INVOICE.ident,
                    file_format=FileFormat.PDF.ident,
                    original_download_url="",
                    original_filename=f"{reference_code}.pdf",
                    document_properties={
                        "customer_number": f"{account_number}",
                        "invoice_number": f"{invoice_number}",
                        "invoice_date": f"{invoice_date}",
                        "total_amount": f"{total_amount}",
                        "vendor_name": self.vendor_name,
                        "restaurant_name": f"{restaurant_name}",
                    },
                )
            except DiscoveredFile.AlreadyExists:
                LOGGER.info(
                    f"Discovered file already exists with reference code : {reference_code}"
                )
                continue  # skip if seen before

            discovered_files.append(discovered_file)
        self.invoice_drop_down().click()
        return discovered_files

    def download_invoice_by_url(self, discovered_file):
        """Download the File in PDF format
        :param discovered_file: DiscoveredFile variable
        """
        _downloader = download.DriverExecuteCDPCmdBasedDownloader(
            self.driver,
            cmd="Page.printToPDF",
            cmd_args={"printBackground": True},
            local_filepath=f"{self.download_location}/invoice.pdf",
            rename_to=os.path.join(
                self.download_location, discovered_file.original_filename
            ),
            file_exists_check_kwargs=dict(timeout=20),
        )
        download.download_discovered_file(discovered_file, _downloader)

    def download_invoice_by_click(self, discovered_file_list):
        """Download the File in PDF format
        :param discovered_file_list: List of discoveredFile variables
        """
        file_pattern = rf"31_75591_[0-9]+"
        self.invoice_drop_down().click()

        for _index, _ in enumerate(discovered_file_list):

            if _index > 0:
                self.invoice_drop_down().click()

            self.driver.execute_script(
                "arguments[0].click();", self.collect_all_invoices()[1:][_index]
            )

            _downloader = download.WebElementClickBasedDownloader(
                element=self.download_element(),
                local_filepath=self.download_location,
                rename_to=os.path.join(
                    self.download_location,
                    discovered_file_list[_index].original_filename,
                ),
                file_exists_check_kwargs=dict(
                    timeout=20, pattern=f"{file_pattern}.pdf$"
                ),
            )
            download.download_discovered_file(discovered_file_list[_index], _downloader)
            close_extra_handles(self.driver)


class UnfiRunner(VendorDocumentDownloadInterface):
    """Runner Class for unfi."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.login_page = UnfiLoginPage(self.driver)
        self.home_page = UnfiHomePage(self.driver)
        self.invoices_page = UnfiInvoicesPage(self.driver, self.download_location)

    def _login(self):
        """
        Login to UNFI
        :return: Nothing
        """
        login_url = "https://customers.unfi.com/_login/LoginPage/Login.aspx"
        get_url(self.driver, login_url)
        self.login_page.login(self.run.job.username, self.run.job.password)

    def _download_invoices(self) -> [DiscoveredFile]:
        """
        Downloads the Invoices
        :return: Returns the list of the Discovered Files
        """
        document_type, discovered_files_list = self.run.job.requested_document_type, []
        if document_type == "invoice":
            LOGGER.info("Extracting data from table...")
            start_date = datetime.strptime(
                self.run.request_parameters["start_date"], "%Y-%m-%d"
            ).date()
            restaurant_name = self.invoices_page.restaurant_name()

            self.invoices_page.get_invoice_page_locations()

            if self.driver.find_elements_by_css_selector(
                INVOICE_TABLE_ELEMENTS["REPORT"]
            ):

                (
                    disc_files_per_page,
                    is_date_out_of_range,
                ) = self.invoices_page.get_table_data(
                    self.run, start_date, restaurant_name
                )
                discovered_files_list.extend(disc_files_per_page)

                if is_date_out_of_range:
                    return discovered_files_list

                for page_number in range(
                    1, int(self.invoices_page.total_table_count())
                ):
                    scroll_down(self.driver)
                    LOGGER.info(f"Currently on page no. {page_number}")
                    self.invoices_page.go_to_next_page()

                    try:
                        wait_for_ajax(self.driver, timeout=20)
                    except TimeoutException:
                        LOGGER.info("No ajax calls found.")

                    (
                        disc_files_per_page,
                        is_date_out_of_range,
                    ) = self.invoices_page.get_table_data(
                        self.run, start_date, restaurant_name
                    )
                    discovered_files_list.extend(disc_files_per_page)

                    if is_date_out_of_range:
                        return discovered_files_list

                LOGGER.info(
                    f"Total Invoices within date range and download link available: "
                    f"{len(discovered_files_list)}"
                )
            else:
                disc_files_per_page = self.invoices_page.get_after_invoice_table(
                    self.run, start_date, restaurant_name
                )
                self.invoices_page.download_invoice_by_click(disc_files_per_page)
                discovered_files_list.extend(disc_files_per_page)
                LOGGER.info(
                    f"Total Invoices within date range and download link available: {len(discovered_files_list)}"
                )
            return discovered_files_list

        raise NotImplementedError(
            f"Requested Document Type is not supported: {document_type}"
        )

    def start_documents_download_flow(self, run: Run) -> [DiscoveredFile]:
        """
        Initiates the Document Download Workflow
        :param run: Run Object
        :return: Returns the list of Discovered Files
        """
        try:
            self._login()
            self.home_page.navigate_order_history()
            discovered_files = self._download_invoices()
            return discovered_files
        finally:
            self._quit_driver()

    def login_flow(self, run: Run):
        self._login()
