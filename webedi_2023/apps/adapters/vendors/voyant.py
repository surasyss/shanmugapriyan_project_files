import os
from datetime import date

from integrator import LOGGER

from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import Select

from apps.adapters.framework.download import (
    BaseDownloader,
    DriverBasedUrlGetDownloader,
)
from apps.adapters.framework.registry import connectors
from apps.adapters.framework.operations.vendor import BaseVendorConnector
from apps.adapters.framework.steps.web import (
    NavigateToUrl,
    SubmitLoginPassword,
    ExplicitWait,
)
from apps.adapters.helpers.webdriver_helper import (
    select_dropdown_option_by_visible_text,
    get_url,
    wait_for_element,
)
from apps.runs.models import FileFormat
from spices.datetime_utils import date_from_string

_LOGIN_URL = "https://www.myebill.com/index.asp?startvpc"
_STATEMENT_SUMMARY_URL = (
    "https://www.myebill.com/index.asp?page=statement&action=summary"
)
_PDF_BILLS_URL = "https://www.myebill.com/index.asp?page=statement&action=pdf"


@connectors.add("voyant")
class VoyantConnector(BaseVendorConnector):
    vendor_name = "Voyant"
    invoice_file_format = FileFormat.PDF.ident  # pylint: disable=no-member
    df_download_url_skip_duplicates = True

    class Selectors:
        LOGIN__USERNAME_TEXTBOX = (By.CSS_SELECTOR, 'input[id="user"]')
        LOGIN__PASSWORD_TEXTBOX = (By.CSS_SELECTOR, 'input[type="password"]')
        LOGIN__LOGIN_BUTTON = (By.CSS_SELECTOR, 'input[type="submit"]')
        LOGIN__ERROR_MESSAGE_TEXT = (By.CSS_SELECTOR, "td.errorMessage")

        HOME_TABMENU = (By.CSS_SELECTOR, "div.tabmenuon")
        STATEMENT_SUMMARY__SELECT_STATEMENT = (By.CSS_SELECTOR, "select.medium")
        STATEMENT_SUMMARY__ACCOUNT_TEXT = (By.CSS_SELECTOR, "td.sidebar td")
        STATEMENT_SUMMARY__TOTAL_AMOUNT = (
            By.XPATH,
            "//td[contains(text(),'Total Amount Due')]/following-sibling::td",
        )
        STATEMENT_SUMMARY__INVOICE_PDF_LINK = (By.CSS_SELECTOR, "td span a.link")

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
        until=EC.visibility_of_element_located(locator=Selectors.HOME_TABMENU)
    )

    def get_invoice_pdf_links(self, start_date: date, end_date: date):
        get_url(self.driver, _PDF_BILLS_URL)
        wait_for_element(
            self.driver, value="td span a.link", retry_attempts=3, msg="PDF Links"
        )
        pdf_link_elements = self.driver.find_elements(
            *self.Selectors.STATEMENT_SUMMARY__INVOICE_PDF_LINK
        )

        pdf_links = {}

        for link_elem in pdf_link_elements:
            invoice_date = date_from_string(link_elem.text.strip(), "%B %d, %Y")

            if not start_date <= invoice_date <= end_date:
                LOGGER.info(
                    f"Skipping remaining invoice pdf links because date '{invoice_date}' is outside requested range"
                )
                break

            pdf_links[str(invoice_date)] = link_elem.get_attribute("href")

        return pdf_links

    def get_select_statement_dropdown(self):
        return self.driver.find_element(
            *self.Selectors.STATEMENT_SUMMARY__SELECT_STATEMENT
        )

    def _iter_invoice_row_elements(self, start_date: date, end_date: date):

        pdf_links = self.get_invoice_pdf_links(start_date, end_date)
        setattr(self, "pdf_links", pdf_links)

        get_url(self.driver, _STATEMENT_SUMMARY_URL)

        wait_for_element(
            self.driver,
            value="select.medium",
            retry_attempts=3,
            msg="Select Statement Dropdown",
        )

        select_statement = Select(self.get_select_statement_dropdown())

        invoice_date_list = [option.text for option in select_statement.options]

        for invoice_date_str in invoice_date_list:

            invoice_date = date_from_string(invoice_date_str, "%m/%d/%Y")
            setattr(self, "invoice_date", invoice_date)

            if not start_date <= invoice_date <= end_date:
                LOGGER.info(
                    f"Skipping remaining invoices because date '{invoice_date}' is outside requested range"
                )
                break

            select_dropdown_option_by_visible_text(
                self.get_select_statement_dropdown(), invoice_date_str
            )

            yield None

    def _construct_downloader(
        self, invoice_row_element, **invoice_fields
    ) -> BaseDownloader:
        original_file_name = (
            f"{invoice_fields['invoice_date'].strftime('%Y.%m.%d')}"
            f" - 0{invoice_fields['customer_number']}.PDF"
        )
        return DriverBasedUrlGetDownloader(
            driver=self.driver,
            download_url=invoice_fields["original_download_url"],
            local_filepath=os.path.join(self.download_location, original_file_name),
            rename_to=os.path.join(
                self.download_location, invoice_fields["original_filename"]
            ),
            file_exists_check_kwargs=dict(timeout=20),
        )

    def _extract_invoice_date(self, invoice_row_element) -> date:
        return getattr(self, "invoice_date")

    def _extract_customer_number(
        self, invoice_row_element, customer_number, customer_number_element
    ) -> str:
        account_text = self.driver.find_element(
            *self.Selectors.STATEMENT_SUMMARY__ACCOUNT_TEXT
        ).text
        return account_text.split()[1].strip("#")

    def _extract_invoice_number(self, invoice_row_element, **invoice_fields) -> str:
        return f"{invoice_fields['customer_number']}_{getattr(self, 'invoice_date').strftime('%y%m%d')}"

    def _extract_total_amount(self, invoice_row_element, **invoice_fields) -> str:
        total_amount = self.driver.find_element(
            *self.Selectors.STATEMENT_SUMMARY__TOTAL_AMOUNT
        )
        return total_amount.text

    def _extract_vendor_name(self, invoice_row_element, **invoice_fields) -> str:
        return self.vendor_name

    def _extract_restaurant_name(self, invoice_row_element, **invoice_fields) -> str:
        account_text = self.driver.find_element(
            *self.Selectors.STATEMENT_SUMMARY__ACCOUNT_TEXT
        ).text
        return account_text.split(maxsplit=2)[-1]

    def _extract_reference_code(self, invoice_row_element, **invoice_fields) -> str:
        customer_number = invoice_fields["customer_number"]
        invoice_number = invoice_fields["invoice_number"]
        return f"{customer_number}_{invoice_number}"

    def _extract_original_download_url(
        self, invoice_row_element, **invoice_fields
    ) -> str:
        return getattr(self, "pdf_links").get(str(invoice_fields["invoice_date"]))

    def _extract_original_filename(self, invoice_row_element, **invoice_fields) -> str:
        return f"{invoice_fields['reference_code']}.pdf"
