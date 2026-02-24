import tempfile
import uuid
from unittest import mock

from spices.documents import DocumentType

from apps.adapters.engine import post_process_discovered_files
from apps.jobconfig.models import FileDiscoveryActionType, EDIType
from tests.apps.jobconfig.factories import FileDiscoveryActionFactory, JobFactory
from tests.apps.runs.factories import DiscoveredFileFactory


@mock.patch("storages.backends.s3boto3.S3Boto3Storage.save")
@mock.patch("apps.runs.tasks.send_to_step_function.apply_async")
def test__payments_upload_edi_actions__called_step_function(
    mocked_send_to_step_function, mock_save
):
    job = JobFactory.create()
    discovery_action = FileDiscoveryActionFactory.create(
        action_type=FileDiscoveryActionType.PAYMENTS_EDI_UPLOAD.ident,
        edi_parser_code=EDIType.EDI_820.ident,
        job=job,
        document_type=DocumentType.PAYMENT.ident,
    )

    mock_save.return_value = "cv.doc"

    with tempfile.NamedTemporaryFile(suffix=".csv") as fp:
        with open(fp.name, "w") as tmpfile:
            tmpfile.write("something")

        with open(fp.name, "rb") as tmpfile:
            df = DiscoveredFileFactory.create(
                document_type=DocumentType.PAYMENT.ident,
                run__job=discovery_action.job,
                piq_upload_id=uuid.uuid4(),
                content_hash=str(uuid.uuid4()),
            )
            df.original_file.save("abc", tmpfile, save=True)

        post_process_discovered_files(df.run)

        payload = {
            "job": {
                "id": job.id,
                "run": df.run.id,
                "name": str(job),
                "type": "820",
                "create_missing_vendors": False,
            },
            "file": df.original_file.url,
        }

    args, kwargs = mocked_send_to_step_function.call_args_list[0]
    params = args[0][0]

    assert "run" in params
    assert "job" in params
    assert "file" in params
