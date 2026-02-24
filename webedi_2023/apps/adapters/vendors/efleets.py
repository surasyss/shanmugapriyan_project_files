import os
import re

from datetime import datetime, date
from typing import List
from retry.api import retry

from selenium.webdriver.remote.webelement import WebElement
from selenium.common.exceptions import WebDriverException
from spices.enum_utils import BaseChoice
from spices.services import ContextualError

from apps.adapters.base import PasswordBasedLoginPage, VendorDocumentDownloadInterface
from apps.adapters.framework import download
from apps.adapters.helpers.webdriver_helper import (
    explicit_wait_till_visibility,
    wait_for_loaders,
    wait_for_element,
)
from apps.runs.models import Run, DiscoveredFile, DocumentType, FileFormat
from integrator import LOGGER
from spices.datetime_utils import date_from_string

# Home Page Locators
HOME_PAGE_LOCATORS = {
    "INVOICE_TABLE_HEADER_ROW": "div.ui-grid-header>div.ui-grid-top-panel>div.ui-grid-header-viewport",
    "INVOICE_TABLE_ROWS": "div.ui-grid-canvas>div",
    "LOADER": "div.loading-div, img.loading-img",
    "MFA_ENABLED": "div.mfaLogin p",
}

# Billing Details Page Locators
BILLING_DETAILS_PAGE_LOCATOR = {
    "INVOICE_TABLE_CELLS": "div.ui-grid-cell-contents",
    "INVOICE_TABLE_ROWS": "div.ui-grid-canvas>div.ui-grid-row",
    "DOWNLOAD_BUTTON": "#download-button",
    "DOWNLOAD_BUTTON_OPTIONS_CSV": "li.ui-menu-item",
    "RESTAURANT_DROPDOWN": "ul.groupedSelect > li > a",
    "ACCOUNT_DROPDOWN": "span.groupedMenuWrapper",
    "MONTH_YEAR_DROPDOWN": 'select[id="asOfDate"] option',
    "CHANGE_COMPANY_DROPDOWN": "#ChangeCompanyWrapper>a",
    "CHANGE_COMPANY_DROPDOWN_OPTIONS": 'ul[class^="company-list"]>div>a',
}

# Billing Summary Page Locators
BILLING_SUMMARY_LOCATORS = {
    "INVOICE_DATE": "div.billing-summary div.row div.large-6.columns p",
    "INVOICE_TOTAL_AMT": "div.billing-summary div.row div.columns table.stack td.text-right a",
    "RESTAURANT_DROPDOWN": "ul.groupedSelect > li > a",
    "ACCOUNT_DROPDOWN": "span.groupedMenuWrapper",
    "DUE_DATE": "div.billing-summary div.row div.small-push-6.large-push-0 p",
}


class EfleetsLoginPage(PasswordBasedLoginPage):
    """Efleets Login Page Web Elements"""

    SELECTOR_USERNAME_TEXTBOX = 'input[id="userId"]'
    SELECTOR_PASSWORD_TEXTBOX = 'input[id="password"]'
    SELECTOR_LOGIN_BUTTON = 'input[id="signInButton"]'
    SELECTOR_ERROR_MESSAGE_TEXT = (
        "div.loginError div.error, form[action='changePassword']"
    )


class EfleetsHomePage:
    """Efleets Home page action methods come here."""

    def __init__(self, driver):
        self.driver = driver

    def get_table_header_row(self) -> WebElement:
        """Return the Home Page Table header Row"""
        return self.driver.find_element_by_css_selector(
            HOME_PAGE_LOCATORS["INVOICE_TABLE_HEADER_ROW"]
        )

    def get_table_rows(self) -> List[WebElement]:
        """Returns Homepage Table data rows"""
        return self.driver.find_elements_by_css_selector(
            HOME_PAGE_LOCATORS["INVOICE_TABLE_ROWS"]
        )

    def change_company_dropdown(self) -> WebElement:
        """Return Home company name drop down button"""
        return self.driver.find_element_by_css_selector(
            BILLING_DETAILS_PAGE_LOCATOR["CHANGE_COMPANY_DROPDOWN"]
        )

    def change_company_dropdown_options(self) -> List[WebElement]:
        """Return the company name list in dropdown"""
        return self.driver.find_elements_by_css_selector(
            BILLING_DETAILS_PAGE_LOCATOR["CHANGE_COMPANY_DROPDOWN_OPTIONS"]
        )

    def loader(self) -> WebElement:
        """Returns the page loader web element"""
        return self.driver.find_element_by_css_selector(HOME_PAGE_LOCATORS["LOADER"])

    def wait_for_loaders(self):
        wait_for_loaders(self.driver, value=HOME_PAGE_LOCATORS["LOADER"])


class EfleetsBillingSummaryPage:
    """Efleets Billing Summary page action methods come here."""

    def __init__(self, driver):
        self.driver = driver

    def navigate_to_billing_summary_page(self):
        """Navigates to the Billing summary page"""
        billing_summary_url = (
            "https://login.efleets.com/fleetweb/billing/billingSummary"
        )
        LOGGER.info("Navigating to %s.", billing_summary_url)
        self.driver.get(billing_summary_url)
        wait_for_element(
            self.driver,
            value=BILLING_SUMMARY_LOCATORS["INVOICE_TOTAL_AMT"],
            msg="Invoice Total Amount",
        )

    def get_invoice_date(self) -> WebElement:
        """Return the invoice date Web Element"""
        return self.driver.find_element_by_css_selector(
            BILLING_SUMMARY_LOCATORS["INVOICE_DATE"]
        )

    def get_total_amount(self) -> WebElement:
        """Return the invoice total amount Web Element"""
        return self.driver.find_element_by_css_selector(
            BILLING_SUMMARY_LOCATORS["INVOICE_TOTAL_AMT"]
        )

    def get_invoice_due_date(self) -> WebElement:
        """Returnn invoice due date Web Element"""
        return self.driver.find_elements_by_css_selector(
            BILLING_SUMMARY_LOCATORS["DUE_DATE"]
        )[0]

    def get_account_dropdown(self) -> WebElement:
        """Return restaurant account dropdown Button Web Element"""
        return self.driver.find_element_by_css_selector(
            BILLING_SUMMARY_LOCATORS["RESTAURANT_DROPDOWN"]
        )

    def get_account_dropdown_options(self) -> List[WebElement]:
        """Return restaurant account list in dropdown"""
        return self.driver.find_elements_by_css_selector(
            BILLING_SUMMARY_LOCATORS["ACCOUNT_DROPDOWN"]
        )

    def get_account_dropdown_options_list(self) -> List:
        """Return the list of the Dropdown text for restaurant account"""
        accounts = self.get_account_dropdown_options()
        account_list = []

        for account in accounts:
            account_list.append(account.text)

        # accounts[0] is the first restaurant of the list
        explicit_wait_till_visibility(
            self.driver, accounts[0], msg="Restaurant Account List"
        )
        self.get_invoice_date().click()
        return account_list

    def select_account_by_name(self, account_name, account_names):
        """
        Select the restaurant account by name
        :param account_name: Name of the restaurant account to select
        :param account_names: Names of all the restaurant account we have
        :self.get_account_dropdown_options()[0]: is the first element of the account List
        """
        self.get_account_dropdown().click()
        # Fetching 1st Element returned
        wait_for_element(
            self.driver,
            value=BILLING_SUMMARY_LOCATORS["ACCOUNT_DROPDOWN"],
            msg="1st Restaurant Account",
        )
        accounts = self.get_account_dropdown_options()
        for index, account in enumerate(account_names):
            if account_name == account:
                accounts[index].click()

    def format_invoice_date(self):
        """Formats the invoice date from summary page"""
        for _ in range(5):
            wait_for_element(
                self.driver,
                value=BILLING_SUMMARY_LOCATORS["INVOICE_DATE"],
                msg="Invoice Date",
            )
            invoice_date = self.get_invoice_date().text
            date_search = re.search(r"\d+/\d+/\d+", invoice_date)
            if date_search:
                # Invoice date(06/03/2020) to fetch from :- As of 06/03/2020
                return date_search.group()
        return None

    def format_invoice_total_amount(self):
        """Formats the invoice total amount from the summary date"""
        wait_for_element(
            self.driver,
            value=BILLING_SUMMARY_LOCATORS["INVOICE_TOTAL_AMT"],
            msg="Invoice Total Amount",
        )
        total_amount = self.get_total_amount().text
        return total_amount

    def get_invoice_data(self, customer_identity_number) -> dict:
        """
        Prepare the invoice data for the discovered files
        :param customer_identity_number: This is the customer id or you can say the Company ID
        """
        invoice_date = self.format_invoice_date()
        customer_id = customer_identity_number
        total_amount = self.format_invoice_total_amount()
        # Restaurant Name(B&G FOOD ENTERPRISES) to fetch from :- B&G FOOD ENTERPRISES (227930B)
        restaurant = self.get_account_dropdown().text.split(" (")
        restaurant_name = restaurant[0]
        restaurant_id = restaurant[1].replace(")", "")
        # Fetching 1st element returned
        wait_for_element(
            self.driver,
            value=BILLING_SUMMARY_LOCATORS["DUE_DATE"],
            msg="Invoice Due Date",
        )

        # Invoice Due Date(06/20/2020) to fetch from :- Due date: 06/20/2020'
        invoice_due_date = self.get_invoice_due_date().text.split(": ")[1]
        invoice_details = {
            "invoice_date": invoice_date,
            "customer_id": customer_id,
            "total_amount": total_amount,
            "restaurant_id": restaurant_id,
            "restaurant_name": restaurant_name,
            "invoice_due_date": invoice_due_date,
        }

        return invoice_details


class EfleetsBillingDetailPage:
    def __init__(self, driver, download_location: str):
        self.driver = driver
        self.home_page = EfleetsHomePage(self.driver)
        self.billing_summary_page = EfleetsBillingSummaryPage(self.driver)
        self.download_location = download_location
        self.vendor_name = "Enterprise Fleet Management"

    @property
    def get_change_company(self) -> WebElement:
        """Get change company link element"""
        return self.driver.find_element_by_css_selector(
            BILLING_DETAILS_PAGE_LOCATOR["CHANGE_COMPANY_DROPDOWN"]
        )

    @property
    def get_change_company_list(self) -> List[WebElement]:
        """Get all companies list elements"""
        return self.driver.find_elements_by_css_selector(
            BILLING_DETAILS_PAGE_LOCATOR["CHANGE_COMPANY_DROPDOWN_OPTIONS"]
        )

    def get_table_header_row(self) -> WebElement:
        """Returns Billing Details page Table header row"""
        return self.driver.find_element_by_css_selector(
            HOME_PAGE_LOCATORS["INVOICE_TABLE_HEADER_ROW"]
        )

    def get_table_rows(self) -> List[WebElement]:
        """Returns the Billing details table rows"""
        return self.driver.find_elements_by_css_selector(
            BILLING_DETAILS_PAGE_LOCATOR["INVOICE_TABLE_ROWS"]
        )

    def get_account_dropdown(self) -> WebElement:
        """Return restaurant account dropdown Button Web Element"""
        return self.driver.find_element_by_css_selector(
            BILLING_DETAILS_PAGE_LOCATOR["RESTAURANT_DROPDOWN"]
        )

    def get_account_dropdown_options(self) -> List[WebElement]:
        """Return restaurant account list in dropdown"""
        return self.driver.find_elements_by_css_selector(
            BILLING_DETAILS_PAGE_LOCATOR["ACCOUNT_DROPDOWN"]
        )

    def month_selector(self) -> List[WebElement]:
        """Month Select element in the Billing details page"""
        return self.driver.find_elements_by_css_selector(
            BILLING_DETAILS_PAGE_LOCATOR["MONTH_YEAR_DROPDOWN"]
        )

    def get_download_dropdown(self) -> WebElement:
        """Returns the Download Button Web Element"""
        return self.driver.find_elements_by_css_selector(
            BILLING_DETAILS_PAGE_LOCATOR["DOWNLOAD_BUTTON"]
        )[0]

    def get_download_dropdown_options(self) -> WebElement:
        """Return the Download button list in the dropdpwn"""
        return self.driver.find_elements_by_css_selector(
            BILLING_DETAILS_PAGE_LOCATOR["DOWNLOAD_BUTTON_OPTIONS_CSV"]
        )[0]

    @retry(WebDriverException, tries=3, delay=2)
    def navigate_to_billing_details_page(self):
        """Navigate to the Billing details Page"""
        billing_details_url = (
            "https://login.efleets.com/fleetweb/billing/billingDetails"
        )
        LOGGER.info("Navigating to %s.", billing_details_url)
        self.driver.get(billing_details_url)
        self.home_page.wait_for_loaders()
        # Fetching 1st element returned
        wait_for_element(
            self.driver,
            value=BILLING_DETAILS_PAGE_LOCATOR["INVOICE_TABLE_ROWS"],
            msg="1st table row",
        )

    def get_invoice_number_index(self):
        """
        Get the index of the invoice number
        :return: Index of the invoice number column
        """
        headers = self.get_table_header_row().find_elements_by_css_selector(
            BILLING_DETAILS_PAGE_LOCATOR["INVOICE_TABLE_CELLS"]
        )
        for index, header in enumerate(headers):
            if header.text == "Consolid Inv Num":
                return index
        return None

    def get_invoice_table_data(
        self, run: Run, from_date: date, customer_id: str
    ) -> List[DiscoveredFile]:
        """
        Extracts invoice details from Table
        :param customer_id: Customer ID
        :param run: Run Object
        :param from_date: Start date of the invoices to be downloaded
        :return: Returns the list of Discovered File
        """
        wait_for_element(
            self.driver,
            value=BILLING_DETAILS_PAGE_LOCATOR["RESTAURANT_DROPDOWN"],
            msg="Account Dropdown",
        )
        self.get_account_dropdown().click()

        # Fetchnig 1st element returned
        wait_for_element(
            self.driver,
            value=BILLING_DETAILS_PAGE_LOCATOR["ACCOUNT_DROPDOWN"],
            msg="1st Account dropdown option",
        )
        discovered_files = []
        account_names = self.billing_summary_page.get_account_dropdown_options_list()

        for account in account_names:
            self.billing_summary_page.select_account_by_name(account, account_names)
            self.home_page.wait_for_loaders()

            invoice_data = self.billing_summary_page.get_invoice_data(customer_id)
            self.navigate_to_billing_details_page()
            self.billing_summary_page.select_account_by_name(account, account_names)

            self.home_page.wait_for_loaders()

            # Fetching 1st element returned
            wait_for_element(
                self.driver,
                value=BILLING_DETAILS_PAGE_LOCATOR["INVOICE_TABLE_ROWS"],
                msg="1st table row",
            )
            LOGGER.info("Extracting invoice details data from the invoice table.")

            first_row = self.get_table_rows()[0].find_elements_by_css_selector(
                BILLING_DETAILS_PAGE_LOCATOR["INVOICE_TABLE_CELLS"]
            )
            # pylint: disable=no-member
            invoice_date = date_from_string(
                invoice_data.get("invoice_date"), "%m/%d/%Y"
            )

            if invoice_date < from_date:
                return discovered_files

            invoice_number = first_row[self.get_invoice_number_index()].text
            reference_code = f'{invoice_data.get("customer_id")}_{invoice_data.get("restaurant_id")}_{invoice_number}'
            document_properties = {
                "customer_number": customer_id,
                "invoice_number": invoice_number,
                "invoice_date": str(invoice_data.get("invoice_date")),
                "due_date": invoice_data.get("invoice_due_date"),
                "total_amount": invoice_data.get("total_amount"),
                "vendor_name": self.vendor_name,
                "restaurant_name": invoice_data.get("restaurant_name"),
            }
            try:
                # pylint: disable=no-member
                discovered_file = DiscoveredFile.build_unique(
                    run,
                    reference_code,
                    document_type=DocumentType.INVOICE.ident,
                    file_format=FileFormat.CSV.ident,
                    original_download_url="NA",
                    original_filename=f'BillingDetail_{invoice_data.get("restaurant_id")}_'
                    f'{self.month_selector()[0].text.replace(" ", "-")}.csv',
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
            self.download_invoice_by_click(discovered_file)

        return discovered_files

    def download_invoice_by_click(self, discovered_file):
        """
        Download the File in CSV format
        :param discovered_file: DiscoveredFile validable variable
        """
        # click download dropdown
        self.get_download_dropdown().click()

        # wait for download button to show
        # Fetching 1st element returned
        wait_for_element(
            self.driver,
            value=BILLING_DETAILS_PAGE_LOCATOR["DOWNLOAD_BUTTON_OPTIONS_CSV"],
            msg="Download csv button",
        )
        download_element = self.get_download_dropdown_options()

        # download file etc
        local_filepath = os.path.join(
            self.download_location, discovered_file.original_filename
        )
        _downloader = download.WebElementClickBasedDownloader(
            element=download_element,
            local_filepath=local_filepath,
            file_exists_check_kwargs=dict(timeout=20),
        )
        download.download_discovered_file(discovered_file, _downloader)


class EfleetsRunner(VendorDocumentDownloadInterface):
    """Runner Class for Enterprise Fleet Management"""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.login_page = EfleetsLoginPage(self.driver)
        self.home_page = EfleetsHomePage(self.driver)
        self.billing_summary_page = EfleetsBillingSummaryPage(self.driver)
        self.billing_detail_page = EfleetsBillingDetailPage(
            self.driver, self.download_location
        )

    @retry(WebDriverException, tries=3, delay=2)
    def _login(self):
        """
        Login using credentials
        :return: Nothing
        """
        login_url = "https://login.efleets.com/fleetweb/login"
        LOGGER.info("Navigating to %s.", login_url)
        self.driver.get(login_url)
        wait_for_element(
            self.driver,
            value=self.login_page.SELECTOR_LOGIN_BUTTON,
            msg="Login Submit Button",
        )
        self.login_page.login(self.run.job.username, self.run.job.password)

    def _post_login_action(self):
        mfa_login = self.get_mfa_login_elements()
        if mfa_login:
            LOGGER.info(mfa_login[0].text)
            raise ContextualError(
                code=ErrorCode.ACCOUNT_MFA_ENABLED_WEB.ident,
                message=ErrorCode.ACCOUNT_MFA_ENABLED_WEB.message.format(
                    username=self.run.job.username
                ),
            )

        wait_for_element(
            self.driver,
            value=HOME_PAGE_LOCATORS["INVOICE_TABLE_HEADER_ROW"],
            msg="Table Header Row",
        )

    def get_mfa_login_elements(self) -> List[WebElement]:
        return self.driver.find_elements_by_css_selector(
            HOME_PAGE_LOCATORS["MFA_ENABLED"]
        )

    def _download_documents(self, customer_id) -> List[DiscoveredFile]:
        """
        Chooses the documents to be downloaded based on the document type
        :return: Returns the list of Discovered Files
        """
        document_type = self.run.job.requested_document_type
        if document_type == "invoice":
            return self._download_invoices(customer_id)

        raise NotImplementedError(
            f"Requested Document Type is not supported: {document_type}"
        )

    def _download_invoices(self, customer_id) -> List[DiscoveredFile]:
        """
        Downloads the Invoices
        :return: Returns the list of the Discovered Files
        """
        LOGGER.info("Extracting data from table...")
        start_date = datetime.strptime(
            self.run.request_parameters["start_date"], "%Y-%m-%d"
        ).date()

        discovered_files_list = self.billing_detail_page.get_invoice_table_data(
            self.run, start_date, customer_id
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
            self._post_login_action()
            self.home_page.wait_for_loaders()

            # change company link initial click
            self.billing_detail_page.get_change_company.click()

            for row_count, _ in enumerate(
                self.billing_detail_page.get_change_company_list
            ):

                if row_count > 1:
                    # after one company change request click dropdown link
                    self.billing_detail_page.get_change_company.click()

                # choose company in the list
                select_option = self.billing_detail_page.get_change_company_list[
                    row_count
                ]

                # filter number only by regex
                customer_id = re.sub(
                    r"[^\d+]", "", select_option.get_attribute("innerText")
                )

                # select the company
                select_option.click()

                wait_for_element(
                    self.driver,
                    value=HOME_PAGE_LOCATORS["INVOICE_TABLE_HEADER_ROW"],
                    msg="Table Header Row",
                )

                self.billing_summary_page.navigate_to_billing_summary_page()
                self.home_page.wait_for_loaders()
                wait_for_element(
                    self.driver,
                    value=BILLING_SUMMARY_LOCATORS["INVOICE_TOTAL_AMT"],
                    msg="Total Amount",
                )

                discovered_files += self._download_documents(customer_id)
        finally:
            self._quit_driver()

        return discovered_files

    def login_flow(self, run: Run):
        self._login()


class ErrorCode(BaseChoice):
    ACCOUNT_MFA_ENABLED_WEB = (
        "intgrt.mfa_enabled.web",
        "Multi Factor Authentication enabled (username: {username})",
    )
