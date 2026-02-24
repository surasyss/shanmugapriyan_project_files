import os
import re
from datetime import date
from integrator import LOGGER

from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC

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
    get_url,
)
from apps.runs.models import FileFormat
from spices.datetime_utils import date_from_string

_LOGIN_URL = "https://mycpau.cityofpaloalto.org/Portal/"
_BILLING_HISTORY = "https://mycpau.cityofpaloalto.org/Portal/BillingHistory.aspx"


@connectors.add("city_of_palo_alto")
class CityOfPaloAltoConnector(BaseVendorConnector):
    vendor_name = "City of Palo Alto"
    invoice_file_format = FileFormat.PDF.ident  # pylint: disable=no-member
    df_download_url_skip_duplicates = True

    class Selectors:
        LOGIN__USERNAME_TEXTBOX = (By.CSS_SELECTOR, 'input[id="txtLogin"]')
        LOGIN__PASSWORD_TEXTBOX = (By.CSS_SELECTOR, 'input[id="txtpwd"]')
        LOGIN__LOGIN_BUTTON = (By.CSS_SELECTOR, 'input[id="btnlogin"]')
        LOGIN__ERROR_MESSAGE_TEXT = (By.CSS_SELECTOR, "div.toast-error")

        BILLING_HISTORY__TABLE_ROWS = (
            By.CSS_SELECTOR,
            'div[id="grid_wugrid_records"] table tbody tr',
        )
        BILLING_HISTORY__RESTAURANT_NAME = (By.CSS_SELECTOR, "span#lblCustName")

        @staticmethod
        def billing_history_data(row_index, col_index, extra_selector=None):
            selector = f"td#grid_wugrid_data_{row_index}_{col_index}"
            if extra_selector:
                return By.CSS_SELECTOR, f"{selector} {extra_selector}"

            return By.CSS_SELECTOR, selector

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
        until=EC.visibility_of_element_located(
            locator=Selectors.BILLING_HISTORY__RESTAURANT_NAME
        )
    )

    def get_restaurant_name(self):
        return self.driver.find_element(
            *self.Selectors.BILLING_HISTORY__RESTAURANT_NAME
        )

    def get_download_element(self, invoice_row_element):
        return invoice_row_element.find_element(
            *self.Selectors.billing_history_data(
                getattr(self, "row_index"), 3, extra_selector="a"
            )
        )

    def get_invoice_table_rows(self):
        return self.driver.find_elements(*self.Selectors.BILLING_HISTORY__TABLE_ROWS)[
            2:-2
        ]

    def _iter_invoice_row_elements(self, start_date: date, end_date: date):
        get_url(self.driver, _BILLING_HISTORY)

        wait_for_loaders(
            self.driver, value='div[id="page_loader"][style="display: block;"]'
        )

        restaurant_name = self.get_restaurant_name()
        setattr(self, "restaurant_name", restaurant_name.text)

        table_rows = self.get_invoice_table_rows()

        for index, row_element in enumerate(table_rows):
            setattr(self, "row_index", index)

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
            element=self.get_download_element(invoice_row_element),
            local_filepath=self.download_location,
            rename_to=os.path.join(
                self.download_location, invoice_fields["original_filename"]
            ),
            file_exists_check_kwargs=dict(
                timeout=20, pattern=rf"^{invoice_fields['customer_number']}_\d+\.pdf$"
            ),
        )

    def _extract_invoice_date(self, invoice_row_element) -> date:
        invoice_date = invoice_row_element.find_element(
            *self.Selectors.billing_history_data(getattr(self, "row_index"), 1)
        )
        return date_from_string(invoice_date.text, "%m-%d-%Y")

    def _extract_customer_number(
        self, invoice_row_element, customer_number, customer_number_element
    ) -> str:
        view_bill_element = self.get_download_element(invoice_row_element)
        customer_number = re.findall(
            r"\d+", view_bill_element.get_attribute("onclick")
        )[0]
        return customer_number.lstrip("0")

    def _extract_invoice_number(self, invoice_row_element, **invoice_fields) -> str:
        return None

    def _extract_total_amount(self, invoice_row_element, **invoice_fields) -> str:
        total_amount = invoice_row_element.find_element(
            *self.Selectors.billing_history_data(getattr(self, "row_index"), 2)
        )
        return total_amount.text.replace(",", "")

    def _extract_vendor_name(self, invoice_row_element, **invoice_fields) -> str:
        return self.vendor_name

    def _extract_restaurant_name(self, invoice_row_element, **invoice_fields) -> str:
        return getattr(self, "restaurant_name", None)

    def _extract_reference_code(self, invoice_row_element, **invoice_fields) -> str:
        customer_number = invoice_fields["customer_number"]
        invoice_date = invoice_fields["invoice_date"]
        total_amount = invoice_fields["total_amount"]

        return f"{customer_number}_{invoice_date}_{total_amount.replace('.', '')}"

    def _extract_original_download_url(
        self, invoice_row_element, **invoice_fields
    ) -> str:
        return invoice_fields["reference_code"]

    def _extract_original_filename(self, invoice_row_element, **invoice_fields) -> str:
        reference_code = self._extract_reference_code(
            invoice_row_element, **invoice_fields
        )
        return f"{reference_code}.pdf"
