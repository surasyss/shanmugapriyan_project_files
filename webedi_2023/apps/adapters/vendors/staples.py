import os
from datetime import date

from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC

from apps.adapters import LOGGER
from apps.adapters.framework.steps.primitives import SequentialSteps

from apps.adapters.framework import download
from apps.adapters.framework.registry import connectors
from apps.adapters.framework.operations.vendor import BaseVendorConnector
from apps.adapters.framework.steps.web import (
    NavigateToUrl,
    SubmitLoginPassword,
    ExplicitWait,
    ClickElement,
    ImplicitWait,
)
from apps.adapters.helpers.webdriver_helper import (
    wait_for_element,
    scroll_down,
    WEB_DRIVER_EXCEPTIONS,
)
from apps.runs.models import FileFormat
from spices.datetime_utils import date_from_string

_LOGIN_URL = "https://www.staples.com"
_ORDER_URL = "https://www.staples.com/ptd/myorders"


@connectors.add("staples")
class StaplesConnector(BaseVendorConnector):
    vendor_name = "staples"
    invoice_file_format = FileFormat.PDF.ident  # pylint: disable=no-member
    df_download_url_skip_duplicates = True

    class Selectors:
        LOGIN__SELECTION = (By.CSS_SELECTOR, 'div[id="top_right_menu_item_1"]')
        LOGIN__SIGN_IN = (By.XPATH, '//span[text()="Sign In"]')

        HOME_SEARCH_BOX = (By.CSS_SELECTOR, "#searchInput")

        LOGIN__USERNAME_TEXTBOX = (By.CSS_SELECTOR, 'input[name="username"]')
        LOGIN__PASSWORD_TEXTBOX = (By.CSS_SELECTOR, 'input[name="password"]')
        LOGIN__LOGIN_BUTTON = (By.CSS_SELECTOR, "#loginBtn")
        LOGIN__ERROR_MESSAGE_TEXT = (
            By.CSS_SELECTOR,
            "span.notificationBubble__content",
        )

        BILLING_HISTORY__TABLE_ROWS = (
            By.CSS_SELECTOR,
            "#PTD_OrderResults>div>div>table>tbody",
        )
        ORDER_RESTAURANT_NAME = 'div[id$="shipAddress.companyName"]'

    # login
    _navigate_to_login_page = NavigateToUrl(_LOGIN_URL, retry_attempts=5)

    # _navigate_to_login_page =
    _submit_login_info__pre = SequentialSteps(
        [
            ClickElement(Selectors.LOGIN__SELECTION),
            ClickElement(Selectors.LOGIN__SIGN_IN),
            ExplicitWait(
                until=EC.visibility_of_element_located(
                    locator=Selectors.LOGIN__USERNAME_TEXTBOX
                )
            ),
        ]
    )
    _submit_login_info = SubmitLoginPassword(
        username_textbox=Selectors.LOGIN__USERNAME_TEXTBOX,
        password_textbox=Selectors.LOGIN__PASSWORD_TEXTBOX,
        login_button=Selectors.LOGIN__LOGIN_BUTTON,
        error_message=Selectors.LOGIN__ERROR_MESSAGE_TEXT,
    )

    # order page navigation
    _submit_login_info__post = SequentialSteps(
        [
            ImplicitWait(timeout=20),
            NavigateToUrl(_ORDER_URL, retry_attempts=5),
        ]
    )

    def _iter_invoice_row_elements(self, start_date: date, end_date: date):
        table_rows = self.driver.find_elements(
            *self.Selectors.BILLING_HISTORY__TABLE_ROWS
        )
        for row in table_rows:
            invoice_date = self._extract_invoice_date(row)
            if not start_date <= invoice_date <= end_date:
                LOGGER.info(
                    f"Skipping remaining invoices because date '{invoice_date}' is outside requested range"
                )
                break

            if "Receipt (pdf)" in row.text:
                yield row

    def _construct_downloader(
        self, invoice_row_element, **invoice_fields
    ) -> download.BaseDownloader:
        return download.DriverBasedUrlGetDownloader(
            self.driver,
            download_url=invoice_fields["original_download_url"],
            local_filepath=os.path.join(
                self.download_location, "transaction-summary.pdf"
            ),
            rename_to=os.path.join(
                self.download_location, invoice_fields["original_filename"]
            ),
            file_exists_check_kwargs=dict(timeout=20),
        )

    def _extract_invoice_date(self, invoice_row_element) -> date:
        return date_from_string(
            invoice_row_element.find_element_by_css_selector(
                'tr>td[data-label="Date"]'
            ).text,
            "%m/%d/%y",
        )

    def _extract_invoice_number(self, invoice_row_element, **invoice_fields) -> str:
        return f'STAPLES-{invoice_fields["invoice_date"]}'

    def _extract_total_amount(self, invoice_row_element, **invoice_fields) -> str:
        return invoice_row_element.find_element_by_css_selector(
            'tr>td[data-label="Total"]'
        ).text

    def _extract_vendor_name(self, invoice_row_element, **invoice_fields) -> str:
        return "Staples"

    def _extract_reference_code(self, invoice_row_element, **invoice_fields) -> str:
        return f'{invoice_fields["customer_number"]}_{invoice_fields["invoice_date"]}'

    def _extract_original_download_url(
        self, invoice_row_element, **invoice_fields
    ) -> str:
        return invoice_row_element.find_element_by_css_selector(
            'a[id$="viewreceipt"]'
        ).get_attribute("href")

    def _extract_original_filename(self, invoice_row_element, **invoice_fields) -> str:
        reference_code = self._extract_reference_code(
            invoice_row_element, **invoice_fields
        )
        return f"{reference_code}.pdf"

    def _extract_customer_number(
        self, invoice_row_element, customer_number, customer_number_element
    ) -> str:
        return None

    def get_order_page(self, invoice_row_element):
        """Get restaurant name"""
        order_page_link = invoice_row_element.find_element_by_css_selector(
            'tr>td[data-label="Order"] a'
        ).get_attribute("href")

        # navigate order link page
        self.driver.execute_script('window.open("' + order_page_link + '","_blank");')
        self.driver.switch_to.window(self.driver.window_handles[1])

        scroll_down(self.driver)

        try:
            wait_for_element(
                self.driver,
                value=self.Selectors.ORDER_RESTAURANT_NAME,
                msg="wait company name",
                retry_attempts=1,
                raise_exception=False,
            )
            restaurant_name = self.driver.find_element_by_css_selector(
                self.Selectors.ORDER_RESTAURANT_NAME
            ).get_attribute("innerText")
        except WEB_DRIVER_EXCEPTIONS:
            restaurant_name = None

        self.driver.close()
        self.driver.switch_to.window(self.driver.window_handles[0])
        return restaurant_name

    def _extract_restaurant_name(self, invoice_row_element, **invoice_fields) -> str:
        get_restaurant_name = self.get_order_page(invoice_row_element)
        return get_restaurant_name
