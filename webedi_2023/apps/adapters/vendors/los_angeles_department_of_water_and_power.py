import os
from datetime import date, timedelta
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC

from apps.adapters import LOGGER
from apps.adapters.framework import download
from apps.adapters.framework.registry import connectors
from apps.adapters.framework.operations.vendor import BaseVendorConnector
from apps.adapters.framework.steps.web import (
    NavigateToUrl,
    SubmitLoginPassword,
    ExplicitWait,
)
from apps.adapters.helpers.helper import sleep
from apps.adapters.helpers.webdriver_helper import get_url, wait_for_element
from apps.runs.models import FileFormat

from spices.datetime_utils import date_from_string

_LOGIN_URL = "https://www.ladwp.com/oamsso/login.html"
_ACCOUNT_LIST_PAGE = "https://www.ladwp.com/ladwp/faces/AccountSummary"


@connectors.add("los_angeles_department_of_water_and_power_flores")
class LosAngeles(BaseVendorConnector):
    vendor_name = "LOS ANGELES DEPARTMENT OF WATER & POWER"
    invoice_file_format = FileFormat.PDF.ident  # pylint: disable=no-member
    df_download_url_skip_duplicates = True
    account_details = None

    class Selectors:
        LOGIN__USERNAME_TEXTBOX = (By.CSS_SELECTOR, 'input[name="userid"]')
        LOGIN__PASSWORD_TEXTBOX = (By.CSS_SELECTOR, 'input[name="password"]')
        LOGIN__LOGIN_BUTTON = (By.CSS_SELECTOR, 'input[type="submit"]')
        LOGIN__ERROR_MESSAGE_TEXT = (
            By.CSS_SELECTOR,
            "div.contentBox.clearfix table tbody "
            "tr td:nth-child(1) div:nth-child(2)",
        )

        ACCOUNT_DETAILS_PAGE = (
            By.CSS_SELECTOR,
            "div.wrapword.af_panelGroupLayout > div > a",
        )
        SINGLE_ACCEPT_OK = (
            By.CSS_SELECTOR,
            'table[id$="ADpgxl6"] > tbody > tr > td > a',
        )
        DUE_DATE = (
            By.CSS_SELECTOR,
            "tbody > tr > td:nth-child(3) > span.requestMsgOutputText",
        )
        TOTAL_AMOUNT = (By.XPATH, "//span[contains(text(),'$')]")
        CUSTOMER_NUMBER = (
            By.XPATH,
            "//span[contains(text(),'Account Number')]/following::span",
        )
        RESTAURANT_NAME = (
            By.XPATH,
            "//div/*[contains(text(),'Edit Account Name')]/following::span",
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

    def check_for_covid_message(self):
        covid_messages = self.driver.find_elements(*self.Selectors.SINGLE_ACCEPT_OK)
        if covid_messages:
            covid_messages[0].click()

    def _iter_invoice_row_elements(self, start_date: date, end_date: date):
        rows = self.driver.find_elements_by_css_selector("table.tableHorLine")
        if rows:
            rows = [row for row in rows if "Closed" not in row.text]
            for index, row in enumerate(rows):
                if index > 0:
                    get_url(self.driver, _ACCOUNT_LIST_PAGE)
                    sleep(5)
                self.driver.find_elements(*self.Selectors.ACCOUNT_DETAILS_PAGE)[
                    index
                ].click()
                self.check_for_covid_message()
                wait_for_element(
                    self.driver,
                    value="span.af_selectOneChoice > select.af_selectOneChoice_content",
                    msg="Account drop down",
                )
                wait_for_element(
                    self.driver,
                    value='table[id$="pgl106"] > tbody > tr > td:nth-child(2) > span',
                    msg="wait for table element",
                    raise_exception=False,
                )
                yield index
        else:
            self.check_for_covid_message()
            wait_for_element(
                self.driver,
                value="span.accountsummaryscanAccountnum",
                retry_attempts=1,
                raise_exception=False,
                msg="wait of account details",
            )
            yield self.driver

    def _construct_downloader(
        self, invoice_row_element, **invoice_fields
    ) -> download.BaseDownloader:
        self.driver.find_element_by_css_selector(
            'div.lftMenu a[title="View Bill"]'
        ).click()
        LOGGER.info("Navigating to the view bill page...")
        sleep(10)
        return download.DriverBasedUrlGetDownloader(
            self.driver,
            download_url="https://www.ladwp.com/ladwp/getbillpdf?index=en",
            local_filepath=os.path.join(self.download_location, "getbillpdf.pdf"),
            rename_to=os.path.join(
                self.download_location, invoice_fields["original_filename"]
            ),
            file_exists_check_kwargs=dict(timeout=20),
        )

    def _extract_invoice_date(self, invoice_row_element) -> date:
        return date_from_string(
            self.driver.find_elements(*self.Selectors.DUE_DATE)[-1].text.strip(),
            "%m/%d/%Y",
        ) - timedelta(days=20)

    def _extract_customer_number(
        self, invoice_row_element, customer_number, customer_number_element
    ) -> str:
        return self.driver.find_element(*self.Selectors.CUSTOMER_NUMBER).text

    def _extract_invoice_number(self, invoice_row_element, **invoice_fields) -> str:
        return None

    def _extract_total_amount(self, invoice_row_element, **invoice_fields) -> str:
        return self.driver.find_elements(*self.Selectors.TOTAL_AMOUNT)[-1].text

    def _extract_vendor_name(self, invoice_row_element, **invoice_fields) -> str:
        return self.vendor_name

    def _extract_restaurant_name(self, invoice_row_element, **invoice_fields) -> str:
        return self.driver.find_element(*self.Selectors.RESTAURANT_NAME).text

    def _extract_reference_code(self, invoice_row_element, **invoice_fields) -> str:
        return f"{invoice_fields['customer_number']}_{invoice_fields['invoice_date']}"

    def _extract_original_download_url(
        self, invoice_row_element, **invoice_fields
    ) -> str:
        return invoice_fields["customer_number"]

    def _extract_original_filename(self, invoice_row_element, **invoice_fields) -> str:
        return f'{invoice_fields["reference_code"]}.pdf'
