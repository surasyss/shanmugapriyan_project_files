import os
from datetime import date, datetime
from typing import List

from furl import furl
from selenium.webdriver.common.by import By
from selenium.webdriver.remote.webelement import WebElement

from apps.adapters.base import VendorDocumentDownloadInterface, PasswordBasedLoginPage
from apps.adapters.framework import download
from apps.adapters.helpers.helper import sleep
from apps.adapters.helpers.webdriver_helper import (
    explicit_wait_till_visibility,
    explicit_wait_till_clickable,
    select_dropdown_option_by_value,
    is_element_present,
    IGNORED_EXCEPTIONS,
    set_implicit_timeout,
)
from apps.adapters.vendors import LOGGER
from apps.runs.models import Run, DiscoveredFile, DocumentType, FileFormat
from spices.datetime_utils import date_from_string

# Home Page Locators
HOME_PAGE_LOCATORS = {"HOME_INVOICES_LINK": 'td[id="ctl00_Header1_menun2"]'}

# Invoices Page Locators
INVOICE_PAGE_LOCATORS = {
    "INVOICES_COMPANY_NAME": 'span[id="ctl00_ContentPlaceHolder1_AccountInfo_accountTabContainer_accountTabPanel_lblCompanyName"]',
    "INVOICES_COMPANY_NUMBER": 'span[id="ctl00_ContentPlaceHolder1_AccountInfo_accountTabContainer_accountTabPanel_lblAccountNumber"]',
    "INVOICES_DATE_FILTER_DROPDOWN": 'select[id="ctl00_ContentPlaceHolder1_InvoicesTabContainer_ctl00_invoices_ddlInvoiceDateFilter"]',
    "INVOICES_DATE_FILTER_DROPDOWN_OPTIONS": 'select[id="ctl00_ContentPlaceHolder1_InvoicesTabContainer_ctl00_invoices_ddlInvoiceDateFilter"]/option',
    "INVOICES_HEADER_DATE": 'span[id="ctl00_ContentPlaceHolder1_InvoicesTabContainer_ctl00_invoices_dlInvoices_ctl00_lblHeaderDate"]',
    "INVOICES_HEADER_INVOICE_NUMBER": "span[id="
    '"ctl00_ContentPlaceHolder1_InvoicesTabContainer_ctl00_invoices_dlInvoices_ctl00_lblHeaderInvoiceNumber"]',
    "INVOICES_HEADER_AMOUNT": "span[id="
    '"ctl00_ContentPlaceHolder1_InvoicesTabContainer_ctl00_invoices_dlInvoices_ctl00_lblHeaderDisplayAmount"]',
    "INVOICES_HEADER_DISCOUNT": 'span[id="ctl00_ContentPlaceHolder1_InvoicesTabContainer_ctl00_invoices_dlInvoices_ctl00_lblHeaderDiscount"]',
    "INVOICES_HEADER_NET_AMOUNT": "span[id="
    '"ctl00_ContentPlaceHolder1_InvoicesTabContainer_ctl00_invoices_dlInvoices_ctl00_lblHeaderDisplayNetAmount"]',
    "INVOICES_HEADER_CASES": 'span[id="ctl00_ContentPlaceHolder1_InvoicesTabContainer_ctl00_invoices_dlInvoices_ctl00_lblHeaderCases"]',
    "INVOICES_HEADER_BOTTLES": 'span[id="ctl00_ContentPlaceHolder1_InvoicesTabContainer_ctl00_invoices_dlInvoices_ctl00_lblHeaderBottles"]',
    "INVOICE_TABLE_ROWS": 'table[id="ctl00_ContentPlaceHolder1_InvoicesTabContainer_ctl00_invoices_dlInvoices"]>tbody>tr',
}

# Invoice Details Page Locators
INVOICE_DETAILS_PAGE_LOCATORS = {
    # 'INVOICE_DETAILS_REPORT_CONTENT': 'div[id="VisibleReportContentreportViewer_ctl09"]',
    "INVOICE_DETAILS_REPORT_CONTENT": "VisibleReportContentreportViewer_ctl09",
    "INVOICE_DETAILS_SAVE_LINK": 'a[id="reportViewer_ctl05_ctl04_ctl00_ButtonLink"]',
    "INVOICE_DETAILS_SAVE_AS_PDF": '//a[@alt="PDF"]',
    "INVOICE_DETAILS_SAVE_AS_EXCEL": '//a[@alt="Excel"]',
}


class SouthernWineOnlineLoginPage(PasswordBasedLoginPage):
    SELECTOR_USERNAME_TEXTBOX = (
        'input[id="ctl00_ContentPlaceHolder1_LoginControl_UserName"]'
    )
    SELECTOR_PASSWORD_TEXTBOX = (
        'input[id="ctl00_ContentPlaceHolder1_LoginControl_Password"]'
    )
    SELECTOR_LOGIN_BUTTON = (
        'input[id="ctl00_ContentPlaceHolder1_LoginControl_loginButton"]'
    )
    SELECTOR_ERROR_MESSAGE_TEXT = "div.errorMessage"


class SouthernWineOnlineHomePage:
    """Southern Wine Online Home page action methods come here."""

    def __init__(self, driver):
        self.driver = driver

    def get_invoices_link(self) -> WebElement:
        """Returns Invoices Link WebElement"""
        return self.driver.find_element_by_css_selector(
            HOME_PAGE_LOCATORS["HOME_INVOICES_LINK"]
        )

    def go_to_invoices_page(self):
        """
        Go to Invoices Page
        :return:
        """
        explicit_wait_till_visibility(
            self.driver,
            self.get_invoices_link(),
            msg="Invoice Link",
            ignored_exceptions=IGNORED_EXCEPTIONS,
        )
        LOGGER.info("Clicking on Invoices Link.")
        self.get_invoices_link().click()


class SouthernWineOnlineInvoicesPage:
    """Southern Wine Online Invoices page action methods come here."""

    def __init__(self, driver):
        self.driver = driver

    def get_company_name(self) -> WebElement:
        """Returns Company name label webelement"""
        return self.driver.find_element_by_css_selector(
            INVOICE_PAGE_LOCATORS["INVOICES_COMPANY_NAME"]
        )

    def get_company_id(self) -> WebElement:
        """Return Company Id label weblement"""
        return self.driver.find_element_by_css_selector(
            INVOICE_PAGE_LOCATORS["INVOICES_COMPANY_NUMBER"]
        )

    @staticmethod
    def get_vendor_name() -> str:
        """Returns Vendor Name"""
        return "Southern Wine Online"

    def get_invoices_date_filter_dropdown(self) -> WebElement:
        """Returns Invoices Date Filter DropDown WebElement"""
        return self.driver.find_element_by_css_selector(
            INVOICE_PAGE_LOCATORS["INVOICES_DATE_FILTER_DROPDOWN"]
        )

    def get_invoice_date_filter_list(self) -> WebElement:
        """Returns the list of Invoice date filter dropdown options"""
        return self.driver.find_elements_by_css_selector(
            INVOICE_PAGE_LOCATORS["INVOICES_DATE_FILTER_DROPDOWN_OPTIONS"]
        )

    def get_invoices_header_date(self) -> WebElement:
        """Returns Invoices Header Date WebElement"""
        return self.driver.find_element_by_css_selector(
            INVOICE_PAGE_LOCATORS["INVOICES_HEADER_DATE"]
        )

    def get_invoices_header_invoice_number(self) -> WebElement:
        """Returns Invoices Header Invoice Number WebElement"""
        return self.driver.find_element_by_css_selector(
            INVOICE_PAGE_LOCATORS["INVOICES_HEADER_INVOICE_NUMBER"]
        )

    def get_invoices_invoices_header_amount(self) -> WebElement:
        """Returns Invoices Header Amount WebElement"""
        return self.driver.find_element_by_css_selector(
            INVOICE_PAGE_LOCATORS["INVOICES_HEADER_AMOUNT"]
        )

    def get_invoices_header_discount(self) -> WebElement:
        """Returns Invoices Header Discount WebElement"""
        return self.driver.find_element_by_css_selector(
            INVOICE_PAGE_LOCATORS["INVOICES_HEADER_DISCOUNT"]
        )

    def get_invoices_header_net_amount(self) -> WebElement:
        """Returns Invoices Header Net Amount WebElement"""
        return self.driver.find_element_by_css_selector(
            INVOICE_PAGE_LOCATORS["INVOICES_HEADER_NET_AMOUNT"]
        )

    def get_invoices_header_cases(self) -> WebElement:
        """Returns Invoices Header Cases WebElement"""
        return self.driver.find_element_by_css_selector(
            INVOICE_PAGE_LOCATORS["INVOICES_HEADER_CASES"]
        )

    def get_invoices_header_bottles(self) -> WebElement:
        """Returns Invoices Header Bottles WebElement"""
        return self.driver.find_element_by_css_selector(
            INVOICE_PAGE_LOCATORS["INVOICES_HEADER_BOTTLES"]
        )

    def get_invoices_table_rows(self):
        """Returns Invoices Table Rows WebElement"""
        return self.driver.find_elements_by_css_selector(
            INVOICE_PAGE_LOCATORS["INVOICE_TABLE_ROWS"]
        )

    def calculate_invoice_date_filter_dropdown_option(
        self, day_count: str
    ) -> (str, None):
        """
        Calculates invoice date filter drop down option by requested day count
        :param day_count: Based on the day count the option value is calculated
        :return: Returns Dropdown option values else None
        """
        LOGGER.info("Calculating invoice date filter drowndown option")
        # options = [x for x in self.get_invoices_date_filter_dropdown().find_elements_by_tag_name("option")]
        options = list(
            self.get_invoices_date_filter_dropdown().find_elements_by_tag_name("option")
        )
        for elem in options:
            option_value = elem.get_attribute("value")
            LOGGER.info("Dropdown options: %s", option_value)
            if int(day_count) <= int(option_value):
                LOGGER.info("Returning %s", option_value)
                return option_value
        return None

    def has_invoices(self) -> bool:
        try:
            set_implicit_timeout(self.driver, 5)
            explicit_wait_till_visibility(
                self.driver, self.get_invoices_table_rows()[0], msg="Invoice Table Row"
            )
            return True
        except IndexError:
            LOGGER.info(f"No invoices were found!")
            return False
        finally:
            set_implicit_timeout(self.driver, 15)

    def get_invoice_table_data(self, run: Run, from_date: date) -> List[DiscoveredFile]:
        """
        Extracts invoice details from Table
        :param run: Run Object
        :param from_date: Start date of the invoices to be downloaded
        :return: Returns the list of Discovered Files
        """
        discovered_files = []
        pdf_links_list = []
        sleep(1, "for invoice table to load.")
        if not self.has_invoices():
            return discovered_files
        LOGGER.info("Extracting Invoice table date.")

        rows = self.get_invoices_table_rows()
        for row in rows[1:]:
            invoice_date = date_from_string(
                row.find_elements_by_tag_name("span")[0].text, "%m/%d/%Y"
            )
            if invoice_date < from_date:
                return discovered_files

            if not is_element_present(self.driver, row.find_element_by_tag_name("a")):
                continue

            invoice_number = row.find_elements_by_tag_name("span")[1].text
            pdf_link = row.find_element_by_tag_name("a").get_attribute("href")
            reference_code = invoice_number

            if pdf_link in pdf_links_list:
                continue

            pdf_links_list.append(pdf_link)

            document_properties = {
                "invoice_number": invoice_number,
                "invoice_date": str(invoice_date),
                "due_date": "",
                "total_amount": row.find_elements_by_tag_name("span")[4].text,
                "vendor_name": self.get_vendor_name(),
                "restaurant_name": self.get_company_name().text,
                "customer_number": self.get_company_id().text,
                # 'amount': row.find_elements_by_tag_name('span')[2].text,
                # 'discount': row.find_elements_by_tag_name('span')[3].text,
                # 'cases': row.find_elements_by_tag_name('span')[5].text,
                # 'bottles': row.find_elements_by_tag_name('span')[6].text
            }
            try:
                # pylint: disable=no-member
                discovered_file = DiscoveredFile.build_unique(
                    run,
                    reference_code,
                    document_type=DocumentType.INVOICE.ident,
                    file_format=FileFormat.PDF.ident,
                    original_download_url=pdf_link,
                    original_filename=f"{invoice_number}.pdf",
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


class SouthernWineOnlineInvoiceDetailsPage:
    """Southern Wine Online Print Invoices page action methods come here."""

    def __init__(self, driver):
        self.driver = driver

    def get_invoice_save_link(self) -> WebElement:
        """Returns Invoices Save Link WebElement"""
        return self.driver.find_element_by_css_selector(
            INVOICE_DETAILS_PAGE_LOCATORS["INVOICE_DETAILS_SAVE_LINK"]
        )

    def get_invoice_save_as_pdf(self) -> WebElement:
        """Returns the list of Invoice Save As PDF options"""
        return self.driver.find_element_by_xpath(
            INVOICE_DETAILS_PAGE_LOCATORS["INVOICE_DETAILS_SAVE_AS_PDF"]
        )

    def get_invoice_save_as_excel(self) -> WebElement:
        """Returns the list of Invoice Save As Excel options"""
        return self.driver.find_element_by_xpath(
            INVOICE_DETAILS_PAGE_LOCATORS["INVOICE_DETAILS_SAVE_AS_EXCEL"]
        )

    def get_invoice_details_report_content(self) -> WebElement:
        """Returns the list of Invoice Details Report Content options"""
        return self.driver.find_element_by_id(
            INVOICE_DETAILS_PAGE_LOCATORS["INVOICE_DETAILS_REPORT_CONTENT"]
        )

    def get_img_src(self):
        """Returns the Image Src from which File Download URL will be formed"""
        return self.driver.find_elements_by_css_selector("table tbody img")[3]

    def get_download_url(self) -> str:
        """
        Create file download url
        :return: URL of the File
        """
        file_url = furl(self.get_img_src().get_attribute("src"))
        del file_url.args["OpType"]
        del file_url.args["IterationId"]
        del file_url.args["StreamID"]
        file_url.args["Mode"] = "true"
        file_url.args["OpType"] = "Export"
        file_url.args["FileName"] = "Invoice"
        file_url.args["ContentDisposition"] = "AlwaysAttachment"
        file_url.args["Format"] = "PDF"
        LOGGER.info("File URL: %s", file_url)
        return file_url.url

    def download_documents_by_link(
        self, download_location: str, discovered_files: List[DiscoveredFile]
    ):
        """
        Downloads the invoice & renames it with the actual invoice Number
        Retries the downloading 3 times in case of exceptions
        :param download_location:
        :param discovered_files: List of Discovered files
        :return: Nothing
        """
        for discovered_file in discovered_files:
            LOGGER.info(f"Navigate to: {discovered_file.original_download_url}")
            self.driver.get(discovered_file.original_download_url)
            explicit_wait_till_clickable(
                self.driver,
                (
                    By.ID,
                    INVOICE_DETAILS_PAGE_LOCATORS["INVOICE_DETAILS_REPORT_CONTENT"],
                ),
            )

            # here, the download_url is different from `discovered_file.original_download_url`
            # because we need to generate a special URL to get the file
            _downloader = download.DriverBasedUrlGetDownloader(
                self.driver,
                download_url=str(self.get_download_url()),
                local_filepath=os.path.join(download_location, "Invoice.pdf"),
                rename_to=os.path.join(
                    download_location, discovered_file.original_filename
                ),
            )
            download.download_discovered_file(discovered_file, _downloader)


class SouthernWineOnlineRunner(VendorDocumentDownloadInterface):
    """Runner Class for Southern Wine Online"""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.login_page = SouthernWineOnlineLoginPage(self.driver)
        self.home_page = SouthernWineOnlineHomePage(self.driver)
        self.invoices_page = SouthernWineOnlineInvoicesPage(self.driver)
        self.invoice_details_page = SouthernWineOnlineInvoiceDetailsPage(self.driver)

    def _login(self):
        """
        Login to Southern Wine Online
        :return: Nothing
        """
        login_url = "https://southernwineonline.com/"
        LOGGER.info(f"Navigating to {login_url}")
        self.driver.get(login_url)
        self.login_page.login(self.run.job.username, self.run.job.password)
        explicit_wait_till_visibility(
            self.driver,
            self.home_page.get_invoices_link(),
            msg="Invoice Link",
            ignored_exceptions=IGNORED_EXCEPTIONS,
        )

    def _goto_download_page(self, document_type: str):
        """
        Go to download page based on the document type
        :param document_type: Specifies the type of the document eg. Invoice/Statement etc.
        :return:
        """
        if document_type == "invoice":
            self.home_page.go_to_invoices_page()
            explicit_wait_till_visibility(
                self.driver,
                self.invoices_page.get_invoices_date_filter_dropdown(),
                msg="Invoices Date Filter DropDown",
                ignored_exceptions=IGNORED_EXCEPTIONS,
            )
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
        explicit_wait_till_visibility(
            self.driver,
            self.invoices_page.get_invoices_date_filter_dropdown(),
            msg="Invoices Date Filter DropDown",
            ignored_exceptions=IGNORED_EXCEPTIONS,
        )

        LOGGER.info("Download invoice process begins.")

        option = "30"
        LOGGER.info(f"Selecting {option} option from the dropdown.")
        select_dropdown_option_by_value(
            self.invoices_page.get_invoices_date_filter_dropdown(), option
        )

        start_date = datetime.strptime(
            self.run.request_parameters["start_date"], "%Y-%m-%d"
        ).date()
        # Fetching all invoice table date & storing it in memory
        discovered_files_list = self.invoices_page.get_invoice_table_data(
            self.run, start_date
        )

        LOGGER.info(
            f"Total Invoices within date range and download link available: {len(discovered_files_list)}"
        )

        # Download all the invoices
        self.invoice_details_page.download_documents_by_link(
            self.download_location, discovered_files_list
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
            self._goto_download_page(self.run.job.requested_document_type)

            discovered_files += self._download_documents()
        finally:
            self._quit_driver()

        return discovered_files

    def login_flow(self, run: Run):
        self._login()
