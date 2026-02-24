import uuid
from datetime import date
from time import sleep
from typing import List

from spices.documents import DocumentType
from spices.services import ContextualError

from apps.adapters.base import VendorDocumentDownloadInterface
from apps.error_codes import ErrorCode
from apps.runs.models import Run, DiscoveredFile


class MockVendorConnector(VendorDocumentDownloadInterface):
    """
    Mock Vendor Connector for testing

    Supports the following connectors:
        - always-fail-with-credential-error
        - always-fail-with-partner-error
        - slow-crawl  (to simulate timeout- variable `t` seconds)
        - success-N-files-found  (variable `n` (count, default 0) and `f` (format, default pdf) )
    """

    @staticmethod
    def _get_variable(variable_name: str, username: str, default=None):
        username_parts = username.split("#")
        username_parts = [
            part for part in username_parts if part.startswith(f"{variable_name}=")
        ]
        if username_parts:
            return username_parts[0].split("=")[-1]
        return default

    def start_documents_download_flow(self, run: Run) -> List[DiscoveredFile]:
        self.login_flow(run)

        connector_name = run.job.connector.name
        username = run.job.username

        if "slow-crawl" in connector_name:
            duration = int(self._get_variable("t", username, "120"))
            sleep(duration)

        discovered_files = []
        if "success-N-files-found" in connector_name:
            df_count = int(self._get_variable("n", username, "0"))
            file_format = self._get_variable("f", username, "pdf")
            if file_format not in ("pdf", "csv"):
                file_format = "pdf"

            for index in range(df_count):
                reference_code = f"{index}_{str(uuid.uuid4())}"
                discovered_file = DiscoveredFile.build_unique(
                    run,
                    reference_code,
                    document_type=DocumentType.INVOICE.ident,  # pylint: disable=no-member
                    file_format=file_format,
                    original_download_url=f"https://beta-api.plateiq.com/integrator/mock/{reference_code}",
                    original_filename=f"invoice_{reference_code}.pdf",
                    document_properties={
                        "invoice_number": reference_code,
                        "invoice_date": str(date.today()),
                    },
                )
                discovered_file.original_file = (
                    f"https://beta-api.plateiq.com/integrator/mock/{reference_code}"
                )
                discovered_file.content_hash = reference_code
                discovered_file.save()
                discovered_files.append(discovered_file)

        return discovered_files

    # pylint: disable=no-member
    def login_flow(self, run: Run) -> bool:
        connector_name = run.job.connector.name
        if "always-fail-with-credential-error" in connector_name:
            self.driver.quit()
            raise ContextualError(
                code=ErrorCode.AUTHENTICATION_FAILED_WEB.ident,
                message=ErrorCode.AUTHENTICATION_FAILED_WEB.message.format(
                    username=run.job.username
                ),
                params={"error_msg": "Mock failure"},
            )
        if "always-fail-with-partner-error" in connector_name:
            self.driver.quit()
            raise ContextualError(
                code=ErrorCode.EXTERNAL_UPSTREAM_UNAVAILABLE.ident,
                message=ErrorCode.EXTERNAL_UPSTREAM_UNAVAILABLE.message,
                params={},
            )
        return True
