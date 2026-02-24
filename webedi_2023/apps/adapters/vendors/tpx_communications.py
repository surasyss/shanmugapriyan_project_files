import os
import datetime
from typing import List

from retry.api import retry
from selenium.common.exceptions import (
    ElementNotInteractableException,
    WebDriverException,
    TimeoutException,
)
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

from apps.adapters.base import VendorDocumentDownloadInterface, PasswordBasedLoginPage
from apps.adapters.framework import download
from apps.adapters.helpers.webdriver_helper import (
    explicit_wait_till_clickable,
    get_url,
    wait_for_element,
)
from apps.adapters.vendors import LOGGER
from apps.runs.models import Run, DiscoveredFile, DocumentType, FileFormat
from spices.datetime_utils import date_from_string


# Home Page Locators
HOME_PAGE_LOCATORS = {
    "MY_BILLING": 'img[onclick="'
    + "displayCategoryPortals('"
    + "myBillingDiv'"
    + ')"]',
}

# Invoices Page Locators
INVOICE_PAGE_LOCATORS = {
    "ACCOUNT_NUMBER_DROP_DOWN": "#ASPxRoundPanel1_ContentPlaceHolder1_ddlAccountNumber_I",
    "ACCOUNT_NUMBERS_DROP_DOWN_VALUES": "#ASPxRoundPanel1_ContentPlaceHolder1_ddlAccountNumber_DDD_L_LBT tbody tr",
    "INVOICE_TABLE_DROP_DOWN": "#ASPxRoundPanel1_ContentPlaceHolder1_ddlInvoiceNumber",
    "INVOICE_TABLE_DROP_DOWN_VALUES": "#ASPxRoundPanel1_ContentPlaceHolder1_ddlInvoiceNumber_DDD_L_LBT tbody tr",
    "TOTAL_AMOUNT": "#ASPxRoundPanel1_ContentPlaceHolder1_lblTotalAmountDue",
    "INVOICE_DATE": "#ASPxRoundPanel1_ContentPlaceHolder1_lblInvoiceDate",
    "RESTAURANT_NAME": "#ASPxRoundPanel1_ContentPlaceHolder1_lblNA",
    "INVOICE_NUMBER": "#ASPxRoundPanel1_RPHT",
    "VIEW_PDF": "#ASPxRoundPanel1_ContentPlaceHolder1_pbPDF_CD span",
}


class TPXCommunicationsLoginPage(PasswordBasedLoginPage):
    """
    One Central TPX Communications login module
    """

    SELECTOR_USERNAME_TEXTBOX = r"#portlet_6_1\{actionForm\.username\}"
    SELECTOR_PASSWORD_TEXTBOX = r"#portlet_6_1\{actionForm\.password\}"
    SELECTOR_LOGIN_BUTTON = (
        'form#portlet_6_1loginFormId.myform img[alt="Click to Login"]'
    )
    SELECTOR_ERROR_MESSAGE_TEXT = "div.bea-portal-window-content td.error-header2"


class TPXInvoicesPage:
    """One central TPX Invoices page action methods come here."""

    vendor_name = "TPX Communications"

    def __init__(self, driver):
        self.driver = driver

    @retry(ElementNotInteractableException, tries=5, delay=2)
    def get_option_values(self, index) -> list:
        """
        Getting list of invoice numbers of values
        :return: Return list of invoice numbers of values
        """
        LOGGER.info("Get the drop down option value")

        # click invoice number selector to get the scrollable table of invoice numbers and dates
        self.driver.find_element_by_css_selector(
            INVOICE_PAGE_LOCATORS["INVOICE_TABLE_DROP_DOWN"]
        ).click()
        invoice_number_web_elements = self.driver.find_elements_by_css_selector(
            INVOICE_PAGE_LOCATORS["INVOICE_TABLE_DROP_DOWN_VALUES"]
        )
        invoice_number_web_elements[index].click()
        return invoice_number_web_elements

    def get_invoice_date(self):
        for _ in range(5):
            try:
                wait_for_element(
                    self.driver,
                    value=INVOICE_PAGE_LOCATORS["INVOICE_DATE"],
                    msg="Invoice Date",
                    retry_attempts=1,
                )
                break
            except WebDriverException as excep:
                LOGGER.info(excep)
                self.driver.refresh()
                continue

        invoice_date_element = self.driver.find_element_by_css_selector(
            INVOICE_PAGE_LOCATORS["INVOICE_DATE"]
        )
        invoice_date = date_from_string(invoice_date_element.text, "%m/%d/%Y")
        return invoice_date

    def get_invoice_number(self):
        invoice_number_element = self.driver.find_element_by_css_selector(
            INVOICE_PAGE_LOCATORS["INVOICE_NUMBER"]
        )
        invoice_number = str(invoice_number_element.text).split(" ")[-1]
        return invoice_number

    def get_invoice_table_data(
        self, run: Run, from_date, download_location, account_number
    ) -> List[DiscoveredFile]:
        """
        Extracts invoice details from Table
        :param account_number: Account number
        :param download_location: Download file path
        :param from_date: Invoice start date
        :param run: Run Object
        :return: Returns the list of Discovered Files
        """
        discovered_files = []
        for index, element in enumerate(self.get_option_values(0)):
            LOGGER.info(f"Drop down web element : {element}")
            if index != 0:
                self.get_option_values(index)

            invoice_date = self.get_invoice_date()

            if invoice_date < from_date:
                LOGGER.info(
                    f"Skipping remaining invoices because date '{invoice_date}' is outside requested range"
                )
                return discovered_files

            try:
                view_pdf_button = explicit_wait_till_clickable(
                    self.driver,
                    (By.CSS_SELECTOR, INVOICE_PAGE_LOCATORS["VIEW_PDF"]),
                    msg="Waiting for view bill pdf button...",
                )
            except TimeoutException:
                LOGGER.info("Pdf invoice not found.")
                continue

            invoice_number = self.get_invoice_number()

            reference_code = (
                f"{account_number}-{invoice_number}-"
                + f"{invoice_date}".replace("-", "")
            )

            restaurant_element = self.driver.find_element_by_css_selector(
                INVOICE_PAGE_LOCATORS["RESTAURANT_NAME"]
            )
            restaurant_name = str(restaurant_element.text).split("\n")[0]

            invoice_total_element = self.driver.find_element_by_css_selector(
                INVOICE_PAGE_LOCATORS["TOTAL_AMOUNT"]
            )

            document_properties = {
                "customer_number": account_number,
                "invoice_number": invoice_number,
                "invoice_date": f"{invoice_date}",
                "total_amount": invoice_total_element.text,
                "vendor_name": self.vendor_name,
                "restaurant_name": restaurant_name,
            }
            try:
                # pylint: disable=no-member
                discovered_file = DiscoveredFile.build_unique(
                    run,
                    reference_code,
                    document_type=DocumentType.INVOICE.ident,
                    file_format=FileFormat.PDF.ident,
                    original_download_url=view_pdf_button,
                    original_filename=f"{reference_code}.pdf",
                    document_properties=document_properties,
                )
            except DiscoveredFile.AlreadyExists:
                LOGGER.info(
                    f"Discovered file already exists with reference code : {reference_code}"
                )
                continue  # skip if seen before
            self.download_documents_by_link(download_location, discovered_file)
            discovered_files.append(discovered_file)
            LOGGER.info(
                f"Invoice details row data: {discovered_file.document_properties}"
            )
        return discovered_files

    def download_documents_by_link(self, download_location: str, discovered_file):
        """
        Downloads the invoice by click the view bill button
        :param download_location: Download path
        :param discovered_file: Discovered file
        :return: Nothing
        """
        pdf_filename = (
            f'01-{discovered_file.document_properties["customer_number"]}-INVOICE-'
            + f'{discovered_file.document_properties["invoice_date"]}'.replace("-", "")
            + ".pdf"
        )

        _downloader = download.DriverExecuteScriptBasedDownloader(
            self.driver,
            script="arguments[0].click();",
            script_args=(discovered_file.original_download_url,),
            local_filepath=os.path.join(download_location, pdf_filename),
            file_exists_check_kwargs=dict(timeout=50),
        )
        download.download_discovered_file(discovered_file, _downloader)


class OneCentralTPXRunner(VendorDocumentDownloadInterface):
    """Runner Class for TPX Communications"""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.login_page = TPXCommunicationsLoginPage(self.driver)
        self.invoices_page = TPXInvoicesPage(self.driver)

    def _login(self):
        """
        Login to TPX communications
        :return: Nothing
        """
        login_url = "https://onecentralportal.tpx.com/OneCentralPortal/"
        get_url(self.driver, login_url)
        self.login_page.login(self.run.job.username, self.run.job.password)

        # Wait until the specific button shows up before we move ahead
        wait_for_element(
            self.driver, value=HOME_PAGE_LOCATORS["MY_BILLING"], msg="MY Billing Button"
        )

    def _iter_account_numbers(self):
        for _ in range(3):
            try:
                wait_for_element(
                    self.driver,
                    value=INVOICE_PAGE_LOCATORS["ACCOUNT_NUMBER_DROP_DOWN"],
                    msg="ACCOUNT NUMBER DROPDOWN",
                    retry_attempts=3,
                )
                # click dropdown
                self.driver.find_element_by_css_selector(
                    INVOICE_PAGE_LOCATORS["ACCOUNT_NUMBER_DROP_DOWN"]
                ).click()
                break
            except WebDriverException as excep:
                LOGGER.warning(f"{excep} found in {self.driver.current_url}")
                get_url(self.driver, "https://onecentral.osgview.com/Summary.aspx")

        # get account number rows
        account_number_elements = self.driver.find_elements_by_css_selector(
            INVOICE_PAGE_LOCATORS["ACCOUNT_NUMBERS_DROP_DOWN_VALUES"]
        )

        for account_number_element in account_number_elements:
            account_number = account_number_element.text
            # click each, and yield them one by one
            account_number_element.click()

            yield account_number, account_number_element

    def _download_documents(self, account_number: str) -> List[DiscoveredFile]:
        """
        Chooses the documents to be downloaded based on the document type
        :return: Returns the list of Discovered Files
        """
        document_type = self.run.job.requested_document_type
        if document_type == "invoice":
            return self._download_invoices(account_number)

        raise NotImplementedError(
            f"Requested Document Type is not supported: {document_type}"
        )

    def _download_invoices(self, account_number: str) -> List[DiscoveredFile]:
        """
        Downloads the Invoices
        :return: Returns the list of the Discovered Files
        """

        start_date = datetime.datetime.strptime(
            self.run.request_parameters["start_date"], "%Y-%m-%d"
        ).date()
        # Fetching all invoice table date & storing it in memory
        discovered_files_list = self.invoices_page.get_invoice_table_data(
            self.run, start_date, self.download_location, account_number
        )
        LOGGER.info(
            f"Total Invoices within date range and download link available: {len(discovered_files_list)}"
        )
        return discovered_files_list

    def start_documents_download_flow(self, run: Run) -> List[DiscoveredFile]:
        """
        Initiates the Document Download Workflow
        :param run: Run Object
        :return: Returns the list of Discovered Files.
        """
        LOGGER.info(f"[tag:WAV_TPX_SDDF10] Starting documents download flow for TPX")
        discovered_files = []
        try:
            LOGGER.info(f"[tag:WAV_TPX_SDDF20] Logging in")
            self._login()

            # click "My Billing"
            LOGGER.debug(
                f'[tag:WAV_TPX_SDDF30] Clicking "My Billing" to go to invoices page'
            )
            self.driver.find_element_by_css_selector(
                HOME_PAGE_LOCATORS["MY_BILLING"]
            ).click()
            self.driver.find_element_by_css_selector("#generatedOsgUrl").click()

            LOGGER.debug(f"[tag:WAV_TPX_SDDF40] Waiting until new window opens")
            WebDriverWait(self.driver, 5).until(EC.number_of_windows_to_be(2))

            LOGGER.debug(f"[tag:WAV_TPX_SDDF50] New window opened, switching to that")
            self.driver.switch_to.window(self.driver.window_handles[1])

            LOGGER.debug(
                f"[tag:WAV_TPX_SDDF60] Iterating over all available account numbers"
            )
            for (account_number, _) in self._iter_account_numbers():
                LOGGER.info(
                    f'[tag:WAV_TPX_SDDF70] Selected account number "{account_number}", downloading invoices'
                )
                discovered_files += self._download_documents(account_number)

        finally:
            self._quit_driver()
        return discovered_files

    def login_flow(self, run: Run):
        self._login()
