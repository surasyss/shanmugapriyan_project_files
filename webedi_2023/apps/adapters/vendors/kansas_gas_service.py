import os
import requests

from datetime import datetime
from typing import List

from spices.datetime_utils import date_from_isoformat_datetime
from spices.documents import DocumentType
from spices.http_utils import make_retryable_session
from spices.services import ContextualError

from selenium.webdriver.common.by import By

from apps.adapters.base import VendorDocumentDownloadInterface
from apps.adapters.framework import download
from apps.adapters.helpers.webdriver_helper import get_url, wait_for_element
from apps.adapters.vendors import LOGGER
from apps.error_codes import ErrorCode
from apps.runs.models import Run, DiscoveredFile, FileFormat


class KansasGasServiceClient:
    """
    Client interface for Kansas Gas Service APIs
    """

    def __init__(self, api_base_url: str):
        self._base_url = api_base_url.rstrip("/")

        # ok to make everything retryable on 5xx
        self._session = make_retryable_session(
            requests.Session(), backoff_factor=2, raise_on_status=False
        )
        self._headers = {
            "Content-Type": "application/json",
            "Accept": "*/*",
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_14_3) AppleWebKit/537.36 (KHTML, like Gecko)",
        }

        self._payload = {
            "auditInfo": {
                "appVersion": "9b28eddc",
                "csrId": "null",
                "isApp": "false",
                "isCSR": "false",
                "isMobile": "false",
                "isWeb": "false",
                "ldcProvider": "KGS",
                "registeredUsername": "null",
                "sessionId": "e9a07242-530d-44c9-bc10-71ed0e4d6a87",
            },
            "culture": "en-US",
            "ldcProvider": "KGS",
        }

    def login_and_get_billing_accounts(self, username: str, password: str):
        """
        Kansas Gas Service Auth Credentials API
        Use this API to Login and getting user accounts
        """
        api_url = "/".join([self._base_url, "api/login"])

        payload = {**self._payload, "email": username, "password": password}

        response = self._session.post(api_url, json=payload, headers=self._headers)
        if response.ok:
            LOGGER.info(f"Response: {response.text}")
            response_json = response.json()
            registered_user_data = response_json.get("registeredUser")
            username = registered_user_data.get("userName")
            billing_accounts = registered_user_data.get("userInfo").get(
                "billingAccounts"
            )
            self._headers.update(
                {"Authorization-Token": response_json.get("accessToken")}
            )
            return username, billing_accounts

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

    def get_account_summary(self, username, account_number):
        """
        Kansas Gas Service account summary API
        """
        api_url = "/".join([self._base_url, "api/getaccountsummary"])
        LOGGER.info(f"[tag:WEWARSD1] Fetch account summary data from url={api_url}")

        self._payload["auditInfo"]["registeredUsername"] = username
        self._payload["billingAccountNumber"] = account_number

        response = self._session.post(
            api_url, json=self._payload, headers=self._headers
        )
        if response.ok:
            LOGGER.info(f"Response: {response.text}")

            return response.json()

        raise Exception(
            f"[tag:WEWARSD2] Failed fetching account summary data!"
            f"with HTTP {response.status_code} (url={api_url},response_body={response.text})"
        )

    def get_statements(self):
        """
        Kansas Gas Service Account statements API
        """
        api_url = "/".join([self._base_url, "api/getstatements"])
        LOGGER.info(f"[tag:WEWARSD1] Fetch account statements data from url={api_url}")

        response = self._session.post(
            api_url, json=self._payload, headers=self._headers
        )
        if response.ok:
            LOGGER.info(f"Response: {response.text}")

            return response.json()

        raise Exception(
            f"[tag:WEWARSD2] Failed fetching account statements data!"
            f"with HTTP {response.status_code} (url={api_url},response_body={response.text})"
        )

    def get_billing_history(self):
        """
        Kansas Gas Service billing history API
        """
        api_url = "/".join([self._base_url, "api/getBillingHistory"])
        LOGGER.info(f"[tag:WEWARSD1] Fetch billing history data from url={api_url}")

        response = self._session.post(
            api_url, json=self._payload, headers=self._headers
        )
        if response.ok:
            LOGGER.info(f"Response: {response.text}")
            bills = response.json()

            bills_dict = {
                str(date_from_isoformat_datetime(bill["billDate"])): bill[
                    "endingBalance"
                ]
                for bill in bills
            }
            return bills_dict

        raise Exception(
            f"[tag:WEWARSD2] Failed fetching billing history data!"
            f"with HTTP {response.status_code} (url={api_url},response_body={response.text})"
        )


class KansasGasServiceRunner(VendorDocumentDownloadInterface):
    """Runner Class"""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.vendor = "Kansas Gas Service"
        self.api_client = KansasGasServiceClient("https://api.kansasgasservice.com")

    def _login(self):
        """
        Login to Kansas Gas Service
        :return: tuple of username, accounts
        """
        LOGGER.info(f"Attempting login")
        username, billing_accounts = self.api_client.login_and_get_billing_accounts(
            self.run.job.username, self.run.job.password
        )
        return username, billing_accounts

    def get_pdf_details(self, run: Run, invoice_details) -> DiscoveredFile:
        """
        Create discovered file object
        :param run: run
        :param invoice_details: invoice data dict
        :return: discovered file object
        """

        invoice_date = invoice_details.get("invoice_date")

        reference_code = f'{invoice_details.get("account_number")}_{invoice_date}'

        try:
            discovered_file = DiscoveredFile.build_unique(
                run,
                reference_code,
                document_type=DocumentType.INVOICE.ident,  # pylint: disable=no-member
                file_format=FileFormat.PDF.ident,  # pylint: disable=no-member
                original_download_url=invoice_details.get("original_download_url"),
                original_filename=f"{reference_code}.pdf",
                document_properties={
                    "customer_number": invoice_details.get("account_number"),
                    "invoice_date": f"{invoice_date}",
                    "vendor_name": self.vendor,
                    "total_amount": invoice_details.get("total_amount"),
                    "invoice_number": invoice_details.get("invoice_number"),
                    "restaurant_name": invoice_details.get("restaurant_name"),
                },
            )

            LOGGER.info(
                "Invoice details row data: %s", str(discovered_file.document_properties)
            )
            return discovered_file

        except DiscoveredFile.AlreadyExists:
            LOGGER.info(
                f"Discovered file already exists with reference code : {reference_code}"
            )

    def _download_documents(self, invoice_details) -> DiscoveredFile:
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

    def _download_invoices(self, invoice_details) -> DiscoveredFile:
        """
        Downloads the Invoices
        :return: Returns the list of the Discovered Files
        """
        discovered_file = self.get_pdf_details(
            run=self.run,
            invoice_details=invoice_details,
        )

        return discovered_file

    def get_pdf_download_element(self):
        return self.driver.find_element(By.CSS_SELECTOR, "a.DocPageSave")

    def download_invoice_by_webelement_click(
        self, discovered_file: DiscoveredFile, invoice_number
    ):
        """
        Download the File in PDF format
        :param discovered_file: DiscoveredFile object
        :param invoice_number: document id
        """
        download_url = (
            "https://statements.kansasgasservice.com"
            + discovered_file.original_download_url
        )
        get_url(self.driver, download_url)
        wait_for_element(self.driver, value="a.DocPageSave", msg="Pdf Download Icon")
        _downloader = download.WebElementClickBasedDownloader(
            element=self.get_pdf_download_element(),
            local_filepath=f"{self.download_location}/DOC_{invoice_number}.pdf",
            rename_to=os.path.join(
                self.download_location, discovered_file.original_filename
            ),
            file_exists_check_kwargs=dict(timeout=30),
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
            username, billing_accounts = self._login()
            LOGGER.info(f"{len(billing_accounts)} Accounts found: {billing_accounts}")

            for account in billing_accounts:
                account_number = account.get("billingAccountNumber")
                LOGGER.info(f"Account number: {account_number}")
                account_summary = self.api_client.get_account_summary(
                    username, account_number
                )
                restaurant_name = account_summary.get("accountOwner").get("lastName")

                invoices = self.api_client.get_statements()

                bills_dict = self.api_client.get_billing_history()

                for invoice in invoices:
                    invoice_number = invoice.get("docId")
                    invoice_date = invoice.get("billDate")

                    invoice_date = date_from_isoformat_datetime(invoice_date)

                    start_date = datetime.strptime(
                        self.run.request_parameters["start_date"], "%Y-%m-%d"
                    ).date()

                    end_date = datetime.strptime(
                        self.run.request_parameters["end_date"], "%Y-%m-%d"
                    ).date()

                    if not start_date <= invoice_date <= end_date:
                        LOGGER.info(
                            f"Skipping remaining invoices because date '{invoice_date}' is outside requested range"
                        )
                        break

                    invoice_details = {
                        "account_number": account_number,
                        "restaurant_name": restaurant_name,
                        "invoice_date": invoice_date,
                        "original_download_url": invoice.get("link"),
                        "invoice_number": invoice_number,
                        "total_amount": bills_dict[str(invoice_date)],
                    }

                    discovered_file = self._download_documents(invoice_details)

                    if discovered_file:
                        self.download_invoice_by_webelement_click(
                            discovered_file, invoice_number
                        )
                        discovered_files.append(discovered_file)
        finally:
            self._quit_driver()

        LOGGER.info(
            f"Total Invoices within date range and download link available: {len(discovered_files)}"
        )
        return discovered_files

    def login_flow(self, run: Run):
        self._login()
