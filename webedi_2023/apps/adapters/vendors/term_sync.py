from datetime import date, datetime
from typing import List

from selenium.common.exceptions import NoSuchElementException

from apps.adapters.base import VendorDocumentDownloadInterface, PasswordBasedLoginPage
from apps.adapters.framework import download
from apps.adapters.helpers.helper import sleep
from apps.adapters.helpers.webdriver_helper import (
    explicit_wait_till_visibility,
    is_element_present,
    explicit_wait_till_invisibility,
    IGNORED_EXCEPTIONS,
    get_url,
)
from apps.adapters.vendors import LOGGER
from apps.runs.models import (
    Run,
    DiscoveredFile,
    DocumentType,
    FileFormat,
)
from spices.datetime_utils import date_from_string

# Home Page Locators
HOME_PAGE_LOCATORS = {
    "USER_MENU_LINK": "show-user-menu",
    "USER_MENU_LIST": '//div[@id="user-menu"]/ul/li',
    "USER_MENU_NAME_LIST": "li div.company_name span.display_name",
    "CUSTOMER_NUMBER": "div.customer_id",
    "RESTAURANT_NAME": "div.company_name",
    "VENDOR_NAME": "div.vendors",
    "ACCOUNT_URL": "a",
}

# Invoices Page Locators
INVOICE_PAGE_LOCATORS = {
    "INVOICES_COUNT": "div.row div.sixteen",
    "INVOICES_INVOICE_DATE_LINK": '//a[text()="Invoice Date"]',
    "INVOICES_PAGINATION_NEXT": '//li[@class="page-item"]/a[text()="Next →"]',
    "INVOICES_PAGINATION_NEXT_DISABLED": '//li[@class="page-item disabled"]/a[text()="Next →"]',
    "INVOICES_PER_PAGE_100": '//div[@class="page_numbers"]/a[text()="100"]',
    "INVOICES_TABLE_HEADER": 'table[id="payments"]>thead>tr',
    "INVOICES_TABLE_ROWS": 'table[id="payments"]>tbody>tr',
    "REQUEST_PDF_BUTTON": "gumby_modal_submit_btn_request_pdf_modal",
}


class TermSyncLoginPage(PasswordBasedLoginPage):
    SELECTOR_USERNAME_TEXTBOX = 'input[name="user_session[email]"]'
    SELECTOR_PASSWORD_TEXTBOX = 'input[name="user_session[password]"]'
    SELECTOR_LOGIN_BUTTON = 'input[name="commit"]'
    SELECTOR_ERROR_MESSAGE_TEXT = "div[id='alert_container'] div#warning"


class TermSyncHomePage:
    """Home page action methods come here."""

    def __init__(self, driver):
        self.driver = driver

    def get_user_menu_link(self):
        return self.driver.find_element_by_id(HOME_PAGE_LOCATORS["USER_MENU_LINK"])

    def get_user_menu_list(self):
        return self.driver.find_elements_by_xpath(HOME_PAGE_LOCATORS["USER_MENU_LIST"])

    def get_user_menu_name_list(self):
        return self.driver.find_elements_by_css_selector(
            HOME_PAGE_LOCATORS["USER_MENU_NAME_LIST"]
        )


class TermSyncInvoicesPage:
    """Invoices page action methods come here."""

    def __init__(self, driver, download_location: str):
        self.driver = driver
        self.download_location = download_location

    def get_table_rows(self):
        """Returns the Invoices Table Row Data WebElement"""
        return self.driver.find_elements_by_css_selector(
            INVOICE_PAGE_LOCATORS["INVOICES_TABLE_ROWS"]
        )

    def get_request_pdf_button(self):
        return self.driver.find_element_by_id(
            INVOICE_PAGE_LOCATORS["REQUEST_PDF_BUTTON"]
        )

    def request_pdf(self, index_list):
        for index in index_list:
            rows = self.get_table_rows()
            pdf = (
                rows[index]
                .find_elements_by_tag_name("td")[8]
                .find_element_by_tag_name("a")
            )
            pdf.click()
            explicit_wait_till_visibility(
                self.driver,
                self.get_request_pdf_button(),
                msg="Request PDF Button",
                ignored_exceptions=IGNORED_EXCEPTIONS,
            )
            self.get_request_pdf_button().click()
            explicit_wait_till_invisibility(
                self.driver,
                self.get_request_pdf_button(),
                msg="Request PDF Button",
                ignored_exceptions=IGNORED_EXCEPTIONS,
            )

    def get_invoice_table_data(
        self, run: Run, from_date: date, accounts_detail_list: list
    ) -> List[DiscoveredFile]:
        """
        Extracts invoice details from Table
        :param run: Run
        :param from_date: Start date for the invoice to be downloaded
        :param accounts_detail_list: Account detail (link, number, name)
        :return Returns the list of Discovered Files
        """
        LOGGER.info("Extracting Invoice table data.")
        discovered_files = []
        for index, account in enumerate(accounts_detail_list):
            LOGGER.info(f"Getting invoices for account: {account['customer_number']}")
            if index > 0:
                get_url(self.driver, account["account_link"])
            get_url(self.driver, "https://www.termsync.com/payments")

            try:
                explicit_wait_till_visibility(
                    self.driver,
                    self.get_table_rows()[0],
                    msg="Table Rows",
                    ignored_exceptions=IGNORED_EXCEPTIONS,
                )
            except NoSuchElementException:
                LOGGER.warning(
                    "Expected element not found. Login required.", exc_info=True
                )
                break

            discovered_files += self._get_invoice_table_data_from_current_page(
                run, from_date, account
            )

        LOGGER.info(f"Invoice details data: {str(discovered_files)}")
        return discovered_files

    def _get_invoice_table_data_from_current_page(
        self, run: Run, from_date: date, account: dict
    ) -> List[DiscoveredFile]:
        """Extracts invoice details from Table on CURRENT page"""
        discovered_files = []
        ref_code_list = []
        request_pdf_list = []

        rows = self.get_table_rows()
        for index, row in enumerate(rows):
            date_str = row.find_elements_by_tag_name("td")[1].text
            try:
                invoice_date = date_from_string(date_str, "%b %d %Y")
            except ValueError:
                invoice_date = date_from_string(date_str, "%d %b %Y")

            if invoice_date < from_date:
                LOGGER.info(
                    f"Skipping invoice because date '{invoice_date}' is outside requested range"
                )
                self.request_pdf(request_pdf_list)
                return discovered_files

            if not is_element_present(
                self.driver,
                row.find_elements_by_tag_name("td")[8].find_elements_by_tag_name("a"),
            ):
                continue

            pdf = row.find_elements_by_tag_name("td")[8].find_element_by_tag_name("a")

            if pdf.text == "Requested":
                continue

            if pdf.text == "Request":
                request_pdf_list.append(index)
                continue

            invoice_number = row.find_elements_by_tag_name("td")[2].text.strip()

            reference_code = f"{account['customer_number']}_{invoice_number}"
            if reference_code in ref_code_list:
                continue
            ref_code_list.append(reference_code)

            try:
                # pylint: disable=no-member
                discovered_file = DiscoveredFile.build_unique(
                    run,
                    reference_code,
                    document_type=DocumentType.INVOICE.ident,
                    file_format=FileFormat.PDF.ident,
                    original_download_url=row.find_elements_by_tag_name("td")[8]
                    .find_element_by_tag_name("a")
                    .get_attribute("href"),
                    original_filename=f"{reference_code}.pdf",
                    document_properties={
                        "invoice_number": invoice_number,
                        "invoice_date": str(invoice_date),
                        "due_date": str(
                            date_from_string(
                                row.find_elements_by_tag_name("td")[5].text.strip(),
                                "%b %d %Y",
                            )
                        ),
                        "total_amount": row.find_elements_by_tag_name("td")[6].text,
                        "vendor_name": account["vendor_name"]
                        .replace("Vendor:", "")
                        .strip(),
                        "restaurant_name": account["restaurant_name"],
                        "customer_number": account["customer_number"],
                    },
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
            self.download_documents_by_link(discovered_file)

        self.request_pdf(request_pdf_list)
        return discovered_files

    def download_documents_by_link(self, discovered_file: DiscoveredFile):
        """Download all discovered files and set appropriate attributes on them"""
        try:
            _downloader = download.DriverBasedUrlGetDownloader(
                self.driver,
                download_url=discovered_file.original_download_url,
                local_filepath=self.download_location,
                file_exists_check_kwargs=dict(
                    timeout=50.0,
                    pattern=f"\S+_{discovered_file.document_properties['invoice_number']}_\S+.pdf$",
                ),
            )
            download.download_discovered_file(discovered_file, _downloader)
        except (TypeError, FileNotFoundError):
            LOGGER.error("There is problem in the invoice download module......")


class TermSyncRunner(VendorDocumentDownloadInterface):
    """Runner Class for Term Sync"""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.login_page = TermSyncLoginPage(self.driver)
        self.home_page = TermSyncHomePage(self.driver)
        self.invoices_page = TermSyncInvoicesPage(self.driver, self.download_location)

    def _login(self):
        """
        Login to Term Sync
        :return: Nothing
        """
        login_url = "https://www.termsync.com/login"
        LOGGER.info(f"Navigating to: {login_url}")
        self.driver.get(login_url)
        self.login_page.login(self.run.job.username, self.run.job.password)
        explicit_wait_till_visibility(
            self.driver,
            self.home_page.get_user_menu_link(),
            msg="User Menu",
            ignored_exceptions=IGNORED_EXCEPTIONS,
        )

    def _open_user_account_menu(self):
        """
        Open User Account Menu
        :return: Nothing
        """
        count = 0
        explicit_wait_till_visibility(
            self.driver,
            self.home_page.get_user_menu_link(),
            msg="User Menu",
            ignored_exceptions=IGNORED_EXCEPTIONS,
        )
        self.home_page.get_user_menu_link().click()
        while len(self.home_page.get_user_menu_name_list()) == 1:
            if count > 20:
                break
            sleep(1)
            count += 1
        explicit_wait_till_visibility(
            self.driver,
            self.home_page.get_user_menu_name_list()[1],
            msg="User Menu Name",
            ignored_exceptions=IGNORED_EXCEPTIONS,
        )

    def _download_documents(self, accounts_detail_list: list) -> List[DiscoveredFile]:
        """
        Chooses the documents to be downloaded based on the document type
        :param accounts_detail_list: Account detail (link, number, name)
        :return: Returns the list of Discovered Files
        """
        document_type = self.run.job.requested_document_type
        if document_type == "invoice":
            return self._download_invoices(accounts_detail_list)

        raise NotImplementedError(
            f"Requested Document Type is not supported: {document_type}"
        )

    def _download_invoices(self, accounts_detail_list: list) -> List[DiscoveredFile]:
        """
        Downloads the Invoices
        :param accounts_detail_list: Account detail (link, number, name)
        :return: Returns the list of the Discovered Files
        """
        LOGGER.info("Download invoice process begins...")

        start_date = datetime.strptime(
            self.run.request_parameters["start_date"], "%Y-%m-%d"
        ).date()
        # Fetching all invoice table date & storing it in memory
        discovered_files_list = self.invoices_page.get_invoice_table_data(
            self.run, start_date, accounts_detail_list
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

            # Getting the list of Account Vendors associated with the logged in user
            self._open_user_account_menu()
            dd_options_list = self.driver.find_elements_by_xpath(
                HOME_PAGE_LOCATORS["USER_MENU_LIST"]
            )
            accounts_detail_list = [
                {
                    "account_link": option.find_element_by_css_selector(
                        HOME_PAGE_LOCATORS["ACCOUNT_URL"]
                    ).get_attribute("href")
                    if option.get_attribute("class") == "related"
                    else None,
                    "customer_number": option.find_element_by_css_selector(
                        HOME_PAGE_LOCATORS["CUSTOMER_NUMBER"]
                    ).text,
                    "restaurant_name": option.find_element_by_css_selector(
                        HOME_PAGE_LOCATORS["RESTAURANT_NAME"]
                    ).text,
                    "vendor_name": option.find_element_by_css_selector(
                        HOME_PAGE_LOCATORS["VENDOR_NAME"]
                    ).text,
                }
                for option in dd_options_list
            ]
            discovered_files += self._download_documents(accounts_detail_list)
        finally:
            self._quit_driver()

        return discovered_files

    def login_flow(self, run: Run):
        self._login()
