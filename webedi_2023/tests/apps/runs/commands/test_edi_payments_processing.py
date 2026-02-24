import tempfile
from unittest.mock import patch

from spices.documents import DocumentType

from apps.adapters.engine import crawl
from apps.adapters.file_actions import PaymentUploadEDIAction
from apps.adapters.framework.download import FTPDownload
from apps.adapters.payment.ftp_payments import _get_content_hash
from apps.jobconfig.models import FileDiscoveryActionType, EDIType
from apps.runs.models import (
    Run,
    RunStatus,
    DiscoveredFile,
    ConnectorCapabilityTypes,
    RunCreatedVia,
)
from tests.apps.definitions.factories import ConnectorCapabilityFactory
from tests.apps.definitions.factories import ConnectorFactory
from tests.apps.jobconfig.factories import (
    FileDiscoveryActionFactory,
    JobFactory,
    FTPCredentialFactory,
)


@patch("storages.backends.s3boto3.S3Boto3Storage.save")
@patch.object(PaymentUploadEDIAction, "execute")
@patch.object(FTPDownload, "move_file_to_processed_folder")
@patch.object(FTPDownload, "download")
def test__edi820__payments_flow(
    mocked_download, mocked_move, mocked_execute, mocked_save
):
    ftp_credential = FTPCredentialFactory.create()
    connector = ConnectorFactory(adapter_code="FTP", channel="FTP")
    job = JobFactory.create(ftp_credential=ftp_credential, connector=connector)
    ConnectorCapabilityFactory(
        connector=connector, type=ConnectorCapabilityTypes.PAYMENT__IMPORT_INFO
    )
    run = Run.objects.create(
        job=job,
        dry_run=False,
        action=ConnectorCapabilityTypes.PAYMENT__IMPORT_INFO,
        created_via=RunCreatedVia.ADMIN_REQUEST,
    )
    discovery_action = FileDiscoveryActionFactory.create(
        action_type=FileDiscoveryActionType.PAYMENTS_EDI_UPLOAD.ident,
        edi_parser_code=EDIType.EDI_820.ident,
        job=job,
        document_type=DocumentType.PAYMENT.ident,
    )

    content_hash = None
    with tempfile.NamedTemporaryFile(suffix=".csv") as fp:
        with open(fp.name, "w") as tmpfile:
            tmpfile.write("something")

        # mocked_get_file.return_value = fp.name
        mocked_download.return_value = fp.name
        mocked_execute.return_value = True
        mocked_save.return_value = "cv.doc"
        mocked_move.return_value = True

        crawl(run)
        content_hash = _get_content_hash(fp.name)

        mocked_execute.assert_called_with()

    run.refresh_from_db()
    assert run.status == RunStatus.SUCCEEDED.ident
    discovered_files = DiscoveredFile.objects.filter(
        run=run, document_type=DocumentType.PAYMENT.ident
    ).first()
    assert discovered_files.content_hash == content_hash
