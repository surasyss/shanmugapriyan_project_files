import datetime
import os
import re
from datetime import date
from typing import List, Optional
from integrator import LOGGER

from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC

from apps.adapters.framework import download
from apps.adapters.framework.registry import connectors
from apps.adapters.framework.operations.vendor import BaseVendorConnector
from apps.adapters.framework.steps.web import (
    NavigateToUrl,
    SubmitLoginPassword,
    ExplicitWait,
    ClickElement,
)
from apps.runs.models import FileFormat
from spices.datetime_utils import date_from_string

_LOGIN_URL = "https://identity.nwnatural.com"


@connectors.add("nw_natural")
class NWNaturalConnector(BaseVendorConnector):
    vendor_name = "NW Natural"
    invoice_file_format = FileFormat.PDF.ident  # pylint: disable=no-member
    df_download_url_skip_duplicates = True

    class Selectors:
        HOME__ACCOUNT_ROWS = (By.CSS_SELECTOR, 'div[id^="account-sel-cont"] span')
        HOME__SIGNIN = (By.CSS_SELECTOR, "form button.Button-link")

        LOGIN__USERNAME_TEXTBOX = (By.CSS_SELECTOR, 'input[name="Username"]')
        LOGIN__PASSWORD_TEXTBOX = (By.CSS_SELECTOR, 'input[name="Password"]')
        LOGIN__LOGIN_BUTTON = (By.CSS_SELECTOR, 'button[data-testingid="signInButton"]')
        LOGIN__ERROR_MESSAGE_TEXT = (By.CSS_SELECTOR, "div.InlineNotification--error")

        BILLING_HISTORY__TABLE_ROWS = (
            By.CSS_SELECTOR,
            'table[id="billHistoryTable"] tbody tr',
        )
        BILL_HISTORY = "div.nav li a.nav-item-bills"
        CONTINUE = "a#account-sel-next"

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

    _step_navigate_to_invoices_list_page__before_account_selection = NavigateToUrl(
        url="https://ipn2.paymentus.com/cp/oidc/nwng/bills"
    )

    def get_account(self, index):
        if index > 0:
            self.driver.find_element_by_css_selector(
                self.Selectors.BILL_HISTORY
            ).click()
        accounts = self.driver.find_elements(*self.Selectors.HOME__ACCOUNT_ROWS)
        accounts[index].click()
        self.driver.find_element_by_css_selector(self.Selectors.CONTINUE).click()

    def _iter_customer_number_selections(self, customer_numbers: Optional[List[str]]):
        elements = []
        accounts = self.driver.find_elements(*self.Selectors.HOME__ACCOUNT_ROWS)
        if accounts:
            for account in accounts:
                customer_number = account.text.split("Account #")[1].strip()
                elements.append((customer_number, None))

            for index, (customer_number, _) in enumerate(elements):
                self.get_account(index)
                LOGGER.info(
                    f"Navigating to the billing history page of account: {customer_number}"
                )
                yield customer_number, None

    def _iter_invoice_row_elements(self, start_date: date, end_date: date):
        table_rows = self.driver.find_elements(
            *self.Selectors.BILLING_HISTORY__TABLE_ROWS
        )
        for row in table_rows:
            if (
                row.find_element_by_css_selector("td").get_attribute("class")
                == "dataTables_empty"
            ):
                LOGGER.info("No invoices found")
                break
            yield row

    def _construct_downloader(
        self, invoice_row_element, **invoice_fields
    ) -> download.BaseDownloader:
        due_date = date_from_string(
            invoice_row_element.find_element_by_css_selector("td.docDate").text,
            "%b %d, %Y",
        ).strftime("%m%d%Y")
        original_file_name = re.search(
            rf"{due_date}.+?\.pdf", invoice_row_element.get_attribute("data-url")
        ).group()
        return download.DriverBasedUrlGetDownloader(
            self.driver,
            download_url=invoice_fields["original_download_url"],
            local_filepath=os.path.join(self.download_location, original_file_name),
            rename_to=os.path.join(
                self.download_location, invoice_fields["original_filename"]
            ),
            file_exists_check_kwargs=dict(timeout=20),
        )

    def _extract_invoice_date(self, invoice_row_element) -> date:
        return date_from_string(
            invoice_row_element.find_element_by_css_selector("td.docDate").text,
            "%b %d, %Y",
        ) - datetime.timedelta(days=16)

    def _extract_customer_number(
        self, invoice_row_element, customer_number, customer_number_element
    ) -> str:
        if customer_number:
            return customer_number
        customer_number = invoice_row_element.find_element_by_css_selector(
            "td.accountNumber"
        ).text
        return customer_number

    def _extract_invoice_number(self, invoice_row_element, **invoice_fields) -> str:
        return None

    def _extract_total_amount(self, invoice_row_element, **invoice_fields) -> str:
        return invoice_row_element.find_element_by_css_selector(
            "td.docDescription"
        ).text

    def _extract_vendor_name(self, invoice_row_element, **invoice_fields) -> str:
        return self.vendor_name

    def _extract_restaurant_name(self, invoice_row_element, **invoice_fields) -> str:
        return None

    def _extract_reference_code(self, invoice_row_element, **invoice_fields) -> str:
        customer_number = invoice_fields["customer_number"]
        due_date = date_from_string(
            invoice_row_element.find_element_by_css_selector("td.docDate").text,
            "%b %d, %Y",
        )
        return f'{customer_number}_{due_date.strftime("%m%d%Y")}'

    def _extract_original_download_url(
        self, invoice_row_element, **invoice_fields
    ) -> str:
        original_download_url = invoice_row_element.find_element_by_css_selector(
            "td.tableActionCol a"
        ).get_attribute("href")
        return original_download_url

    def _extract_original_filename(self, invoice_row_element, **invoice_fields) -> str:
        reference_code = self._extract_reference_code(
            invoice_row_element, **invoice_fields
        )
        return f"{reference_code}.pdf"
