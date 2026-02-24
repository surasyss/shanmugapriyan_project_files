import os
import re
import requests

from datetime import date, timedelta
from typing import List

from spices import datetime_utils
from spices.datetime_utils import date_from_string
from spices.http_utils import make_retryable_session
from spices.services import ContextualError

from apps.adapters.base import VendorDocumentDownloadInterface
from apps.adapters.framework import download
from apps.adapters.helpers.helper import sleep
from apps.adapters.helpers.webdriver_helper import get_url, wait_for_element
from apps.adapters.vendors import LOGGER
from apps.error_codes import ErrorCode
from apps.runs.models import Run, DiscoveredFile, DocumentType, FileFormat


class EdwardDonClient:
    """
    Client interface for Edward Don APIs
    """

    def __init__(self, api_base_url: str):
        self._base_url = api_base_url.rstrip("/")

        # ok to make everything retryable on 5xx
        self.session = make_retryable_session(
            requests.Session(), backoff_factor=2, raise_on_status=False
        )
        self._headers = {
            "Content-Type": "application/x-www-form-urlencoded",
            "Accept": "application/json, text/plain, */*",
            "Authorization": "Basic aXNjOjAwOUFDNDc2LUIyOEUtNEUzMy04QkFFLUI1RjEwM0ExNDJCQw==",
            "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/96.0.4664.45 "
            "Safari/537.36",
        }

    def login(self, username: str, password: str):
        """
        Auth API to login into Edward Don
        """
        api_url = "https://www.don.com/identity/connect/token"
        payload = {
            "grant_type": "password",
            "username": username,
            "password": password,
            "scope": "iscapi",
        }

        response = self.session.post(api_url, data=payload, headers=self._headers)
        if response.ok:
            LOGGER.info(f"Response: {response.text}")
            response_json = response.json()
            access_token = (
                response_json["token_type"] + " " + response_json["access_token"]
            )
            self._headers.update(
                {
                    "Authorization": access_token,
                    "Content-Type": "application/json;charset=UTF-8",
                }
            )
            api_url = "https://www.don.com/api/v1/sessions"
            session_payload = {"userName": username, "password": password}
            response = self.session.post(
                api_url, json=session_payload, headers=self._headers
            )
            if response.ok:
                LOGGER.info(f"Response: {response.text}")
                response_json = response.json()

                general_customer = response_json.get("generalCustomer")
                if general_customer:
                    setattr(self, "single_customer_id", general_customer.get("id"))

                return response.status_code

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

    def get_accounts_list(self):
        """
        Edward Don api to fetch accounts list
        """
        api_url = "https://www.don.com/api/don/corporate/searchlocations"
        LOGGER.info(f"[tag:WEWARSD1] Fetch accounts list from url={api_url}")
        payload = {
            "pagination": {
                "currentPage": 1,
                "defaultPageSize": 15,
                "pageSize": 15,
                "sortType": "2,0",
            }
        }

        response = self.session.post(api_url, json=payload, headers=self._headers)
        if response.ok:
            LOGGER.info(f"Response: {response.text}")
            return response.json().get("searchResults")

        raise Exception(
            f"[tag:WEWARSD2] Failed fetching accounts list data!"
            f"with HTTP {response.status_code} (url={api_url},response_body={response.text})"
        )

    def get_unit_customer_id(self, account_number):
        """
        Edward Don api to fetch unit customer id for an account
        """
        headers = {
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,"
            "image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.9",
            "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/96.0.4664.45 Safari/537.36",
        }
        account_url = f"https://www.don.com/corporate/locations/billinginformation/{account_number}"
        response = self.session.get(account_url, headers=headers)
        if response.ok:
            response_text = response.text
            unit_customer_id = re.findall(
                r'id\s*=\s*"unitCustomerId".+?value\s*=\s*"([\w-]+)"', response_text
            )[0]
            LOGGER.info(f"Unit customer id: {unit_customer_id}")
            return unit_customer_id

        LOGGER.info(
            f"[tag:WEWARSD2] Failed fetching unit customer id for account!"
            f"with HTTP {response.status_code} (url={account_url})"
        )

    def get_periods_for_account(self, unit_customer_id=None):
        """
        Edward Don api to fetch periods list for an account
        """
        api_url = "https://www.don.com/api/don/manageorders/billinginfo"

        if unit_customer_id:
            api_url = f"https://www.don.com/api/don/corporate/billinginfo?unitCustomerId={unit_customer_id}"

        LOGGER.info(
            f"[tag:WEWARSD1] Fetch periods data for an account from url={api_url}"
        )

        response = self.session.get(api_url, headers=self._headers)
        if response.ok:
            LOGGER.info(f"Response: {response.text}")
            response_json = response.json()
            return response_json.get("billingPeriods") or response_json.get(
                "billingInfo"
            ).get("billingPeriods")

        raise Exception(
            f"[tag:WEWARSD2] Failed fetching periods details for account data!"
            f"with HTTP {response.status_code} (url={api_url},response_body={response.text})"
        )

    def get_invoices_for_single_account(self):
        """
        Edward Don api to fetch invoices list for single account
        """

        unit_customer_id = getattr(self, "single_customer_id")

        api_url = f"https://www.don.com/api/don/manageorders/recent?customerId={unit_customer_id}"

        LOGGER.info(f"[tag:WEWARSD1] Fetch invoices from url={api_url}")

        response = self.session.get(api_url, headers=self._headers)
        if response.ok:
            LOGGER.info(f"Response: {response.text}")
            response_json = response.json()
            return response_json.get("recentOrders")

        raise Exception(
            f"[tag:WEWARSD2] Failed fetching periods details for account data!"
            f"with HTTP {response.status_code} (url={api_url},response_body={response.text})"
        )

    def get_invoices_for_period(self, bucket_name: str, unit_customer_id=None):
        """
        Edward Don api to fetch invoices list for a period
        """
        api_url = (
            f"https://www.don.com/api/don/manageorders/invoices?bucketName={bucket_name}"
            f"&currentPage=1&pageSize=30&sortType=2,1"
        )

        if unit_customer_id:
            api_url = (
                f"https://www.don.com/api/don/corporate/invoices?bucketName={bucket_name}&"
                f"currentPage=1&pageSize=30&sortType=2,1&unitCustomerId={unit_customer_id}"
            )

        LOGGER.info(
            f"[tag:WEWARSD1] Fetch invoice details data for period {bucket_name} from url={api_url}"
        )

        response = self.session.get(api_url, headers=self._headers)
        if response.ok:
            LOGGER.info(f"Response: {response.text}")
            return response.json().get("invoices")

        raise Exception(
            f"[tag:WEWARSD2] Failed fetching invoices details for period {bucket_name}!"
            f"with HTTP {response.status_code} (url={api_url},response_body={response.text})"
        )


class EdwardDonRunner(VendorDocumentDownloadInterface):
    """Runner Class for Edward Don"""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.access_token = None
        self.company_id = None
        self.api_client = EdwardDonClient("https://www.don.com/api")
        get_url(self.driver, "https://www.don.com/")

    def _login(self):
        """
        Login to Edward Don
        :return: Nothing
        """
        self.api_client.login(self.run.job.username, self.run.job.password)

    def get_accounts(self):
        """
        Get all accounts detail
        """
        accounts_list = self.api_client.get_accounts_list()
        total_accounts = []

        for account in accounts_list:
            account_detail = {
                "account_number": account.get("customerNumber"),
                "restaurant_name": account.get("name"),
            }
            total_accounts.append(account_detail)
        return total_accounts

    def get_invoices_list(self, periods: List, unit_customer_id):
        """
        Get invoices for all periods
        """
        invoices_for_all_periods = []
        for period in periods:
            LOGGER.info(f"Getting invoices for period {period}")

            if int(period.get("invoiceCount")) > 0:
                bucket_name = period.get("name")
                invoices = self.api_client.get_invoices_for_period(
                    bucket_name, unit_customer_id=unit_customer_id
                )
                invoices_for_all_periods.extend(invoices)
        return invoices_for_all_periods

    def get_discovered_files(
        self, run: Run, account: dict, invoices: List
    ) -> List[DiscoveredFile]:
        """
        :param run: run for Job jobconfig
        :param account: Account detail dict
        :param invoices: List of invoices
        :return: list of discovered files
        """
        discovered_files = []
        for invoice in invoices:
            start_date = self._get_start_invoice_date()
            end_date = self._get_end_invoice_date()

            invoice_date_str = (
                invoice.get("invoiceDate") or invoice.get("orderDate").split()[0]
            )
            invoice_date = date_from_string(invoice_date_str, "%m/%d/%Y")

            if not start_date <= invoice_date <= end_date:
                LOGGER.info(
                    f"Skipping invoice because date '{invoice_date}' is outside requested range"
                )
                continue

            account_number = account.get("account_number")
            invoice_number = invoice.get("invoiceNumber") or invoice.get("orderNumber")
            reference_code = f"{account_number}_{invoice_number}_{invoice_date}"

            document_properties = {
                "invoice_number": invoice_number,
                "invoice_date": str(invoice_date),
                "total_amount": invoice.get("invoiceAmountDisplay")
                or invoice.get("orderTotalDisplay"),
                "vendor_name": "Edward Don and Company",
                "restaurant_name": account.get("restaurant_name"),
                "account_number": account_number,
            }
            try:
                # pylint: disable=no-member
                discovered_file = DiscoveredFile.build_unique(
                    run,
                    reference_code,
                    document_type=DocumentType.INVOICE.ident,
                    file_format=FileFormat.PDF.ident,
                    original_download_url=invoice.get("invoiceDetailUrl")
                    or invoice.get("orderDetailUrl"),
                    original_filename=f"{reference_code}.pdf",
                    document_properties=document_properties,
                )
            except DiscoveredFile.AlreadyExists:
                LOGGER.info(
                    f"Discovered file already exists with reference code : {reference_code}"
                )
                continue

            discovered_files.append(discovered_file)
            self.download_invoice_by_cdp_command(discovered_file)

            LOGGER.info("Invoice details: %s", str(discovered_file.document_properties))

        return discovered_files

    def _download_documents(self, account, invoices: List) -> List[DiscoveredFile]:
        """
        Chooses the documents to be downloaded based on the document type
        :return: Returns the list of Discovered Files
        """
        document_type = self.run.job.requested_document_type
        if document_type == "invoice":
            return self._download_invoices(account, invoices)

        raise NotImplementedError(
            f"Requested Document Type is not supported: {document_type}"
        )

    def _download_invoices(self, account, invoices: List) -> List[DiscoveredFile]:
        """
        Downloads the Invoices
        :return: Returns the list of the Discovered Files
        """

        LOGGER.info("Download invoice process begins.")

        discovered_files_list = self.get_discovered_files(self.run, account, invoices)
        LOGGER.info(
            f"Total Invoices within date range and download link available: {len(discovered_files_list)}"
        )
        return discovered_files_list

    def add_cookies(self):
        """Add cookies from session to webdriver"""
        for key, value in self.api_client.session.cookies.items():
            self.driver.add_cookie(
                {"name": key, "value": value, "domain": "www.don.com"}
            )

    def remove_date_printed_element(self):
        """
        Removing Date printed webelement from the html since it changes everytime we download it
        & generate different content-hash resulting in duplicate invoices
        """
        self.driver.execute_script(
            """
            var elements = document.querySelectorAll("ul.inline-list li");
            for (const element of elements) {
                if (element.innerText.includes("Date printed:"))
                    element.parentNode.removeChild(element);
            }
        """
        )

    def download_invoice_by_cdp_command(self, discovered_file: DiscoveredFile):
        """
        Download the html page in PDF format
        :param discovered_file: DiscoveredFile object
        """
        original_download_url = (
            "https://www.don.com"
            + discovered_file.original_download_url
            + "?printable=true"
        )
        get_url(self.driver, original_download_url)
        wait_for_element(
            self.driver,
            value="article#invoice-detail, article#order-detail",
            msg="Invoice Detail",
            retry_attempts=3,
        )
        sleep(5, msg="Wait for page load")
        self.remove_date_printed_element()
        _downloader = download.DriverExecuteCDPCmdBasedDownloader(
            self.driver,
            cmd="Page.printToPDF",
            cmd_args={"printBackground": True},
            local_filepath=os.path.join(self.download_location, "invoice.pdf"),
            rename_to=os.path.join(
                self.download_location,
                discovered_file.original_filename.replace("/", "_"),
            ),
            file_exists_check_kwargs=dict(timeout=30),
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
            discovered_files = []

            accounts = self.get_accounts()
            for account in accounts:
                LOGGER.info(
                    f'Found account: {account["account_number"]}: {account["restaurant_name"]}'
                )
                unit_customer_id = self.api_client.get_unit_customer_id(
                    account["account_number"]
                )

                try:
                    billing_periods = self.api_client.get_periods_for_account(
                        unit_customer_id=unit_customer_id
                    )
                    invoices = self.get_invoices_list(billing_periods, unit_customer_id)
                except Exception as excep:  # pylint: disable=broad-except
                    LOGGER.warning(excep)
                    invoices = self.api_client.get_invoices_for_single_account()

                self.add_cookies()
                discovered_files = self._download_documents(account, invoices)
        finally:
            self._quit_driver()

        return discovered_files

    def login_flow(self, run: Run):
        self._login()
