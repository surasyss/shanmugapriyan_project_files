import os

from datetime import date
from integrator import LOGGER

from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.remote.webelement import WebElement

from apps.adapters.framework import download
from apps.adapters.framework.context import ExecutionContext
from apps.adapters.framework.registry import connectors
from apps.adapters.framework.steps.primitives import SequentialSteps
from apps.adapters.framework.operations.vendor import BaseVendorConnector
from apps.adapters.framework.steps.web import (
    NavigateToUrl,
    SubmitLoginPassword,
    ExplicitWait,
    ClickElement,
    handle_login_errors,
)
from apps.adapters.helpers.webdriver_helper import (
    explicit_wait_till_visibility,
    get_url,
    select_dropdown_option,
    handle_popup,
    has_invoices,
    explicit_wait_till_url_contains,
    wait_for_loaders,
)
from apps.runs.models import FileFormat
from spices.datetime_utils import date_from_string

_LOGIN_URL = "https://shop.sgproof.com/sgws/en/usd/"


class HandleModalBox:
    """Handle select location modal box"""

    MODAL_LOCATION_DROPDOWN = (
        By.CSS_SELECTOR,
        "div.modal-dialog form select#stateSelect",
    )
    MODAL_YES_BUTTON = (
        By.CSS_SELECTOR,
        'button[data-click-component="AgeGateModalYesButton"]',
    )
    GOT_IT_BUTTON = "//button[contains(text(), 'Got It')]"

    def __call__(self, execution_context: ExecutionContext):
        elem = execution_context.driver.find_element(
            *HandleModalBox.MODAL_LOCATION_DROPDOWN
        )
        select_dropdown_option(elem, index=1)
        execution_context.driver.find_element(*HandleModalBox.MODAL_YES_BUTTON).click()
        handle_popup(
            execution_context.driver,
            by_selector=By.XPATH,
            value=HandleModalBox.GOT_IT_BUTTON,
            retry_attempts=1,
        )


class WaitForLoaders:
    def __call__(self, execution_context: ExecutionContext):
        wait_for_loaders(
            execution_context.driver,
            value="div[class='loading-overlay'][style$='display: block;']",
            retry_attempts=2,
        )


class HandleUpdatePasswordPopup:
    def __call__(self, execution_context: ExecutionContext):
        if execution_context.driver.find_elements(
            By.CSS_SELECTOR, "div[id='gigya-password-change-required-screen']"
        ):
            handle_login_errors("Update Password", execution_context.job.username)


@connectors.add("southern_glazers_of_ca_south")
class SouthernGlazersOfCASouthConnector(BaseVendorConnector):
    vendor_name = "Southern Glazer's Of CA South"
    invoice_file_format = FileFormat.PDF.ident  # pylint: disable=no-member
    df_download_url_skip_duplicates = True

    class Selectors:
        HOME__LOGIN_BUTTON = (
            By.CSS_SELECTOR,
            'div.account-guest-actions a[data-click-value="Log In"]',
        )

        LOGIN__USERNAME_TEXTBOX = (
            By.CSS_SELECTOR,
            'form#gigya-login-form input[class="gigya-input-text"]',
        )
        LOGIN__PASSWORD_TEXTBOX = (
            By.CSS_SELECTOR,
            'form#gigya-login-form input[class="gigya-input-password"]',
        )
        LOGIN__LOGIN_BUTTON = (
            By.CSS_SELECTOR,
            'input[class="gigya-input-submit"][value="Log In"]',
        )
        LOGIN__ERROR_MESSAGE_TEXT = (By.CSS_SELECTOR, "div.gigya-error-msg-active")
        HOME__USER_INFO = (By.CSS_SELECTOR, "div.nav-user-info")

        INVOICES_LIST__TABLE_ROWS = (
            By.CSS_SELECTOR,
            "table.invoice-data-table tbody tr.invoice-list-row",
        )
        INVOICES_LIST__INVOICE_DATE = (By.CSS_SELECTOR, "td div.invoice-table-value")
        INVOICES_LIST__INVOICE_LINK = (By.CSS_SELECTOR, "td a.invoice-table-value")
        INVOICES_LIST__NEXT_PAGE_DISABLED = (
            By.CSS_SELECTOR,
            "li.pagination-btn a.pagination-next.pagination-disabled",
        )
        INVOICES_LIST__NEXT_PAGE = (
            By.CSS_SELECTOR,
            "li.pagination-btn a.pagination-next",
        )

        INVOICE_DETAIL__ACCOUNT_NUMBER = (
            By.CSS_SELECTOR,
            "p.location-select-accountnumber",
        )
        INVOICE_DETAIL__RESTAURANT_NAME = (By.CSS_SELECTOR, "p.location-select-name")
        INVOICE_DETAIL__INVOICE_NUMBER = (
            By.CSS_SELECTOR,
            "div.invoice-card .document-details-summary-invoice-header span",
        )
        INVOICE_DETAIL__INVOICE_DATE = (
            By.CSS_SELECTOR,
            "div.invoice-card p.invoice-card-title + p",
        )
        INVOICE_DETAIL__VIEW_PDF = (By.CSS_SELECTOR, "a.order-invoice-pdf")
        ATTENTION_POPUP = "//button[contains(text(), 'Close')]"
        MAINTENANCE_ANNOUNCEMENT_POPUP = (
            "div.walkme-to-remove button svg.wm-ignore-css-reset"
        )

    _navigate_to_login_page = NavigateToUrl(_LOGIN_URL, retry_attempts=5)

    _navigate_to_login_page__post = SequentialSteps(
        [
            ExplicitWait(
                until=EC.visibility_of_element_located(
                    locator=Selectors.HOME__LOGIN_BUTTON
                )
            ),
            HandleModalBox(),
            ExplicitWait(
                until=EC.element_to_be_clickable(locator=Selectors.HOME__LOGIN_BUTTON)
            ),
            ClickElement(Selectors.HOME__LOGIN_BUTTON),
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
            HandleUpdatePasswordPopup(),
            WaitForLoaders(),
            ExplicitWait(
                until=EC.visibility_of_element_located(
                    locator=Selectors.HOME__USER_INFO
                )
            ),
        ]
    )

    def select_custom_date_range(self, start_date):
        """Select invoice date range to list out recent invoices."""
        from_date_element = self.driver.find_element(
            By.CSS_SELECTOR, "input.invoice-from-date-range"
        )
        self.driver.execute_script(
            "arguments[0].removeAttribute('readonly');", from_date_element
        )
        from_date_element.clear()

        start_date_str = start_date.strftime("%m/%d/%Y")
        self.set_attribute(from_date_element, "value", start_date_str)
        LOGGER.info(f"Entering start date {start_date_str}")

        wait_for_loaders(
            self.driver,
            value="div[class='loading-overlay'][style$='display: block;']",
        )

        to_date_element = self.driver.find_element(
            By.CSS_SELECTOR, "input.invoice-to-date-range"
        )
        self.driver.execute_script(
            "arguments[0].removeAttribute('readonly');", to_date_element
        )
        to_date_element.clear()

        end_date_str = date.today().strftime("%m/%d/%Y")
        self.set_attribute(to_date_element, "value", end_date_str)
        LOGGER.info(f"Entering end date {end_date_str}")

        wait_for_loaders(
            self.driver,
            value="div[class='loading-overlay'][style$='display: block;'], div#walkme-overlay-all",
        )

        search_button = self.driver.find_element(
            By.CSS_SELECTOR, "a.invoice-search-btn"
        )
        self.set_attribute(
            search_button,
            "class",
            "button button-secondary invoice-search-btn invoice-apply-btn",
        )
        search_button.click()

    def set_attribute(self, element: WebElement, att_name: str, att_value: str):
        self.driver.execute_script(
            "arguments[0].setAttribute(arguments[1], arguments[2]);",
            element,
            att_name,
            att_value,
        )

    def get_invoice_links(self, start_date: date, end_date: date):

        get_url(self.driver, "https://shop.sgproof.com/sgws/en/usd/Invoices")
        wait_for_loaders(
            self.driver,
            value="div#walkme-overlay-all",
        )

        handle_popup(
            self.driver,
            value=self.Selectors.MAINTENANCE_ANNOUNCEMENT_POPUP,
            msg="Maintenance Announcement",
            retry_attempts=1,
        )

        handle_popup(
            self.driver,
            by_selector=By.XPATH,
            value=self.Selectors.ATTENTION_POPUP,
            msg="Attention Wine Enthusiasts",
            retry_attempts=1,
        )

        invoices_data = []
        while True:
            self.select_custom_date_range(start_date)

            handle_popup(
                self.driver,
                by_selector=By.XPATH,
                value=self.Selectors.ATTENTION_POPUP,
                msg="Attention Wine Enthusiasts",
                retry_attempts=1,
            )

            if not has_invoices(
                self.driver,
                value=self.Selectors.INVOICES_LIST__TABLE_ROWS[1],
                msg="Invoice Table Row",
                retry_attempts=3,
            ):
                break

            table_rows = self.driver.find_elements(
                *self.Selectors.INVOICES_LIST__TABLE_ROWS
            )
            for row in table_rows:
                invoice_date = row.find_element(
                    *self.Selectors.INVOICES_LIST__INVOICE_DATE
                ).text
                invoice_date = date_from_string(invoice_date, "%m/%d/%Y")
                invoice_link = row.find_element(
                    *self.Selectors.INVOICES_LIST__INVOICE_LINK
                ).get_attribute("href")

                if not start_date <= invoice_date <= end_date:
                    LOGGER.info(
                        f"Skipping remaining invoices because date '{invoice_date}' is outside requested range"
                    )
                    return invoices_data

                invoices_data.append((invoice_date, invoice_link))

            if self.driver.find_elements(
                *self.Selectors.INVOICES_LIST__NEXT_PAGE_DISABLED
            ):
                break
            self.driver.find_element(*self.Selectors.INVOICES_LIST__NEXT_PAGE).click()
            explicit_wait_till_url_contains(self.driver, "&page=")
            LOGGER.info("Navigating to the next page...")

        return invoices_data

    def _iter_invoice_row_elements(self, start_date: date, end_date: date):
        invoices_data = self.get_invoice_links(start_date, end_date)
        for inv_data in invoices_data:
            get_url(self.driver, inv_data[1])
            explicit_wait_till_visibility(
                self.driver,
                self.driver.find_element(
                    *self.Selectors.INVOICE_DETAIL__ACCOUNT_NUMBER
                ),
                timeout=10,
                msg="Account Number",
            )

            if not has_invoices(
                self.driver,
                value=self.Selectors.INVOICE_DETAIL__INVOICE_NUMBER[1],
                msg="Invoice Number",
            ):
                continue
            yield inv_data

    def remove_date_printed_element(self):
        """
        Removing Date printed web-element from the html since it changes everytime we download it
        & generate different content-hash resulting in duplicate invoices
        """
        self.driver.execute_script(
            """
            var elements = document.querySelectorAll("div#invoice-print-header div");
            for (const element of elements) {
                if (element.innerText.includes("Printed on"))
                    element.parentNode.removeChild(element);
            }
        """
        )

    def _construct_downloader(
        self, invoice_row_element, **invoice_fields
    ) -> download.BaseDownloader:
        if invoice_fields["original_download_url"] == invoice_fields["reference_code"]:
            self.remove_date_printed_element()
            return download.DriverExecuteCDPCmdBasedDownloader(
                self.driver,
                cmd="Page.printToPDF",
                cmd_args={"printBackground": True},
                local_filepath=os.path.join(
                    self.download_location, f"{invoice_fields['original_filename']}"
                ),
                file_exists_check_kwargs=dict(timeout=20),
            )
        return download.DriverBasedUrlGetDownloader(
            self.driver,
            download_url=invoice_fields["original_download_url"],
            local_filepath=os.path.join(
                self.download_location,
                f"Invoice_{invoice_fields['invoice_number']}.pdf",
            ),
            rename_to=os.path.join(
                self.download_location, invoice_fields["original_filename"]
            ),
            file_exists_check_kwargs=dict(timeout=20),
        )

    def _extract_invoice_date(self, invoice_row_element) -> date:
        return invoice_row_element[0]

    def _extract_customer_number(
        self, invoice_row_element, customer_number, customer_number_element
    ) -> str:
        if customer_number:
            return self.driver.find_element(
                *self.Selectors.INVOICE_DETAIL__ACCOUNT_NUMBER
            ).text.replace("ACCOUNT:", "")
        return None

    def _extract_invoice_number(self, invoice_row_element, **invoice_fields) -> str:
        return self.driver.find_element(
            *self.Selectors.INVOICE_DETAIL__INVOICE_NUMBER
        ).text

    def _extract_total_amount(self, invoice_row_element, **invoice_fields) -> str:
        return None

    def _extract_vendor_name(self, invoice_row_element, **invoice_fields) -> str:
        return self.vendor_name

    def _extract_restaurant_name(self, invoice_row_element, **invoice_fields) -> str:
        return self.driver.find_element(
            *self.Selectors.INVOICE_DETAIL__RESTAURANT_NAME
        ).text

    def _extract_reference_code(self, invoice_row_element, **invoice_fields) -> str:
        invoice_number = invoice_fields["invoice_number"]
        invoice_date = invoice_fields["invoice_date"]
        return f"{invoice_number}_{invoice_date}"

    def _extract_original_download_url(
        self, invoice_row_element, **invoice_fields
    ) -> str:
        original_download_url = self.driver.find_elements(
            *self.Selectors.INVOICE_DETAIL__VIEW_PDF
        )
        if original_download_url:
            return original_download_url[0].get_attribute("href")
        return invoice_fields["reference_code"]

    def _extract_original_filename(self, invoice_row_element, **invoice_fields) -> str:
        return f"{invoice_fields['reference_code']}.pdf"
