import functools
import os
import time
from datetime import date
from typing import List, Optional

from selenium.common.exceptions import StaleElementReferenceException
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
)
from apps.adapters.helpers.helper import sleep
from apps.adapters.helpers.webdriver_helper import (
    get_url,
    execute_script_click,
    scroll_down_to_element,
    wait_for_loaders,
    has_invoices,
)
from apps.runs.models import FileFormat, DiscoveredFile
from spices.datetime_utils import date_from_string

_LOGIN_URL = "https://ebilling.dawnfoods.com/"
_OPEN_REVIEW_INV = [
    "https://ebilling.dawnfoods.com/customerportal/PayInvoice",
    "https://ebilling.dawnfoods.com/customerportal/PayInvoice/ClosedInvoices",
]


def do_if_element_stale(func):
    @functools.wraps(func)
    def func_wrapper(*args, **kwargs):
        context, invoice_row_element, *args = args

        try:
            result = func(context, invoice_row_element, *args, **kwargs)
        except StaleElementReferenceException as excep:
            setattr(context, "is_row_stale", True)
            LOGGER.warning(f"{excep} found in {context.driver.current_url}")
            get_url(context.driver, getattr(context, "invoice_page_url"))
            context.sort_invoice_date_by_desc()

            wait_for_loaders(
                context.driver, value="div.k-loading-mask", retry_attempts=1
            )
            sleep(2)

            invoice_row_element = context.driver.find_elements(
                *context.Selectors.BILLING_HISTORY__TABLE_ROWS
            )[getattr(context, "row_count")]
            result = func(context, invoice_row_element, *args, **kwargs)
        return result

    return func_wrapper


@connectors.add("dawn_food")
class DawnConnector(BaseVendorConnector):
    vendor_name = "dawn foods"
    invoice_file_format = FileFormat.PDF.ident  # pylint: disable=no-member
    df_download_url_skip_duplicates = True
    _table_type_flag = None

    class Selectors:

        LOGIN__USERNAME_TEXTBOX = (By.CSS_SELECTOR, 'input[name="UserName"]')
        LOGIN__PASSWORD_TEXTBOX = (By.CSS_SELECTOR, 'input[name="Password"]')
        LOGIN__LOGIN_BUTTON = (By.CSS_SELECTOR, 'button[name="submit"]')
        LOGIN__ERROR_MESSAGE_TEXT = (By.CSS_SELECTOR, "div.validation-summary-errors")

        # table row elements
        BILLING_HISTORY__TABLE_ROWS = (By.CSS_SELECTOR, "table.k-selectable>tbody>tr")

        # after select the row
        WAIT_FOR_TAB_ELEMENT = (
            By.CSS_SELECTOR,
            'ul[id="menu"]',
        )
        DATE_FILTER_CLICK = (
            By.CSS_SELECTOR,
            'th[data-title="Invoice Date"] .k-link',
        )

    # login
    _navigate_to_login_page = NavigateToUrl(_LOGIN_URL, retry_attempts=5)

    # _navigate_to_login_page =
    _submit_login_info__pre = SequentialSteps(
        [
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

    _step_navigate_to_invoices_list_page__before_account_selection = SequentialSteps(
        [
            ExplicitWait(
                until=EC.visibility_of_element_located(
                    locator=Selectors.WAIT_FOR_TAB_ELEMENT
                )
            )
        ]
    )

    _step_navigate_to_invoices_list_page__after_account_selection = SequentialSteps(
        [
            ExplicitWait(
                until=EC.visibility_of_element_located(
                    locator=Selectors.DATE_FILTER_CLICK
                )
            )
        ]
    )

    def _iter_customer_number_selections(self, customer_numbers: Optional[List[str]]):
        # switching review and open invoices
        for switch_row in _OPEN_REVIEW_INV:
            setattr(self, "invoice_page_url", switch_row)
            get_url(self.driver, switch_row)
            sleep(2)
            if has_invoices(
                self.driver,
                value=self.Selectors.BILLING_HISTORY__TABLE_ROWS[1],
                msg="Invoice table row",
            ):
                yield None, None

    def sort_invoice_date_by_desc(self):
        for _ in range(2):
            execute_script_click(
                self.driver,
                self.driver.find_element_by_css_selector(
                    self.Selectors.DATE_FILTER_CLICK[1]
                ),
            )
            sleep(2)

    def _iter_invoice_row_elements(self, start_date: date, end_date: date):

        # change table to descending order
        self.sort_invoice_date_by_desc()

        for row_count, _ in enumerate(
            self.driver.find_elements(*self.Selectors.BILLING_HISTORY__TABLE_ROWS),
            start=0,
        ):
            setattr(self, "row_count", row_count)

            if getattr(self, "is_row_stale", False):
                get_url(self.driver, getattr(self, "invoice_page_url"))
                setattr(self, "is_row_stale", False)

            if row_count > 0:
                self.scroll_down_min(row_count)
                time.sleep(2)
                if self._table_type_flag == 2:
                    LOGGER.info("Open invoice checkbox unselected")
                    execute_script_click(
                        self.driver,
                        self.handling_different_row_position(
                            self.driver.find_elements(
                                *self.Selectors.BILLING_HISTORY__TABLE_ROWS
                            )[row_count - 1]
                        )[1],
                    )
                else:
                    LOGGER.info("Review invoice checkbox unselected")
                    execute_script_click(
                        self.driver,
                        self.handling_different_row_position(
                            self.driver.find_elements(
                                *self.Selectors.BILLING_HISTORY__TABLE_ROWS
                            )[row_count - 1]
                        )[0],
                    )

            yield self.driver.find_elements(
                *self.Selectors.BILLING_HISTORY__TABLE_ROWS
            )[row_count]

    def scroll_down_min(self, row_count):
        scroll_down_to_element(
            self.driver,
            self.driver.find_elements(*self.Selectors.BILLING_HISTORY__TABLE_ROWS)[
                row_count
            ],
        )

    @do_if_element_stale
    def _construct_downloader(
        self, invoice_row_element, **invoice_fields
    ) -> download.BaseDownloader:
        if self._table_type_flag == 2:
            LOGGER.info("Open invoice checkbox selected")
            execute_script_click(
                self.driver,
                self.handling_different_row_position(invoice_row_element)[1],
            )
        else:
            LOGGER.info("Review invoice checkbox selected")
            execute_script_click(
                self.driver,
                self.handling_different_row_position(invoice_row_element)[0],
            )

        self.driver.implicitly_wait(20)

        return download.WebElementClickBasedDownloader(
            element=self.driver.find_elements_by_css_selector("#btnPrintInvoice")[0],
            local_filepath=os.path.join(self.download_location, "InvoiceReprint.pdf"),
            rename_to=os.path.join(
                self.download_location, invoice_fields["original_filename"]
            ),
            file_exists_check_kwargs=dict(timeout=30),
        )

    def _download_invoices(self):
        start_date = self._get_start_invoice_date()
        end_date = self._get_end_invoice_date()
        customer_numbers = self.run.request_parameters.get("customer_numbers")

        self._step_navigate_to_invoices_list_page__before_account_selection(
            self.execution_context
        )

        seen_download_urls = set()
        discovered_files = []
        for (
            customer_number,
            customer_number_element,
        ) in self._iter_customer_number_selections(customer_numbers):
            if (
                customer_numbers
                and customer_number
                and (customer_number not in customer_numbers)
            ):
                continue

            self._navigate_to_invoices_list_page__after_account_selection(
                customer_number, customer_number_element
            )

            invoices_iterator = self._iter_invoices(
                customer_number, customer_number_element, start_date, end_date
            )
            for (invoice_dict, file_downloader) in invoices_iterator:
                # we do this check for a second time, because
                invoice_date = invoice_dict["invoice_date"]
                if invoice_date < start_date:
                    LOGGER.info(
                        f"Skipping remaining invoices because date '{invoice_date}' is outside requested range"
                    )
                    break

                original_download_url = invoice_dict["original_download_url"]
                if self.df_download_url_skip_duplicates and (
                    original_download_url in seen_download_urls
                ):
                    LOGGER.info(
                        f"Skipping file because url '{original_download_url}' was already seen in this run"
                    )
                    continue

                seen_download_urls.add(original_download_url)

                try:
                    discovered_file = DiscoveredFile.build_unique(
                        self.run,
                        invoice_dict["reference_code"],
                        document_type=self.invoice_document_type,
                        file_format=self.invoice_file_format,
                        original_download_url=invoice_dict["original_download_url"],
                        original_filename=invoice_dict["original_filename"],
                        document_properties={
                            "customer_number": invoice_dict["customer_number"],
                            "invoice_number": invoice_dict["invoice_number"],
                            "total_amount": invoice_dict["total_amount"],
                            "invoice_date": invoice_dict["invoice_date"].isoformat(),
                            "restaurant_name": invoice_dict["restaurant_name"],
                            "vendor_name": invoice_dict["vendor_name"],
                        },
                    )
                except DiscoveredFile.AlreadyExists:
                    LOGGER.info(
                        f'Discovered file already exists with reference code: {invoice_dict["reference_code"]}'
                    )
                    continue

                download.download_discovered_file(discovered_file, file_downloader)

                if discovered_file.original_filename not in os.listdir(
                    self.download_location
                ):
                    LOGGER.info("No downloaded invoice found for this discovered file.")
                    continue

                discovered_files.append(discovered_file)

        return discovered_files

    @do_if_element_stale
    def _extract_invoice_date(self, invoice_row_element) -> date:
        # Assign type flag globally
        self._table_type_flag = len(
            self.handling_different_row_position(invoice_row_element)
        )

        try:
            if self._table_type_flag == 2:
                LOGGER.info("Open invoice page")
                return date_from_string(
                    invoice_row_element.find_elements_by_css_selector(
                        'td[role="gridcell"]'
                    )[8].text,
                    "%m/%d/%Y",
                )
            LOGGER.info("Review invoice page")
            return date_from_string(
                invoice_row_element.find_elements_by_css_selector(
                    'td[role="gridcell"]'
                )[2].text,
                "%m/%d/%Y",
            )
        except ValueError as excep:
            LOGGER.warning(excep)
            return None

    @do_if_element_stale
    def _extract_invoice_number(self, invoice_row_element, **invoice_fields) -> str:
        if self._table_type_flag == 1:
            return invoice_row_element.find_elements_by_css_selector(
                'td[role="gridcell"]'
            )[4].text
        return invoice_row_element.find_elements_by_css_selector('td[role="gridcell"]')[
            6
        ].text

    @do_if_element_stale
    def _extract_total_amount(self, invoice_row_element, **invoice_fields) -> str:
        if self._table_type_flag == 1:
            return invoice_row_element.find_elements_by_css_selector(
                'td[role="gridcell"]'
            )[6].text
        return invoice_row_element.find_elements_by_css_selector('td[role="gridcell"]')[
            3
        ].text

    def _extract_vendor_name(self, invoice_row_element, **invoice_fields) -> str:
        return "Dawn Foods"

    def _extract_reference_code(self, invoice_row_element, **invoice_fields) -> str:
        return f'{invoice_fields["customer_number"]}_{invoice_fields["invoice_date"]}'

    def _extract_original_download_url(
        self, invoice_row_element, **invoice_fields
    ) -> str:
        return invoice_fields["reference_code"]

    def _extract_original_filename(self, invoice_row_element, **invoice_fields) -> str:
        reference_code = self._extract_reference_code(
            invoice_row_element, **invoice_fields
        )
        return f"{reference_code}.pdf"

    @do_if_element_stale
    def _extract_customer_number(
        self, invoice_row_element, customer_number, customer_number_element
    ) -> str:
        cus_num = invoice_row_element.find_elements_by_css_selector(
            'td[role="gridcell"]>div>input[type="checkbox"]'
        )
        return cus_num[0].get_attribute("class").split("||")[3]

    def _extract_restaurant_name(self, invoice_row_element, **invoice_fields) -> str:
        return None

    @staticmethod
    def handling_different_row_position(invoice_row_element):
        return invoice_row_element.find_elements_by_css_selector(
            'td[role="gridcell"]>div>input[type="checkbox"]'
        )
