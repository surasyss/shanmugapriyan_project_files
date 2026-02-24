import os
from datetime import date
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
    has_invoices,
    close_extra_handles,
)
from apps.adapters.framework import download
from apps.runs.models import FileFormat
from spices.datetime_utils import date_from_string

_LOGIN_URL = "https://secured.crrwasteservices.com/webpak2sw/signin.jsp"


@connectors.add("cr_r")
class CrAndRConnector(BaseVendorConnector):
    vendor_name = "	CR&R"
    invoice_file_format = FileFormat.PDF.ident  # pylint: disable=no-member
    df_download_url_skip_duplicates = True

    class Selectors:

        LOGIN__USERNAME_TEXTBOX = (By.CSS_SELECTOR, "#txtSigninEmail")
        LOGIN__PASSWORD_TEXTBOX = (By.CSS_SELECTOR, "#txtPassword")
        LOGIN__LOGIN_BUTTON = (By.CSS_SELECTOR, "#btnSignin")
        LOGIN__ERROR_MESSAGE_TEXT = (By.CSS_SELECTOR, "#msgSignin p")

        HOME__ACCOUNT_NAME = (
            By.CSS_SELECTOR,
            "#ui-accordion-billingAccordion-header-0",
        )

        INVOICE__TABLE_ROW = (By.CSS_SELECTOR, "#tblDetail0 tbody tr")
        INVOICE__PDF_ICON = (By.CSS_SELECTOR, "td a")
        INVOICE__SINGLE_ROW = (By.CSS_SELECTOR, "#DG1 tbody tr:nth-child(2)")
        INVOICE__PDF_BUTTON = (By.CSS_SELECTOR, 'input[value="View/Print"]')
        INVOICE__DATE = (By.CSS_SELECTOR, "td:nth-child(2)")
        INVOICE__NUMBER = (By.CSS_SELECTOR, "td:nth-child(3)")
        INVOICE_TOTAL_AMOUNT = (By.CSS_SELECTOR, "td:nth-child(3)")
        CUSTOMER__NAME = (By.CSS_SELECTOR, "td:nth-child(7)")
        ACCOUNT__NUMBER = (By.CSS_SELECTOR, "td:nth-child(9)")

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
        until=EC.visibility_of_element_located(locator=Selectors.HOME__ACCOUNT_NAME)
    )

    def _iter_invoice_row_elements(self, start_date: date, end_date: date):

        table_rows = self.driver.find_elements(*self.Selectors.INVOICE__TABLE_ROW)
        for index, row in enumerate(table_rows):

            if index > 0:
                close_extra_handles(self.driver)

            row.find_element(*self.Selectors.INVOICE__PDF_ICON).click()

            # move to next window
            self.driver.switch_to.window(self.driver.window_handles[1])

            if not has_invoices(
                self.driver,
                value=self.Selectors.INVOICE__SINGLE_ROW[1],
                retry_attempts=3,
            ):
                continue

            invoice_row_element = self.driver.find_element(
                *self.Selectors.INVOICE__SINGLE_ROW
            )

            invoice_date = self._extract_invoice_date(invoice_row_element)
            if not start_date <= invoice_date <= end_date:
                LOGGER.info(
                    f"Skipping remaining invoices because date '{invoice_date}' is outside requested range."
                )
                break

            yield invoice_row_element

    def _construct_downloader(
        self, invoice_row_element, **invoice_fields
    ) -> download.BaseDownloader:

        _download_patter = self.driver.current_url.split("=")[-1]
        _download_patter = (
            invoice_fields["customer_number"] + "-INVOICE-" + _download_patter + ".pdf"
        )
        return download.WebElementClickBasedDownloader(
            element=invoice_row_element.find_element(
                *self.Selectors.INVOICE__PDF_BUTTON
            ),
            local_filepath=os.path.join(self.download_location, _download_patter),
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
        return invoice_row_element.find_element(*self.Selectors.ACCOUNT__NUMBER).text

    def _extract_invoice_number(self, invoice_row_element, **invoice_fields) -> str:
        return invoice_row_element.find_element(*self.Selectors.INVOICE__NUMBER).text

    def _extract_total_amount(self, invoice_row_element, **invoice_fields) -> str:
        return invoice_row_element.find_element(
            *self.Selectors.INVOICE_TOTAL_AMOUNT
        ).text

    def _extract_vendor_name(self, invoice_row_element, **invoice_fields) -> str:
        return self.vendor_name

    def _extract_restaurant_name(self, invoice_row_element, **invoice_fields) -> str:
        return invoice_row_element.find_element(*self.Selectors.CUSTOMER__NAME).text

    def _extract_reference_code(self, invoice_row_element, **invoice_fields) -> str:
        return f"{invoice_fields['customer_number'].replace(' ', '')}_{invoice_fields['invoice_number']}"

    def _extract_original_download_url(
        self, invoice_row_element, **invoice_fields
    ) -> str:
        return invoice_fields["reference_code"]

    def _extract_original_filename(self, invoice_row_element, **invoice_fields) -> str:
        return f"{invoice_fields['reference_code']}.pdf"
