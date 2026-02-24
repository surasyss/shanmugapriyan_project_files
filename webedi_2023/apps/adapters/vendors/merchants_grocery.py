import os
import re
import time
from datetime import date

from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC

from apps.adapters.framework import download
from apps.adapters.framework.registry import connectors
from apps.adapters.framework.operations.vendor import BaseVendorConnector
from apps.adapters.helpers.webdriver_helper import wait_for_loaders
from apps.adapters.framework.steps.web import (
    NavigateToUrl,
    SubmitLoginPassword,
    ExplicitWait,
)
from apps.runs.models import FileFormat
from spices.datetime_utils import date_from_string

_LOGIN_URL = "http://mgc-customerzone.com/pnet/eOrder"


# This crawler is not being used anywhere as its not enabled(ie connector is still backlog).
# reason being its not downloaded invoices do not have any tax component.


@connectors.add("merchants_grocery")
class MerchantsGroceryConnector(BaseVendorConnector):
    vendor_name = "Merchants Grocery"
    invoice_file_format = FileFormat.PDF.ident  # pylint: disable=no-member
    df_download_url_skip_duplicates = True

    class Selectors:
        LOGIN__USERNAME_TEXTBOX = (By.CSS_SELECTOR, 'input[name="UserName"]')
        LOGIN__PASSWORD_TEXTBOX = (By.CSS_SELECTOR, 'input[name="Password"]')
        LOGIN__LOGIN_BUTTON = (By.CSS_SELECTOR, 'button[name="SubmitBtn"]')
        LOGIN__ERROR_MESSAGE_TEXT = (By.CSS_SELECTOR, "#newid")

        HOME__INVOICE_TABLE = (By.CSS_SELECTOR, "table#account")
        HOME__INVOICE_ROWS = (By.CSS_SELECTOR, "#account tbody tr")
        HOME__ACCOUNT_LINK = (By.CSS_SELECTOR, "li#mainmenuli-account")
        HOME__STATEMENT_STATUS = (By.CSS_SELECTOR, "#mainmenu-account00 a span.menu")

        INVOICE_ROW_ELEMENTS = (By.CSS_SELECTOR, "#scrollable table tbody tr")
        ACCOUNT_CENTER__RESTAURANT_NAME = (
            By.CSS_SELECTOR,
            "table.pageInfo tbody tr td:nth-child(2) table tbody tr td",
        )
        INVOICE_BACK_BUTTON = (By.CSS_SELECTOR, "#pagemenu-back a")

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

    def invoice_page_navigations(self):
        #  Navigation to statement statues page.
        self.driver.find_element(*self.Selectors.HOME__ACCOUNT_LINK).click()
        self.driver.find_element(*self.Selectors.HOME__STATEMENT_STATUS).click()

        #  Switch the driver to i-frame.
        self.driver.switch_to_frame(
            self.driver.find_element_by_css_selector('iframe[name="ContentFrame"')
        )

    def _iter_invoice_row_elements(self, start_date: date, end_date: date):
        self.invoice_page_navigations()

        wait_for_loaders(self.driver, value="#scrollable table tbody tr")

        for count, _ in enumerate(
            self.driver.find_elements(*self.Selectors.INVOICE_ROW_ELEMENTS)
        ):
            if count >= 1:
                self.driver.find_elements(*self.Selectors.INVOICE_BACK_BUTTON)[
                    0
                ].click()
            yield self.driver.find_elements(*self.Selectors.INVOICE_ROW_ELEMENTS)[count]

    def _construct_downloader(
        self, invoice_row_element, **invoice_fields
    ) -> download.BaseDownloader:
        MerchantsGroceryConnector._invoice_number_element(invoice_row_element).click()
        time.sleep(5)
        return download.DriverExecuteCDPCmdBasedDownloader(
            self.driver,
            cmd="Page.printToPDF",
            cmd_args={"printBackground": True},
            local_filepath=os.path.join(
                self.download_location, "MERCHANTS-GROCERY.pdf"
            ),
            rename_to=os.path.join(
                self.download_location, invoice_fields["original_filename"]
            ),
            file_exists_check_kwargs=dict(timeout=40),
        )

    def _extract_invoice_date(self, invoice_row_element) -> date:
        return date_from_string(
            invoice_row_element.find_elements_by_css_selector("td")[1].text, "%m/%d/%Y"
        )

    def _extract_customer_number(
        self, invoice_row_element, customer_number, customer_number_element
    ) -> str:
        return self.get_single_format_account_number

    @staticmethod
    def _invoice_number_element(invoice_row_element):
        return invoice_row_element.find_elements_by_css_selector("td > input")[0]

    def _extract_invoice_number(self, invoice_row_element, **invoice_fields) -> str:
        return invoice_row_element.find_elements_by_css_selector("td > input")[
            0
        ].get_attribute("value")

    def _extract_total_amount(self, invoice_row_element, **invoice_fields) -> str:
        return invoice_row_element.find_elements_by_css_selector("td")[3].text

    def _extract_vendor_name(self, invoice_row_element, **invoice_fields) -> str:
        return "Merchants Grocery"

    def _extract_restaurant_name(self, invoice_row_element, **invoice_fields) -> str:
        return re.search(
            r"(?:([A-Z]+\s)+)",
            self.driver.find_element(
                *self.Selectors.ACCOUNT_CENTER__RESTAURANT_NAME
            ).text,
        ).group()

    def _extract_reference_code(self, invoice_row_element, **invoice_fields) -> str:
        # TODO: THIS IS WRONG! The download_id should be the reference code
        customer_number = invoice_fields["customer_number"]
        invoice_number = invoice_fields["invoice_number"]
        invoice_date = invoice_fields["invoice_date"]
        return f"{customer_number}_{invoice_number}_{invoice_date}"

    def _extract_original_download_url(
        self, invoice_row_element, **invoice_fields
    ) -> str:
        original_download_url = invoice_row_element.find_elements_by_css_selector(
            "td > input"
        )[0].get_attribute("onclick")
        return original_download_url

    def _extract_original_filename(self, invoice_row_element, **invoice_fields) -> str:
        return f'{invoice_fields["reference_code"]}.pdf'

    @property
    def get_single_format_account_number(self):
        return (
            self.driver.find_element(*self.Selectors.ACCOUNT_CENTER__RESTAURANT_NAME)
            .text.split("-")[1]
            .strip()
        )
