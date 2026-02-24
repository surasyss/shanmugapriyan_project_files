import hashlib
import os
import shutil
import tempfile
import urllib.request

import requests
from django.conf import settings
from django.core.exceptions import ValidationError
from retry import retry

from apps.adapters import LOGGER
from apps.jobconfig.models import PIQMapping, FileDiscoveryActionType, EDIType
from apps.runs.models import DiscoveredFile


class DiscoveredFileActionBase:
    """Base class for actions that can be taken on"""

    def __init__(self, discovered_file: DiscoveredFile):
        self.discovered_file = discovered_file

    def execute(self):
        """Execute logic"""
        raise NotImplementedError


class DoNothingAction(DiscoveredFileActionBase):
    def execute(self):
        pass


class _RetryException(Exception):
    pass


class SkipProcessing(Exception):
    pass


class InvoiceStandardPIQUploadAction(DiscoveredFileActionBase):
    """Applicable for discovered invoices only. Feed into the Plate IQ system via the standard upload API"""

    upload_through = "webedi"
    is_edi = False

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.piq_url = None

    def _upload_to_s3(self):
        """
        Upload downloaded local file to S3. Returns True if operation completes successfully
        """
        if not settings.DISCOVERED_FILE_PIQ_API_SWITCH:
            LOGGER.warning(
                f"[DiscoveredFile:{self.discovered_file.id}] "
                f"DISCOVERED_FILE_PIQ_API_SWITCH is False, skipping S3 upload"
            )
            return False

        temp = None
        if (
            not self.discovered_file.local_filepath
        ):  # or not os.path.exists(self.discovered_file.local_filepath):
            if self.discovered_file.original_file:
                temp = self._populate_local_filepath()
            else:
                raise ValidationError(
                    f"[DiscoveredFile:{self.discovered_file.id}] "
                    f"Local file path not set, skipping processing"
                )

        try:
            signed_json = self._fetch_signed_s3_url()
            if not signed_json:
                raise ValidationError(
                    f"[DiscoveredFile:{self.discovered_file.id}] Could not get signed url, skipping"
                )

            put_request_url = signed_json["put_request"]
            headers = signed_json["headers"]

            uploaded = self._upload_to_signed_s3_url_internal(put_request_url, headers)
            if not uploaded:
                raise ValidationError(
                    f"[DiscoveredFile:{self.discovered_file.id}] Upload to S3 failed, skipping"
                )

            self.piq_url = signed_json["url"]
            self.discovered_file.piq_upload_id = signed_json["upload_id"]
            self.discovered_file.save()
        finally:
            if temp:
                temp.close()

        return True

    def _populate_local_filepath(self):
        temp = tempfile.NamedTemporaryFile()

        # Download the file from url and save it locally
        # Looks complicated, but recommended approach here: https://stackoverflow.com/a/7244263
        with urllib.request.urlopen(
            self.discovered_file.original_file.url
        ) as response, open(temp.name, "wb") as out_file:
            shutil.copyfileobj(response, out_file)

        self.discovered_file.local_filepath = temp.name
        return temp

    def _fetch_signed_s3_url(self) -> dict:
        """Fetch signed S3 URLs for discovered file upload"""
        df = self.discovered_file
        name, ext = os.path.splitext(
            df.original_filename or f"df-{df.id}.{df.file_format}"
        )
        ext = ext.replace(" ", "")
        display_name = name + ext

        unique_filename = f"{df.id}-{df.content_hash}"
        unique_filename = hashlib.sha1(unique_filename.encode()).hexdigest()
        unique_filename = unique_filename + ext

        signed_json = settings.PIQ_CORE_CLIENT.get_s3_signed_url(
            query_params={
                "filename": unique_filename,
                "display_name": display_name,
            }
        )

        return signed_json

    def _upload_to_signed_s3_url_internal(self, url: str, headers: dict):
        with open(self.discovered_file.local_filepath, "rb") as file_contents:
            try:
                return self._upload_to_signed_s3_url_with_retry(
                    url, headers=headers, data=file_contents
                )
                # try:
                #     return self._upload_to_signed_s3_url_with_retry(url, headers=headers, data=file_contents)
                # except UnicodeDecodeError:
                #     LOGGER.debug('Stripping file contents of unicode chars')
                #     file_contents = re.sub(r'[^\x00-\x7F]+', ' ', file_contents)
                #     return self._upload_to_signed_s3_url_internal(url, headers=headers, data=file_contents)

            except _RetryException:
                LOGGER.error(
                    f"upload for discovered file {self.discovered_file.id} failed despite multiple retries"
                )
        return None

    @staticmethod
    @retry(_RetryException, tries=5, delay=2, backoff=3, logger=LOGGER)
    def _upload_to_signed_s3_url_with_retry(url: str, headers: dict, data):
        put_response = requests.put(url, headers=headers, data=data)
        if put_response.ok:
            return put_response

        LOGGER.debug(
            f"upload attempt failed with HTTP {put_response.status_code}, (body: {put_response.text}"
        )
        raise _RetryException()

    def get_payload(self):
        job = self.discovered_file.run.job
        job_dict = {
            "id": job.id,
            "name": str(job),
            "create_missing_vendors": job.create_missing_vendors,
        }
        df = self.discovered_file
        account_id = df.run.job.account.remote_id
        location_group_id = (
            df.run.job.location_group and df.run.job.location_group.remote_id
        )

        # pylint: disable=no-member
        contains_support_document = (
            df.connector.connector_vendor.contains_support_document
        )

        return {
            "restaurant": self._fetch_location_id(),
            "restaurant_account": account_id,
            "restaurant_group": location_group_id,
            "upload_id": df.piq_upload_id,
            "image": self.piq_url,
            "contains_support_document": contains_support_document,
            "upload_through": self.upload_through,
            "is_edi": self.is_edi,
            "job": job_dict,
        }

    def _create_invoice_in_core_api(self):
        df = self.discovered_file

        if not settings.DISCOVERED_FILE_PIQ_CREATE_DOC:
            LOGGER.warning(
                f"[DiscoveredFile:{df.id}] DISCOVERED_FILE_PIQ_CREATE_DOC is False, skipping PIQ create"
            )
            return

        if df.piq_container_id:
            raise SkipProcessing(
                f"[DiscoveredFile:{df.id}] PIQ container already created."
            )

        if not self.piq_url or not df.piq_upload_id:
            raise ValidationError(
                f"[DiscoveredFile:{df.id}] Both 'url' and 'piq_upload_id' need to be set "
                f"before creating document via PIQ API"
            )

        self._internal_create_invoice_in_core_api()

    def _internal_create_invoice_in_core_api(self):
        df = self.discovered_file

        payload = self.get_payload()
        response = settings.PIQ_CORE_CLIENT.create_invoice(payload)
        LOGGER.debug(
            f"[DiscoveredFile:{df.id}] Create PIQ invoice returned response body: {response}"
        )

        container_id = response["container_id"] if response else None
        if not container_id:
            raise ValidationError(
                f"[DiscoveredFile:{df.id}] Create invoice operation failed"
            )

        df.piq_container_id = container_id
        df.save()

    def _fetch_location_id(self) -> int:
        return (
            self.__fetch_location_id_from_job()
            or self.__fetch_location_id_from_customer_number_mapping()
            or self.__fetch_location_id_from_piq_mapping()
            or settings.PIQ_UNKNOWN_RESTAURANT_ID
        )

    def __fetch_location_id_from_job(self):
        return (
            self.discovered_file.run.job.location
            and self.discovered_file.run.job.location.remote_id
        )

    def __fetch_location_id_from_customer_number_mapping(self):
        customer_number = self.discovered_file.document_properties.get(
            "customer_number"
        )
        if not customer_number:
            return None

        return None

    def __fetch_location_id_from_piq_mapping(self):
        # TODO: remove this logic eventually
        location_name = (
            self.discovered_file.document_properties.get("restaurant_name") or ""
        ).strip()
        location_id = PIQMapping.get_piq_mapped_data(
            job=self.discovered_file.run.job,
            mapping_field=location_name,
            mapping_type="r",
        )
        return location_id

    def execute(self):
        success = self._upload_to_s3()
        if not success:
            return

        self._create_invoice_in_core_api()


class InvoiceEDIPIQUploadAction(InvoiceStandardPIQUploadAction):
    """Applicable for discovered invoices only. Feed into the Plate IQ system via the EDI upload API"""

    upload_through = "edi"
    is_edi = True

    def get_payload(self):
        fda = self.discovered_file.discovery_action

        if not fda:
            raise ValidationError(
                f"Discovery action not configured for file {self.discovered_file.id}"
            )

        if not fda.edi_parser_code:
            raise ValidationError(
                f"EDI parser code not set for file {self.discovered_file.id} "
                f"and file discovery action {fda.id}"
            )

        edi_type = EDIType(
            fda.edi_parser_code
        )  # pylint: disable=no-value-for-parameter

        payload = super().get_payload()
        payload["job"].update({"type": edi_type.value})
        return payload


class PaymentUploadEDIAction(DiscoveredFileActionBase):
    def get_payload(self):
        run = self.discovered_file.run
        job = run.job
        fda = self.discovered_file.discovery_action
        edi_type = EDIType(
            fda.edi_parser_code
        )  # pylint: disable=no-value-for-parameter

        payload = {
            "run": run.id,
            "file": self.discovered_file.original_file.url,
            "discovered_file": self.discovered_file.id,
            "job": {
                "id": job.id,
                "name": str(job),
                "type": edi_type.value,
            },
        }

        return payload

    def execute(self):
        from apps.runs.tasks import (  # pylint: disable=cyclic-import, import-outside-toplevel
            send_to_step_function,
        )

        payload = self.get_payload()
        send_to_step_function.apply_async((payload,), countdown=5)


# pylint: disable=no-member
def factory(discovered_file: DiscoveredFile) -> DiscoveredFileActionBase:
    discovery_action = discovered_file.discovery_action
    action_type = discovery_action and discovery_action.action_type

    mapping = {
        None: DoNothingAction,
        FileDiscoveryActionType.NONE.ident: DoNothingAction,
        FileDiscoveryActionType.PIQ_STANDARD_UPLOAD.ident: InvoiceStandardPIQUploadAction,
        FileDiscoveryActionType.PIQ_EDI_UPLOAD.ident: InvoiceEDIPIQUploadAction,
        FileDiscoveryActionType.PAYMENTS_EDI_UPLOAD.ident: PaymentUploadEDIAction,
    }

    # in theory you can have a KeyError here, but that would be a code bug (adding an action without adding it here)
    # so not wrapping this in a try/except
    action_cls = mapping[action_type]
    return action_cls(discovered_file)
