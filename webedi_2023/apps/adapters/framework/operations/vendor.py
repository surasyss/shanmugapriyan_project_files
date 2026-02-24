import abc
import os
from datetime import date, timedelta
from typing import Optional, List, Iterable, Tuple

from selenium.webdriver.remote.webelement import WebElement

from apps.adapters import LOGGER
from apps.adapters.base import TEMP_DOWNLOAD_DIR, get_end_invoice_date
from apps.adapters.framework import download
from apps.adapters.framework.context import ExecutionContext
from apps.adapters.framework.operations.interfaces import AbstractVendorConnector
from apps.adapters.framework.steps.primitives import NoOp
from apps.runs.models import Run, DiscoveredFile, FileFormat
from spices import datetime_utils
from spices.documents import DocumentType


# pylint: disable=unused-argument,no-self-use


class HomePageNavigationMixin:
    execution_context: ExecutionContext

    _navigate_to_home_page = NoOp()

    def navigate_to_home_page(self):
        self._navigate_to_home_page(self.execution_context)


class LoginMixin:
    run: Run
    execution_context: ExecutionContext

    _navigate_to_login_page__pre = NoOp()
    _navigate_to_login_page = NoOp()
    _navigate_to_login_page__post = NoOp()

    _submit_login_info__pre = NoOp()
    _submit_login_info = NoOp()
    _submit_login_info__post = NoOp()

    def perform_login(self):
        """Navigate to login page, and submit login information"""
        self._navigate_to_login_page__pre(self.execution_context)
        self._navigate_to_login_page(self.execution_context)
        self._navigate_to_login_page__post(self.execution_context)

        self._submit_login_info__pre(self.execution_context)
        self._submit_login_info(self.execution_context)
        self._submit_login_info__post(self.execution_context)


class SkipFile(Exception):
    pass


class InvoiceDownloadMixinBase:
    run: Run
    execution_context: ExecutionContext

    def __init__(self, *args, **kwargs):
        """we want to run some init-time validation to make sure implementers aren't missing some things"""
        super().__init__(*args, **kwargs)
        self._run_init_validations()

    def download_invoices(self):
        return self._download_invoices()

    invoice_document_type = DocumentType.INVOICE.ident  # pylint: disable=no-member
    invoice_file_format = FileFormat.PDF.ident  # pylint: disable=no-member
    df_download_url_skip_duplicates = False
    vendor_name = None

    _step_navigate_to_invoices_list_page__before_account_selection = NoOp()
    _step_navigate_to_invoices_list_page__after_account_selection = NoOp()

    __FIELDS_ORDER__ = (
        # we exclude invoice_date and customer_number because they are always processed first
        # invoice fields
        "vendor_name",
        "restaurant_name",
        "invoice_number",
        "total_amount",
        # df fields
        "reference_code",
        "original_filename",
        "original_download_url",
    )
    __REQUIRED_FIELDS = frozenset(
        __FIELDS_ORDER__
    )  # save an immutable copy that we can compare against

    def _run_init_validations(self):
        if set(self.__REQUIRED_FIELDS) != set(self.__FIELDS_ORDER__):
            raise Exception(
                "Initialization error: Perhaps you intended to reorder fields extraction and missed one?"
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
                if not start_date <= invoice_date <= end_date:
                    LOGGER.info(
                        f"Skipping invoice because date '{invoice_date}' is outside requested range"
                    )
                    continue

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
                discovered_files.append(discovered_file)

        return discovered_files

    def _get_start_invoice_date(self):
        start_date_str = self.run.request_parameters.get("start_date")
        if not start_date_str:
            return date.today() - timedelta(days=90)

        return datetime_utils.date_from_isoformat(start_date_str)

    def _get_end_invoice_date(self):
        return get_end_invoice_date(self.run)

    # noinspection PyMethodMayBeStatic,PyUnusedLocal
    def _iter_customer_number_selections(self, customer_numbers: Optional[List[str]]):
        """Yield (customer_number text, customer_number element) tuples"""
        yield None, None

    # noinspection PyUnusedLocal
    def _navigate_to_invoices_list_page__after_account_selection(
        self, customer_number: str, customer_number_element: WebElement
    ):
        return self._step_navigate_to_invoices_list_page__after_account_selection(
            self.execution_context
        )

    def _iter_invoice_row_elements(self, start_date, end_date) -> Iterable[WebElement]:
        """Find parent element for each invoice"""
        raise NotImplementedError

    def _iter_invoices(
        self,
        customer_number: str,
        customer_number_element: WebElement,
        start_date: date,
        end_date: date,
    ) -> Iterable[Tuple[dict, download.BaseDownloader]]:
        """Find parent element for each invoice"""
        for invoice_row_element in self._iter_invoice_row_elements(
            start_date, end_date
        ):
            invoice_date = self._extract_invoice_date(invoice_row_element)
            customer_number = self._clean_customer_number(
                self._extract_customer_number(
                    invoice_row_element, customer_number, customer_number_element
                )
            )

            invoice_dict = {
                "invoice_date": invoice_date,
                "customer_number": customer_number,
            }
            for field_name in self.__FIELDS_ORDER__:
                field = getattr(self, f"_extract_{field_name}")(
                    invoice_row_element, **invoice_dict
                )
                field = getattr(self, f"_clean_{field_name}")(field)
                invoice_dict[field_name] = field

            file_downloader = self._construct_downloader(
                invoice_row_element, **invoice_dict
            )

            yield invoice_dict, file_downloader

    def _construct_downloader(
        self, invoice_row_element, **invoice_fields
    ) -> download.BaseDownloader:
        raise NotImplementedError

    def _extract_invoice_date(self, invoice_row_element) -> date:
        raise NotImplementedError

    # noinspection PyMethodMayBeStatic,PyUnusedLocal
    def _extract_customer_number(
        self, invoice_row_element, customer_number, customer_number_element
    ) -> str:
        return customer_number

    def _extract_vendor_name(self, invoice_row_element, **invoice_fields) -> str:
        vendor_name = getattr(self, "vendor_name", None)
        if vendor_name:
            return vendor_name
        raise NotImplementedError

    def _extract_restaurant_name(
        self, invoice_row_element, **invoice_fields
    ) -> Optional[str]:
        return None

    def _extract_invoice_number(self, invoice_row_element, **invoice_fields) -> str:
        raise NotImplementedError

    def _extract_total_amount(self, invoice_row_element, **invoice_fields) -> str:
        raise NotImplementedError

    def _extract_reference_code(self, invoice_row_element, **invoice_fields) -> str:
        raise NotImplementedError

    def _extract_original_download_url(
        self, invoice_row_element, **invoice_fields
    ) -> str:
        raise NotImplementedError

    def _extract_original_filename(self, invoice_row_element, **invoice_fields) -> str:
        raise NotImplementedError

    @staticmethod
    def _clean_invoice_date(invoice_date) -> date:
        return invoice_date

    @staticmethod
    def _clean_customer_number(customer_number) -> str:
        return customer_number and customer_number.strip()

    @staticmethod
    def _clean_vendor_name(vendor_name) -> str:
        return vendor_name and vendor_name.strip()

    @staticmethod
    def _clean_restaurant_name(restaurant_name) -> str:
        return restaurant_name and restaurant_name.strip()

    @staticmethod
    def _clean_invoice_number(invoice_number) -> str:
        return invoice_number and invoice_number.strip()

    @staticmethod
    def _clean_total_amount(total_amount) -> str:
        """Ideally, this should parse the string amount and return float"""
        return total_amount

    @staticmethod
    def _clean_reference_code(reference_code) -> str:
        return reference_code.strip()

    @staticmethod
    def _clean_original_download_url(original_download_url) -> str:
        return original_download_url.strip()

    @staticmethod
    def _clean_original_filename(original_filename) -> str:
        return original_filename.strip()


# pylint: enable=unused-argument,no-self-use


# pylint: disable=abstract-method
class BaseVendorConnector(
    ExecutionContext,
    HomePageNavigationMixin,
    LoginMixin,
    InvoiceDownloadMixinBase,
    AbstractVendorConnector,
    abc.ABC,
):
    """
    We inherit from ExecutionContext so we can conveniently pass `self` around instead of ec
    """

    @property
    def execution_context(self):
        """convenience property"""
        return self

    # noinspection PyUnusedLocal
    def login_flow(self, run):  # pylint: disable=unused-argument
        """backward compat"""
        try:
            self.perform_login()
        finally:
            self.driver.quit()

    # noinspection PyUnusedLocal
    def start_documents_download_flow(self, run):  # pylint: disable=unused-argument
        """backward compat"""
        try:
            self.perform_login()
            dfs = self.download_invoices()
            # Commenting these lines since the current logic of partial success needs to be corrected.
            # download_location = f"{TEMP_DOWNLOAD_DIR}/runs/{run.id}"
            # if len(dfs) != len(os.listdir(download_location)):
            #     run.record_partial_success()
            return dfs
        finally:
            self.driver.quit()
