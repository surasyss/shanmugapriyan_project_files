import os
from datetime import date
from typing import List, Optional

from selenium.common.exceptions import NoSuchElementException
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC

from apps.adapters.framework import download
from apps.adapters.framework.context import ExecutionContext
from apps.adapters.framework.registry import connectors
from apps.adapters.framework.operations.vendor import BaseVendorConnector
from apps.adapters.framework.steps.primitives import SequentialSteps
from apps.adapters.framework.steps.web import (
    NavigateToUrl,
    SubmitLoginPassword,
    ExplicitWait,
)
from apps.adapters.helpers.helper import sleep
from apps.adapters.helpers.webdriver_helper import (
    get_url,
    wait_for_element,
    has_invoices,
    close_extra_handles,
    wait_for_loaders,
)
from apps.runs.models import FileFormat
from spices.datetime_utils import date_from_string

from integrator import LOGGER

_LOGIN_URL = "https://customerportal.rollins.com/"
SERVICE__HISTORY_URL = "https://customerportal.rollins.com/Service"
HOME__ACCOUNT_PAGE = "https://customerportal.rollins.com/Home/PickAccount"


class WaitForBackgroundImageLoad:
    """Wait for background image to load."""

    def __call__(self, execution_context: ExecutionContext):
        bg_img = execution_context.driver.find_element(
            By.CSS_SELECTOR, 'img[src*="email_main_image"]'
        )
        retry = 5
        while retry:
            if execution_context.driver.execute_script(
                "return arguments[0].complete;", bg_img
            ):
                LOGGER.info("Background image loaded.")
                break
            sleep(5, msg="Wait for background image to load")
            retry -= 1


@connectors.add("orkin")
class OrkinConnector(BaseVendorConnector):
    vendor_name = "ORKIN"
    invoice_file_format = FileFormat.PDF.ident  # pylint: disable=no-member

    class Selectors:
        LOGIN__USERNAME_TEXTBOX = (By.CSS_SELECTOR, "input#logonIdentifier")
        LOGIN__PASSWORD_TEXTBOX = (By.CSS_SELECTOR, "input#password")
        LOGIN__LOGIN_BUTTON = (By.CSS_SELECTOR, "button#next")
        LOGIN__ERROR_MESSAGE_TEXT = (By.CSS_SELECTOR, "div.error.pageLevel > p")

        HOME__ACCOUNT_TABLE = (By.CSS_SELECTOR, "#tblAccounts > tbody > tr")
        HOME__ACCOUNT_LINK = (
            By.CSS_SELECTOR,
            "#tblAccounts > tbody > tr > td > a.goToLink",
        )

        INVOICE__TABLE_ROW = (By.CSS_SELECTOR, "#tblServiceHistory > tbody > tr")
        HOME__ACCOUNT_NUMBER = (
            By.CSS_SELECTOR,
            "div:nth-child(1) > div[class^='col-md-8']",
        )
        HOME__ACCOUNT_NAME = (
            By.CSS_SELECTOR,
            "div:nth-child(2) > div[class^='col-md-8']",
        )
        INVOICE__TOTAL_PAGES = (
            By.CSS_SELECTOR,
            "#tblServiceHistory_paginate > span > a",
        )
        INVOICE__NEXT_PAGE = (By.CSS_SELECTOR, "#tblServiceHistory_next")

        RECENT_INVOICES__DOWNLOAD_FILE = (By.CSS_SELECTOR, "a.lnkreprint > span")
        INVOICES_TABLE_TD = (By.CSS_SELECTOR, "td")
        ACCEPT_BUTTON = (By.CSS_SELECTOR, "#btnAcceptTC")
        LOADER = "span.dataProcessing"

    _navigate_to_login_page = NavigateToUrl(_LOGIN_URL, retry_attempts=5)

    _submit_login_info__pre = SequentialSteps(
        [
            WaitForBackgroundImageLoad(),
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

    def account_table_rows(self):
        return self.driver.find_elements(*self.Selectors.HOME__ACCOUNT_TABLE)

    def select_account_row(self, account_index):
        for _ in range(5):
            if "PickAccount" not in self.driver.current_url:
                break
            self.driver.execute_script(
                "arguments[0].click();",
                self.driver.find_elements(*self.Selectors.HOME__ACCOUNT_LINK)[
                    account_index
                ],
            )
            wait_for_loaders(
                self.driver,
                value=self.Selectors.LOADER,
            )

    def _iter_customer_number_selections(self, customer_numbers: Optional[List[str]]):
        account_table_rows = self.account_table_rows()

        if account_table_rows:
            for account_index, _ in enumerate(account_table_rows):
                get_url(self.driver, HOME__ACCOUNT_PAGE)

                wait_for_loaders(
                    self.driver,
                    value=self.Selectors.LOADER,
                )

                wait_for_element(
                    self.driver,
                    value=self.Selectors.HOME__ACCOUNT_TABLE[1],
                    retry_attempts=1,
                    raise_exception=False,
                    msg="Account Rows",
                )

                customer_number_row = self.account_table_rows()[account_index]
                customer_number = customer_number_row.find_element(
                    *self.Selectors.INVOICES_TABLE_TD
                ).text
                self.select_account_row(account_index)

                if "termsofuse" in self.driver.current_url.lower():
                    self.driver.find_element(*self.Selectors.ACCEPT_BUTTON).click()

                yield customer_number, None
        else:
            yield None, None

    def _iter_invoice_row_elements(self, start_date: date, end_date: date):
        get_url(self.driver, SERVICE__HISTORY_URL)

        if not has_invoices(
            self.driver,
            value=self.Selectors.INVOICE__TABLE_ROW[1],
            retry_attempts=3,
        ):
            return

        for page_number, _ in enumerate(
            self.driver.find_elements(*self.Selectors.INVOICE__TOTAL_PAGES)
        ):

            if page_number > 0:
                self.driver.execute_script(
                    "arguments[0].click();",
                    self.driver.find_element(*self.Selectors.INVOICE__NEXT_PAGE),
                )

            table_rows = self.driver.find_elements(*self.Selectors.INVOICE__TABLE_ROW)
            for row_index, _ in enumerate(table_rows):
                close_extra_handles(self.driver)
                row_element = self.driver.find_elements(
                    *self.Selectors.INVOICE__TABLE_ROW
                )[row_index]
                if self.row_has_pdf(row_element):
                    yield [
                        row_element,
                        self.driver.find_element(*self.Selectors.HOME__ACCOUNT_NAME),
                        self.driver.find_element(*self.Selectors.HOME__ACCOUNT_NUMBER),
                    ]

    def row_has_pdf(self, row_element):
        try:
            row_element.find_element(*self.Selectors.RECENT_INVOICES__DOWNLOAD_FILE)
            return True
        except NoSuchElementException:
            LOGGER.info("Pdf not available to download.")
            return False

    def _construct_downloader(
        self, invoice_row_element, **invoice_fields
    ) -> download.BaseDownloader:
        return download.WebElementClickBasedDownloader(
            element=invoice_row_element[0].find_element(
                *self.Selectors.RECENT_INVOICES__DOWNLOAD_FILE
            ),
            local_filepath=f"{self.download_location}/"
            f'{invoice_fields["invoice_number"]}.pdf',
            rename_to=os.path.join(
                self.download_location, invoice_fields["original_filename"]
            ),
            file_exists_check_kwargs=dict(timeout=20),
        )

    def _extract_invoice_date(self, invoice_row_element) -> date:
        return date_from_string(
            invoice_row_element[0]
            .find_elements(*self.Selectors.INVOICES_TABLE_TD)[0]
            .text,
            "%m/%d/%Y",
        )

    def _extract_customer_number(
        self, invoice_row_element, customer_number, customer_number_element
    ) -> str:
        return invoice_row_element[-1].text

    def _extract_invoice_number(self, invoice_row_element, **invoice_fields) -> str:
        return (
            invoice_row_element[0]
            .find_elements(*self.Selectors.INVOICES_TABLE_TD)[3]
            .text
        )

    def _extract_total_amount(self, invoice_row_element, **invoice_fields) -> str:
        return (
            invoice_row_element[0]
            .find_elements(*self.Selectors.INVOICES_TABLE_TD)[5]
            .text
        )

    def _extract_vendor_name(self, invoice_row_element, **invoice_fields) -> str:
        return self.vendor_name

    def _extract_restaurant_name(self, invoice_row_element, **invoice_fields) -> str:
        return invoice_row_element[1].text

    def _extract_reference_code(self, invoice_row_element, **invoice_fields) -> str:
        customer_number = invoice_fields["customer_number"]
        invoice_number = invoice_fields["invoice_number"]
        invoice_date = invoice_fields["invoice_date"]
        return f"{customer_number}_{invoice_number}_{invoice_date}"

    def _extract_original_download_url(
        self, invoice_row_element, **invoice_fields
    ) -> str:
        download_element = (
            invoice_row_element[0]
            .find_elements(*self.Selectors.INVOICES_TABLE_TD)[3]
            .text
        )
        return download_element

    def _extract_original_filename(self, invoice_row_element, **invoice_fields) -> str:
        reference_code = self._extract_reference_code(
            invoice_row_element, **invoice_fields
        )
        return f"{reference_code}.pdf"
