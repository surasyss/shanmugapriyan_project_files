import os
from datetime import date
from typing import List, Optional
from integrator import LOGGER
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC

from apps.adapters.framework.registry import connectors
from apps.adapters.framework.operations.vendor import BaseVendorConnector
from apps.adapters.framework.steps.web import (
    NavigateToUrl,
    SubmitLoginPassword,
    ExplicitWait,
)
from apps.adapters.helpers.webdriver_helper import (
    get_url,
    wait_for_element,
)
from apps.adapters.framework import download
from apps.runs.models import FileFormat
from spices.datetime_utils import date_from_string

_LOGIN_URL = "https://mygwp.glendaleca.gov/Register"
_account_billing = "https://mygwp.glendaleca.gov/my-account/billing"


@connectors.add("glendale_water_and_power")
class GlendaleWaterPowerConnector(BaseVendorConnector):
    vendor_name = "City of Glendale"
    invoice_file_format = FileFormat.PDF.ident  # pylint: disable=no-member
    df_download_url_skip_duplicates = True

    class Selectors:

        LOGIN__USERNAME_TEXTBOX = (By.CSS_SELECTOR, "#dnn_dnnLogin_username")
        LOGIN__PASSWORD_TEXTBOX = (By.CSS_SELECTOR, "#passworddnnLogin")
        LOGIN__LOGIN_BUTTON = (By.CSS_SELECTOR, "button[type='submit']")
        LOGIN__ERROR_MESSAGE_TEXT = (By.CSS_SELECTOR, "label.error")

        HOME__ACCOUNT = (By.CSS_SELECTOR, "div.Normal h1")
        HOME__ACCOUNT_DROP_DOWN = (By.CSS_SELECTOR, "#account-selected span")
        HOME__ACCOUNT_LIST = (By.CSS_SELECTOR, "#ul-list-acccount li a")
        HOME__ACCOUNT_NUMBER = (By.CSS_SELECTOR, "#account-selected")

        INVOICE__TABLE_ROW = (
            By.CSS_SELECTOR,
            "table.table.aus-table.aus-table-striped.no-more-tables tbody tr",
        )
        INVOICE__PDF_BUTTON = (By.CSS_SELECTOR, "td[data-title='View eBill'] a")
        INVOICE__DATE = (By.CSS_SELECTOR, "td[data-title='Bill Date']")
        INVOICE_TOTAL_AMOUNT = (By.CSS_SELECTOR, "td[data-title='Bill Amount']")

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
        until=EC.visibility_of_element_located(locator=Selectors.HOME__ACCOUNT)
    )

    def _account_drop_down(self):
        """handle drop down."""
        wait_for_element(self.driver, value=self.Selectors.HOME__ACCOUNT_DROP_DOWN[1])
        self.driver.find_element(*self.Selectors.HOME__ACCOUNT_DROP_DOWN).click()

    def _iter_customer_number_selections(self, customer_numbers: Optional[List[str]]):

        get_url(self.driver, _account_billing)

        self._account_drop_down()

        cus_rows = self.driver.find_elements(*self.Selectors.HOME__ACCOUNT_LIST)

        for index, row in enumerate(cus_rows):

            if index > 0:
                self._account_drop_down()

            customer_number = str(row.text).split(" ")[0]

            # find account row elements before every account selection as it becomes stale
            wait_for_element(self.driver, value=self.Selectors.HOME__ACCOUNT_LIST[1])
            self.driver.find_elements(*self.Selectors.HOME__ACCOUNT_LIST)[index].click()

            yield customer_number, None

    def _iter_invoice_row_elements(self, start_date: date, end_date: date):

        wait_for_element(self.driver, value=self.Selectors.INVOICE__TABLE_ROW[1])

        table_rows = self.driver.find_elements(*self.Selectors.INVOICE__TABLE_ROW)

        for index, row in enumerate(table_rows):

            invoice_date = self._extract_invoice_date(
                self.driver.find_elements(*self.Selectors.INVOICE__TABLE_ROW)[index]
            )
            if not start_date <= invoice_date <= end_date:
                LOGGER.info(
                    f"Skipping remaining invoices because date '{invoice_date}' is outside requested range"
                )
                break
            yield self.driver.find_elements(*self.Selectors.INVOICE__TABLE_ROW)[index]

    def _construct_downloader(
        self, invoice_row_element, **invoice_fields
    ) -> download.BaseDownloader:

        _cus_num = self.driver.find_element(*self.Selectors.HOME__ACCOUNT_NUMBER).text
        _download_patter = (
            str(_cus_num).split(" ")[0]
            + "_"
            + str(self._extract_invoice_date(invoice_row_element))
        )

        return download.DriverBasedUrlGetDownloader(
            self.driver,
            download_url=invoice_row_element.find_element(
                *self.Selectors.INVOICE__PDF_BUTTON
            ).get_attribute("href"),
            local_filepath=os.path.join(
                self.download_location, _download_patter + ".pdf"
            ),
            rename_to=os.path.join(
                self.download_location, invoice_fields["original_filename"]
            ),
            file_exists_check_kwargs=dict(timeout=40),
        )

    def _extract_invoice_date(self, invoice_row_element) -> date:
        return date_from_string(
            invoice_row_element.find_element(*self.Selectors.INVOICE__DATE).text,
            "%m/%d/%Y",
        )

    def _extract_customer_number(
        self, invoice_row_element, customer_number, customer_number_element
    ) -> str:
        return customer_number if customer_number else None

    def _extract_invoice_number(self, invoice_row_element, **invoice_fields) -> str:
        return None

    def _extract_total_amount(self, invoice_row_element, **invoice_fields) -> str:
        return invoice_row_element.find_element(
            *self.Selectors.INVOICE_TOTAL_AMOUNT
        ).text

    def _extract_vendor_name(self, invoice_row_element, **invoice_fields) -> str:
        return self.vendor_name

    def _extract_restaurant_name(self, invoice_row_element, **invoice_fields) -> str:
        return None

    def _extract_reference_code(self, invoice_row_element, **invoice_fields) -> str:
        customer_number = invoice_fields["customer_number"]
        invoice_date = invoice_fields["invoice_date"]
        return f"{customer_number}_{invoice_date}"

    def _extract_original_download_url(
        self, invoice_row_element, **invoice_fields
    ) -> str:
        return f"{invoice_fields['reference_code']}_{invoice_fields['total_amount']}"

    def _extract_original_filename(self, invoice_row_element, **invoice_fields) -> str:
        reference_code = self._extract_reference_code(
            invoice_row_element, **invoice_fields
        )
        return f"{reference_code}.pdf"
