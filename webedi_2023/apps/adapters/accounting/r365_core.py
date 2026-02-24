import logging
from urllib.parse import quote_plus

import requests
from spices.django3.conf import LOCAL_ENV
from spices.http_utils import make_retryable_session
from spices.services import ContextualError

from apps.error_codes import ErrorCode

LOGGER = logging.getLogger("apps.adapters.accounting")


class R365CoreClient:
    """
    Client interface for R365 APIs
    """

    def __init__(self, r365_api_base_url: str):
        self._base_url = r365_api_base_url.rstrip("/")

        # ok to make everything retryable on 5xx
        self._session = make_retryable_session(
            requests.Session(), backoff_factor=2, raise_on_status=False
        )
        self._headers = {
            "Content-Type": "application/json",
            "Accept": "application/json, text/plain, */*",
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_14_3) AppleWebKit/537.36 (KHTML, like Gecko)",
        }

        # save checkrun_id here for logging context
        self.ctx = ""

    def set_context(self, checkrun_id: str):
        self.ctx = f"[cr:{checkrun_id}]"

    def reset_context(self):
        self.ctx = ""

    def get_auth_credentials(self, username: str, password: str):
        """
        R365 Auth Credentials API
        Use this API to Login into R365
        """
        api_url = "/".join([self._base_url, "ServiceStack/auth/credentials"])
        params = {"isFromWeb": "true"}
        payload = {"UserName": username, "Password": password}

        # LOGGER.debug(f'[tag:WEWARAC1] Adding Accounting Bank Account from url={api_url} using payload={payload}')
        response = self._session.post(
            api_url, json=payload, headers=self._headers, params=params
        )
        if response.ok:
            LOGGER.info(f"Response: {response.text}")
            return response.json()["SessionId"]

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

    def get_session_data(self, session_id: str):
        """
        R365 Session Data API
        Basically to fetch the User session data like UserID, AccessRights, UserRole etc
        """
        api_url = "/".join([self._base_url, "ServiceStack/SessionData", session_id])

        LOGGER.info(f"[tag:WEWARSD1] Fetch user session data from url={api_url}")

        response = self._session.get(api_url, headers=self._headers)
        if response.ok:
            LOGGER.info(f"Response: {response.text}")
            return response.json()["userId"]

        raise Exception(
            f"[tag:WEWARSD2] Failed fetching session data!"
            f"with HTTP {response.status_code} (url={api_url},response_body={response.text})"
        )

    def get_saved_view(self, user_id: str, input_list: str):
        """
        R365 Get Saved View API
        Use this API to fetch saved views like 'Vendors', 'Bank Accounts' for a user
        """
        api_url = "/".join([self._base_url, "ServiceStack/GetSavedViews"])
        payload = {"userID": user_id, "list": input_list}
        return self._fetch_response_body("get_saved_views", api_url, payload)

    @staticmethod
    def prepare_filter_text(filter_text):
        return quote_plus(filter_text)

    @classmethod
    def _prepare_grid_source_text(
        cls,
        grid_name: str,
        user_id: str,
        count: int = 250,
        order_by: str = None,
        filters: str = None,
    ):
        text = ""
        text += "%24inlinecount=allpages&"
        text += "%24format=json&"
        text += f"gridName={grid_name}&"
        text += f"userID={user_id}&"
        text += f"%24top={count}&"
        if order_by:
            text += f"%24orderby={order_by}&"
        if filters:
            text += f"%24filter={filters}"
        return text

    def get_grid_source_request(
        self, login_type: str = "0", order_by: str = "1", **kwargs
    ):
        """
        R365 Grid Source Request API
        Use this API to fetch details like 'Vendors', 'Bank Accounts' for a user
        """
        grid_name = kwargs["grid_name"]
        text = self._prepare_grid_source_text(
            grid_name=grid_name,
            user_id=kwargs["user_id"],
            count=kwargs["count"],
            order_by=order_by,
            filters=kwargs["filters"],
        )
        api_url = "/".join([self._base_url, "ServiceStack/GridSourceRequest"])
        payload = {
            "text": text,
            "isEmployee": kwargs["is_employee"],
            "LoginType": login_type,
            "isGridActionRefresh": False,
        }
        return self._fetch_response_body(f"ggsr:{grid_name}", api_url, payload)[
            "results"
        ]

    def get_grid_source_request_v1(self, **kwargs):
        """
        R365 Grid Source Request API
        Use this API to fetch details like 'Vendors', 'Bank Accounts' for a user
        """
        text = kwargs.get("text", None)
        api_url = "/".join([self._base_url, "ServiceStack/GridSourceRequest"])
        payload = {
            "text": text,
            "isEmployee": kwargs.get("is_employee", 0),
            "LoginType": kwargs.get("login_type", 0),
            "isGridActionRefresh": kwargs.get("isGridActionRefresh", False),
        }
        return self._fetch_response_body(f"ggsr:", api_url, payload)["results"]

    def save_transaction(self, **kwargs):
        """Save & Approves payment - Final step for payment export"""
        api_url = "/".join([self._base_url, "ServiceStack/SaveTransaction"])
        payload = {
            "userId": kwargs["user_id"],
            "transaction": kwargs["transaction"],
            "transactionDetails": kwargs["transaction_details"],
            "applyRecords": kwargs["apply_records"],
            "action": kwargs["action"],
            "attachmentFileParameters": None,
            "isNew": False,
            "PurchaseOrderId": "",
        }

        if LOCAL_ENV:
            raise PermissionError("Not allowed in local environment")

        return self._fetch_response_body("save_transaction", api_url, payload)

    def approve_txn(self, **kwargs):
        """Approves txn"""
        api_url = "/".join([self._base_url, "ServiceStack/Transaction/Approve"])
        payload = {
            "transactions": kwargs["transactions"],
            "transactionType": kwargs["transactionType"],
            "autoCreatePayment": kwargs["autoCreatePayment"],
        }

        if LOCAL_ENV:
            raise PermissionError("Not allowed in local environment")

        return self._fetch_response_body("approve_txn", api_url, payload)

    def get_checking_bank_accounts(self, **kwargs):
        """Get Checking Bank Accounts"""
        api_url = "/".join([self._base_url, "ServiceStack/CheckingBankAccounts"])
        payload = {
            "location": kwargs["location"],
            "accountId": kwargs["account_id"],
            "userId": kwargs["user_id"],
            "transactionId": kwargs["transaction_id"],
        }
        return self._fetch_response_body("get_checking_bank_accounts", api_url, payload)

    def get_grid_source_vendor_cc(self, **kwargs):
        """
        Get Vendor Details
        """
        text = self._prepare_grid_source_text(
            grid_name=kwargs["grid_name"],
            user_id=kwargs["user_id"],
            filters=kwargs["filters"],
        )
        api_url = "/".join([self._base_url, "ServiceStack/GetGridSourceVendorCC"])
        payload = {
            "Text": text,
            "Locations": kwargs["location_ids"],
            "VendorId": kwargs["vendor_id"],
            "transactionType": kwargs["transaction_type"],
        }
        return self._fetch_response_body("get_grid_source_vendor_cc", api_url, payload)

    def get_locations(self, **kwargs):
        """Get Location Details"""
        api_url = "/".join([self._base_url, "ServiceStack/GetLocations"])
        payload = {
            "glAccountId": kwargs["gl_account_id"],
            "transactionType": kwargs["transaction_type"],
            "userId": kwargs["user_id"],
        }
        return self._fetch_response_body("get_locations", api_url, payload)

    def get_locations_all(self):
        """Get All Location"""
        api_url = "/".join([self._base_url, "ServiceStack/LocationsAll"])
        LOGGER.info(f"[tag:WEWARSD1] Fetch All locations from url={api_url}")

        response = self._session.get(api_url, headers=self._headers)
        if response.ok:
            LOGGER.info(f"Response: {response.text}")
            return response.json()

        raise Exception(
            f"[tag:WEWARSD2] Failed fetching all locations!"
            f"with HTTP {response.status_code} (url={api_url},response_body={response.text})"
        )

    def get_transaction_apply_records(self, **kwargs):
        """
        Get Transaction Apply Records
        """
        api_url = "/".join([self._base_url, "ServiceStack/GetTransactionApplyRecords"])
        payload = {
            "company": kwargs["company"],
            "transactionId": kwargs["transaction_id"],
            "trxType": kwargs["trx_type"],
            "location": kwargs["location"],
        }
        return self._fetch_response_body(
            "get_transaction_apply_records", api_url, payload
        )

    def get_transaction(self, **kwargs):
        """Get Transaction"""
        api_url = "/".join([self._base_url, "ServiceStack/GetTransaction"])
        payload = {"transactionId": kwargs["transaction_id"]}
        return self._fetch_response_body("get_transaction", api_url, payload)

    def get_transaction_details(self, **kwargs):
        """Get Transaction details"""
        api_url = "/".join([self._base_url, "ServiceStack/GetTransactionDetails"])
        payload = {"transactionId": kwargs["transaction_id"]}
        return self._fetch_response_body("get_transaction_details", api_url, payload)

    def detect_checking_account_duplicate_number(self, **kwargs):
        """Detect Duplicate Checking Account Number"""
        api_url = "/".join(
            [self._base_url, "ServiceStack/DetectCheckingAccountDuplicateNumber"]
        )
        payload = {
            "userId": kwargs["user_id"],
            "startCheckNumber": kwargs["start_check_number"],
            "checkingAccountId": kwargs["checking_account_id"],
            "transactionId": kwargs["transaction_id"],
        }
        return self._fetch_response_body(
            "detect_duplicate_checking_account_number", api_url, payload
        )

    def _fetch_response_body(
        self, operation: str, request_url: str, request_body: dict, **request_kwargs
    ):
        LOGGER.info(
            f"[tag:WEAR365ARRB10]{self.ctx}[{operation}]: Making request"
            f" (url:{request_url}, other: {request_kwargs}, body: {request_body})"
        )

        request_kwargs.setdefault("headers", self._headers)
        response = self._session.post(request_url, json=request_body, **request_kwargs)

        return self._return_response_body(
            operation, request_url, request_body, response
        )

    def _validate_successful_response(
        self,
        operation: str,
        request_url: str,
        request_body: dict,
        response: requests.Response,
    ):
        if operation in ["save_transaction"]:
            result = response.json()[0]
            if result[0] == "1":
                LOGGER.info(
                    f"[tag:WEAR365AVSR25]{self.ctx}[{operation}]:"
                    f" Transaction saved: {result[1]}"
                )
            else:
                raise ContextualError(
                    code=ErrorCode.PE_RESPONSE_VALIDATION_FAILED.ident,  # pylint: disable=no-member
                    message=ErrorCode.PE_RESPONSE_VALIDATION_FAILED.message.format(
                        error_message=result[1]
                    ),  # pylint: disable=no-member
                    params={
                        "request_url": request_url,
                        "request_body": request_body,
                        "response_body": response.text,
                    },
                )

    def _return_response_body(
        self,
        operation: str,
        request_url: str,
        request_body: dict,
        response: requests.Response,
    ):
        LOGGER.info(
            f"[tag:WEAR365ARRB20]{self.ctx}[{operation}]:"
            f" Request to url:{request_url} returned a {response.status_code} response"
            f" (Response: {response.text}, Request: {request_body})"
        )

        if response.ok:
            self._validate_successful_response(
                operation, request_url, request_body, response
            )
            return response.json()

        if response.status_code >= 500:
            raise ContextualError(
                code=ErrorCode.EXTERNAL_UPSTREAM_UNAVAILABLE.ident,  # pylint: disable=no-member
                message=ErrorCode.EXTERNAL_UPSTREAM_UNAVAILABLE.message,  # pylint: disable=no-member
                params={
                    "request_url": request_url,
                    "request_body": request_body,
                    "response_body": response.text,
                },
            )

        raise Exception(
            f"[tag:WEAR365ARRB30]{self.ctx}[{operation}] "
            f"Operation failed with HTTP {response.status_code}"
        )
