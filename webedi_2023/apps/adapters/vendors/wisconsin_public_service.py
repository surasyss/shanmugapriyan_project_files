import os
import re
from datetime import date
from typing import List, Optional

from selenium.common.exceptions import (
    WebDriverException,
    NoSuchElementException,
    StaleElementReferenceException,
)
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC

from apps.adapters.framework import download
from apps.adapters.framework.registry import connectors
from apps.adapters.framework.operations.vendor import BaseVendorConnector
from apps.adapters.framework.steps.web import (
    NavigateToUrl,
    SubmitLoginPassword,
    ExplicitWait,
)
from apps.adapters.helpers import LOGGER
from apps.adapters.helpers.webdriver_helper import (
    wait_for_element,
    has_invoices,
    wait_for_loaders,
    get_url,
)
from apps.runs.models import FileFormat
from spices.datetime_utils import date_from_string

_LOGIN_URL = (
    "https://login.wecenergygroup.com/84e7e01a-f85a-4cb6-befb-42089b669b88/oauth2/v2.0/authorize?p=b2c_1a_"
    "ya_signup_signin&brand=wisconsinpublicservice&client_id=dc024f51-6409-4a48-a19b-43f2008802df&grant_"
    "type=authorization_code&id_token=code&profile=profile_&redirect_uri=https%3A%2F%2F"
    "www.wisconsinpublicservice.com%2Foauth%2Fclient%2Fredirect&response_type=code&scope=https%3A%2F%2"
    "Flogin.we-energies.com%2Ff5apmazureb2c%2Fuser_impersonation&state=5stgf--9g78OUHHwjnYQ94Q#Bookmark"
)
_ACCOUNTS_URL = "https://www.wisconsinpublicservice.com/secure/auth/l/acct/billhistory_accounts.aspx?show_list=true"


@connectors.add("wisconsin_public_service")
class WisconsinConnector(BaseVendorConnector):

    vendor_name = "Wisconsin Public Service"
    invoice_file_format = FileFormat.PDF.ident  # pylint: disable=no-member
    df_download_url_skip_duplicates = True

    class Selectors:

        LOGIN__USERNAME_TEXTBOX = (By.CSS_SELECTOR, "#signInName")
        LOGIN__PASSWORD_TEXTBOX = (By.CSS_SELECTOR, "#password")
        LOGIN__LOGIN_BUTTON = (By.CSS_SELECTOR, "#next")
        LOGIN__ERROR_MESSAGE_TEXT = (By.CSS_SELECTOR, ".errors-container")

        ACCOUNT__TABLE_ROWS = (
            By.CSS_SELECTOR,
            "#ctl00_ctl00_TemplateBody_BodyContent_tblAccounts > tbody > tr",
        )
        VIEW_BILL_HISTORY = (By.CSS_SELECTOR, "a[href*='view/BillHistory']")
        INVOICE_TABLE_ROWS = (By.CSS_SELECTOR, 'table[class="siteTable"] tbody tr')
        ACCOUNT_CENTER__BILLING_AND_USAGE = (By.CSS_SELECTOR, 'a[id="viewbills"]')
        ACCOUNT_CENTER__ACCOUNT_RESTAURANT_VALUE = (By.CSS_SELECTOR, "div.grpBodyCell")
        ACCOUNT_CENTER__RESTAURANT_NAME = (
            By.CSS_SELECTOR,
            "#amountDuePanel > div > h2",
        )
        ACCOUNT_NUMBER_TEXTBOX = (
            By.CSS_SELECTOR,
            "input#ctl00_ctl00_TemplateSidebar_SidebarContent_txtLast5DigitsOfAccount",
        )
        CUSTOMER_NAME_TEXTBOX = (
            By.CSS_SELECTOR,
            "input#ctl00_ctl00_TemplateSidebar_SidebarContent_txtCustName",
        )
        SEARCH_BUTTON = (
            By.CSS_SELECTOR,
            "input#ctl00_ctl00_TemplateSidebar_SidebarContent_btnUpdate",
        )

    # login
    _navigate_to_login_page = NavigateToUrl(_LOGIN_URL, retry_attempts=5)
    _submit_login_info__pre = ExplicitWait(
        until=EC.visibility_of_element_located(
            locator=Selectors.LOGIN__USERNAME_TEXTBOX
        )
    )
    _submit_login_info = SubmitLoginPassword(
        username_textbox=Selectors.LOGIN__USERNAME_TEXTBOX,
        password_textbox=Selectors.LOGIN__PASSWORD_TEXTBOX,
        login_button=Selectors.LOGIN__LOGIN_BUTTON,
        error_message=Selectors.LOGIN__ERROR_MESSAGE_TEXT,
    )
    _submit_login_info__post = ExplicitWait(
        until=EC.visibility_of_element_located(locator=Selectors.ACCOUNT__TABLE_ROWS)
    )

    def account_table_row(self):
        """Return all account table row elements"""
        wait_for_element(
            self.driver,
            value=self.Selectors.ACCOUNT__TABLE_ROWS[1],
            msg="Accounts table row",
            retry_attempts=3,
        )
        return self.driver.find_elements(*self.Selectors.ACCOUNT__TABLE_ROWS)

    def view_bill_history(self):
        """Return all view bill history element"""
        return self.driver.find_element(*self.Selectors.VIEW_BILL_HISTORY)

    def invoice_table_row(self):
        """Return all invoice table row elements"""
        wait_for_element(
            self.driver,
            value=self.Selectors.INVOICE_TABLE_ROWS[1],
            msg="Invoice table row",
        )
        return self.driver.find_elements(*self.Selectors.INVOICE_TABLE_ROWS)

    def page_forward_element(self):
        """Returns next page element"""
        return self.driver.find_element(
            By.CSS_SELECTOR, "p.pagingSection a.pagerForward"
        )

    def has_next_page(self):
        """Checks for next page"""
        try:
            self.page_forward_element()
            LOGGER.info(f"Next page found")
            return True
        except WebDriverException:
            LOGGER.info(f"No more pages found")
            return False

    def scroll_to_element_position(self, element):
        x_pos = element.location.get("x")
        y_pos = element.location.get("y")
        self.driver.execute_script(f"window.scrollTo({x_pos}, {y_pos + 70});")

    def select_account(self, account_row):
        for retry in range(5):
            try:
                if retry > 0:
                    self.scroll_to_element_position(account_row)
                    LOGGER.info("Selecting account again...")

                account_row.click()
                wait_for_loaders(
                    self.driver, value="body.loadingPage", retry_attempts=1
                )
                continue
            except (NoSuchElementException, StaleElementReferenceException):
                break

    def get_account_numbers(self):
        account_numbers = []
        while True:
            for _, account_row in enumerate(self.account_table_row()):
                address_td = account_row.find_element(
                    By.CSS_SELECTOR, "td.accountSelectionAddress"
                )
                restaurant_name, *_, account = [
                    line.strip() for line in address_td.text.split("\n")
                ]
                account_number = re.search(r"Account\s+#:\s*([\d-]+)", account).group(1)
                account_numbers.append(
                    (account_number, restaurant_name.split("-")[0].strip())
                )

            if not self.has_next_page():
                break

            self.navigate_to_next_page()
        return account_numbers

    def get_account_number_textbox(self):
        return self.driver.find_element(*self.Selectors.ACCOUNT_NUMBER_TEXTBOX)

    def get_customer_name_textbox(self):
        return self.driver.find_element(*self.Selectors.CUSTOMER_NAME_TEXTBOX)

    def get_search_button(self):
        return self.driver.find_element(*self.Selectors.SEARCH_BUTTON)

    def filter_by_account_number(self, account_number, restaurant_name):
        get_url(self.driver, _ACCOUNTS_URL)
        LOGGER.info(
            f"Searching the account with account number: {account_number} and customer name: {restaurant_name}"
        )

        account_input = self.get_account_number_textbox()
        account_input.clear()
        account_input.send_keys(account_number.split("-")[1])

        customer_input = self.get_customer_name_textbox()
        customer_input.clear()
        customer_input.send_keys(restaurant_name)

        search = self.get_search_button()
        search.click()

        for index, account_row in enumerate(self.account_table_row()):
            if account_number in account_row.text:
                self.select_account(account_row)
                break

    def navigate_to_next_page(self):
        self.page_forward_element().click()
        wait_for_loaders(
            self.driver,
            value=self.Selectors.ACCOUNT__TABLE_ROWS[1],
            timeout=10,
            retry_attempts=1,
        )

    def _iter_customer_number_selections(self, customer_numbers: Optional[List[str]]):
        account_numbers = self.get_account_numbers()
        for _, (account_number, restaurant_name) in enumerate(account_numbers):
            try:
                self.filter_by_account_number(account_number, restaurant_name)
            except WebDriverException:
                error = self.driver.find_element(By.CSS_SELECTOR, "p.errorDescription")
                LOGGER.info(error.text)
                continue

            LOGGER.info(f"Selected account: {account_number}")

            if not has_invoices(
                self.driver,
                value=self.Selectors.VIEW_BILL_HISTORY[1],
                retry_attempts=3,
                msg="View bill history",
            ):
                continue

            yield account_number, None

    def _iter_invoice_row_elements(self, start_date: date, end_date: date):
        if "BillHistory" not in self.driver.current_url:
            self.view_bill_history().click()

        invoices_list = []

        if has_invoices(
            self.driver,
            value=self.Selectors.INVOICE_TABLE_ROWS[1],
        ):
            for row_element in self.invoice_table_row()[1:-1]:
                try:
                    download_url_elem = row_element.find_element_by_css_selector(
                        "td > span > a"
                    )
                except NoSuchElementException:
                    LOGGER.info("Pdf not available to download.")
                    continue

                invoice_date = date_from_string(
                    row_element.find_elements_by_css_selector("td")[0].text,
                    "%m/%d/%Y",
                )

                if not start_date <= invoice_date <= end_date:
                    LOGGER.info(
                        f"Skipping invoices because date '{invoice_date}' is outside requested range"
                    )
                    break

                invoices_list.append(
                    {
                        "invoice_date": invoice_date,
                        "total_amount": row_element.find_elements_by_css_selector("td")[
                            -1
                        ].text,
                        "original_download_url": download_url_elem.get_attribute(
                            "href"
                        ),
                    }
                )
        else:
            LOGGER.info(f"This account has no invoice found.")

        for invoice_data in invoices_list:
            LOGGER.info(f"Found invoice: {invoice_data}")
            yield invoice_data

    def _construct_downloader(
        self, invoice_row_element, **invoice_fields
    ) -> download.BaseDownloader:

        return download.DriverBasedUrlGetDownloader(
            self.driver,
            download_url=invoice_fields["original_download_url"],
            local_filepath=self.download_location,
            rename_to=os.path.join(
                self.download_location, invoice_fields["original_filename"]
            ),
            file_exists_check_kwargs=dict(timeout=20, pattern=r"bill[0-9]+.pdf$"),
        )

    def _extract_invoice_date(self, invoice_row_element) -> date:
        return invoice_row_element["invoice_date"]

    def _extract_customer_number(
        self, invoice_row_element, customer_number, customer_number_element
    ) -> str:
        if customer_number:
            return customer_number

        customer_number_url = customer_number_element.get_attribute("href")
        customer_number = customer_number_url.split("accountNumber=")[1]
        return customer_number

    def _extract_invoice_number(self, invoice_row_element, **invoice_fields) -> str:
        return ""

    def _extract_total_amount(self, invoice_row_element, **invoice_fields) -> str:
        return invoice_row_element["total_amount"]

    def _extract_vendor_name(self, invoice_row_element, **invoice_fields) -> str:
        return self.vendor_name

    def _extract_restaurant_name(self, invoice_row_element, **invoice_fields) -> str:
        return self.driver.find_element(
            *self.Selectors.ACCOUNT_CENTER__RESTAURANT_NAME
        ).text

    def _extract_reference_code(self, invoice_row_element, **invoice_fields) -> str:
        # TODO: THIS IS WRONG! The download_id should be the reference code
        customer_number = invoice_fields["customer_number"]
        invoice_date = invoice_fields["invoice_date"]
        return f"{customer_number}_{invoice_date}"

    def _extract_original_download_url(
        self, invoice_row_element, **invoice_fields
    ) -> str:
        return invoice_row_element["original_download_url"]

    def _extract_original_filename(self, invoice_row_element, **invoice_fields) -> str:
        return f"{invoice_fields['reference_code']}.pdf"
