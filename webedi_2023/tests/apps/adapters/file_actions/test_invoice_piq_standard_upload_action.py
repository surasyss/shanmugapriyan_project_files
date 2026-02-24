import uuid
from unittest import mock

import pytest
from django.core.exceptions import ValidationError
from django.test import override_settings
from spices.documents import DocumentType

from apps.adapters.file_actions import InvoiceStandardPIQUploadAction, SkipProcessing
from apps.jobconfig.models import FileDiscoveryActionType, EDIType
from tests.apps.definitions.factories import (
    ConnectorVendorInfoFactory,
    ConnectorFactory,
)
from tests.apps.jobconfig.factories import FileDiscoveryActionFactory, JobFactory
from tests.apps.runs.factories import DiscoveredFileFactory


@pytest.mark.unit
@override_settings(DISCOVERED_FILE_PIQ_API_SWITCH=False)
def test__skip_s3_upload():
    class Action(InvoiceStandardPIQUploadAction):
        _create_invoice_in_core_api = mock.Mock()

    discovered_file = mock.Mock()
    # if code proceeds beyond expected stopping point, this will ensure a validation error
    discovered_file.local_filepath = None

    action = Action(discovered_file=discovered_file)
    action.execute()
    action._create_invoice_in_core_api.assert_not_called()


@pytest.mark.unit
@override_settings(DISCOVERED_FILE_PIQ_API_SWITCH=True)
def test__no_local_filepath__no_original_file():
    class Action(InvoiceStandardPIQUploadAction):
        _create_invoice_in_core_api = mock.Mock()

    discovered_file = mock.Mock()
    discovered_file.local_filepath = None
    discovered_file.original_file = None
    action = Action(discovered_file=discovered_file)
    with pytest.raises(ValidationError):
        action.execute()
    action._create_invoice_in_core_api.assert_not_called()


@pytest.mark.unit
@override_settings(DISCOVERED_FILE_PIQ_API_SWITCH=True)
def test__no_local_filepath__with_original_file():
    temp = mock.Mock()
    exc = Exception()

    class Action(InvoiceStandardPIQUploadAction):
        called = False

        def _populate_local_filepath(self):
            self.called = True
            self.discovered_file.local_filepath = "local"
            return temp

        _create_invoice_in_core_api = mock.Mock()
        _fetch_signed_s3_url = mock.Mock(side_effect=exc)

    discovered_file = mock.Mock()
    discovered_file.local_filepath = None
    discovered_file.original_file.url = "original_file.url"

    action = Action(discovered_file=discovered_file)

    with pytest.raises(Exception) as exception:
        action.execute()

    assert exc == exception.value
    assert action.called
    temp.close.assert_called_once()


@pytest.mark.unit
@override_settings(DISCOVERED_FILE_PIQ_API_SWITCH=True)
def test__signed_json_empty():
    class Action(InvoiceStandardPIQUploadAction):
        _create_invoice_in_core_api = mock.Mock()
        _fetch_signed_s3_url = mock.Mock()

    discovered_file = mock.Mock()
    discovered_file.local_filepath = "local"
    action = Action(discovered_file=discovered_file)
    action._fetch_signed_s3_url.return_value = {}
    with pytest.raises(ValidationError):
        action.execute()
    action._create_invoice_in_core_api.assert_not_called()


@pytest.mark.unit
@override_settings(DISCOVERED_FILE_PIQ_API_SWITCH=True)
def test__signed_json_valid__upload_failed():
    class Action(InvoiceStandardPIQUploadAction):
        _create_invoice_in_core_api = mock.Mock()
        _fetch_signed_s3_url = mock.Mock()
        _upload_to_signed_s3_url_internal = mock.Mock()

    discovered_file = mock.Mock()
    discovered_file.local_filepath = "local"
    action = Action(discovered_file=discovered_file)
    action._fetch_signed_s3_url.return_value = {
        "put_request": "https://fake.integrator.plateiq.com/blah",
        "headers": {"hello": "world"},
        "url": f"url-{uuid.uuid4()}",
        "upload_id": f"upload_id-{uuid.uuid4()}",
    }
    action._upload_to_signed_s3_url_internal.return_value = False
    with pytest.raises(ValidationError):
        action.execute()
    action._create_invoice_in_core_api.assert_not_called()


@pytest.mark.unit
@override_settings(DISCOVERED_FILE_PIQ_API_SWITCH=True)
def test__signed_json_valid__upload_succeeded__mocked_create_invoice():
    class Action(InvoiceStandardPIQUploadAction):
        _create_invoice_in_core_api = mock.Mock()
        _fetch_signed_s3_url = mock.Mock()
        _upload_to_signed_s3_url_internal = mock.Mock()

    expected_url = f"url-{uuid.uuid4()}"
    expected_upload_id = f"upload_id-{uuid.uuid4()}"

    discovered_file = mock.Mock()
    discovered_file.local_filepath = "local"
    action = Action(discovered_file=discovered_file)
    action._fetch_signed_s3_url.return_value = {
        "put_request": "https://fake.integrator.plateiq.com/blah",
        "headers": {"hello": "world"},
        "url": expected_url,
        "upload_id": expected_upload_id,
    }
    action._upload_to_signed_s3_url_internal.return_value = True
    action.execute()

    assert action.piq_url == expected_url
    assert discovered_file.piq_upload_id == expected_upload_id
    discovered_file.save.assert_called_once()
    action._create_invoice_in_core_api.assert_called()


@pytest.mark.unit
@override_settings(DISCOVERED_FILE_PIQ_CREATE_DOC=False)
def test__create_piq_container__disabled():
    class Action(InvoiceStandardPIQUploadAction):
        _upload_to_s3 = mock.Mock()

    discovered_file = mock.Mock()
    # if code proceeds beyond expected stopping point, this will ensure a validation error
    discovered_file.piq_container_id = "hello"
    action = Action(discovered_file=discovered_file)
    action._upload_to_s3.return_value = True
    action.execute()
    # no validation error raised is proof enough


@pytest.mark.unit
@override_settings(DISCOVERED_FILE_PIQ_CREATE_DOC=True)
def test__create_piq_container__already_created():
    class Action(InvoiceStandardPIQUploadAction):
        _upload_to_s3 = mock.Mock()

    discovered_file = mock.Mock()
    discovered_file.piq_container_id = "hello"
    action = Action(discovered_file=discovered_file)
    action._upload_to_s3.return_value = True
    with pytest.raises(SkipProcessing):
        action.execute()


@pytest.mark.unit
@override_settings(DISCOVERED_FILE_PIQ_CREATE_DOC=True)
@pytest.mark.parametrize("attribute", ["url", "piq_upload_id"])
def test__create_piq_container__attribute_missing(attribute):
    class Action(InvoiceStandardPIQUploadAction):
        _upload_to_s3 = mock.Mock()

    discovered_file = mock.Mock()
    discovered_file.piq_container_id = None
    setattr(discovered_file, attribute, None)

    action = Action(discovered_file=discovered_file)
    action._upload_to_s3.return_value = True
    with pytest.raises(ValidationError):
        action.execute()


@pytest.mark.unit
@override_settings(DISCOVERED_FILE_PIQ_CREATE_DOC=True)
def test__create_piq_container__check_that_final_method_is_being_called():
    class Action(InvoiceStandardPIQUploadAction):
        _upload_to_s3 = mock.Mock()

    discovered_file = mock.Mock()
    discovered_file.piq_container_id = None
    discovered_file.url = f"url-{uuid.uuid4()}"
    discovered_file.upload_id = f"upload_id-{uuid.uuid4()}"

    # deliberately induce AttributeError, we only want to check that the method
    # _internal_create_invoice_in_core_api is being called, not test the body
    discovered_file.run = None

    action = Action(discovered_file=discovered_file)
    action._upload_to_s3.return_value = True
    action.piq_url = f"url-{uuid.uuid4()}"
    with pytest.raises(AttributeError):
        action.execute()


@override_settings(DISCOVERED_FILE_PIQ_CREATE_DOC=True)
@mock.patch("apps.utils.base.settings.PIQ_CORE_CLIENT.create_invoice")
def test__create_piq_container__create_invoice_being_called_with_required_parameters(
    mock_patcher,
):
    mock_patcher.return_value = {"container_id": 123}

    connector = ConnectorFactory.create()
    ConnectorVendorInfoFactory(contains_support_document=False, connector=connector)
    job = JobFactory(connector=connector)
    discovery_action = FileDiscoveryActionFactory.create(
        action_type=FileDiscoveryActionType.PIQ_STANDARD_UPLOAD.ident,
        edi_parser_code=EDIType.DOORDASH.ident,
        job=job,
    )
    df = DiscoveredFileFactory.create(
        document_type=DocumentType.INVOICE.ident,
        run__job=discovery_action.job,
        piq_upload_id=uuid.uuid4(),
        content_hash=str(uuid.uuid4()),
    )

    class Action(InvoiceStandardPIQUploadAction):
        _upload_to_s3 = mock.Mock()
        _fetch_restaurant_id = mock.Mock()

    action = Action(discovered_file=df)

    action._upload_to_s3.return_value = True
    action._fetch_restaurant_id.return_value = 123
    action.piq_url = f"url-{uuid.uuid4()}"

    action.execute()

    arguments = mock_patcher.call_args[0][0]
    assert not arguments["is_edi"]
    assert "job" in arguments.keys()


@override_settings(DISCOVERED_FILE_PIQ_CREATE_DOC=True)
def test_invoice_standard_piq_upload_action__get_payload():

    connector = ConnectorFactory.create()
    ConnectorVendorInfoFactory(contains_support_document=False, connector=connector)
    job = JobFactory(connector=connector)
    discovery_action = FileDiscoveryActionFactory.create(
        action_type=FileDiscoveryActionType.PIQ_STANDARD_UPLOAD.ident,
        edi_parser_code=EDIType.DOORDASH.ident,
        job=job,
    )
    upload_id = uuid.uuid4()
    df = DiscoveredFileFactory.create(
        document_type=DocumentType.INVOICE.ident,
        run__job=discovery_action.job,
        piq_upload_id=upload_id,
        content_hash=str(uuid.uuid4()),
    )
    location_group_id = (
        df.run.job.location_group and df.run.job.location_group.remote_id
    )
    contains_support_document = df.connector.connector_vendor.contains_support_document

    expected_payload = {
        "restaurant": df.run.job.location.remote_id,
        "restaurant_account": df.run.job.account.remote_id,
        "restaurant_group": location_group_id,
        "upload_id": df.piq_upload_id,
        "image": None,
        "contains_support_document": contains_support_document,
        "upload_through": "webedi",
        "is_edi": False,
        "job": {
            "id": job.id,
            "name": str(job),
            "create_missing_vendors": job.create_missing_vendors,
        },
    }

    action = InvoiceStandardPIQUploadAction(discovered_file=df)
    payload = action.get_payload()
    assert payload == expected_payload
