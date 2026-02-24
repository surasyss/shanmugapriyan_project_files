import os
from datetime import datetime, date
from json.decoder import JSONDecodeError
from typing import List

import requests
from retry import retry
from spices.datetime_utils import date_from_string
from spices.documents import DocumentType
from spices.http_utils import make_retryable_session
from spices.services import ContextualError

from apps.adapters.base import VendorDocumentDownloadInterface
from apps.adapters.framework import download
from apps.adapters.vendors import LOGGER
from apps.error_codes import ErrorCode
from apps.runs.models import Run, DiscoveredFile, FileFormat


class FrontierClient:
    """
    Client interface for Frontier APIs
    """

    def __init__(self, api_base_url: str):
        self._base_url = api_base_url.rstrip("/")

        # ok to make everything retryable on 5xx
        self._session = make_retryable_session(
            requests.Session(), backoff_factor=2, raise_on_status=False
        )
        self._headers = {
            "Content-Type": "application/json",
            "Accept": "application/json, text/plain, */*",
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_14_3) AppleWebKit/537.36 (KHTML, like Gecko)",
        }

    def login(self, username: str, password: str):
        """
        Republic Services Auth Credentials API
        Use this API to Login into Republic Services
        """
        api_url = "/".join([self._base_url, "api/login"])
        payload = {"loginId": username, "password": password}

        response = self._session.post(api_url, json=payload, headers=self._headers)
        if response.ok:
            LOGGER.info(f"Response: {response.text}")
            return response.json().get("uid")

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

    def get_session(self):
        """
        Frontier User session API
        """
        api_url = "/".join([self._base_url, "api/session"])
        LOGGER.info(f"[tag:WEWARSD1] Fetch user session data from url={api_url}")

        response = self._session.get(api_url, headers=self._headers)
        if response.ok:
            LOGGER.info(f"Response: {response.text}")
            return response.json()

        raise Exception(
            f"[tag:WEWARSD2] Failed fetching user session data!"
            f"with HTTP {response.status_code} (url={api_url},response_body={response.text})"
        )

    def get_accounts(self):
        """
        Frontier Accounts API
        """
        api_url = "/".join([self._base_url, "api/accounts"])
        LOGGER.info(f"[tag:WEWARSD1] Fetch accounts from url={api_url}")

        response = self._session.get(api_url, headers=self._headers)
        if response.ok:
            LOGGER.info(f"Response: {response.text}")
            return response.json()

        raise Exception(
            f"[tag:WEWARSD2] Failed fetching accounts data!"
            f"with HTTP {response.status_code} (url={api_url},response_body={response.text})"
        )

    def get_account_details(self, account_id: str):
        """
        Frontier Account details API
        """
        api_url = "/".join([self._base_url, f"api/accounts/{account_id}"])
        LOGGER.info(f"[tag:WEWARSD1] Fetch account details from url={api_url}")

        response = self._session.get(api_url, headers=self._headers)
        if response.ok:
            LOGGER.info(f"Response: {response.text}")
            return response.json()

        raise Exception(
            f"[tag:WEWARSD2] Failed fetching account details data!"
            f"with HTTP {response.status_code} (url={api_url},response_body={response.text})"
        )

    @retry(JSONDecodeError, tries=3, delay=0.1, max_delay=1, backoff=2, logger=LOGGER)
    def get_statements(self, account_id: str):
        """
        Frontier Account statements API
        """
        api_url = "/".join([self._base_url, f"api/accounts/{account_id}/statements"])
        LOGGER.info(f"[tag:WEWARSD1] Fetch account details from url={api_url}")

        response = self._session.get(api_url, headers=self._headers)
        if response.ok:
            LOGGER.info(f"Response: {response.text}")
            return response.json()

        raise Exception(
            f"[tag:WEWARSD2] Failed fetching account statements data!"
            f"with HTTP {response.status_code} (url={api_url},response_body={response.text})"
        )


class FrontierRunner(VendorDocumentDownloadInterface):
    """Runner Class"""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.vendor = "Frontier"
        self.api_client = FrontierClient("https://frontier.com")

    def _login(self):
        """
        Login to Frontier
        :return: Nothing
        """
        LOGGER.info(f"Attempting login")
        self.api_client.login(self.run.job.username, self.run.job.password)

    def get_pdf_details(
        self, run: Run, from_date: date, invoices: [], account: dict
    ) -> List[DiscoveredFile]:
        """
        Fetch pdf details for all invoices of their respective accounts
        :param run: run
        :param from_date: date to start looking for invoice
        :param invoices: list of all invoices for an account
        :param account: Account details
        :return: list of discovered files
        """
        LOGGER.info(f"Fetching pdf invoices")
        discovered_files = []

        for invoice in invoices:
            invoice_date = date_from_string(invoice.get("date"), "%Y-%m-%d")
            if invoice_date < from_date:
                return discovered_files

            account_id = account.get("id")
            reference_code = f'{account_id}_{invoice.get("statementId")}'

            try:
                discovered_file = DiscoveredFile.build_unique(
                    run,
                    reference_code,
                    document_type=DocumentType.INVOICE.ident,  # pylint: disable=no-member
                    file_format=FileFormat.PDF.ident,  # pylint: disable=no-member
                    original_download_url=invoice.get("pdfLink"),
                    original_filename=f"{reference_code}.pdf",
                    document_properties={
                        "customer_number": account_id,
                        "invoice_date": f"{invoice_date}",
                        "vendor_name": self.vendor,
                        "total_amount": invoice.get("amount"),
                        "invoice_number": invoice.get("statementId"),
                        "restaurant_name": account.get("name"),
                    },
                )
            except DiscoveredFile.AlreadyExists:
                LOGGER.info(
                    f"Discovered file already exists with reference code : {reference_code}"
                )
                continue  # skip if seen before

            discovered_files.append(discovered_file)
            LOGGER.info(
                "Invoice details row data: %s", str(discovered_file.document_properties)
            )
        return discovered_files

    def _download_documents(self, invoices: list, account=dict) -> List[DiscoveredFile]:
        """
        Chooses the documents to be downloaded based on the document type
        :return: Returns the list of Discovered Files
        """
        document_type = self.run.job.requested_document_type
        if document_type == "invoice":
            return self._download_invoices(invoices=invoices, account=account)

        raise NotImplementedError(
            f"Requested Document Type is not supported: {document_type}"
        )

    def _download_invoices(self, invoices: list, account=dict) -> List[DiscoveredFile]:
        """
        Downloads the Invoices
        :return: Returns the list of the Discovered Files
        """
        LOGGER.info("Download invoice process begins.")
        start_date = datetime.strptime(
            self.run.request_parameters["start_date"], "%Y-%m-%d"
        ).date()

        # Fetching all invoice table date & storing it in memory
        discovered_files = self.get_pdf_details(
            run=self.run, from_date=start_date, invoices=invoices, account=account
        )

        LOGGER.info(
            f"Total Invoices within date range and download link available: {len(discovered_files)}"
        )
        return discovered_files

    def download_invoice_by_url(self, discovered_files: list):
        """
        Download the File in PDF format
        :param discovered_files: DiscoveredFile variable
        """
        LOGGER.info(f"Downloading invocies from URL")
        for discovered_file in discovered_files:
            _downloader = download.DriverBasedUrlGetDownloader(
                self.driver,
                download_url=discovered_file.original_download_url,
                local_filepath=f"{self.download_location}/viewBillDetailESS.pdf",
                rename_to=os.path.join(
                    self.download_location, discovered_file.original_filename
                ),
                file_exists_check_kwargs=dict(timeout=20),
            )
            download.download_discovered_file(discovered_file, _downloader)

    def start_documents_download_flow(self, run: Run) -> List[DiscoveredFile]:
        """
        Initiates the Document Download Workflow
        :param run: Run Object
        :return: Returns the list of Discovered Files
        """
        discovered_files = []
        try:
            self._login()
            self.api_client.get_session()
            accounts = self.api_client.get_accounts()
            LOGGER.info(f"{len(accounts)} Accounts found: {accounts}")

            for account in accounts:
                LOGGER.info(
                    f'Account ID: {account.get("id")}, Account name: {account.get("name")}'
                )
                invoices = self.api_client.get_statements(account_id=account["id"])
                invoices.sort(key=lambda invoice: invoice["date"], reverse=True)

                LOGGER.info(f"Invoices found sorted by date: {invoices}")
                discovered_files += self._download_documents(
                    invoices=invoices, account=account
                )
            self.download_invoice_by_url(discovered_files)
        finally:
            self._quit_driver()

        return discovered_files

    def login_flow(self, run: Run):
        self._login()
