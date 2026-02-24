import os
import re
from datetime import date
from typing import List, Optional

from integrator import LOGGER

from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC

from apps.adapters.framework.download import (
    DriverBasedUrlGetDownloader,
    BaseDownloader,
)
from apps.adapters.framework.context import ExecutionContext
from apps.adapters.framework.registry import connectors
from apps.adapters.framework.operations.vendor import BaseVendorConnector
from apps.adapters.framework.steps.web import (
    NavigateToUrl,
    SubmitLoginPassword,
    ExplicitWait,
)
from apps.adapters.helpers.webdriver_helper import (
    get_url,
    handle_popup,
)
from apps.runs.models import FileFormat
from spices.datetime_utils import date_from_string

_LOGIN_URL = "https://account.tecoenergy.com/"
_ACCOUNTS_SELECTION_URL = "https://account.tecoenergy.com/Selection"


class HandlePopup:
    def __call__(self, execution_context: ExecutionContext):
        handle_popup(
            execution_context.driver,
            by_selector=By.CSS_SELECTOR,
            value="div#paperlessPrompt button#closeButton",
            msg="One click to go Paperless",
            retry_attempts=1,
        )


@connectors.add("tampa_electric")
class TampaElectricConnector(BaseVendorConnector):
    vendor_name = "Tampa Electric"
    invoice_file_format = FileFormat.PDF.ident  # pylint: disable=no-member
    df_download_url_skip_duplicates = True

    class Selectors:
        LOGIN__USERNAME_TEXTBOX = (By.CSS_SELECTOR, 'input[id="UserName"]')
        LOGIN__PASSWORD_TEXTBOX = (By.CSS_SELECTOR, 'input[id="Credentials_Password"]')
        LOGIN__LOGIN_BUTTON = (By.CSS_SELECTOR, 'button[id="login-submit"]')
        LOGIN__ERROR_MESSAGE_TEXT = (By.CSS_SELECTOR, "div.validation-summary-errors")

        HOME__ACCOUNT_ROWS = (By.CSS_SELECTOR, "table.table tbody tr")
        HOME__ACCOUNT_NUMBER = (By.CSS_SELECTOR, "td:nth-child(2)")

        BILLING_HISTORY__TABLE_ROWS = (
            By.CSS_SELECTOR,
            "div#BillHistoryData table.table tbody tr",
        )
        BILLING_HISTORY__CUSTOMER_NUMBER = (By.CSS_SELECTOR, "input#contractAccountId")
        BILLING_HISTORY__INVOICE_DATE = (By.CSS_SELECTOR, "td")
        BILLING_HISTORY__TOTAL_AMOUNT = (By.CSS_SELECTOR, "td:nth-child(2)")
        BILLING_HISTORY__INVOICE_DOWNLOAD_URL = (By.CSS_SELECTOR, "td:nth-child(4) a")

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
        until=EC.visibility_of_element_located(locator=Selectors.HOME__ACCOUNT_ROWS)
    )

    # handle popup after every account selection
    _step_navigate_to_invoices_list_page__after_account_selection = HandlePopup()

    def _iter_customer_number_selections(self, customer_numbers: Optional[List[str]]):
        if "Selection" in self.driver.current_url:
            customer_row_elems = self.driver.find_elements(
                *self.Selectors.HOME__ACCOUNT_ROWS
            )
            for index, _ in enumerate(customer_row_elems):
                if index > 0:
                    get_url(self.driver, _ACCOUNTS_SELECTION_URL)

                # find account row elements before every account selection as it becomes stale
                customer_row_elem = self.driver.find_elements(
                    *self.Selectors.HOME__ACCOUNT_ROWS
                )[index]

                # get customer number from second table data
                customer_number = customer_row_elem.find_element(
                    *self.Selectors.HOME__ACCOUNT_NUMBER
                ).text

                # navigate to invoices page
                customer_row_elem.click()

                yield customer_number, None
        else:
            customer_number = self.get_customer_number()
            yield customer_number, None

    def get_customer_number(self):
        customer_num_input = self.driver.find_element(
            *self.Selectors.BILLING_HISTORY__CUSTOMER_NUMBER
        )
        self.driver.execute_script(
            "arguments[0].setAttribute('type', '')", customer_num_input
        )
        return customer_num_input.get_attribute("value")

    def _iter_invoice_row_elements(self, start_date: date, end_date: date):
        table_rows = self.driver.find_elements(
            *self.Selectors.BILLING_HISTORY__TABLE_ROWS
        )
        for index, row in enumerate(table_rows):
            invoice_date = self._extract_invoice_date(row)
            if not start_date <= invoice_date <= end_date:
                LOGGER.info(
                    f"Skipping remaining invoices because date '{invoice_date}' is outside requested range"
                )
                break
            yield row

    def _construct_downloader(
        self, invoice_row_element, **invoice_fields
    ) -> BaseDownloader:
        return DriverBasedUrlGetDownloader(
            self.driver,
            download_url=invoice_fields["original_download_url"],
            local_filepath=os.path.join(self.download_location, "BillDownload.pdf"),
            rename_to=os.path.join(
                self.download_location, invoice_fields["original_filename"]
            ),
            file_exists_check_kwargs=dict(timeout=20),
        )

    def _extract_invoice_date(self, invoice_row_element) -> date:
        return date_from_string(
            invoice_row_element.find_element(
                *self.Selectors.BILLING_HISTORY__INVOICE_DATE
            ).text,
            "%m/%d/%Y",
        )

    def _extract_customer_number(
        self, invoice_row_element, customer_number, customer_number_element
    ) -> str:
        return customer_number if customer_number else None

    def _extract_invoice_number(self, invoice_row_element, **invoice_fields) -> str:
        download_url = self._extract_original_download_url(
            invoice_row_element, **invoice_fields
        )
        try:
            return download_url.split("invoiceId=")[1]
        except IndexError:
            LOGGER.info(f"Download url {download_url} has no split text 'invoiceId='")
            return None

    def _extract_total_amount(self, invoice_row_element, **invoice_fields) -> str:
        return invoice_row_element.find_element(
            *self.Selectors.BILLING_HISTORY__TOTAL_AMOUNT
        ).text

    def _extract_vendor_name(self, invoice_row_element, **invoice_fields) -> str:
        return self.vendor_name

    def _extract_restaurant_name(self, invoice_row_element, **invoice_fields) -> str:
        return None

    def _extract_reference_code(self, invoice_row_element, **invoice_fields) -> str:
        customer_number = invoice_fields["customer_number"]
        invoice_number = invoice_fields["invoice_number"]
        invoice_date = invoice_fields["invoice_date"]
        return f"{customer_number}_{invoice_number}_{invoice_date}"

    def _extract_original_download_url(
        self, invoice_row_element, **invoice_fields
    ) -> str:
        _invoice_url = invoice_row_element.find_element(
            *self.Selectors.BILLING_HISTORY__INVOICE_DOWNLOAD_URL
        ).get_attribute("href")
        _url_body = "ContractAccount/BillDownload?invoiceId="
        _inv_number = re.split(r"Id=|id=", _invoice_url)[-1]
        _invoice_url = _invoice_url[:31] + _url_body + _inv_number
        return _invoice_url

    def _extract_original_filename(self, invoice_row_element, **invoice_fields) -> str:
        reference_code = self._extract_reference_code(
            invoice_row_element, **invoice_fields
        )
        return f"{reference_code}.pdf"
