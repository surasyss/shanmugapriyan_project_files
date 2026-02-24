import os
from datetime import date, datetime, timedelta
from typing import List

import requests
from spices.datetime_utils import date_from_string
from spices.http_utils import make_retryable_session
from spices.services import ContextualError

from apps.adapters.base import VendorDocumentDownloadInterface
from apps.adapters.framework import download
from apps.adapters.vendors import LOGGER
from apps.error_codes import ErrorCode
from apps.runs.models import Run, DiscoveredFile, DocumentType, FileFormat


class RepublicServiceClient:
    """
    Client interface for Republic Services APIs
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

    def get_access_token(self, username: str, password: str):
        """
        Republic Services Auth Credentials API
        Use this API to Login into Republic Services
        """
        api_url = "/".join([self._base_url, "api/v1/auth/login"])
        payload = {"username": username, "password": password}

        response = self._session.post(api_url, json=payload, headers=self._headers)
        if response.ok:
            LOGGER.info(f"Response: {response.text}")
            return response.json().get("data").get("id_token")

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

    def get_user_details(self, token: str):
        """
        Republic Services User Details Data API
        Basically to fetch the User details data like Account name, Account Number etc
        """
        api_url = "/".join([self._base_url, "api/v1/mr/users/default"])
        self._headers["Authorization"] = f"Bearer {token}"
        LOGGER.info(f"[tag:WEWARSD1] Fetch user details data from url={api_url}")

        response = self._session.get(api_url, headers=self._headers)
        if response.ok:
            LOGGER.info(f"Response: {response.text}")
            return response.json().get("data").get("accounts")

        raise Exception(
            f"[tag:WEWARSD2] Failed fetching user details data!"
            f"with HTTP {response.status_code} (url={api_url},response_body={response.text})"
        )

    def get_invoices_for_account(self, token: str, account: str):
        """
        Republic Services Invoices Details for an account Data API
        """
        api_url = "/".join(
            [self._base_url, f"api/v1/mr/accounts/{account}/bills?limit=10000000"]
        )
        self._headers["Authorization"] = f"Bearer {token}"
        LOGGER.info(f"[tag:WEWARSD1] Fetch user details data from url={api_url}")

        response = self._session.get(api_url, headers=self._headers)
        if response.ok:
            LOGGER.info(f"Response: {response.text}")
            return response.json().get("data").get("bills")

        raise Exception(
            f"[tag:WEWARSD2] Failed fetching invoices details for account data!"
            f"with HTTP {response.status_code} (url={api_url},response_body={response.text})"
        )

    def get_pdf(self, token: str, account: str, invoice_id: str):
        """
        Republic Services PDF Details Data API
        Basically to fetch the PDF details data like pdf_url
        """
        api_url = "/".join(
            [self._base_url, f"api/v1/mr/accounts/{account}/bills/{invoice_id}/pdf"]
        )
        self._headers["Authorization"] = f"Bearer {token}"
        LOGGER.info(f"[tag:WEWARSD1] Fetch user details data from url={api_url}")

        response = self._session.get(api_url, headers=self._headers)
        if response.ok:
            LOGGER.info(f"Response: {response.text}")
            return response.json().get("data").get("url")

        raise Exception(
            f"[tag:WEWARSD2] Failed fetching pdf details data!"
            f"with HTTP {response.status_code} (url={api_url},response_body={response.text})"
        )


class RepublicServicesRunner(VendorDocumentDownloadInterface):
    """Runner Class for Republic Services Online"""

    # uses_proxy = True

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.token = None
        self.vendor = "Republic Services"
        self.api_client = RepublicServiceClient("https://www.republicservices.com")

    def _login(self):
        """
        Login to Republic Services
        :return: Nothing
        """
        self.token = self.api_client.get_access_token(
            self.run.job.username, self.run.job.password
        )

    def get_account_details(self):
        """
        Get User Account details
        eg. Account IDs & Account names
        """
        user_details = self.api_client.get_user_details(token=self.token)
        account_details = []

        for user_detail in user_details:
            if not (user_detail.get("accountId") and user_detail.get("name")):
                continue
            account_detail = {
                "id": user_detail.get("accountId"),
                "name": user_detail.get("name"),
            }
            account_details.append(account_detail)

        return account_details

    def get_invoice_details(self, account_id: str, account_name: str):
        """
        Fetch Invoice Details for an account
        :param account_id: account id
        :param account_name: account name
        :return: dict of account_id and invoices against it
        """
        invoice_list = []
        try:
            bill_list = self.api_client.get_invoices_for_account(
                token=self.token, account=account_id
            )

            for bill in bill_list:
                invoice = {
                    "account_name": account_name,
                    "invoice_id": bill.get("billId"),
                    "invoice_number": bill.get("billReferenceId"),
                    "total_amount": bill.get("amountDue").get("amount"),
                    "due_date": bill.get("dueDate"),
                }
                invoice_list.append(invoice)

        except Exception as excep:  # pylint: disable=broad-except
            LOGGER.info(f"No invoice found: {excep}")

        return {account_id: invoice_list}

    def get_pdf_details(
        self, run: Run, from_date: date, invoice_details: dict
    ) -> List[DiscoveredFile]:
        """
        Fetch pdf details for all invoices of their respective accounts
        :param run: run
        :param from_date: date to start looking for invoice
        :param invoice_details: dict containing all invoice details for all accounts
        :return: list of discovered files
        """
        discovered_files = []

        for invoice_detail in invoice_details:
            if not invoice_details[invoice_detail]:
                continue

            for invoice in invoice_details[invoice_detail]:
                customer_number = invoice_detail
                invoice_id = invoice.get("invoice_id")
                invoice_number = invoice.get("invoice_number")
                reference_code = f"{customer_number}_{invoice_number}"

                due_date = date_from_string(invoice.get("due_date"), "%Y-%m-%d")
                invoice_date = due_date - timedelta(days=20)
                if invoice_date < from_date:
                    continue

                pdf_link = self.api_client.get_pdf(
                    token=self.token, account=customer_number, invoice_id=invoice_id
                )
                document_properties = {
                    "invoice_number": invoice_number,
                    "invoice_date": str(invoice_date),
                    "total_amount": invoice.get("total_amount"),
                    "vendor_name": self.vendor,
                    "restaurant_name": invoice.get("account_name"),
                    "customer_number": customer_number,
                }
                try:
                    # pylint: disable=no-member
                    discovered_file = DiscoveredFile.build_unique(
                        run,
                        reference_code,
                        document_type=DocumentType.INVOICE.ident,
                        file_format=FileFormat.PDF.ident,
                        original_download_url=pdf_link,
                        original_filename=f"{reference_code}.pdf",
                        document_properties=document_properties,
                    )
                except DiscoveredFile.AlreadyExists:
                    LOGGER.info(
                        f"Discovered file already exists with reference code : {reference_code}"
                    )
                    continue  # skip if seen before
                discovered_files.append(discovered_file)
                LOGGER.info(
                    "Invoice details: %s", str(discovered_file.document_properties)
                )

        return discovered_files

    def _download_documents(self, invoice_details: dict) -> List[DiscoveredFile]:
        """
        Chooses the documents to be downloaded based on the document type
        :return: Returns the list of Discovered Files
        """
        document_type = self.run.job.requested_document_type
        if document_type == "invoice":
            return self._download_invoices(invoice_details)

        raise NotImplementedError(
            f"Requested Document Type is not supported: {document_type}"
        )

    def _download_invoices(self, invoice_details: dict) -> List[DiscoveredFile]:
        """
        Downloads the Invoices
        :return: Returns the list of the Discovered Files
        """

        LOGGER.info("Download invoice process begins.")
        start_date = datetime.strptime(
            self.run.request_parameters["start_date"], "%Y-%m-%d"
        ).date()

        # Fetching all invoice table date & storing it in memory
        discovered_files_list = self.get_pdf_details(
            self.run, start_date, invoice_details
        )

        LOGGER.info(
            f"Total Invoices within date range and download link available: {len(discovered_files_list)}"
        )

        self.download_invoice_by_url(discovered_files_list)

        return discovered_files_list

    def download_invoice_by_url(self, discovered_files: list):
        """
        Download the File in PDF format
        :param discovered_files: DiscoveredFile variable
        """
        for discovered_file in discovered_files:
            _downloader = download.DriverBasedUrlGetDownloader(
                self.driver,
                download_url=discovered_file.original_download_url,
                local_filepath=f"{self.download_location}/document.pdf",
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
        try:
            self._login()
            invoice_details = {}

            for account in self.get_account_details():
                LOGGER.info(f'Found account: {account["id"]}: {account["name"]}')
                invoice_details.update(
                    self.get_invoice_details(
                        account_id=account["id"], account_name=account["name"]
                    )
                )

            discovered_files = self._download_documents(invoice_details)
        finally:
            self._quit_driver()

        return discovered_files

    def login_flow(self, run: Run):
        self._login()
