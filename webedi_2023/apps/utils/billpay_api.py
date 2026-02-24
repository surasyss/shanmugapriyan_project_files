import logging

from spices.http_utils import get_new_retryable_session_500

LOGGER = logging.getLogger("apps.utils")


class BillPayCoreClient:
    """
    Client interface for BillPay APIs
    """

    def __init__(self, bill_pay_api_base_url: str, bill_pay_api_token: str):
        self._base_url = f"{bill_pay_api_base_url}/api"
        self._token = bill_pay_api_token
        self._headers = {
            "Authorization": self._token,
            "Content-Type": "application/json",
            "Accept": "application/json, text/plain, */*",
        }

    def get_manual_payment_list(
        self, account_id=None, company_id=None, restaurant_id=None
    ):
        api_url = f"{self._base_url}/billpay_manual_payments/list_payments/"
        params = {"dashboard": "pending", "status": "Delivered"}
        if account_id:
            params["account_id"] = account_id
        if company_id:
            params["company_id"] = company_id
        if restaurant_id:
            params["restaurant_id"] = restaurant_id

        LOGGER.info(
            f"[tag:BPGMPL1] Get manual payments from url={api_url}, params={params}"
        )

        session = get_new_retryable_session_500(raise_on_status=False)
        response = session.get(api_url, params=params, headers=self._headers)
        if response.ok:
            LOGGER.info(f"[tag:BPGMPL2] API response: {response.text}")
            data = response.json()
            return data.get("results", None)
        raise Exception(
            f"[tag:BPGMPL3] Failed getting manual payments"
            f"with HTTP {response.status_code} (url={api_url},response_body={response.text})"
        )

    def update_notes_for_payment(self, billpay_payment_id: str, notes: str):
        api_url = f"{self._base_url}/billpay_manual_payments/{billpay_payment_id}/note/"
        data = {
            "note": notes,
        }
        LOGGER.info(
            f"[tag:BPUPS1] Update status of payment from url={api_url}, body={data}"
        )

        session = get_new_retryable_session_500(raise_on_status=False)
        response = session.patch(api_url, data=data, headers=self._headers)
        if response.ok:
            LOGGER.info(f"[tag:BPUPS2] API response: {response.text}")
            data = response.json()
            return data.get("results", None)
        raise Exception(
            f"[tag:BPUPS3] Failed updating status of payment"
            f"with HTTP {response.status_code} (url={api_url},response_body={response.text})"
        )

    def update_payment_status(self, billpay_payment_id: str):
        api_url = (
            f"{self._base_url}/billpay_manual_payments/{billpay_payment_id}/processed/"
        )
        LOGGER.info(f"[tag:BPUPS1] Update status of payment from url={api_url}")

        session = get_new_retryable_session_500(raise_on_status=False)
        response = session.patch(api_url, data={}, headers=self._headers)
        if response.ok:
            LOGGER.info(f"[tag:BPUPS2] API response: {response.text}")
            data = response.json()
            return data.get("results", None)
        raise Exception(
            f"[tag:BPUPS3] Failed updating status of payment"
            f"with HTTP {response.status_code} (url={api_url},response_body={response.text})"
        )
