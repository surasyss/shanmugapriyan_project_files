import os
from datetime import date
from integrator import LOGGER

from selenium.webdriver import ActionChains
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
from apps.adapters.helpers.webdriver_helper import hover_over_element
from apps.runs.models import FileFormat
from spices.datetime_utils import date_from_string

_LOGIN_URL = "https://app.next.nuorder.com/"


@connectors.add("rainforest_distributon_corp")
class AtmosConnector(BaseVendorConnector):
    vendor_name = "Rainforest Distribution Corp"
    invoice_file_format = FileFormat.PDF.ident  # pylint: disable=no-member
    df_download_url_skip_duplicates = True

    class Selectors:
        LOGIN__USERNAME_TEXTBOX = (
            By.CSS_SELECTOR,
            'input[id^="email-undefined-undefined"]',
        )
        LOGIN__PASSWORD_TEXTBOX = (
            By.CSS_SELECTOR,
            'input[id^="password-undefined-undefined"]',
        )
        LOGIN__LOGIN_BUTTON = (By.CSS_SELECTOR, "button.loginSubmit")
        LOGIN__ERROR_MESSAGE_TEXT = (By.CSS_SELECTOR, 'div[data-test="login-error"]')

        BILLING_HISTORY__TABLE_ROWS = (
            By.CSS_SELECTOR,
            "div.ordersPageOrdersList div[data-css-1himxbx]",
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

    def _iter_invoice_row_elements(self, start_date: date, end_date: date):
        menu_navigation = self.driver.find_element_by_css_selector(
            'nav[data-test="site-nav"]'
        )
        orders = self.driver.find_element_by_css_selector('div a[data-test="orders"]')
        ActionChains(self.driver).move_to_element(menu_navigation).click(
            orders
        ).perform()

        collected_rows = []
        date_in_range = True

        self.driver.execute_script(
            "var element = arguments[0];" "element.parentNode.removeChild(element);",
            self.driver.find_element_by_xpath('//div/button[contains(text(), "Help")]'),
        )

        while date_in_range:
            table_rows = self.driver.find_elements(
                *self.Selectors.BILLING_HISTORY__TABLE_ROWS
            )

            for index, _ in enumerate(table_rows):
                row = self.driver.find_elements(
                    *self.Selectors.BILLING_HISTORY__TABLE_ROWS
                )[index]
                row_text = row.text
                if row_text in collected_rows:
                    continue
                collected_rows.append(row_text)

                invoice_date = self._extract_invoice_date(row)
                if not start_date <= invoice_date <= end_date:
                    date_in_range = False
                    LOGGER.info(
                        f"Skipping remaining invoices because date '{invoice_date}' is outside requested range"
                    )
                    break
                yield row

            self.driver.execute_script(
                "window.scrollTo(0, document.body.scrollHeight);"
            )

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
            file_exists_check_kwargs=dict(
                timeout=20, pattern=r"rainforest_distribution_order\S+.pdf$"
            ),
        )

    def _extract_invoice_date(self, invoice_row_element) -> date:
        return date_from_string(
            invoice_row_element.find_element_by_css_selector(
                'div[data-test="created-on"]'
            ).text,
            "%b %d, %Y",
        )

    def _extract_customer_number(
        self, invoice_row_element, customer_number, customer_number_element
    ) -> str:
        return customer_number if customer_number else None

    def _extract_invoice_number(self, invoice_row_element, **invoice_fields) -> str:
        return invoice_row_element.find_element_by_css_selector(
            'div[data-test="order-number"]'
        ).text

    def _extract_total_amount(self, invoice_row_element, **invoice_fields) -> str:
        return invoice_row_element.find_element_by_css_selector(
            'div[data-test="total"]'
        ).text

    def _extract_vendor_name(self, invoice_row_element, **invoice_fields) -> str:
        return self.vendor_name

    def _extract_restaurant_name(self, invoice_row_element, **invoice_fields) -> str:
        return invoice_row_element.find_element_by_css_selector(
            'div[data-test="company-name"]'
        ).text

    def _extract_reference_code(self, invoice_row_element, **invoice_fields) -> str:
        invoice_number = invoice_fields["invoice_number"]
        invoice_date = invoice_fields["invoice_date"]
        return f"{invoice_number}_{invoice_date}"

    def _extract_original_download_url(
        self, invoice_row_element, **invoice_fields
    ) -> str:
        hover_over_element(self.driver, invoice_row_element)
        more = invoice_row_element.find_element_by_css_selector(
            'div.inner button[data-test="more-actions-icon"]'
        )
        ActionChains(self.driver).move_to_element(more).click(more).perform()
        original_download_url = self.driver.find_element_by_css_selector(
            'a[data-test="action-pdf"]'
        ).get_attribute("href")
        invoice_row_element.find_element_by_css_selector("div.offClick").click()
        return original_download_url

    def _extract_original_filename(self, invoice_row_element, **invoice_fields) -> str:
        reference_code = self._extract_reference_code(
            invoice_row_element, **invoice_fields
        )
        return f"{reference_code}.pdf"
