import base64
import os
import requests

from datetime import date, timedelta
from typing import List

from spices import datetime_utils
from spices.datetime_utils import date_from_isoformat_datetime, date_to_isoformat
from spices.http_utils import make_retryable_session
from spices.services import ContextualError

from apps.adapters.base import VendorDocumentDownloadInterface
from apps.adapters.framework import download
from apps.adapters.framework.download import BaseDownloader
from apps.adapters.vendors import LOGGER
from apps.error_codes import ErrorCode
from apps.runs.models import Run, DiscoveredFile, DocumentType, FileFormat


class NVEnergyClient:
    """
    Client interface for NV Energy APIs
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
        Auth API to login into NV Energy
        """
        api_url = "/".join([self._base_url, "factors/auth"])
        payload = {
            "username": username,
            "password": password,
            "type": "sms",
            "isLoggingInFromMobileApp": False,
            "isFingerPrintEnabled": False,
            "breachedPasswordCheck": True,
            "nvesource": "CUSTOMER WEB ACCESS(CWA)",
        }

        response = self._session.post(api_url, json=payload, headers=self._headers)
        if response.ok:
            LOGGER.info(f"Response: {response.text}")

            response_body = response.json().get("ResponseBody")
            if response_body.get("status") == "LOCKED_OUT":
                raise ContextualError(
                    code=ErrorCode.ACCOUNT_DISABLED_FAILED_WEB.ident,
                    message=ErrorCode.ACCOUNT_DISABLED_FAILED_WEB.message.format(
                        username=username
                    ),
                    params={"error_msg": ""},
                )

            api_url = "/".join([self._base_url, "auth/retrieveAuthentication"])
            response = self._session.post(api_url, json=payload, headers=self._headers)
            if response.ok:
                user_data = response.json().get("ResponseBody").get("user")
                access_token = user_data["jwt"]
                company_id = user_data["companyID"]
                return access_token, company_id

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

    def get_accounts_list(self, access_token: str, company_id: str):
        """
        NV Energy account details API
        """
        api_url = "/".join([self._base_url, "userAccount/retrieveAccountList"])
        self._headers["Authorization"] = access_token
        LOGGER.info(f"[tag:WEWARSD1] Fetch account details from url={api_url}")
        payload = {
            "_companyCode": company_id,
            "getBothCompanyCodeLists": False,
            "nvesource": "CUSTOMER WEB ACCESS(CWA)",
        }

        response = self._session.post(api_url, json=payload, headers=self._headers)
        if response.ok:
            LOGGER.info(f"Response: {response.text}")
            return response.json().get("ResponseBody").get("accountLists")

        raise Exception(
            f"[tag:WEWARSD2] Failed fetching user details data!"
            f"with HTTP {response.status_code} (url={api_url},response_body={response.text})"
        )

    def get_invoices_for_account(
        self, access_token: str, account_number: str, bill_type: str
    ):
        """
        NV Energy api to fetch invoices list for an account
        """
        api_url = "/".join([self._base_url, "accountfeed/retrieveAccountHistory"])
        self._headers["Authorization"] = access_token
        LOGGER.info(f"[tag:WEWARSD1] Fetch user details data from url={api_url}")
        payload = {
            "billType": bill_type,
            "nvesource": "CUSTOMER WEB ACCESS(CWA)",
            "userAccountNumber": account_number,
        }

        response = self._session.post(api_url, json=payload, headers=self._headers)
        if response.ok:
            LOGGER.info(f"Response: {response.text}")
            return response.json().get("ResponseBody").get("accountHistoryItems")

        raise Exception(
            f"[tag:WEWARSD2] Failed fetching invoices details for account data!"
            f"with HTTP {response.status_code} (url={api_url},response_body={response.text})"
        )

    def get_pdf(
        self, access_token: str, account_number: str, invoice_date: str, bill_type: str
    ):
        """
        NV Energy PDF Data download API
        """
        api_url = "/".join([self._base_url, "accountfeed/viewbill"])
        self._headers["Authorization"] = access_token
        payload = {
            "printDate": invoice_date,
            "billType": bill_type,
            "displayCode": "Y",
            "nvesource": "CUSTOMER WEB ACCESS(CWA)",
            "userAccountNumber": account_number,
        }
        LOGGER.info(
            f"[tag:WEWARSD1] Fetch user details data from url={api_url}, payload={payload}"
        )

        response = self._session.post(api_url, json=payload, headers=self._headers)
        if response.ok:
            # LOGGER.info(f"Response: {response.text}")
            return response.json().get("ResponseBody")

        raise Exception(
            f"[tag:WEWARSD2] Failed fetching pdf details data!"
            f"with HTTP {response.status_code} (url={api_url},response_body={response.text})"
        )


class NVEnergyRunner(VendorDocumentDownloadInterface):
    """Runner Class for NV Energy"""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.access_token = None
        self.company_id = None
        self.api_client = NVEnergyClient("https://services.nvenergy.com/api/1.0/cdx")

    def _login(self):
        """
        Login to NV Energy
        :return: Nothing
        """
        self.access_token, self.company_id = self.api_client.get_access_token(
            self.run.job.username, self.run.job.password
        )

    def get_accounts(self):
        """
        Get all accounts detail
        """
        accounts_list = self.api_client.get_accounts_list(
            access_token=self.access_token, company_id=self.company_id
        )
        total_accounts = []

        for account in accounts_list:
            account_detail = {
                "account_number": account.get("accountNumber"),
                "restaurant_name": account.get("customerLastName").replace(
                    "&amp;", "&"
                ),
                "bill_type": account.get("billType"),
            }
            total_accounts.append(account_detail)
        return total_accounts

    def get_invoice_details(self, account_detail: dict):
        """
        Fetch Invoice Detail for an account
        :param account_detail: account detail
        :return: dict of account_number with its list of invoices
        """
        invoice_list = []
        start_date = self._get_start_invoice_date()
        end_date = self._get_end_invoice_date()

        account_number = account_detail["account_number"]
        bills_list = self.api_client.get_invoices_for_account(
            self.access_token,
            account_detail["account_number"],
            account_detail["bill_type"],
        )

        for bill in bills_list:
            if bill.get("transType") == "Bill":
                invoice_date_str = bill.get("statement").get("transactionDate")
                invoice_date = date_from_isoformat_datetime(invoice_date_str)

                if not start_date <= invoice_date <= end_date:
                    LOGGER.info(
                        f"Skipping invoice because date '{invoice_date}' is outside requested range"
                    )
                    continue
                invoice_data = {
                    **account_detail,
                    "invoice_date": invoice_date,
                    "total_amount": bill.get("statement").get("totalBillAmount"),
                }
                invoice_list.append(invoice_data)
                return {account_number: invoice_list}

    def get_discovered_files(
        self, run: Run, invoice_details: dict
    ) -> List[DiscoveredFile]:
        """
        Fetch pdf details for all invoices of their respective accounts
        :param run: run for Job jobconfig
        :param invoice_details: dict containing all invoice details for all accounts
        :return: list of discovered files
        """
        discovered_files = []
        for account_number, invoices_list in invoice_details.items():
            for invoice in invoices_list:
                invoice_date = invoice.get("invoice_date")
                reference_code = f"{account_number}_{invoice_date}"

                pdf_base64_array = self.api_client.get_pdf(
                    access_token=self.access_token,
                    account_number=account_number,
                    invoice_date=date_to_isoformat(invoice_date),
                    bill_type=invoice.get("bill_type"),
                )
                if not pdf_base64_array:
                    continue

                document_properties = {
                    "invoice_number": None,
                    "invoice_date": str(invoice_date),
                    "total_amount": invoice.get("total_amount"),
                    "vendor_name": "NV Energy",
                    "restaurant_name": invoice.get("restaurant_name"),
                    "account_number": account_number,
                }
                try:
                    # pylint: disable=no-member
                    discovered_file = DiscoveredFile.build_unique(
                        run,
                        reference_code,
                        document_type=DocumentType.INVOICE.ident,
                        file_format=FileFormat.PDF.ident,
                        original_download_url=pdf_base64_array,
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

        # Fetching all invoice table date & storing it in memory
        discovered_files_list = self.get_discovered_files(self.run, invoice_details)

        LOGGER.info(
            f"Total Invoices within date range and download link available: {len(discovered_files_list)}"
        )

        self.download_invoice_by_content_array(discovered_files_list)

        return discovered_files_list

    def download_invoice_by_content_array(self, discovered_files: list):
        """
        Download the File in PDF format
        :param discovered_files: DiscoveredFile variable
        """
        for discovered_file in discovered_files:
            _downloader = Base64Downloader(
                base64_string=discovered_file.original_download_url,
                local_filepath=os.path.join(self.download_location, "invoice.pdf"),
                rename_to=os.path.join(
                    self.download_location, discovered_file.original_filename
                ),
                file_exists_check_kwargs=dict(timeout=20),
            )
            download.download_discovered_file(discovered_file, _downloader)

    def _get_start_invoice_date(self):
        start_date_str = self.run.request_parameters.get("start_date")
        if not start_date_str:
            return date.today() - timedelta(days=90)

        return datetime_utils.date_from_isoformat(start_date_str)

    def _get_end_invoice_date(self):
        end_date_str = self.run.request_parameters.get("end_date")
        if not end_date_str or end_date_str == str(date.today()):
            return date.today() + timedelta(days=60)

        return datetime_utils.date_from_isoformat(end_date_str)

    def start_documents_download_flow(self, run: Run) -> List[DiscoveredFile]:
        """
        Initiates the Document Download Workflow
        :param run: Run Object
        :return: Returns the list of Discovered Files
        """
        try:
            self._login()
            invoice_details = {}

            for account in self.get_accounts():
                LOGGER.info(
                    f'Found account: {account["account_number"]}: {account["restaurant_name"]}'
                )
                invoice_data = self.get_invoice_details(account)
                if invoice_data:
                    invoice_details.update(invoice_data)

            discovered_files = self._download_documents(invoice_details)
        finally:
            self._quit_driver()

        return discovered_files

    def login_flow(self, run: Run):
        self._login()


class Base64Downloader(BaseDownloader):
    """
    Selenium downloader implementation that downloads by decoding base64_string, with built-in retries.
    Provides optional functionality to rename the downloaded file if desired.
    """

    def __init__(self, base64_string, **kwargs):
        super().__init__(**kwargs)
        self.base64_string = base64_string

    def _perform_download_action(self):
        """Perform the download action"""
        with open(self.local_filepath, "wb") as file:
            file.write(base64.b64decode(self.base64_string))
