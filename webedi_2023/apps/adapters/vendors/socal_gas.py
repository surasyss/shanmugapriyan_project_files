import os
from datetime import datetime, date
from typing import List

from retry.api import retry
from selenium.common.exceptions import (
    StaleElementReferenceException,
    WebDriverException,
    NoSuchElementException,
    TimeoutException,
)
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.select import Select
from selenium.webdriver.remote.webelement import WebElement
from selenium.webdriver.support.wait import WebDriverWait

from apps.adapters.base import PasswordBasedLoginPage, VendorDocumentDownloadInterface
from apps.adapters.framework import download
from apps.adapters.helpers.webdriver_helper import (
    get_url,
    handle_popup,
    explicit_wait_till_url_contains,
    wait_for_loaders,
    wait_for_element,
    select_dropdown_option_by_visible_text,
    explicit_wait_till_visibility,
    close_extra_handles,
    has_invoices,
    WEB_DRIVER_EXCEPTIONS,
)
from apps.runs.models import Run, DiscoveredFile, DocumentType, FileFormat
from integrator import LOGGER
from spices.datetime_utils import date_from_string

# Home Page Locators
HOME_PAGE_LOCATORS = {
    "LOADER": "span.af_document_splash-screen-message",
    "LOGOUT_BUTTON": "//*[contains(text(),'Log Out')]",
    "POP_UP": "div.main-content.af_panelGroupLayout a.af_commandLink",
    "BODY_LOADER": 'body[style="cursor: wait;"]',
    "CONFIRM": 'button[id="pt1:cb2"]',
}

REVIEW_INFO_PAGE_LOCATORS = {
    "MY_INFO_IS_CORRECT_LINK": '//a[text()="My information is correct"]'
}

# Billing History Page Locators
BILLING_HISTORY_PAGE = {
    "ACCOUNT_DROPDOWN": "select.af_selectOneChoice_content, span.af_selectOneChoice_content",
    "GO_BUTTON": "button.btnGo",
    "EXPORT_TO_EXCEL_LINK": '//a[text()="Export to Excel"]',
    "TABLE_ROWS": 'div[id="pt1:pgl5"] table tbody tr',
}


class SoCalGasLoginPage(PasswordBasedLoginPage):
    """SoCal Gas Login Page Web Elements"""

    SELECTOR_USERNAME_TEXTBOX = 'input[id="pt1:pli1:loginid::content"]'
    SELECTOR_PASSWORD_TEXTBOX = 'input[id="pt1:pwli:pwd::content"]'
    SELECTOR_LOGIN_BUTTON = 'button[id="pt1:cb1"]'
    SELECTOR_ERROR_MESSAGE_TEXT = "div[id='pt1:errli:pgl3'], iframe[title^='recaptcha']"


class SoCalGasBillingHistoryPage:
    """Billing History Page class for SoCal Gas"""

    def __init__(self, driver, download_location: str):
        self.driver = driver
        self.download_location = download_location
        self.vendor = "SoCal Gas"

    def get_account_dropdown(self) -> WebElement:
        """Return Account dropdown WebElement"""
        return self.driver.find_element_by_css_selector(
            BILLING_HISTORY_PAGE["ACCOUNT_DROPDOWN"]
        )

    def get_account_dropdown_list_text(self) -> list:
        """Return Account Dropdown options text"""
        for _ in range(5):
            try:
                explicit_wait_till_visibility(
                    self.driver,
                    self.get_account_dropdown(),
                    timeout=10,
                    msg="Select Account Dropdown",
                )

                selected_account_text = self.get_account_dropdown().text
                try:
                    account_names_list = [
                        account_name.strip()
                        for account_name in selected_account_text.split("\n")
                    ]
                except NoSuchElementException:
                    td = self.driver.find_element_by_xpath(
                        '//td/span[text()="Account:"]/following::td'
                    )
                    account_names_list = [td.text]
                LOGGER.info(f"Accounts: {account_names_list}")
                return account_names_list

            except StaleElementReferenceException:
                LOGGER.warning(
                    "Element is not attached to the page document. Finding it again..."
                )

    def navigate_to_billing_history_page(self):
        """Navigate to the Billing History page"""
        billing_history_url = (
            "https://business.socalgas.com/portal/faces/adf.task-flow?adf.tfId=bill-history-flow&"
            "adf.tfDoc=/WEB-INF/taskflows/billHistory/bill-history-flow.xml&"
            "_adf.ctrl-state=yloi7l0vu_90&nodeId=billHistory913913136"
        )
        home_page_url = "https://business.socalgas.com/portal/faces/pages/myaccount/myAccountHome.jspx"

        for index in range(5):
            try:
                get_url(self.driver, billing_history_url)
                wait_for_element(
                    self.driver,
                    by_selector=By.XPATH,
                    value=BILLING_HISTORY_PAGE["EXPORT_TO_EXCEL_LINK"],
                    msg="Export to Excel link",
                    retry_attempts=1,
                )
                if self.driver.current_url != home_page_url:
                    LOGGER.info(
                        f"{index}. Navigated to billing history page: {self.driver.current_url}"
                    )
                    if has_invoices(self.driver, value="div.desktopTabletTable table"):
                        break

            except WebDriverException as excep:
                LOGGER.warning(
                    f"Something went wrong while navigating to Billing History Page - {excep}"
                )

    def select_account(self, account: str):
        for _ in range(5):
            try:
                wait_for_element(
                    self.driver,
                    value=BILLING_HISTORY_PAGE["ACCOUNT_DROPDOWN"],
                    retry_attempts=2,
                    msg="Select Account Dropdown",
                    raise_exception=False,
                )
                try:
                    account_dropdown = self.get_account_dropdown()
                except NoSuchElementException:
                    LOGGER.info(
                        f"Accounts dropdown not found. Current page url is {self.driver.current_url}"
                    )
                    self.navigate_to_billing_history_page()
                    continue

                select_dropdown_option_by_visible_text(account_dropdown, account)
                wait_for_loaders(
                    self.driver, value=HOME_PAGE_LOCATORS["BODY_LOADER"], timeout=10
                )

                if Select(account_dropdown).first_selected_option.text == account:
                    LOGGER.info(f"Selected {account} from the Account DropDown.")
                    break
            except StaleElementReferenceException:
                LOGGER.warning("Element becomes stale. Finding it again...")

    def get_go_button(self) -> WebElement:
        """Return GO button Web Element"""
        return self.driver.find_element_by_css_selector(
            BILLING_HISTORY_PAGE["GO_BUTTON"]
        )

    def get_billing_period(self, index):
        for _ in range(3):
            try:
                row = self.get_table_rows()[index]
                return row.find_elements_by_css_selector("td")[1].text.replace(
                    "Corrected", ""
                )
            except (StaleElementReferenceException, NoSuchElementException) as excep:
                LOGGER.info(f"{excep} found in {self.driver.current_url}")
                if index == 2:
                    raise

    def get_table_rows(self) -> List[WebElement]:
        """Return the table row data"""
        return self.driver.find_elements_by_css_selector(
            BILLING_HISTORY_PAGE["TABLE_ROWS"]
        )

    def get_table_data(
        self, run: Run, from_date: date, restaurant_name: str, account_number: str
    ) -> List[DiscoveredFile]:
        """
        Extracts invoice details from Table
        :param run: Run Object
        :param from_date: Start date of the invoices to be downloaded
        :param account_number: Accounts account number
        :param restaurant_name: Account Name
        :return: Returns the list of Discovered File
        """
        discovered_files = []
        try:
            wait_for_element(
                self.driver,
                value=BILLING_HISTORY_PAGE["TABLE_ROWS"],
                msg="Table 1st row",
                retry_attempts=1,
            )
        except WebDriverException as excep:
            LOGGER.warning(f"No Table rows found. {excep}")
            return discovered_files

        LOGGER.info(f"Extract invoice table data.")
        for index, _ in enumerate(self.get_table_rows()):
            billing_period = self.get_billing_period(index)
            invoice_date = date_from_string(
                billing_period.split("\n")[0].split("-")[1].strip(), "%m/%d/%y"
            )

            if invoice_date < from_date:
                LOGGER.info(
                    f"Skipping invoices because date '{invoice_date}' is outside requested range"
                )
                return discovered_files

            reference_code = f"{account_number}_{invoice_date}"
            file_name = f"{account_number[:-1]}_{invoice_date}"

            document_properties = {
                "invoice_number": reference_code,
                "customer_number": account_number,
                "invoice_date": f"{invoice_date}",
                "total_amount": self.get_download_element(index).text,
                "vendor_name": self.vendor,
                "restaurant_name": restaurant_name,
            }
            try:
                # pylint: disable=no-member
                discovered_file = DiscoveredFile.build_unique(
                    run,
                    reference_code,
                    document_type=DocumentType.INVOICE.ident,
                    file_format=FileFormat.PDF.ident,
                    original_download_url=reference_code,
                    original_filename=f"{file_name}.pdf",
                    document_properties=document_properties,
                )
            except DiscoveredFile.AlreadyExists:
                LOGGER.info(
                    f"Discovered file already exists with reference code : {reference_code}"
                )
                continue  # skip if seen before
            discovered_files.append(discovered_file)
            LOGGER.info(
                f"Invoice details row data: {str(discovered_file.document_properties)}"
            )

            self.download_invoice_by_click(discovered_file, index)
            close_extra_handles(self.driver)
        return discovered_files

    def get_download_element(self, index) -> WebElement:
        for attempt in range(3):
            try:
                row = self.get_table_rows()[index]
                return row.find_element_by_css_selector("a.af_link")
            except WEB_DRIVER_EXCEPTIONS as excep:
                LOGGER.warning(f"{excep} in {self.driver.current_url}")
                if attempt == 2:
                    raise

    def download_invoice_by_click(self, discovered_file, index):
        """
        Download the File in pdf format
        :param discovered_file: DiscoveredFile
        :param index: invoice row number
        """
        _downloader = download.WebElementClickBasedDownloader(
            element=self.get_download_element(index),
            local_filepath=os.path.join(
                self.download_location, discovered_file.original_filename
            ),
            file_exists_check_kwargs=dict(timeout=40),
        )
        download.download_discovered_file(discovered_file, _downloader)


class SoCalGasRunner(VendorDocumentDownloadInterface):
    """Runner Class for SoCal Gas"""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.login_page = SoCalGasLoginPage(self.driver)
        self.billing_history_page = SoCalGasBillingHistoryPage(
            self.driver, self.download_location
        )

    @retry(WebDriverException, tries=3, delay=1)
    def _login(self):
        """
        Login using credentials
        :return: Nothing
        """
        login_url = "https://business.socalgas.com/"
        redirected_login_url = (
            "https://business.socalgas.com/publicsvc/faces/login-flow/login"
        )
        get_url(self.driver, login_url)

        try:
            explicit_wait_till_url_contains(self.driver, redirected_login_url)
        except TimeoutException as excep:
            LOGGER.warning(f"{excep} found in {self.driver.current_url}")

        wait_for_loaders(self.driver, value=HOME_PAGE_LOCATORS["LOADER"], timeout=10)
        self.login_page.login(self.run.job.username, self.run.job.password)
        self.do_post_login()

    def handle_alert_if_exists(self):
        try:
            WebDriverWait(self.driver, 3).until(
                EC.alert_is_present(),
                "Timed out waiting for PA creation " + "confirmation popup to appear.",
            )

            alert = self.driver.switch_to.alert
            LOGGER.info(f"Alert is present with text :  {alert.text}")
            alert.dismiss()
            LOGGER.info(f"Dismissed alert.")
        except (TimeoutException, WebDriverException):
            LOGGER.info(f"No Alert present")

    def do_post_login(self):

        self.handle_alert_if_exists()

        try:
            self.confirm_account_info().click()
            LOGGER.info("Confirming Contact Information...")
        except NoSuchElementException:
            LOGGER.info("Navigating to the account page...")

        handle_popup(
            self.driver,
            by_selector=By.XPATH,
            value=REVIEW_INFO_PAGE_LOCATORS["MY_INFO_IS_CORRECT_LINK"],
            msg="Review Your Information",
        )
        handle_popup(
            self.driver,
            value=HOME_PAGE_LOCATORS["POP_UP"],
            msg="Go paperless",
            retry_attempts=1,
        )

        for index in range(3):
            try:
                wait_for_element(
                    self.driver,
                    by_selector=By.CSS_SELECTOR,
                    value="nav#mainNavigation",
                    msg="Main Navigation",
                    retry_attempts=3,
                )
                break
            except WebDriverException as excep:
                LOGGER.warning(f"{excep} found in {self.driver.current_url}")
                get_url(
                    self.driver,
                    "https://business.socalgas.com/portal/faces/pages/myaccount/myAccountHome.jspx",
                )
                if index == 2:
                    raise

    def confirm_account_info(self):
        return self.driver.find_element_by_css_selector(HOME_PAGE_LOCATORS["CONFIRM"])

    def has_maintenance_page(self) -> bool:
        LOGGER.info(f"Checking for maintenance page")
        if self.driver.current_url == "https://business.socalgas.com/maintenance.html":
            LOGGER.info(f"Socal Gas: Maintenance page found!")
            self.billing_history_page.navigate_to_billing_history_page()
            return True
        return False

    def select_account(self, account, tries=2):
        self.billing_history_page.select_account(account)
        self.billing_history_page.get_go_button().click()
        wait_for_loaders(
            self.driver, value=HOME_PAGE_LOCATORS["BODY_LOADER"], timeout=10
        )

        if self.has_maintenance_page() and tries > 0:
            LOGGER.info(f"Selecting account: {account} again. Retry attempt = {tries}")
            self.select_account(account=account, tries=tries - 1)

    def _download_documents(
        self, restaurant_name, account_number
    ) -> List[DiscoveredFile]:
        """
        Chooses the documents to be downloaded based on the document type
        :return: Returns the list of Discovered Files
        """
        document_type = self.run.job.requested_document_type
        if document_type == "invoice":
            return self._download_invoices(restaurant_name, account_number)

        raise NotImplementedError(
            f"Requested Document Type is not supported: {document_type}"
        )

    def _download_invoices(
        self, restaurant_name, account_number
    ) -> List[DiscoveredFile]:
        """
        Downloads the Invoices
        :return: Returns the list of the Discovered Files
        """
        start_date = datetime.strptime(
            self.run.request_parameters["start_date"], "%Y-%m-%d"
        ).date()
        discovered_files_list = self.billing_history_page.get_table_data(
            self.run, start_date, restaurant_name, account_number
        )
        LOGGER.info(
            f"Total Invoices within date range for {account_number} account: {len(discovered_files_list)}"
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
            self.billing_history_page.navigate_to_billing_history_page()
            accounts = self.billing_history_page.get_account_dropdown_list_text()
            for account in accounts:
                LOGGER.info(f"Selecting the account :- {account}")
                account_number, restaurant_name = (
                    account.replace(")", "").replace("(", "").split(maxsplit=1)
                )

                if len(accounts) > 1:
                    self.select_account(account=account)
                discovered_files += self._download_documents(
                    restaurant_name, account_number
                )
            LOGGER.info(
                f"Downloaded invoice by download link available: {len(discovered_files)}"
            )
        finally:
            self._quit_driver()

        return discovered_files

    def login_flow(self, run: Run):
        self._login()
