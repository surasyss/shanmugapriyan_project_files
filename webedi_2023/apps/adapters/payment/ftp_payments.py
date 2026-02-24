import hashlib
import os

from django.db import IntegrityError, transaction

from apps.adapters.base import PaymentInformationImportInterface
from apps.adapters.framework import download
from apps.runs.models import DiscoveredFile, DocumentType
from integrator import LOGGER


def _get_content_hash(file_path):
    with open(file_path, "rb") as file_contents:
        contents = file_contents.read()
        content_hash = hashlib.sha1(contents)
        return content_hash.hexdigest()


def _clean_extension(orig_file_name):
    _, extension = os.path.splitext(orig_file_name)
    if extension is None or not extension:
        return f"{orig_file_name}.payments"
    return orig_file_name


def _unique_file_hash(job_id, content_hash):
    unique_file_hash = f"{job_id}-{content_hash}"
    unique_file_hash = hashlib.sha1(unique_file_hash.encode()).hexdigest()

    return unique_file_hash


def _get_display_name_and_ex(orig_file_name):
    file_name = _clean_extension(orig_file_name)
    name, ext = os.path.splitext(file_name)
    ext = ext.replace(" ", "")
    display_name = name + ext

    return display_name, ext


class FTPPayment(PaymentInformationImportInterface):
    def start_payment_import_flow(self):
        processed_files = list()
        job = self.run.job

        while True:
            if not job.ftp_credential:
                LOGGER.info(
                    f"Run: {self.run.id}. Job  {job.id} does not have the FTP credential."
                )
                break

            downloader = download.FTPDownload(
                job.ftp_credential.download_folder, job.ftp_credential
            )
            file_path = None

            try:
                file_path = downloader.download()
            except Exception as ex:  # pylint: disable=broad-except
                LOGGER.error(
                    f"[tag: EDP10] Run: {self.run.id}. Error occurred in fetching files Job: {job.id} {ex}"
                )

            if not file_path:
                break

            orig_file_name = os.path.basename(file_path)
            if orig_file_name in processed_files:
                break

            processed_files.append(orig_file_name)
            display_name = _clean_extension(orig_file_name)
            _, ext = _get_display_name_and_ex(orig_file_name)

            unique_file_hash = _unique_file_hash(job.id, _get_content_hash(file_path))

            try:
                # This is done for the test case to not fail
                with transaction.atomic():
                    discovered_file = DiscoveredFile(
                        run=self.run,
                        document_type=DocumentType.PAYMENT.ident,  # pylint: disable=no-member
                        connector=job.connector,
                        original_filename=display_name,
                        original_download_url=display_name,
                        downloaded_successfully=True,
                    )
                    discovered_file.local_filepath = file_path
                    discovered_file.save_content(
                        discovered_file.local_filepath,
                        compute_extracted_text_hash=self.run.job.connector.get_custom_properties.get(
                            "compute_extracted_text_hash", True
                        ),
                    )
            except IntegrityError:
                LOGGER.info(
                    f"[tag:FTPP100] Run: {self.run.id}. Discovered file {display_name} already exists"
                )

            try:
                downloader.move_file_to_processed_folder(orig_file_name)
            except Exception as ex:
                message = (
                    f"[tag:EPP200] Run: {self.run.id}. Failed moving file {orig_file_name} to processed folder."
                    f" Ex: {ex}"
                )
                LOGGER.debug(message)
                raise Exception(message) from ex
