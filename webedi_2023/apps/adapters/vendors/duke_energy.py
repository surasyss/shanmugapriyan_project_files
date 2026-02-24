import os
import requests

from datetime import date, timedelta
from typing import List

from spices import datetime_utils
from spices.datetime_utils import date_from_string
from spices.http_utils import make_retryable_session
from spices.services import ContextualError

from apps.adapters.base import VendorDocumentDownloadInterface
from apps.adapters.framework import download
from apps.adapters.framework.download import BaseDownloader
from apps.adapters.vendors import LOGGER
from apps.error_codes import ErrorCode
from apps.runs.models import Run, DiscoveredFile, DocumentType, FileFormat


class DukeEnergyClient:
    """Client interface for Duke Energy APIs"""

    def __init__(self, api_base_url: str):
        self._base_url = api_base_url.rstrip("/")

        # ok to make everything retryable on 5xx
        self._session = make_retryable_session(
            requests.Session(), backoff_factor=2, raise_on_status=False
        )
        self._headers = {
            "Content-Type": "application/x-www-form-urlencoded;charset=utf-8",
            "Accept": "application/json, text/plain, */*",
            "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/102.0.0.0 Safari/537.36",
        }

    def login(self, username: str, password: str):
        """Login API to login into Duke Energy"""
        api_url = "https://www.duke-energy.com/facade/api/Authentication/SignIn"
        payload = {
            "loginIdentity": username,
            "password": password,
        }
        headers = {
            "Content-Type": "application/json",
            "Accept": "text/plain",
            "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/112.0.0.0 Safari/537.36",
        }

        response = self._session.post(api_url, json=payload, headers=headers)
        if response.json().get("Token"):
            LOGGER.info(f"Response: {response.text}")
            token = response.json().get("Token")

            redirect_url_headers = {
                "Accept": "text/html,application/xhtml+xml,application/xml;"
                "q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-"
                "exchange;v=b3;q=0.7",
                "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/112.0.0.0 Safari/537.36",
            }
            redirect_url = (
                f"https://dukeenergy.smartcmobile.com/ssoservice/api/dukesso/ProcessRequest?"
                f"state=TG9naW4=&"
                f"scope=SSA_BUSINESS&"
                f"response_type=code&"
                f"redirect_uri=https://dukeenergy.smartcmobile.com/SSOService/api/dukesso/"
                f"ProcessRequest&client_id=undefined&access_token={token}"
            )
            redirect_resp = self._session.get(
                redirect_url, headers=redirect_url_headers
            )
            if redirect_resp.ok:
                LOGGER.info(f"Redirect Response: {redirect_resp.text}")
                duke_access_token = redirect_resp.url.split("UserData=")[1]
                return duke_access_token

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

    def get_token(self):
        """Duke Energy access token api"""
        token_api_url = "/".join([self._base_url, "Auth/api/Token"])
        token_headers = {
            "Content-Type": "application/json",
            "Accept": "*/*",
            "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/102.0.0.0 Safari/537.36",
        }
        token_payload = "MTMxMzU5OmpHbUZuNWFrdGxKYmM4OUxNLzMrOFhadnllaFdUaUpyeWNNbVZDSGZEYkFoMEE9PQ=="

        LOGGER.info(f"[tag:WEWARSD1] Fetch token from url={token_api_url}")

        token_response = self._session.post(
            token_api_url, json=token_payload, headers=token_headers
        )
        if token_response.ok:
            LOGGER.info(f"Response: {token_response.text}")
            token_response_json = token_response.json()
            return token_response_json.get("access_token")

        raise Exception(
            f"[tag:WEWARSD2] Failed fetching access token!"
            f"with HTTP {token_response.status_code} (url={token_api_url},response_body={token_response.text})"
        )

    def get_user_id(self, duke_access_token):
        """Duke Energy user id api"""

        api_url = "/".join(
            [self._base_url, "registrationInternal/api/SSOSetting/checksso"]
        )
        payload = {"DukeAccessToken": duke_access_token}
        user_id_headers = {
            "Content-Type": "application/json",
            "Accept": "*/*",
            "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/112.0.0.0 Safari/537.36",
        }
        LOGGER.info(f"[tag:WEWARSD1] Fetch user id from url={api_url}")

        response = self._session.post(api_url, json=payload, headers=user_id_headers)
        if response.ok:
            LOGGER.info(f"Response: {response.text}")
            response_json = response.json()
            result = response_json.get("Result")[0]
            return result.get("userId"), result.get("customerNo")

        raise Exception(
            f"[tag:WEWARSD2] Failed fetching user id!"
            f"with HTTP {response.status_code} (url={api_url},response_body={response.text})"
        )

    def get_portfolio_id(self, access_token: str, user_id: str, customer_number: str):
        """Duke Energy portfolio id api"""

        api_url = "/".join(
            [
                self._base_url,
                f"Portfolio/api/Portfolio/portfolio?UserId={user_id}&CustomerNo={customer_number}&Flag=B",
            ]
        )

        headers = {
            "Content-Type": "application/json",
            "Accept": "*/*",
            "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/102.0.0.0 Safari/537.36",
            "Authorization": f"bearer {access_token}",
        }
        LOGGER.info(f"[tag:WEWARSD1] Fetch portfolio id from url={api_url}")

        response = self._session.get(api_url, headers=headers)
        if response.ok:
            LOGGER.info(f"Response: {response.text}")
            response_json = response.json()
            return response_json.get("Result")[0].get("portfolioID")

        raise Exception(
            f"[tag:WEWARSD2] Failed fetching portfolio id!"
            f"with HTTP {response.status_code} (url={api_url},response_body={response.text})"
        )

    def get_customer_numbers_list(
        self, portfolio_id: str, customer_no: str, username: str, access_token: str
    ):
        """Duke Energy customer numbers api"""

        api_url = "/".join(
            [self._base_url, "ProfileData/api/ServiceAccount/serviceaccbyportfolio/"]
        )

        headers = {
            "Content-Type": "application/json",
            "Accept": "*/*",
            "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/102.0.0.0 Safari/537.36",
            "Authorization": f"bearer {access_token}",
        }
        payload = {
            "PortfolioId": [portfolio_id],
            "CustomerNo": customer_no,
            "requestedBy": username.upper(),
            "experience": "COMM",
        }

        LOGGER.info(f"[tag:WEWARSD1] Fetch user id from url={api_url}")

        response = self._session.post(api_url, json=payload, headers=headers)
        if response.ok:
            LOGGER.info(f"Response: {response.text}")
            response_json = response.json()
            customer_numbers = {
                item.get("contractAccountNumber"): item.get("dba")
                for item in response_json.get("Result")
            }
            return customer_numbers

        raise Exception(
            f"[tag:WEWARSD2] Failed fetching customer numbers data!"
            f"with HTTP {response.status_code} (url={api_url},response_body={response.text})"
        )

    def get_invoice_history(
        self, account_number_list: list, username: str, access_token: str
    ):
        """Duke Energy invoices history api"""

        api_url = "/".join(
            [self._base_url, "billing/api/autopayment/getinvoicehistory"]
        )

        headers = {
            "Content-Type": "application/json",
            "Accept": "*/*",
            "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/102.0.0.0 Safari/537.36",
            "Authorization": f"bearer {access_token}",
        }
        payload = {
            "Accountnolst": account_number_list,
            "Bpnumber": "",
            "RecordsFrom": 1,
            "RecordsTo": 2000,
            "GetTotalCount": True,
            "Orderby": "DueDate",
            "Ordertype": "desc",
            "requestedBy": username.upper(),
            "experience": "COMM",
        }

        LOGGER.info(f"[tag:WEWARSD1] Fetch invoice history from url={api_url}")

        response = self._session.post(
            api_url,
            json=payload,
            headers=headers,
        )
        if response.ok:
            LOGGER.info(f"Response: {response.text}")
            account_response = response.json()
            return account_response["Result"][0].get("invoiceRecords")

        raise Exception(
            f"[tag:WEWARSD2] Failed fetching invoices history data!"
            f"with HTTP {response.status_code} (url={api_url},"
            f"response_body={response.text})"
        )

    def get_pdf(self, access_token: str, document_number: str):
        """Duke Energy pdf download api"""

        api_url = "/".join([self._base_url, "common/api/pdf/getpdf"])
        headers = {
            "Content-Type": "application/json",
            "Accept": "*/*",
            "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/102.0.0.0 Safari/537.36",
            "Authorization": f"bearer {access_token}",
        }
        LOGGER.info(f"[tag:WEWARSD1] Fetch pdf data from url={api_url}")

        payload = {"DocumentNumber": document_number}

        response = self._session.post(api_url, json=payload, headers=headers)
        if response.ok:
            return response.content

        raise Exception(
            f"[tag:WEWARSD2] Failed fetching pdf data!"
            f"with HTTP {response.status_code} (url={api_url},response_body={response.text})"
        )


class DukeEnergyRunner(VendorDocumentDownloadInterface):
    """Runner Class for Duke Energy"""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.access_token = None
        self.api_client = DukeEnergyClient("https://dukeapi-prod.smartcmobile.com")

    def _login(self):
        """
        Login to Duke Energy
        :return: Nothing
        """
        duke_access_token = self.api_client.login(
            self.run.job.username, self.run.job.password
        )
        return duke_access_token

    def get_discovered_files(
        self, run: Run, invoices_list: List[dict], customer_numbers_dict: dict
    ) -> List[DiscoveredFile]:
        """
        Fetch pdf details for all invoices of their respective accounts
        :param run: run for Job jobconfig
        :param invoices_list: list of all invoices for an accounts
        :param customer_numbers_dict: customer numbers
        :return: list of discovered files
        """
        discovered_files = []
        for invoice in invoices_list:
            account_number = invoice.get("contractAccountNumber")
            invoice_number = invoice.get("invoiceNumber")

            invoice_date = date_from_string(
                invoice.get("date"), "%m/%d/%Y"
            ) - timedelta(days=21)
            start_date = self._get_start_invoice_date()
            end_date = self._get_end_invoice_date()

            if not start_date <= invoice_date <= end_date:
                LOGGER.info(
                    f"Skipping invoice because date '{invoice_date}' is outside requested range"
                )
                continue

            document_properties = {
                "invoice_number": invoice_number,
                "invoice_date": str(invoice_date),
                "total_amount": invoice.get("amount"),
                "vendor_name": "Duke Energy",
                "restaurant_name": customer_numbers_dict.get(account_number),
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
                    original_download_url=invoice.get("documentNumber"),
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

    def _download_documents(
        self, invoices_list: List[dict], customer_numbers_dict: dict
    ) -> List[DiscoveredFile]:
        """
        Chooses the documents to be downloaded based on the document type
        :return: Returns the list of Discovered Files
        """
        document_type = self.run.job.requested_document_type
        if document_type == "invoice":
            return self._download_invoices(invoices_list, customer_numbers_dict)

        raise NotImplementedError(
            f"Requested Document Type is not supported: {document_type}"
        )

    def _download_invoices(
        self, invoices_list: List[dict], customer_numbers_dict: dict
    ) -> List[DiscoveredFile]:
        """
        Downloads the Invoices
        :return: Returns the list of the Discovered Files
        """

        LOGGER.info("Download invoice process begins.")
        discovered_files_list = self.get_discovered_files(
            self.run, invoices_list, customer_numbers_dict
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
            document_number = discovered_file.original_download_url

            _downloader = DriverBasedApiDownloader(
                pdf_byte_content=self.api_client.get_pdf(
                    self.access_token, document_number
                ),
                local_filepath=os.path.join(self.download_location, "Billing.pdf"),
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
        discovered_files = []
        try:
            duke_access_token = self._login()
            self.access_token = self.api_client.get_token()

            user_id, customer_number = self.api_client.get_user_id(duke_access_token)

            portfolio_id = self.api_client.get_portfolio_id(
                self.access_token, user_id, customer_number
            )

            customer_numbers_dict = self.api_client.get_customer_numbers_list(
                portfolio_id, customer_number, self.run.job.username, self.access_token
            )
            LOGGER.info(f"Found accounts: {customer_numbers_dict}")

            invoices_history_list = self.api_client.get_invoice_history(
                list(customer_numbers_dict.keys()),
                self.run.job.username,
                self.access_token,
            )

            discovered_files += self._download_documents(
                invoices_history_list, customer_numbers_dict
            )

        finally:
            self._quit_driver()

        return discovered_files

    def login_flow(self, run: Run):
        self._login()


class DriverBasedApiDownloader(BaseDownloader):
    """
    Simple Selenium downloader implementation that downloads using a byte content, with built-in retries.
    Provides optional functionality to rename the downloaded file if desired.
    """

    def __init__(self, pdf_byte_content, **kwargs):
        super().__init__(**kwargs)
        self.pdf_byte_content = pdf_byte_content

    def _perform_download_action(self):
        """Perform the download action"""
        with open(self.local_filepath, "wb") as file:
            file.write(self.pdf_byte_content)
