import os
import re
from datetime import date
from typing import Optional, List

from apps.adapters.framework.context import ExecutionContext
from apps.adapters.framework.steps.primitives import SequentialSteps
from integrator import LOGGER

from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import Select

from apps.adapters.framework.download import (
    BaseDownloader,
    WebElementClickBasedDownloader,
)
from apps.adapters.framework.registry import connectors
from apps.adapters.framework.operations.vendor import BaseVendorConnector
from apps.adapters.framework.steps.web import (
    NavigateToUrl,
    SubmitLoginPassword,
    ExplicitWait,
)
from apps.adapters.helpers.webdriver_helper import (
    wait_for_loaders,
    select_dropdown_option_by_visible_text,
    handle_popup,
)
from apps.runs.models import FileFormat
from spices.datetime_utils import date_from_string

_LOGIN_URL = "https://my.burbankwaterandpower.com/portal/"
_BILLING_HISTORY = "https://my.burbankwaterandpower.com/Portal/BillingHistory.aspx"


class HandlePopup:
    """Handle popup"""

    def __init__(self, value, msg):
        self.value = value
        self.msg = msg

    def __call__(self, execution_context: ExecutionContext):
        handle_popup(
            execution_context.driver,
            by_selector=By.CSS_SELECTOR,
            value=self.value,
            msg=self.msg,
            retry_attempts=1,
        )


@connectors.add("burbank_water_and_power")
class BurbankWaterAndPowerConnector(BaseVendorConnector):
    vendor_name = "Burbank Water and Power"
    invoice_file_format = FileFormat.PDF.ident  # pylint: disable=no-member
    df_download_url_skip_duplicates = True

    class Selectors:
        LOGIN__USERNAME_TEXTBOX = (By.CSS_SELECTOR, 'input[id="txtLogin"]')
        LOGIN__PASSWORD_TEXTBOX = (By.CSS_SELECTOR, 'input[id="txtpwd"]')
        LOGIN__LOGIN_BUTTON = (By.CSS_SELECTOR, 'input[id="btnlogin"]')
        LOGIN__ERROR_MESSAGE_TEXT = (By.CSS_SELECTOR, "div.toast-error")

        BILLING_HISTORY__ACCOUNTS_DROPDOWN = (By.CSS_SELECTOR, "select#ddlAddress")
        BILLING_HISTORY__TABLE_ROWS = (
            By.CSS_SELECTOR,
            'table[id="wugridTable"] tbody tr',
        )
        BILLING_HISTORY__RESTAURANT_NAME = (By.CSS_SELECTOR, "span#lblCustName")
        PAGE_LOAD_POPUP = "div.modal.in button.close"

    # login
    _navigate_to_login_page = SequentialSteps(
        [
            NavigateToUrl(_LOGIN_URL, retry_attempts=5),
            HandlePopup(
                value=Selectors.PAGE_LOAD_POPUP,
                msg="Online Payments Just Got More Secure",
            ),
        ]
    )
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
        until=EC.visibility_of_element_located(
            locator=Selectors.BILLING_HISTORY__RESTAURANT_NAME
        )
    )

    _step_navigate_to_invoices_list_page__before_account_selection = NavigateToUrl(
        url=_BILLING_HISTORY
    )

    def get_restaurant_name(self):
        return self.driver.find_element(
            *self.Selectors.BILLING_HISTORY__RESTAURANT_NAME
        )

    @staticmethod
    def get_download_element(invoice_row_element):
        return invoice_row_element.find_element(By.CSS_SELECTOR, "td:nth-child(3) img")

    def get_invoice_table_rows(self):
        return self.driver.find_elements(*self.Selectors.BILLING_HISTORY__TABLE_ROWS)

    def get_account_select_dropdown(self):
        return self.driver.find_element(
            *self.Selectors.BILLING_HISTORY__ACCOUNTS_DROPDOWN
        )

    def _iter_customer_number_selections(self, customer_numbers: Optional[List[str]]):

        restaurant_name = self.get_restaurant_name()
        setattr(self, "restaurant_name", restaurant_name.text)

        customer_select_dd = Select(self.get_account_select_dropdown())
        accounts = [option.text for option in customer_select_dd.options]

        for account in accounts:
            select_dropdown_option_by_visible_text(
                self.get_account_select_dropdown(), account
            )
            wait_for_loaders(
                self.driver, value='div[id="page_loader"][style="display: block;"]'
            )
            customer_number = re.findall(r"\d+", account)[-1]
            yield customer_number, None

    def _iter_invoice_row_elements(self, start_date: date, end_date: date):

        table_rows = self.get_invoice_table_rows()

        for index, row_element in enumerate(table_rows):

            invoice_date = self._extract_invoice_date(row_element)
            if not start_date <= invoice_date <= end_date:
                LOGGER.info(
                    f"Skipping remaining invoices because date '{invoice_date}' is outside requested range"
                )
                break

            yield row_element

    def _construct_downloader(
        self, invoice_row_element, **invoice_fields
    ) -> BaseDownloader:
        return WebElementClickBasedDownloader(
            element=BurbankWaterAndPowerConnector.get_download_element(
                invoice_row_element
            ),
            local_filepath=os.path.join(self.download_location, "document.pdf"),
            rename_to=os.path.join(
                self.download_location, invoice_fields["original_filename"]
            ),
            file_exists_check_kwargs=dict(timeout=20),
        )

    def _extract_invoice_date(self, invoice_row_element) -> date:
        invoice_date = invoice_row_element.find_element(
            By.CSS_SELECTOR, "td:nth-child(1)"
        )
        return date_from_string(invoice_date.text, "%m/%d/%y")

    def _extract_customer_number(
        self, invoice_row_element, customer_number, customer_number_element
    ) -> str:
        return customer_number

    def _extract_invoice_number(self, invoice_row_element, **invoice_fields) -> str:
        return None

    def _extract_total_amount(self, invoice_row_element, **invoice_fields) -> str:
        total_amount = invoice_row_element.find_element(
            By.CSS_SELECTOR, "td:nth-child(2)"
        )
        return total_amount.text

    def _extract_vendor_name(self, invoice_row_element, **invoice_fields) -> str:
        return self.vendor_name

    def _extract_restaurant_name(self, invoice_row_element, **invoice_fields) -> str:
        return getattr(self, "restaurant_name", None)

    def _extract_reference_code(self, invoice_row_element, **invoice_fields) -> str:
        customer_number = invoice_fields["customer_number"]
        invoice_date = invoice_fields["invoice_date"]
        total_amount = invoice_fields["total_amount"].replace(",", "").replace(".", "")
        return f"{customer_number}_{invoice_date}_{total_amount}"

    def _extract_original_download_url(
        self, invoice_row_element, **invoice_fields
    ) -> str:
        return invoice_fields["reference_code"]

    def _extract_original_filename(self, invoice_row_element, **invoice_fields) -> str:
        return f"{invoice_fields['reference_code']}.pdf"
