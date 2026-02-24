import os.path
from datetime import date
from typing import List, Optional

from integrator import LOGGER

from selenium.webdriver.remote.webelement import WebElement
from selenium.webdriver.common.by import By
from selenium.common.exceptions import WebDriverException
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import Select

from apps.adapters.framework.download import (
    BaseDownloader,
    WebElementClickBasedDownloader,
)
from apps.adapters.framework.steps.primitives import SequentialSteps
from apps.adapters.framework.registry import connectors
from apps.adapters.framework.operations.vendor import BaseVendorConnector
from apps.adapters.framework.steps.web import (
    NavigateToUrl,
    SubmitLoginPassword,
    ExplicitWait,
    ClickElement,
)
from apps.adapters.helpers.webdriver_helper import (
    wait_for_element,
    select_dropdown_option_by_value,
    has_invoices,
)
from apps.runs.models import FileFormat
from spices.datetime_utils import date_from_string

_LOGIN_URL = "https://epay.uwscompany.com/Login.aspx"
_VIEW_INVOICES_URL = "https://epay.uwscompany.com/ViewInvoices.aspx"


@connectors.add("universal_waste_systems")
class UniversalWasteSystemsConnector(BaseVendorConnector):
    vendor_name = "Universal Waste Systems"
    invoice_file_format = FileFormat.PDF.ident  # pylint: disable=no-member
    df_download_url_skip_duplicates = True

    class Selectors:
        LOGIN__USERNAME_TEXTBOX = (
            By.CSS_SELECTOR,
            "input[id='ctl00_MainContent_txtUserID']",
        )
        LOGIN__PASSWORD_TEXTBOX = (
            By.CSS_SELECTOR,
            "input[id='ctl00_MainContent_txtPassword']",
        )
        LOGIN__LOGIN_BUTTON = (
            By.CSS_SELECTOR,
            "input[id='ctl00_MainContent_cmdSignIn']",
        )
        LOGIN__ERROR_MESSAGE_TEXT = (
            By.CSS_SELECTOR,
            "div[id='ctl00_MainContent_lMessage']",
        )

        ACCOUNT_DROPDOWN = (By.CSS_SELECTOR, "select#ctl00_cCustomerSelectionDropDown")
        INVOICE_HISTORY = (By.CSS_SELECTOR, "a#ctl00_MainContent_lbViewHistory")

        ACCOUNT_DETAILS = (By.CSS_SELECTOR, "a#ctl00_hlCurrentCustomer")
        INVOICE_TABLE_ROWS = (By.CSS_SELECTOR, "table tbody.ig_Item tr")
        INVOICE_NUMBER = (By.CSS_SELECTOR, "td:nth-child(4)")
        INVOICE_DATE = (By.CSS_SELECTOR, "td:nth-child(5)")
        TOTAL_AMOUNT = (By.CSS_SELECTOR, "td:nth-child(7)")
        VIEW_BILL = (By.CSS_SELECTOR, "td a[id$='lbView']")

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
        until=EC.visibility_of_element_located(locator=Selectors.ACCOUNT_DROPDOWN)
    )

    _step_navigate_to_invoices_list_page__before_account_selection = SequentialSteps(
        [
            NavigateToUrl(_VIEW_INVOICES_URL),
            ExplicitWait(
                until=EC.visibility_of_element_located(
                    locator=Selectors.INVOICE_HISTORY
                )
            ),
            ClickElement(Selectors.INVOICE_HISTORY),
        ]
    )

    def get_account_dropdown(self):
        wait_for_element(
            self.driver,
            value=self.Selectors.ACCOUNT_DROPDOWN[1],
            retry_attempts=3,
            msg="Account Dropdown",
        )
        return self.driver.find_element(*self.Selectors.ACCOUNT_DROPDOWN)

    def get_invoice_table_rows(self) -> List[WebElement]:
        wait_for_element(
            self.driver,
            value=self.Selectors.INVOICE_TABLE_ROWS[1],
            retry_attempts=3,
            msg="Invoice Table Rows",
        )
        return self.driver.find_elements(*self.Selectors.INVOICE_TABLE_ROWS)

    def _iter_customer_number_selections(self, customer_numbers: Optional[List[str]]):

        try:
            select = Select(self.get_account_dropdown())
            values = {
                option.get_attribute("value"): option.text for option in select.options
            }

            for option_value, option_text in values.items():
                select_dropdown_option_by_value(
                    self.get_account_dropdown(), option_value
                )
                customer_number, restaurant_name, *_ = option_text.split("-")
                setattr(self, "restaurant_name", restaurant_name.strip())
                yield customer_number.strip(), None
        except WebDriverException as excep:
            LOGGER.info(excep)

            account_text = self.driver.find_element(
                By.CSS_SELECTOR, "a#ctl00_hlCurrentCustomer"
            ).text
            customer_number, restaurant_name, *_ = account_text.split("-")

            setattr(self, "restaurant_name", restaurant_name.strip())
            yield customer_number.strip(), None

    def _iter_invoice_row_elements(self, start_date: date, end_date: date):
        invoice_row_elements = self.get_invoice_table_rows()

        for index, invoice_row_element in enumerate(invoice_row_elements):

            invoice_date = self._extract_invoice_date(invoice_row_element)

            if not start_date <= invoice_date <= end_date:
                LOGGER.info(
                    f"Skipping remaining invoices because date '{invoice_date}' is outside requested range"
                )
                break

            if not has_invoices(
                invoice_row_element, value="td a[id$='lbView']", msg="View Invoice"
            ):
                continue

            yield invoice_row_element

    def _construct_downloader(
        self, invoice_row_element, **invoice_fields
    ) -> BaseDownloader:

        return WebElementClickBasedDownloader(
            element=invoice_row_element.find_element(*self.Selectors.VIEW_BILL),
            local_filepath=self.download_location,
            rename_to=os.path.join(
                self.download_location, invoice_fields["original_filename"]
            ),
            file_exists_check_kwargs=dict(timeout=30, pattern=r"[a-z0-9-]+.pdf.pdf$"),
        )

    def _extract_invoice_date(self, invoice_row_element) -> date:
        return date_from_string(
            invoice_row_element.find_element(*self.Selectors.INVOICE_DATE).text,
            "%m/%d/%Y",
        )

    def _extract_customer_number(
        self, invoice_row_element, customer_number, customer_number_element
    ) -> str:
        return customer_number

    def _extract_invoice_number(self, invoice_row_element, **invoice_fields) -> str:
        return invoice_row_element.find_element(*self.Selectors.INVOICE_NUMBER).text

    def _extract_total_amount(self, invoice_row_element, **invoice_fields) -> str:
        return invoice_row_element.find_element(*self.Selectors.TOTAL_AMOUNT).text

    def _extract_vendor_name(self, invoice_row_element, **invoice_fields) -> str:
        return self.vendor_name

    def _extract_restaurant_name(self, invoice_row_element, **invoice_fields) -> str:
        return getattr(self, "restaurant_name", None)

    def _extract_reference_code(self, invoice_row_element, **invoice_fields) -> str:
        return (
            f"{invoice_fields['customer_number']}"
            f"_{invoice_fields['invoice_number']}"
            f"_{invoice_fields['invoice_date']}"
        )

    def _extract_original_download_url(
        self, invoice_row_element, **invoice_fields
    ) -> str:
        return invoice_fields["reference_code"]

    def _extract_original_filename(self, invoice_row_element, **invoice_fields) -> str:
        return f"{invoice_fields['reference_code']}.pdf"
