import os
from datetime import date
from typing import List, Optional
from retry import retry

from apps.adapters.framework.context import ExecutionContext
from apps.adapters.framework.download import WebElementClickBasedDownloader
from apps.adapters.framework.steps.primitives import SequentialSteps
from apps.adapters.helpers.helper import ZeroFileSizeException
from integrator import LOGGER

from selenium.common.exceptions import (
    ElementNotInteractableException,
    WebDriverException,
    ElementClickInterceptedException,
)
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.remote.webelement import WebElement

from apps.adapters.framework.registry import connectors
from apps.adapters.framework.operations.vendor import BaseVendorConnector
from apps.adapters.framework.steps.web import (
    get_url,
    NavigateToUrl,
    SubmitLoginPassword,
    ExplicitWait,
    handle_login_errors,
)
from apps.adapters.helpers.webdriver_helper import (
    wait_for_element,
    WEB_DRIVER_EXCEPTIONS,
    wait_for_loaders,
    explicit_wait_till_clickable,
)
from apps.adapters.framework import download
from apps.runs.models import FileFormat
from spices.datetime_utils import date_from_string

_LOGIN_URL = "https://my.xcelenergy.com/MyAccount/XE_Login?template=XE_MA_Template"
_ACCOUNTS_URL = "https://my.xcelenergy.com/MyAccount/s/profile/billing-accounts-view"
_BILLING_AND_PAYMENT_URL = "https://my.xcelenergy.com/MyAccount/s/billing-and-payment"


class AgreeTermsAndCondition:

    TERMS_AND_CONDITION_FORM = (
        "div#gigya-complete-registration-screen form#gigya-profile-form"
    )
    CHECKBOX = (By.CSS_SELECTOR, "input#gigya-checkbox-subscribe")
    AGREE_BUTTON = (By.CSS_SELECTOR, "input[value='Agree']")

    def __call__(self, execution_context: ExecutionContext):
        try:
            wait_for_element(
                execution_context.driver,
                value=self.TERMS_AND_CONDITION_FORM,
                msg="Accept Terms and Condition",
                retry_attempts=1,
            )
            checkbox = execution_context.driver.find_element(*self.CHECKBOX)
            checkbox.click()

            agree_button = execution_context.driver.find_element(*self.AGREE_BUTTON)
            agree_button.click()
        except WebDriverException as excep:
            LOGGER.info(f"Accept Terms and Condition page not found. {excep}")


class HandleMaintenancePage:
    MAINTENANCE_MESSAGE_TEXT = "div.maintenance-message"

    def __call__(self, execution_context: ExecutionContext):
        try:
            wait_for_element(
                execution_context.driver,
                value=self.MAINTENANCE_MESSAGE_TEXT,
                msg="Maintenance msg",
                retry_attempts=1,
                raise_exception=False,
            )
            error_message_element = (
                execution_context.driver.find_element_by_css_selector(
                    self.MAINTENANCE_MESSAGE_TEXT
                )
            )
            if error_message_element:
                error_text = (
                    error_message_element.text and error_message_element.text.strip()
                )
                handle_login_errors(error_text, execution_context.job.username)
        except WEB_DRIVER_EXCEPTIONS:
            LOGGER.info("No maintenance page found.")


@connectors.add("xcel_energy")
class XcelEnergy(BaseVendorConnector):
    vendor_name = "XCEL ENERGY"
    invoice_file_format = FileFormat.PDF.ident  # pylint: disable=no-member
    df_download_url_skip_duplicates = True

    class Selectors:
        LOGIN__USERNAME_TEXTBOX = (By.CSS_SELECTOR, "input[id^='gigya-loginID']")
        LOGIN__PASSWORD_TEXTBOX = (By.CSS_SELECTOR, "input[id^='gigya-password']")
        LOGIN__LOGIN_BUTTON = (
            By.CSS_SELECTOR,
            "form#gigya-login-form input.gigya-input-submit",
        )
        LOGIN__ERROR_MESSAGE_TEXT = (By.CSS_SELECTOR, "div#error-form-invalid-login")

        TERMS_AND_CONDITION_FORM = (
            By.CSS_SELECTOR,
            "div#gigya-complete-registration-screen form#gigya-profile-form",
        )
        CHECKBOX = (By.CSS_SELECTOR, "input.gigya-input-checkbox")
        AGREE_BUTTON = (By.CSS_SELECTOR, "input[value='Agree']")

        BILLING = (By.XPATH, "//li[@class='nav-item-root']/a[text()='Billing']")

        ACCOUNT_DROPDOWN = (By.XPATH, "//button[starts-with(@id, 'combobox-button')]")
        ACCOUNT_DROPDOWN_LIST = (
            By.XPATH,
            "//div[starts-with(@id,'dropdown-element')]/"
            "lightning-base-combobox-item/span/span[@class='slds-truncate']",
        )

        SEARCH_INPUT = (By.XPATH, "//input[@class='slds-input']")
        GO_BUTTON = (By.XPATH, "//button[@name='Go']")

        INVOICE_TABLE__ROW = (
            By.XPATH,
            "//table[@lightning-datatable_table]/tbody/tr[@class='slds-hint-parent']",
        )
        INVOICE_TABLE__DATE = (By.XPATH, "//th//lightning-formatted-date-time")
        INVOICE_TABLE__DESCRIPTION = (By.XPATH, "//td[@data-label='Description']")
        INVOICE_TABLE__TOTAL_AMOUNT = (By.XPATH, "//td[@data-label='Charges']")
        INVOICE_TABLE__PDF = (
            By.XPATH,
            "//td[@data-label='PDF']//button[@name='pdfLink']",
        )
        SPINNER = "//c-ma-service-addresses-datatable/lightning-spinner[@class='slds-spinner_container']"

    # login
    _navigate_to_login_page = NavigateToUrl(_LOGIN_URL, retry_attempts=5)

    _submit_login_info__pre = SequentialSteps(
        [
            HandleMaintenancePage(),
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

    _submit_login_info__post = SequentialSteps(
        [
            AgreeTermsAndCondition(),
            ExplicitWait(
                until=EC.presence_of_element_located(locator=Selectors.BILLING)
            ),
        ]
    )

    _step_navigate_to_invoices_list_page__before_account_selection = NavigateToUrl(
        _ACCOUNTS_URL, retry_attempts=5
    )
    _step_navigate_to_invoices_list_page__after_account_selection = NavigateToUrl(
        _BILLING_AND_PAYMENT_URL, retry_attempts=5
    )

    @retry(ElementClickInterceptedException, tries=3, delay=1)
    def click_account_dropdown_button(self):
        wait_for_loaders(
            self.driver, by_selector=By.XPATH, value=self.Selectors.SPINNER, timeout=10
        )
        explicit_wait_till_clickable(
            self.driver, self.Selectors.ACCOUNT_DROPDOWN, msg="Accounts Dropdown"
        )
        self.driver.find_element(*self.Selectors.ACCOUNT_DROPDOWN).click()

    def get_dropdown_list_elements(self):
        return self.driver.find_elements(*self.Selectors.ACCOUNT_DROPDOWN_LIST)[1:]

    def _iter_customer_number_selections(self, customer_numbers: Optional[List[str]]):

        self.click_account_dropdown_button()
        acc_dd_list = self.get_dropdown_list_elements()

        if acc_dd_list:
            for index, dd_option in enumerate(acc_dd_list):
                if index > 0:
                    get_url(self.driver, _ACCOUNTS_URL)
                    self.click_account_dropdown_button()

                account_element = self.get_dropdown_list_elements()[index]
                customer_number = account_element.text
                account_element.click()
                LOGGER.info(f"Selected account {customer_number} from the dropdown.")

                yield customer_number, None

        else:
            customer_number = self.driver.find_element(
                By.XPATH, "//button[contains(@id,'combobox-button')]"
            )
            yield customer_number.text, None

    def filter_statements(self):
        self.driver.find_element(*self.Selectors.SEARCH_INPUT).send_keys("Statement")
        LOGGER.info("Filtering statements from the table rows...")

        self.driver.find_element(*self.Selectors.GO_BUTTON).click()

    def _iter_invoice_row_elements(self, start_date: date, end_date: date):

        wait_for_element(
            self.driver,
            by_selector=By.XPATH,
            value=self.Selectors.INVOICE_TABLE__ROW[1],
            msg="Invoice Table Row",
        )
        self.filter_statements()

        table_rows = self.driver.find_elements(*self.Selectors.INVOICE_TABLE__ROW)

        for index, invoice_row_element in enumerate(table_rows):
            setattr(self, "row_index", index)

            invoice_date = self._extract_invoice_date(invoice_row_element)
            if not start_date <= invoice_date <= end_date:
                LOGGER.info(
                    f"Skipping remaining invoices because date '{invoice_date}' is outside requested range"
                )
                break

            try:
                if invoice_row_element.find_elements(
                    *self.Selectors.INVOICE_TABLE__PDF
                )[index]:
                    LOGGER.info(f"Invoice found in row: {index}")
            except IndexError:
                LOGGER.info(f"No invoice found in row: {index}")
                continue

            yield invoice_row_element

    def _construct_downloader(
        self, invoice_row_element, **invoice_fields
    ) -> download.BaseDownloader:
        return XcelWebElementClickBasedDownloader(
            element=invoice_row_element.find_elements(
                *self.Selectors.INVOICE_TABLE__PDF
            )[getattr(self, "row_index")],
            local_filepath=os.path.join(
                self.download_location, invoice_fields["original_filename"]
            ),
            rename_to=os.path.join(
                self.download_location, f'{invoice_fields["reference_code"]}.pdf'
            ),
            file_exists_check_kwargs=dict(timeout=20),
        )

    def _extract_invoice_date(self, invoice_row_element) -> date:
        return date_from_string(
            invoice_row_element.find_elements(*self.Selectors.INVOICE_TABLE__DATE)[
                getattr(self, "row_index")
            ].text,
            "%b %d, %Y",
        )

    def _extract_customer_number(
        self, invoice_row_element, customer_number, customer_number_element
    ) -> str:
        return customer_number if customer_number else None

    def _extract_invoice_number(self, invoice_row_element, **invoice_fields) -> str:
        invoice_number = invoice_row_element.find_elements(
            *self.Selectors.INVOICE_TABLE__DESCRIPTION
        )[getattr(self, "row_index")].text.replace("Statement: ", "")
        return invoice_number

    def _extract_total_amount(self, invoice_row_element, **invoice_fields) -> str:
        return invoice_row_element.find_elements(
            *self.Selectors.INVOICE_TABLE__TOTAL_AMOUNT
        )[getattr(self, "row_index")].text

    def _extract_vendor_name(self, invoice_row_element, **invoice_fields) -> str:
        return self.vendor_name

    def _extract_restaurant_name(self, invoice_row_element, **invoice_fields) -> str:
        return None

    def _extract_reference_code(self, invoice_row_element, **invoice_fields) -> str:
        customer_number = invoice_fields["customer_number"]
        invoice_number = invoice_fields["invoice_number"]
        invoice_date = invoice_fields["invoice_date"]
        return f"{customer_number}_{invoice_number}_{invoice_date}"

    def _extract_original_download_url(
        self, invoice_row_element, **invoice_fields
    ) -> str:
        return invoice_fields["reference_code"]

    def _extract_original_filename(self, invoice_row_element, **invoice_fields) -> str:
        return (
            f"{invoice_fields['invoice_number']}_{invoice_fields['invoice_date']}.pdf"
        )


class XcelWebElementClickBasedDownloader(WebElementClickBasedDownloader):
    def __init__(self, element: WebElement, **kwargs):
        super().__init__(element, **kwargs)
        self.element = element

    def _perform_download_action(self):
        """Perform the download action"""
        try:
            self.element.click()
        except ElementNotInteractableException as excep:
            LOGGER.info(excep)
            raise ZeroFileSizeException
