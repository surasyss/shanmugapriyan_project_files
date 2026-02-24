import os
from datetime import date
from typing import List, Optional

from apps.adapters.framework.download import WebElementClickBasedDownloader
from apps.adapters.framework.registry import connectors
from integrator import LOGGER

from selenium.webdriver.common.by import By
from selenium.common.exceptions import (
    TimeoutException,
    StaleElementReferenceException,
    ElementClickInterceptedException,
)
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait
from selenium.common.exceptions import WebDriverException, NoSuchElementException

from apps.adapters.framework.operations.vendor import BaseVendorConnector
from apps.adapters.framework.steps.web import (
    NavigateToUrl,
    ExplicitWait,
    SubmitLoginPassword,
)
from apps.adapters.helpers.webdriver_helper import (
    wait_for_element,
    wait_for_loaders,
    close_extra_handles,
    hover_over_element,
    execute_script_click,
)
from apps.adapters.framework import download
from apps.runs.models import FileFormat
from spices.datetime_utils import date_from_string

_LOGIN_URL = "https://www.myentergy.com/s/login/"
_LAST_ACTIVE_ACCOUNT_URL = "https://www.myentergy.com/s/lastactiveaccountredirect"


@connectors.add("entergy")
class EntergyConnector(BaseVendorConnector):
    vendor_name = "Entergy"
    invoice_file_format = FileFormat.PDF.ident  # pylint: disable=no-member
    df_download_url_skip_duplicates = True

    class Selectors:
        LOGIN__USERNAME_TEXTBOX = (By.XPATH, '//input[@id="input-0"]')
        LOGIN__PASSWORD_TEXTBOX = (By.XPATH, '//input[@id="input-1"]')
        LOGIN__LOGIN_BUTTON = (By.CSS_SELECTOR, "button.slds-button.modalButton")
        LOGIN__ERROR_MESSAGE_TEXT = (By.CSS_SELECTOR, "p.error")

        SWITCH_ACCOUNT_BUTTON = (
            By.CSS_SELECTOR,
            "div.switchButtons button.switchAccountButton",
        )
        ACCOUNT_ROW = (
            By.XPATH,
            "//div[contains(@class, 'desktopSAView')]//table/tbody/tr",
        )
        GO_TO_MY_ACCOUNT = (By.CSS_SELECTOR, "a.ctaBtnOne")
        ACCOUNT_NUMBER = (By.CSS_SELECTOR, "a.slds-card__header-link")
        BILLING_AND_PAYMENTS = (By.XPATH, "//a[@id='bp__item']")
        BILLING_AND_PAYMENTS_ACTIVE = "div.cCDI_BillHistory.cCDI_BillingAndPaymentTab"

        INVOICE__TABLE_ROWS = (
            By.CSS_SELECTOR,
            "div.cCDI_BillHistory table.slds-table tbody tr",
        )
        INVOICE_PDF = (By.CSS_SELECTOR, "td a[href*='ShowPDF']")
        INVOICE_TOTAL_AMOUNT = (
            By.CSS_SELECTOR,
            "td p.paymentValue lightning-formatted-number",
        )
        POPUP = (
            By.CSS_SELECTOR,
            "section.cCDI_UpdateAddressModal lightning-primitive-icon, "
            "div.cCDI_EbillSignupInterceptModal lightning-primitive-icon",
        )
        UPDATE_ADDRESS_MODAL_POPUP = (
            By.CSS_SELECTOR,
            "section.cCDI_UpdateAddressModal lightning-primitive-icon",
        )
        EBILL_SIGNUP_INTERCEPT_MODAL_POPUP = (
            By.CSS_SELECTOR,
            "div.cCDI_EbillSignupInterceptModal lightning-primitive-icon",
        )

        ACCOUNT_ROW_BY_DATA_KEY_VALUE = (
            "//div[contains(@class, 'desktopSAView')]//table/tbody/"
            "tr[@data-row-key-value='{}']/td/lightning-primitive-cell-checkbox"
        )
        LOADER = ".slds-spinner_container, div[class='siteforceSpinnerManager siteforcePanelsContainer']"
        DASHBOARD = "article.cCDI_Dashboard div.mobileRowContent"

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

    _submit_login_info__post = NavigateToUrl(url=_LAST_ACTIVE_ACCOUNT_URL)

    def get_popups(self):
        popup_elements = []
        popup_selectors = [
            self.Selectors.UPDATE_ADDRESS_MODAL_POPUP,
            self.Selectors.EBILL_SIGNUP_INTERCEPT_MODAL_POPUP,
        ]

        for selector in popup_selectors:
            try:
                popup = self.driver.find_element(*selector)
                popup_elements.append(popup)
            except NoSuchElementException:
                continue
        return popup_elements

    def close_ebill_intercept_modal(self):
        exception_raised = False
        try:
            popups = self.get_popups()
            for _ in range(2):
                for popup in popups:
                    try:
                        popup.click()
                        LOGGER.info("Popup found and closed.")
                    except ElementClickInterceptedException as eci_excep:
                        exception_raised = True
                        LOGGER.info(eci_excep)
                        continue

                if exception_raised:
                    continue
                break

        except (NoSuchElementException, StaleElementReferenceException):
            LOGGER.info("Popup not found.")

    def click_switch_account(self):
        for _ in range(3):
            try:
                switch_account_button = self.driver.find_element(
                    *self.Selectors.SWITCH_ACCOUNT_BUTTON
                )
                switch_account_button.click()
                break
            except ElementClickInterceptedException as excep:
                LOGGER.info(excep)
                self.close_ebill_intercept_modal()
        LOGGER.info("Clicking on switch account...")

        wait_for_loaders(
            self.driver,
            value=self.Selectors.LOADER,
            timeout=10,
        )

    def expand_accounts_window(self):
        for idx in range(3):
            try:
                self.click_switch_account()
                LOGGER.info("Opening accounts window...")

                wait_for_element(
                    self.driver,
                    by_selector=By.XPATH,
                    value=self.Selectors.ACCOUNT_ROW[1],
                    retry_attempts=1,
                    msg="Account Table Row",
                )
                break
            except WebDriverException as excep:
                LOGGER.info(excep)
                if idx == 2:
                    raise

    def switch_account(self, data_row_key_value):
        self.expand_accounts_window()

        account_row = self.driver.find_element(
            By.XPATH,
            self.Selectors.ACCOUNT_ROW_BY_DATA_KEY_VALUE.format(data_row_key_value),
        )

        account_row.click()
        LOGGER.info(f"Selected account: {data_row_key_value}")

    def get_accounts(self):
        self.expand_accounts_window()
        account_elements = self.driver.find_elements(*self.Selectors.ACCOUNT_ROW)
        return account_elements

    def click_billing_and_payments(self):

        for retries in range(5):
            try:
                bill_pay = self.driver.find_element(
                    *self.Selectors.BILLING_AND_PAYMENTS
                )
                execute_script_click(self.driver, bill_pay)
                LOGGER.info("Clicking on Billing and Payments...")

                wait_for_element(
                    self.driver,
                    value=self.Selectors.BILLING_AND_PAYMENTS_ACTIVE,
                    msg="Billing and Payments Active",
                    retry_attempts=1,
                )
                break

            except WebDriverException as excep:
                LOGGER.info(excep)
                LOGGER.info("Billing and Payments not clicked. Checking for popup...")
                self.close_ebill_intercept_modal()
                if retries == 4:
                    raise

    def has_bill_history(self):
        wait_for_element(
            self.driver,
            by_selector=By.CSS_SELECTOR,
            value="div#db article.cCDI_Dashboard div.mobileRowContent.col > span",
            msg="Account Number",
        )

        self.click_billing_and_payments()

        try:
            wait_for_element(
                self.driver,
                value="div.cCDI_BillHistory td lightning-formatted-date-time",
                msg="Invoice Date",
            )
            self.driver.find_element(*self.Selectors.INVOICE_PDF)
            LOGGER.info("Invoices found.")
            return True
        except WebDriverException:
            LOGGER.info("No invoice found.")
            return False

    def has_multiple_accounts(self):
        try:
            WebDriverWait(self.driver, 20).until(
                EC.text_to_be_present_in_element(
                    self.Selectors.SWITCH_ACCOUNT_BUTTON,
                    "SWITCH ACCOUNT",
                )
            )
            LOGGER.info("Found multiple accounts.")
            return True
        except TimeoutException:
            LOGGER.info("Found single account.")
            return False

    def get_customer_number(self):
        cust_num_elem = self.driver.find_element(*self.Selectors.ACCOUNT_NUMBER)
        customer_number = cust_num_elem.text.split(":")[1]
        return customer_number

    def get_invoice_table_rows(self):
        return self.driver.find_elements(*self.Selectors.INVOICE__TABLE_ROWS)

    def _iter_customer_number_selections(self, customer_numbers: Optional[List[str]]):

        if self.has_multiple_accounts():

            account_row_elements = self.get_accounts()

            data_row_key_values = []

            for index, account_row in enumerate(account_row_elements):
                data_row_key_value = account_row.get_attribute("data-row-key-value")
                data_row_key_values.append(data_row_key_value)

            self.click_switch_account()
            LOGGER.info("Closing accounts window...")

            for data_row_key_value in data_row_key_values:
                self.switch_account(data_row_key_value)
                LOGGER.info(
                    f"Navigating to {data_row_key_value} account details page..."
                )

                if not self.has_bill_history():
                    continue

                customer_number = self.get_customer_number()

                yield customer_number, None
        else:
            if self.has_bill_history():
                customer_number = self.get_customer_number()
                yield customer_number, None

    def _iter_invoice_row_elements(self, start_date: date, end_date: date):

        table_rows = self.get_invoice_table_rows()

        for index, _ in enumerate(table_rows):

            close_extra_handles(self.driver)

            row_element = self.get_invoice_table_rows()[index]

            try:
                self.get_pdf_element(row_element)
            except NoSuchElementException:
                LOGGER.info("Pdf element not found")
                continue

            invoice_date = self._extract_invoice_date(row_element)

            if not start_date <= invoice_date <= end_date:
                LOGGER.info(
                    f"Skipping remaining invoices because date '{invoice_date}' is outside requested range"
                )
                break
            yield row_element

    def _construct_downloader(
        self, invoice_row_element, **invoice_fields
    ) -> download.BaseDownloader:

        return EntergyWebElementClickBasedDownloader(
            handle_popup=self.close_ebill_intercept_modal,
            pre_download_action=hover_over_element(self.driver, invoice_row_element),
            element=self.get_pdf_element(invoice_row_element),
            local_filepath=self.download_location,
            rename_to=os.path.join(
                self.download_location, invoice_fields["original_filename"]
            ),
            file_exists_check_kwargs=dict(timeout=20, pattern=r"EBill[a-z]+.pdf$"),
        )

    def _extract_invoice_date(self, invoice_row_element) -> date:
        return date_from_string(
            invoice_row_element.find_element(By.CSS_SELECTOR, "td").text, "%m/%d/%Y"
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
        return self.driver.find_element(*self.Selectors.ACCOUNT_NUMBER).text.split(":")[
            0
        ]

    def _extract_reference_code(self, invoice_row_element, **invoice_fields) -> str:
        customer_number = invoice_fields["customer_number"]
        invoice_date = invoice_fields["invoice_date"]
        total_amount = invoice_fields["total_amount"].replace(",", "").replace(".", "")
        return f"{customer_number}_{invoice_date}_{total_amount}"

    def _extract_original_download_url(
        self, invoice_row_element, **invoice_fields
    ) -> str:
        return self.get_pdf_element(invoice_row_element).get_attribute("href")

    def _extract_original_filename(self, invoice_row_element, **invoice_fields) -> str:
        return f"{invoice_fields['reference_code']}.pdf"

    def get_pdf_element(self, invoice_row_element):
        return invoice_row_element.find_element(*self.Selectors.INVOICE_PDF)


class EntergyWebElementClickBasedDownloader(WebElementClickBasedDownloader):
    def __init__(self, handle_popup, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.handle_popup = handle_popup

    def _perform_download_action(self):
        """Perform the download action"""
        for retries in range(2):
            try:
                self.element.click()
                break
            except ElementClickInterceptedException as excep:
                LOGGER.info(excep)
                self.handle_popup()

                if retries == 1:
                    raise
