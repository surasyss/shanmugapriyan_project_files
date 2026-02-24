import os
from datetime import date
from typing import Optional, List

from integrator import LOGGER
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.remote.webelement import WebElement
from selenium.common.exceptions import (
    NoSuchElementException,
    ElementClickInterceptedException,
)

from apps.adapters.framework.context import ExecutionContext
from apps.adapters.framework.download import WebElementClickBasedDownloader
from apps.adapters.framework.registry import connectors
from apps.adapters.framework.steps.primitives import SequentialSteps
from apps.adapters.helpers.helper import (
    sleep,
    extract_zip_file,
    delete_files,
    rename_file,
)
from apps.adapters.framework.operations.vendor import BaseVendorConnector
from apps.adapters.framework.steps.web import (
    NavigateToUrl,
    ExplicitWait,
    SubmitLoginPassword,
)
from apps.adapters.helpers.webdriver_helper import (
    wait_for_element,
    wait_for_loaders,
    hover_over_element,
    close_extra_handles,
    explicit_wait_till_clickable,
    handle_popup,
    get_url,
    scroll_down_to_element,
)
from apps.adapters.helpers.helper import wait_until_file_exists
from apps.adapters.framework import download
from apps.runs.models import FileFormat
from spices.datetime_utils import date_from_string

_LOGIN_URL = "https://pay.sysco.com"
_INVOICE_AND_CREDITS_URL = "https://corasysco.force.com/v2/s/invoice"


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


@connectors.add("sysco")
class SyscoConnector(BaseVendorConnector):
    vendor_name = "Sysco Payments"
    invoice_file_format = FileFormat.PDF.ident  # pylint: disable=no-member
    df_download_url_skip_duplicates = True

    class Selectors:
        LOGIN__USERNAME_TEXTBOX = (By.CSS_SELECTOR, "input#okta-signin-username")
        LOGIN__PASSWORD_TEXTBOX = (By.CSS_SELECTOR, "input#okta-signin-password")
        LOGIN__LOGIN_BUTTON = (By.CSS_SELECTOR, "input#okta-signin-submit")
        LOGIN__ERROR_MESSAGE_TEXT = (
            By.CSS_SELECTOR,
            "div.okta-form-infobox-error p, form[action*='SamlError']",
        )

        NAV_INVOICES = (By.CSS_SELECTOR, "nav.Frenchmenu.cEIPPV2_GenericComponent")
        ALL_INVOICES_OPTION = (
            By.XPATH,
            "//span[contains(@data-filter, 'All')]//button",
        )
        ASCENDING_ORDER_DATE = (By.CSS_SELECTOR, "#Create_Date__c")

        TABLE_ROW = (
            By.CSS_SELECTOR,
            "table.slds-table tbody tr",
        )
        CHECKBOX = (By.CSS_SELECTOR, "td div.ChkBox label, td input.uiInputCheckbox")
        SELECT_DOWNLOAD_OPTION = (
            By.CSS_SELECTOR,
            "td:nth-child(11) div div div ul li:nth-child(1)",
        )
        DOWNLOAD_OPTION = (
            By.CSS_SELECTOR,
            "div.download-active, button.slds-button_icon-container-more",
        )
        TOAST = (By.CSS_SELECTOR, "div.toastContent")
        DOWNLOAD_PDF = (
            By.XPATH,
            "//div[contains(@class, 'buttonWrap')]//button[@title='Download']",
        )
        LOADER = "div.cEIPPV2_Spinner, .slds-spinner_container"
        TERMS_AND_CONDITIONS = "div.TermsConditionBlock div.Footer button"
        CANCEL_DOWNLOAD = "//div[contains(@class, 'cEIPPV2_DownloadInvoice')]//button[@title='Cancel']"

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

    _submit_login_info__post = SequentialSteps(
        [
            HandlePopup(
                value=Selectors.TERMS_AND_CONDITIONS, msg="Agree Terms and Conditions"
            ),
            ExplicitWait(
                until=EC.visibility_of_element_located(locator=Selectors.NAV_INVOICES)
            ),
        ]
    )

    @staticmethod
    def get_nth_child_element(invoice_row_element, nth_value):
        return invoice_row_element.find_element(
            By.CSS_SELECTOR, f"td:nth-child({nth_value})"
        )

    def wait_for_invoice_table_rows(self):
        LOGGER.info("wait for invoice table rows...")
        wait_for_element(
            self.driver,
            value=self.Selectors.TABLE_ROW[1],
            retry_attempts=3,
            msg="Invoice Table Row",
        )

    def uncheck_prev_row(self, prev_row_element):
        close_extra_handles(self.driver)
        handle_popup(
            self.driver,
            by_selector=By.XPATH,
            value=self.Selectors.CANCEL_DOWNLOAD,
            msg="Download Popup",
            retry_attempts=1,
        )

        explicit_wait_till_clickable(
            self.driver,
            self.Selectors.CHECKBOX,
            msg="Checkbox",
            timeout=30,
        )
        wait_for_loaders(self.driver, value=self.Selectors.LOADER)

        prev_row_element.find_element(*self.Selectors.CHECKBOX).click()

    def remove_sticky_footer_element(self):
        try:
            sticky_footer = self.driver.find_element(By.CSS_SELECTOR, "div.pwrdGenpact")
            self.driver.execute_script(
                "var element = arguments[0];"
                "element.parentNode.removeChild(element);",
                sticky_footer,
            )
            LOGGER.info("Removed sticky footer.")
        except NoSuchElementException:
            LOGGER.info("No sticky footer found.")

    def _iter_customer_number_selections(self, customer_numbers: Optional[List[str]]):
        get_url(self.driver, _INVOICE_AND_CREDITS_URL)
        self.wait_for_invoice_table_rows()

        all_invoices = self.driver.find_element_by_xpath(
            self.Selectors.ALL_INVOICES_OPTION[1]
        )
        scroll_down_to_element(self.driver, all_invoices)
        all_invoices.click()
        sleep(2)

        ascending_date = self.driver.find_element(*self.Selectors.ASCENDING_ORDER_DATE)
        ascending_date.click()
        wait_for_loaders(self.driver, value=self.Selectors.LOADER)

        ascending_date.click()
        wait_for_loaders(self.driver, value=self.Selectors.LOADER)
        yield None, None

    def _iter_invoice_row_elements(self, start_date: date, end_date: date):
        prev_row_element = None
        self.wait_for_invoice_table_rows()
        self.remove_sticky_footer_element()

        table_rows = self.driver.find_elements(*self.Selectors.TABLE_ROW)

        if not table_rows:
            LOGGER.info("No invoice found.")

        for index, row_element in enumerate(table_rows):
            setattr(self, "inv_row_idx", index)

            if prev_row_element:
                self.uncheck_prev_row(prev_row_element)

            invoice_date = self._extract_invoice_date(row_element)
            if not start_date <= invoice_date <= end_date:
                LOGGER.info(
                    f"Skipping remaining invoices because date '{invoice_date}' is outside requested range"
                )
                break
            prev_row_element = row_element
            yield row_element

    def pre_download_action(self, invoice_row_element):
        hover_over_element(self.driver, invoice_row_element)

        invoice_row_element.find_element(*self.Selectors.CHECKBOX).click()
        wait_for_loaders(
            self.driver,
            timeout=10,
            value=self.Selectors.LOADER,
            retry_attempts=1,
        )

    def wait_and_extract_zip_file(self):
        LOGGER.info("Checking for zip file...")
        try:
            downloaded_file = wait_until_file_exists(
                file_path=self.download_location,
                timeout=10,
                pattern=r"^Invoice.zip$",
            )
            LOGGER.info("Zip file found")
            extracted_files = extract_zip_file(downloaded_file)
            delete_files(self.download_location, "Invoice.zip")
            actual_path = os.path.join(self.download_location, extracted_files[0])
            rename_to = os.path.join(self.download_location, "Invoice.pdf")
            rename_file(actual_path, rename_to)
        except TimeoutError:
            LOGGER.info("No zip file found")

    def post_download_actions(self):
        try:
            wait_for_loaders(self.driver, value=self.Selectors.LOADER, retry_attempts=1)
            toast = self.driver.find_element(*self.Selectors.TOAST)
            LOGGER.info(toast.text)
            raise TimeoutError
        except NoSuchElementException:
            LOGGER.info("Downloading file...")

        self.wait_and_extract_zip_file()

    def _construct_downloader(
        self, invoice_row_element, **invoice_fields
    ) -> download.BaseDownloader:

        return SyscoWebElementClickDownloader(
            driver=self.driver,
            pre_download_action=self.pre_download_action(invoice_row_element),
            post_download_action=self.post_download_actions,
            element=self.get_pdf_element(),
            local_filepath=os.path.join(self.download_location, "Invoice.pdf"),
            rename_to=os.path.join(
                self.download_location, invoice_fields["original_filename"]
            ),
            file_exists_check_kwargs=dict(timeout=20),
        )

    def _extract_invoice_date(self, invoice_row_element) -> date:
        return date_from_string(
            SyscoConnector.get_nth_child_element(invoice_row_element, 3).text,
            "%m/%d/%y",
        )

    def _extract_customer_number(
        self, invoice_row_element, customer_number, customer_number_element
    ) -> str:
        return SyscoConnector.get_nth_child_element(invoice_row_element, 6).text.split(
            maxsplit=1
        )[0]

    def _extract_invoice_number(self, invoice_row_element, **invoice_fields) -> str:
        return SyscoConnector.get_nth_child_element(invoice_row_element, 2).text

    def _extract_total_amount(self, invoice_row_element, **invoice_fields) -> str:
        return SyscoConnector.get_nth_child_element(invoice_row_element, 8).text

    def _extract_vendor_name(self, invoice_row_element, **invoice_fields) -> str:
        return self.vendor_name

    def _extract_restaurant_name(self, invoice_row_element, **invoice_fields) -> str:
        return SyscoConnector.get_nth_child_element(invoice_row_element, 6).text.split(
            maxsplit=1
        )[1]

    def _extract_reference_code(self, invoice_row_element, **invoice_fields) -> str:
        customer_number = invoice_fields["customer_number"]
        invoice_number = invoice_fields["invoice_number"]
        return f"{customer_number}_{invoice_number}"

    def _extract_original_download_url(
        self, invoice_row_element, **invoice_fields
    ) -> str:
        return invoice_fields["reference_code"]

    def _extract_original_filename(self, invoice_row_element, **invoice_fields) -> str:
        return f"{invoice_fields['reference_code']}.pdf"

    def get_pdf_element(self):
        wait_for_element(
            self.driver,
            value=self.Selectors.DOWNLOAD_OPTION[1],
            retry_attempts=1,
            msg="Select Download Option Dropdown",
        )
        invoice_row_element = self.driver.find_elements(*self.Selectors.TABLE_ROW)[
            getattr(self, "inv_row_idx")
        ]
        download_three_dot = invoice_row_element.find_element(
            *self.Selectors.DOWNLOAD_OPTION
        )
        scroll_down_to_element(self.driver, download_three_dot)
        download_three_dot.click()

        download_elem = invoice_row_element.find_element(
            *self.Selectors.SELECT_DOWNLOAD_OPTION
        )
        download_elem.click()

        explicit_wait_till_clickable(
            self.driver,
            self.Selectors.DOWNLOAD_PDF,
            msg="Download pdf",
            timeout=30,
        )
        return invoice_row_element.find_element(*self.Selectors.DOWNLOAD_PDF)


class SyscoWebElementClickDownloader(WebElementClickBasedDownloader):
    def __init__(self, driver, element: WebElement, **kwargs):
        super().__init__(element, **kwargs)
        self.driver = driver

    def _perform_download_action(self):
        for index in range(3):
            try:
                self.element.click()
                break
            except ElementClickInterceptedException as excep:
                LOGGER.info(excep)
                wait_for_loaders(
                    self.driver,
                    value="div.cEIPPV2_Spinner, .slds-spinner_container",
                    timeout=10,
                )

                if index == 2:
                    raise
