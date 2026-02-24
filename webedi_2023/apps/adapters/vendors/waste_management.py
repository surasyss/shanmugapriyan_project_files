import datetime
import os
import time
import requests

from datetime import date, timedelta
from typing import List

from spices import datetime_utils
from spices.http_utils import make_retryable_session
from spices.services import ContextualError

from apps.adapters.base import VendorDocumentDownloadInterface
from apps.adapters.framework import download
from apps.adapters.vendors import LOGGER
from apps.error_codes import ErrorCode
from apps.runs.models import Run, DiscoveredFile, DocumentType, FileFormat


class WasteManagementClient:
    """Client interface for Waste Management APIs"""

    def __init__(self, api_base_url: str):
        self._base_url = api_base_url.rstrip("/")

        # ok to make everything retryable on 5xx
        self._session = make_retryable_session(
            requests.Session(), backoff_factor=2, raise_on_status=False
        )
        self._headers = {
            "Content-Type": "application/json",
            "Accept": "application/json, text/plain, */*",
            "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/101.0.4951.64 Safari/537.36",
        }

    def get_access_token(self, username: str, password: str):
        """
        Auth API to login into Waste Management
        """
        api_url = "/".join([self._base_url, "user/authenticate"])
        payload = {
            "username": username,
            "password": password,
            "locale": "en_US",
        }
        login_headers = {**self._headers, "apikey": "6277FF29BB19666078AC"}

        response = self._session.post(api_url, json=payload, headers=login_headers)
        if response.ok:
            LOGGER.info(f"Response: {response.text}")
            login_response = response.json()
            response_data = login_response["data"]

            if response_data.get("status") == "LOCKED_OUT":
                raise ContextualError(
                    code=ErrorCode.ACCOUNT_DISABLED_FAILED_WEB.ident,
                    message=ErrorCode.ACCOUNT_DISABLED_FAILED_WEB.message.format(
                        username=username
                    ),
                    params={"error_msg": ""},
                )

            access_token = response_data.get("access_token")
            user_id = login_response["data"]["id"]
            return access_token, user_id

        LOGGER.warning(
            f"[tag:WEWARAC2] Login Failed for user: {username}"
            f"with HTTP {response.status_code} (url={api_url},request_payload={payload},response_body={response.text})"
        )

        if response.status_code >= 500:
            raise ContextualError(
                code=ErrorCode.EXTERNAL_UPSTREAM_UNAVAILABLE.ident,  # pylint: disable=no-member
                message=ErrorCode.EXTERNAL_UPSTREAM_UNAVAILABLE.message,  # pylint: disable=no-member
                params={
                    "request_url": api_url,
                    "username": username,
                    "response_body": response.text,
                },
            )

        # 4XX failure
        raise ContextualError(
            code=ErrorCode.AUTHENTICATION_FAILED_WEB.ident,  # pylint: disable=no-member
            message=ErrorCode.AUTHENTICATION_FAILED_WEB.message.format(  # pylint: disable=no-member
                username=username
            ),
            params={"username": username},
        )

    def get_accounts_list(self, access_token: str, user_id: str):
        """
        Waste Management account details API
        """
        api_url = "/".join(
            [
                self._base_url,
                f"authorize/user/{user_id}/accounts?timestamp={time.time_ns()}&lang=en_US",
            ]
        )
        account_headers = {
            **self._headers,
            "oktatoken": access_token,
            "apikey": "AABFF96D4542575160FC",
        }
        LOGGER.info(f"[tag:WEWARSD1] Fetch account details from url={api_url}")

        response = self._session.get(api_url, headers=account_headers)
        if response.ok:
            LOGGER.info(f"Response: {response.text}")
            account_response = response.json()
            return account_response["data"]["linkedAccounts"]

        raise Exception(
            f"[tag:WEWARSD2] Failed fetching user details data!"
            f"with HTTP {response.status_code} (url={api_url},response_body={response.text})"
        )

    def get_invoices_for_account(
        self, access_token: str, user_id: str, account_number: str, from_date, to_date
    ):
        """
        Waste Management api to fetch invoices list for an account
        """
        api_url = "/".join(
            [
                self._base_url,
                f"account/{account_number}/invoice?lang=en_US&fromDate={from_date}&toDate={to_date}&userId={user_id}",
            ]
        )
        invoice_header = {
            **self._headers,
            "token": access_token,
            "apikey": "615F2EFC82FF8BB2F864",
        }
        LOGGER.info(f"[tag:WEWARSD1] Fetch user details data from url={api_url}")

        response = self._session.get(api_url, headers=invoice_header)
        if response.ok:
            LOGGER.info(f"Response: {response.text}")
            invoices = response.json()["body"].get("invoices")
            return invoices

        raise Exception(
            f"[tag:WEWARSD2] Failed fetching invoices details for account data!"
            f"with HTTP {response.status_code} (url={api_url},response_body={response.text})"
        )


class WasteManagementRunner(VendorDocumentDownloadInterface):
    """Runner Class for Waste Management"""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.access_token = None
        self.user_id = None
        self.api_client = WasteManagementClient("https://rest-api.wm.com")

    def _login(self):
        """
        Login to Waste Management
        :return: Nothing
        """
        self.access_token, self.user_id = self.api_client.get_access_token(
            self.run.job.username, self.run.job.password
        )

    def get_invoices_list(self, account_number: str):
        """
        Fetch Invoice Detail for an account
        :param account_number:
        :return: dict of account_number with its list of invoices
        """
        discovered_invoices = []
        start_date = self._get_start_invoice_date()
        end_date = self._get_end_invoice_date()

        start_date_str = datetime.datetime.strftime(
            self._get_start_invoice_date(), "%Y-%m-%d"
        )
        end_date_str = datetime.datetime.strftime(
            self._get_end_invoice_date(), "%Y-%m-%d"
        )

        invoices_list = self.api_client.get_invoices_for_account(
            self.access_token,
            self.user_id,
            account_number,
            start_date_str,
            end_date_str,
        )

        if not invoices_list:
            LOGGER.info("No invoice found.")
            return discovered_invoices

        for invoice in invoices_list:

            if not invoice["invoiceUrl"]:
                LOGGER.info(
                    f"Pdf download url not found for invoice {invoice.get('formatedInvoiceId')}"
                )
                continue

            invoice_date = datetime.datetime.strptime(
                invoice["date"], "%Y-%m-%d"
            ).date()

            if not start_date <= invoice_date <= end_date:
                LOGGER.info(
                    f"Skipping invoice because date '{invoice_date}' is outside requested range"
                )
                continue

            invoice["date"] = invoice_date
            invoice["account_number"] = account_number

            discovered_invoices.append(invoice)
        return discovered_invoices

    @staticmethod
    def get_discovered_files(
        run: Run, invoices_list: List[dict]
    ) -> List[DiscoveredFile]:
        """
        Fetch pdf details for all invoices of their respective accounts
        :param run: run for Job jobconfig
        :param invoices_list: list of all invoices for an accounts
        :return: list of discovered files
        """
        discovered_files = []
        for invoice in invoices_list:
            account_number = invoice.get("account_number")
            invoice_number = invoice.get("formatedInvoiceId")
            invoice_date = invoice.get("date")

            document_properties = {
                "invoice_number": invoice_number,
                "invoice_date": str(invoice_date),
                "total_amount": invoice.get("amount"),
                "vendor_name": "Waste Management",
                "restaurant_name": None,
                "account_number": account_number,
            }

            reference_code = f"{account_number}_{invoice_number}_{invoice_date}"

            try:
                # pylint: disable=no-member
                discovered_file = DiscoveredFile.build_unique(
                    run,
                    reference_code,
                    document_type=DocumentType.INVOICE.ident,
                    file_format=FileFormat.PDF.ident,
                    original_download_url=invoice.get("invoiceUrl"),
                    original_filename=f"{reference_code}.pdf",
                    document_properties=document_properties,
                )
            except DiscoveredFile.AlreadyExists:
                LOGGER.info(
                    f"Discovered file already exists with reference code : {reference_code}"
                )
                continue  # skip if seen before
            discovered_files.append(discovered_file)
            LOGGER.info("Invoice details: %s", str(discovered_file.document_properties))

        return discovered_files

    def _download_documents(self, invoices_list: List[dict]) -> List[DiscoveredFile]:
        """
        Chooses the documents to be downloaded based on the document type
        :return: Returns the list of Discovered Files
        """
        document_type = self.run.job.requested_document_type
        if document_type == "invoice":
            return self._download_invoices(invoices_list)

        raise NotImplementedError(
            f"Requested Document Type is not supported: {document_type}"
        )

    def _download_invoices(self, invoices_list: List[dict]) -> List[DiscoveredFile]:
        """
        Downloads the Invoices
        :return: Returns the list of the Discovered Files
        """

        LOGGER.info("Download invoice process begins.")

        # Fetching all invoice table date & storing it in memory
        discovered_files_list = WasteManagementRunner.get_discovered_files(
            self.run, invoices_list
        )

        LOGGER.info(
            f"Total Invoices within date range and download link available: {len(discovered_files_list)}"
        )

        self.download_invoice_by_url(discovered_files_list)

        return discovered_files_list

    def download_invoice_by_url(self, discovered_files: List):
        """
        Download the File in PDF format
        :param discovered_files: DiscoveredFile variable
        """
        for discovered_file in discovered_files:
            _downloader = download.DriverBasedUrlGetDownloader(
                driver=self.driver,
                download_url=discovered_file.original_download_url,
                local_filepath=self.download_location,
                rename_to=os.path.join(
                    self.download_location, discovered_file.original_filename
                ),
                file_exists_check_kwargs=dict(timeout=20, pattern=r"Invoice.pdf$"),
            )
            download.download_discovered_file(discovered_file, _downloader)

    def _get_start_invoice_date(self):
        start_date_str = self.run.request_parameters.get("start_date")
        if not start_date_str:
            return date.today() - timedelta(days=60)

        return datetime_utils.date_from_isoformat(start_date_str)

    def _get_end_invoice_date(self):
        end_date_str = self.run.request_parameters.get("end_date")
        if not end_date_str or end_date_str == str(date.today()):
            return date.today() + timedelta(days=1)

        return datetime_utils.date_from_isoformat(end_date_str)

    def start_documents_download_flow(self, run: Run) -> List[DiscoveredFile]:
        """
        Initiates the Document Download Workflow
        :param run: Run Object
        :return: Returns the list of Discovered Files
        """
        discovered_files = []
        try:
            self._login()
            accounts_list = self.api_client.get_accounts_list(
                access_token=self.access_token, user_id=self.user_id
            )

            for account in accounts_list:
                LOGGER.info(f'Found account: {account["custAccountId"]}')
                invoices_list = self.get_invoices_list(account["custAccountId"])

                discovered_files += self._download_documents(invoices_list)
        finally:
            self._quit_driver()

        return discovered_files

    def login_flow(self, run: Run):
        self._login()
