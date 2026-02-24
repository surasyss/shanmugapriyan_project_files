import copy
import logging
from typing import Optional, List

import requests
import retry
from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.exceptions import PermissionDenied
from rest_framework import status

from spices.http_utils import get_new_retryable_session_500
from spices.services import ServiceError

LOGGER = logging.getLogger("apps.utils")


class PIQCoreClient:  # pylint: disable=too-many-public-methods
    """
    Client interface fo Plate IQ server APIs
    """

    def __init__(self, piq_api_base_url: str, piq_api_token: str):
        self._base_url = piq_api_base_url.rstrip("/")
        self._token = f"Token {piq_api_token}"
        self._headers = {
            "Authorization": self._token,
            "Content-Type": "application/json",
            "Accept": "application/json, text/plain, */*",
        }

    def get_s3_signed_url(self, query_params: dict) -> Optional[dict]:
        url = "/".join([self._base_url, "invoice/s3sign/"])
        LOGGER.info(
            f"[tag:WEWUPCGSS1] Fetching signed URLs from url={url} using params={query_params}"
        )

        response = get_new_retryable_session_500().get(
            url,
            params=query_params,
            headers={
                "X-TRUST-IMAGE-NAME-UNIQUE": "True",
                "Authorization": self._token,
            },
        )

        if not response.ok:
            LOGGER.info(
                f"[tag:WEWUPCGSS2] Fetching signed URLs from url={url} failed with "
                f"HTTP {response.status_code}, body: {response.text}"
            )
            return None

        LOGGER.info(f"[tag:WEWUPCGSS3] API response: {response.text}")
        return response.json()

    def create_invoice(self, payload: dict) -> Optional[dict]:
        api_url = "/".join([self._base_url, "invoice/"])

        LOGGER.info(
            f"[tag:WEWUPCCI1] Creating invoice container from url={api_url} using payload={payload}"
        )

        response = get_new_retryable_session_500().post(
            api_url, json=payload, headers={"Authorization": self._token}
        )
        if response.ok:
            LOGGER.info(f"[tag:WEWUPCCI2] API response: {response.text}")
            return response.json()

        if response.status_code == 409:
            LOGGER.info(
                f'[tag:WEWUPCCI3] Got 409, container already exists for image={payload["image"]}, '
                f"response_body={response.text}"
            )
            # Retrieve the Invoice and send #
            return {}

        raise Exception(
            f'[tag:WEWUPCCI4] Failed creating container for image={payload["image"]} '
            f"with HTTP {response.status_code} (url={api_url},request_payload={payload},response_body={response.text})"
        )

    def get_invoice_container_admin_url(self, container_id: str):
        return "/".join([self._base_url, "admin/invoices/container", container_id])

    @property
    def billpay_export_api_url(self):
        return "/".join([self._base_url, "billpay/export/"])

    def billpay_export_dry_run(self, restaurant: int, dry_run: bool = True):
        api_url = self.billpay_export_api_url
        payload = {
            "dry_run": dry_run,
            "restaurant": restaurant,
            "skip_canceled": True,
            "skip_flagged": True,
        }

        LOGGER.info(
            f"[tag:WEWUPCBED1] Getting Bill Pay Checks from url={api_url} using payload={payload}"
        )

        response = get_new_retryable_session_500().post(
            api_url, json=payload, headers=self._headers
        )
        if response.ok:
            LOGGER.info(f"[tag:WEWUPCBED2] API response: {response.text}")
            return response.json()

        if response.status_code == 404:
            LOGGER.warning(
                f"Status: {response.status_code}, Response: {response.json()}"
            )
            return None

        raise Exception(
            f"[tag:WEWUPCBED3] Failed retrieving Bill Pay Checks "
            f"with HTTP {response.status_code} (url={api_url},request_payload={payload},response_body={response.text})"
        )

    def billpay_export_patch(self, cheques: list):
        api_url = self.billpay_export_api_url
        payload = {
            "cheques": cheques,
        }

        LOGGER.info(
            f"[tag:WEWUPCBEP1] Updating Bill Pay Check as Exported from url={api_url} using payload={payload}"
        )

        response = get_new_retryable_session_500().post(
            api_url, json=payload, headers=self._headers
        )
        if response.ok:
            LOGGER.info(f"[tag:WEWUPCBEP2] API response: {response.text}")
            return response.json()

        LOGGER.info(
            f"[tag:WEWUPCBEP3] Failed marking Bill Pay check as Exported for cheques={cheques}"
            f"with HTTP {response.status_code} (url={api_url},request_payload={payload},"
            f"response_body={response.text})"
        )
        return None

    @property
    def accounting_bank_account_api_url(self):
        return "/".join([self._base_url, "accounting/bank_account/"])

    def get_accounting_bank_account(self, restaurant: int, page: int = 1):
        """Get Accounting Bank Account"""

        api_url = self.accounting_bank_account_api_url
        params = {"restaurant": restaurant, "page": page}

        LOGGER.info(
            f"[tag:WEWUPCGABC1] Get Accounting Bank Account from url={api_url}, restaurant={restaurant}"
        )

        response = get_new_retryable_session_500().get(
            api_url, headers=self._headers, params=params
        )
        if response.ok:
            LOGGER.info(f"[tag:WEWUPCGABC2] API response: {response.text}")
            return response.json()

        raise Exception(
            f"[tag:WEWUPCGABC3] Failed getting Bank Accounts"
            f"with HTTP {response.status_code} (url={api_url},response_body={response.text})"
        )

    def post_accounting_bank_account(
        self,
        location_id: int,
        account_number: str,
        account_name: str,
        accounting_sw_id: str,
        bank_account_type: int,
    ):
        """Add Accounting Bank Account"""

        api_url = self.accounting_bank_account_api_url
        payload = {
            "restaurant": location_id,
            "account_number": account_number,
            "account_name": account_name,
            "accounting_sw_id": accounting_sw_id,
            "bank_account_type": bank_account_type,
        }

        LOGGER.info(
            f"[tag:WEWUPCPABC1] Adding Accounting Bank Account from url={api_url} using payload={payload}"
        )

        try:
            response = get_new_retryable_session_500().post(
                api_url, json=payload, headers=self._headers
            )
            LOGGER.info(
                f"[tag:WEWUPCPABC3] API response_code:{response.status_code} - response_body: {response.text}"
            )
            return response

        except Exception:  # pylint: disable=broad-except
            return {
                "url": api_url,
                "request": {"method": "POST", "body": payload},
                "status_code": response.status_code,
                "text": response.text,
            }

    def patch_accounting_bank_account(self, patch_id: int, **kwargs):
        """Update Accounting Bank Account"""

        api_url = self.accounting_bank_account_api_url + f"{patch_id}/"
        payload = kwargs

        LOGGER.info(
            f"[tag:WEWUPCPABC4] Updating Accounting Bank Account from url={api_url} using payload={payload}"
        )

        try:
            response = get_new_retryable_session_500().patch(
                api_url, json=payload, headers=self._headers
            )
            LOGGER.info(
                f"[tag:WEWUPCPABC5] API response_code:{response.status_code} - response_body: {response.text}"
            )
            return response

        except Exception:  # pylint: disable=broad-except
            return {
                "url": api_url,
                "request": {"method": "POST", "body": payload},
                "status_code": response.status_code,
                "text": response.text,
            }

    @property
    def restaurant_api_url(self):
        return "/".join([self._base_url, f"restaurant/"])

    def get_restaurant_by_id(self, location_id: int):
        """Get Restaurant Details by Restaurant ID"""

        api_url = self.restaurant_api_url + f"{location_id}/"

        LOGGER.info(f"[tag:WEWUPCGRI1] Get Restaurant Details from url={api_url}")

        response = get_new_retryable_session_500().get(api_url, headers=self._headers)
        if response.ok:
            LOGGER.info(f"[tag:WEWUPCGRI2] API response: {response.text}")
            return response.json()

        raise Exception(
            f"[tag:WEWUPCGRI3] Failed getting Restaurant Details"
            f"with HTTP {response.status_code} (url={api_url},response_body={response.text})"
        )

    @property
    def accounting_company_api_url(self):
        return "/".join([self._base_url, f"accounting/company/"])

    def get_accounting_company_by_id(self, company_id: int):
        """
        Get Company Details by Company ID
        """

        api_url = self.accounting_company_api_url + f"{company_id}/"

        LOGGER.info(f"[tag:WEWUPCGACI1] Get Company Details from url={api_url}")

        response = get_new_retryable_session_500().get(api_url, headers=self._headers)
        if response.ok:
            LOGGER.info(f"[tag:WEWUPCGACI2] API response: {response.text}")
            return response.json()

        raise Exception(
            f"[tag:WEWUPCGACI3] Failed getting Company Details"
            f"with HTTP {response.status_code} (url={api_url},response_body={response.text})"
        )

    @property
    def accounting_vendor_api_url(self):
        return "/".join([self._base_url, "accounting/vendor/"])

    def get_accounting_vendor(self, company: int):
        """Get Accounting Vendor"""

        api_url = self.accounting_vendor_api_url
        params = {"company": company}

        LOGGER.info(
            f"[tag:WEWUPCGAV1] Get Vendor from url={api_url}, company={company}"
        )

        response = get_new_retryable_session_500().get(
            api_url, headers=self._headers, params=params
        )
        if response.ok:
            LOGGER.info(f"[tag:WEWUPCGAV2] API response: {response.text}")
            return response.json()

        raise Exception(
            f"[tag:WEWUPCGAV3] Failed getting Accounting Vendors"
            f"with HTTP {response.status_code} (url={api_url},response_body={response.text})"
        )

    @property
    def rest_sub_account_api_url(self):
        return "/".join([self._base_url, "accounting/restaurant_sub_account/"])

    def get_rest_sub_account(self, company=None, restaurant=None, page: int = 1):
        """Get Accounting Restaurant Sub Account"""

        api_url = self.rest_sub_account_api_url
        params = {"restaurant": restaurant, "company": company, "page": page}

        LOGGER.info(
            f"[tag:WEWUPCGARSA1] Get Accounting Restaurant Sub Account from url={api_url}, params={params}"
        )

        response = get_new_retryable_session_500().get(
            api_url, headers=self._headers, params=params
        )
        if response.ok:
            LOGGER.info(f"[tag:WEWUPCGARSA2] API response: {response.text}")
            return response.json()

        raise Exception(
            f"[tag:WEWUPCGARSA3] Failed getting Accounting Restaurant Sub Accounts"
            f"with HTTP {response.status_code} (url={api_url},response_body={response.text})"
        )

    def patch_rest_sub_account(self, patch_id: int, **kwargs):
        """Update Accounting Restaurant Sub Account"""

        api_url = self.rest_sub_account_api_url + f"{patch_id}/"
        payload = kwargs

        LOGGER.info(
            f"[tag:WEWUPCPARSA1] Patching Accounting Restaurant Sub Account from url={api_url} "
            f"using payload={payload}"
        )

        try:
            response = get_new_retryable_session_500().patch(
                api_url, json=payload, headers=self._headers
            )
            LOGGER.info(
                f"[tag:WEWUPCPARSA2] API response_code:{response.status_code} - response_body: {response.text}"
            )
            return response

        except Exception:  # pylint: disable=broad-except
            return {
                "url": api_url,
                "request": {"method": "POST", "body": payload},
                "status_code": response.status_code,
                "text": response.text,
            }

    def post_rest_sub_account(
        self, account_number: str, account_name: str, company: int, **kwargs
    ):
        """Add New Accounting Restaurant Sub Account"""

        api_url = self.rest_sub_account_api_url
        payload = {
            "account_number": account_number,
            "account_name": account_name,
            "company": company,
        }
        payload.update(kwargs)

        LOGGER.info(
            f"[tag:WEWUPCPARSA1] Adding new Accounting Restaurant Sub Account from url={api_url} "
            f"using payload={payload}"
        )
        try:
            response = get_new_retryable_session_500().post(
                api_url, json=payload, headers=self._headers
            )
            LOGGER.info(
                f"[tag:WEWUPCPARSA2] API response_code:{response.status_code} - response_body: {response.text}"
            )
            return response

        except Exception:  # pylint: disable=broad-except
            return {
                "url": api_url,
                "request": {"method": "POST", "body": payload},
                "status_code": response.status_code,
                "text": response.text,
            }

    @property
    def billpay_cheque_api_url(self):
        return "/".join([self._base_url, f"billpay/cheque/"])

    def post_billpay_cheque_error(self, cheque_id: int, error: str):
        """Adds any error occured during BillPay"""

        api_url = self.billpay_cheque_api_url + f"{cheque_id}/error/"
        payload = {"error": error}

        LOGGER.info(
            f"[tag:WEWUPBPCE1] Adding BillPay Cheque Error from url={api_url} using payload={payload}"
        )

        response = get_new_retryable_session_500().post(
            api_url, json=payload, headers=self._headers
        )
        if response.ok:
            LOGGER.info(f"[tag:WEWUPBPCE2] API response: {response.text}")
            return response.json()

        raise Exception(
            f"[tag:WEWUPBPCE3] Failed Adding BillPay Cheque Error for cheque_id: {cheque_id} with HTTP "
            f"{response.status_code} (url={api_url},request_payload={payload},response_body={response.text})"
        )

    @property
    def acc_vendor_bulk_create_api_url(self):
        return "/".join([self._base_url, f"accounting/vendor/bulk_create/"])

    def post_acc_vendor_bulk_create(self, vendors: List[dict], company: int):
        """Adds/Updates/Delete Accounting Vendors in Bulk"""

        api_url = self.acc_vendor_bulk_create_api_url
        payload = {"vendors": vendors, "company": company}

        LOGGER.info(
            f"[tag:WEWUPAVBC1] Accounting Vendor Bulk Create from url={api_url} using payload={payload}"
        )

        try:
            response = get_new_retryable_session_500().post(
                api_url, json=payload, headers=self._headers
            )
            LOGGER.info(
                f"[tag:WEWUPAVBC2] API response_code:{response.status_code} - response_body: {response.text}"
            )
            return response

        except Exception:  # pylint: disable=broad-except
            return {
                "url": api_url,
                "request": {"method": "POST", "body": payload},
                "status_code": response.status_code,
                "text": response.text,
            }

    @property
    def get_rest_groups_url(self):
        return "/".join([self._base_url, f"restaurant_group_webedi/"])

    def get_accessible_location_groups_for(self, auth_header: str):
        """
        Get (json serialized) list of location groups accessible by current user (whose token is used for init)

        :param auth_header: auth header to pass along
        :param pagination_limit: Maximum number of pages to call
        """
        sess = get_new_retryable_session_500(raise_on_status=False)
        headers = copy.deepcopy(self._headers)
        headers["Authorization"] = auth_header

        url = self.get_rest_groups_url

        LOGGER.info(
            f"[tag:WEWUPCGRG10] Get Restaurant Groups for the user from url={url}"
        )
        response = sess.get(url=url, headers=headers)

        if not response.ok:
            raise ServiceError(
                http_status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                message=f"[tag:WEWUPCGRG20] Failed getting Restaurant Groups with HTTP {response.status_code}"
                f" (url={url}, response_body={response.text})",
            )

        LOGGER.info(f"[tag:WEWUPCGRG30] API response: {response.text}")
        json_response = response.json()

        LOGGER.debug(
            f"[tag:WEWUPCGRG30] Returning {len(json_response)} location groups accessible by user."
        )

        return json_response

    def get_accessible_account_ids_for(self, auth_header: str = None):
        """Get list of all account ids accessible by user token"""
        location_groups = self.get_accessible_location_groups_for(auth_header)
        return list(
            {lg["account"]["id"] for lg in location_groups if lg.get("account")}
        )


# noinspection PyProtectedMember
class PlateIQAuthenticationBackend:  # pylint: disable=protected-access,no-self-use
    """
    Django Authentication Backend that authenticates using the main PIQ database
    """

    only_allow_staff = True

    # noinspection PyMethodMayBeStatic
    def get_user(self, user_id):
        user_model_cls = get_user_model()
        try:
            return user_model_cls._default_manager.get(pk=user_id)
        except user_model_cls.DoesNotExist:
            return None

    def authenticate(self, request, username: str, password: str):
        serialized_user = None

        # try token auth first if applicable
        if username == password:
            serialized_user = self._get_serialized_piq_user_by_token_auth(
                token=username
            )

        # else try password remote auth
        if not serialized_user:
            serialized_user = self._get_serialized_piq_user_by_password_auth(
                username, password
            )

        return self._get_user_from_serialized_user(serialized_user)

    @staticmethod
    @retry.retry(Exception, tries=3, delay=0.1, max_delay=1, backoff=2, logger=LOGGER)
    def _get_serialized_piq_user_by_token_auth(token: str) -> Optional[dict]:
        response = requests.get(
            settings.PIQ_API_BASE_URL + "/user/me/",
            headers={"Authorization": f"Token {token}"},
        )
        return response.json() if response.ok else None

    @staticmethod
    @retry.retry(Exception, tries=3, delay=0.1, max_delay=1, backoff=2, logger=LOGGER)
    def _get_serialized_piq_user_by_password_auth(
        username: str, password: str
    ) -> Optional[dict]:
        response = requests.post(
            settings.PIQ_API_BASE_URL + "/auth/remote_auth/",
            json={"username": username, "password": password},
            headers={"Authorization": f"Token {settings.PIQ_API_TOKEN}"},
        )
        return response.json() if response.ok else None

    def _get_user_from_serialized_user(self, serialized_user: dict):
        if not serialized_user:
            raise PermissionDenied

        if self.only_allow_staff and not serialized_user["is_staff"]:
            raise PermissionDenied

        user_model_cls = get_user_model()
        try:
            return user_model_cls._default_manager.get_by_natural_key(
                serialized_user["username"]
            )
        except user_model_cls.DoesNotExist:
            user = user_model_cls._default_manager.create_user(
                username=serialized_user["username"],
                password=f"{serialized_user['username']}_{serialized_user['id']}",
            )
            user.first_name = serialized_user["first_name"]
            user.last_name = serialized_user["last_name"]
            user.email = serialized_user["username"]
            user.save()
            return user


class FakeRequest:
    def __init__(self, token: str):
        self.META = {  # pylint: disable=invalid-name
            "HTTP_AUTHORIZATION": f"Token {token}"
        }
