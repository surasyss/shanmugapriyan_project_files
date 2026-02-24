import copy
import os
import uuid
from datetime import datetime
from unittest import mock
from unittest.mock import patch

import pytest
import pytz
from rest_framework import status
from spices.documents import DocumentType
from spices.services import ContextualError

from apps.error_codes import ErrorCode
from apps.runs.models import RunStatus, FileFormat
from tests.apps.definitions.factories import (
    ConnectorFactory,
    ConnectorCapabilityFactory,
)
from tests.apps.jobconfig.api.test_job import (
    __assert_job_serialized_structure_and_values,
)
from tests.apps.runs.factories import RunFactory, DiscoveredFileFactory


def __assert_run_serialized_structure(run_dict: dict):
    run_dict = copy.copy(run_dict)
    run_list = run_dict.pop("results")

    assert isinstance(run_list, list)
    assert isinstance(run_dict.pop("count"), int)
    assert run_dict.pop("next") is None
    assert run_dict.pop("previous") is None
    assert not run_dict

    if run_list:
        run = run_list[0]
        execution_start_ts = run.pop("execution_start_ts")
        execution_end_ts = run.pop("execution_end_ts")
        grouped_discovered_files = run.pop("grouped_discovered_files")
        failure_issue = run.pop("failure_issue")

        assert isinstance(run.pop("id"), str)
        assert isinstance(run.pop("job"), dict)
        assert isinstance(run.pop("status"), int)
        assert isinstance(run.pop("status_text"), str)
        assert isinstance(run.pop("action"), str)
        assert isinstance(run.pop("dry_run"), bool)
        assert isinstance(run.pop("request_parameters"), dict)
        assert not run

        if execution_start_ts:
            assert isinstance(execution_start_ts, str)
        else:
            assert execution_start_ts is None

        if execution_end_ts:
            assert isinstance(execution_end_ts, str)
        else:
            assert execution_end_ts is None


def __assert_run_serialized_structure_and_values(run_dict: dict, **kwargs):
    run_dict = copy.copy(run_dict)
    job = run_dict.pop("job")

    execution_start_ts = run_dict.pop("execution_start_ts")
    execution_end_ts = run_dict.pop("execution_end_ts")
    request_parameters = run_dict.pop("request_parameters")

    datetime_format = "%Y-%m-%dT%H:%M:%S.%fZ"  # 2020-03-25T18:53:49.700315Z
    if execution_start_ts:
        execution_start_ts = datetime.strptime(execution_start_ts, datetime_format)
        execution_start_ts = execution_start_ts.replace(tzinfo=pytz.UTC)

    if execution_end_ts:
        execution_end_ts = datetime.strptime(execution_end_ts, datetime_format)
        execution_end_ts = execution_end_ts.replace(tzinfo=pytz.UTC)

    if request_parameters:
        assert request_parameters.get("version")
        assert request_parameters.get("end_date")
        assert request_parameters.get("start_date")

    assert run_dict.pop("id") == kwargs["run"].id
    assert run_dict.pop("status") == kwargs["run"].status
    assert run_dict.pop("action") == str(kwargs["run"].action)
    assert run_dict.pop("status_text") == kwargs["status_text"]
    assert execution_start_ts == kwargs["run"].execution_start_ts
    assert execution_end_ts == kwargs["run"].execution_end_ts
    assert run_dict.pop("dry_run") == kwargs["run"].dry_run

    failure_issue = run_dict.pop("failure_issue")
    if failure_issue is not None:
        assert failure_issue["code"] is not None
        assert failure_issue["message"] is not None

    grouped_discovered_files = run_dict.pop("grouped_discovered_files")
    if grouped_discovered_files is not None:
        assert isinstance(grouped_discovered_files, dict)
        for key, value in grouped_discovered_files.items():
            assert (key is None) or isinstance(key, str)
            assert isinstance(value, list)

    assert not run_dict

    __assert_job_serialized_structure_and_values(job, job=kwargs["run"].job)


def get_status_text(status: int):
    return RunStatus(status).message


@pytest.mark.api("run-list")
@pytest.mark.parametrize("count", [0, 1, 2])
def test_list__run__with_diff_counts(seed_authenticated_api, count):
    """Run List: with 'x' results"""

    for index in range(count):
        RunFactory(job__account=seed_authenticated_api.account)

    seed_authenticated_api.api.set_url_params()

    response = seed_authenticated_api.api.get()

    assert response.status_code == status.HTTP_200_OK
    assert response.data["count"] == count
    assert len(response.data["results"]) == count

    __assert_run_serialized_structure(response.data)


@pytest.mark.api("run-detail")
def test_retrieve__run__status__created(seed_authenticated_api):
    """Run Retrieve: with status = created"""

    run = RunFactory(job__account=seed_authenticated_api.account)

    seed_authenticated_api.api.set_url_params(pk=run.id)

    response = seed_authenticated_api.api.get()

    status_text = get_status_text(0)

    assert response.status_code == status.HTTP_200_OK
    assert response.data["status"] == run.status
    assert response.data["status_text"] == status_text
    assert response.data["execution_start_ts"] is None
    assert response.data["execution_end_ts"] is None

    __assert_run_serialized_structure_and_values(
        response.data, run=run, status_text=status_text
    )


@pytest.mark.api("run-detail")
def test_retrieve__run__status__scheduled(seed_authenticated_api):
    """Run Retrieve: with status = scheduled"""

    run = RunFactory(job__account=seed_authenticated_api.account)
    run.execute_async()

    seed_authenticated_api.api.set_url_params(pk=run.id)

    response = seed_authenticated_api.api.get()

    status_text = get_status_text(1)

    assert response.status_code == status.HTTP_200_OK
    assert response.data["status"] == run.status
    assert response.data["status_text"] == status_text
    assert response.data["execution_start_ts"] is None
    assert response.data["execution_end_ts"] is None

    __assert_run_serialized_structure_and_values(
        response.data, run=run, status_text=status_text
    )


@pytest.mark.api("run-detail")
def test_retrieve__run__status__started(seed_authenticated_api):
    """Run Retrieve: with status = started"""

    run = RunFactory(job__account=seed_authenticated_api.account)
    run.record_execution_start()

    seed_authenticated_api.api.set_url_params(pk=run.id)

    response = seed_authenticated_api.api.get()

    status_text = get_status_text(2)

    assert response.status_code == status.HTTP_200_OK
    assert response.data["status"] == run.status
    assert response.data["status_text"] == status_text
    assert response.data["execution_start_ts"] is not None
    assert response.data["execution_end_ts"] is None

    __assert_run_serialized_structure_and_values(
        response.data, run=run, status_text=status_text
    )


@pytest.mark.api("run-detail")
def test_retrieve__run__status__succeeded(seed_authenticated_api):
    """Run Retrieve: with status = succeeded"""

    run = RunFactory(job__account=seed_authenticated_api.account)
    run.record_execution_start()
    run.record_success()

    seed_authenticated_api.api.set_url_params(pk=run.id)

    response = seed_authenticated_api.api.get()

    status_text = get_status_text(3)

    assert response.status_code == status.HTTP_200_OK
    assert response.data["status"] == run.status
    assert response.data["status_text"] == status_text
    assert response.data["execution_start_ts"] is not None
    assert response.data["execution_end_ts"] is not None

    __assert_run_serialized_structure_and_values(
        response.data, run=run, status_text=status_text
    )


@pytest.mark.api("run-detail")
def test_retrieve__run__status__partially_succeeded(seed_authenticated_api):
    """Run Retrieve: with status = partially_succeeded"""

    run = RunFactory(job__account=seed_authenticated_api.account)
    run.record_execution_start()
    run.record_partial_success()

    seed_authenticated_api.api.set_url_params(pk=run.id)

    response = seed_authenticated_api.api.get()

    status_text = get_status_text(6)
    assert response.status_code == status.HTTP_200_OK
    assert response.data["status"] == run.status
    assert response.data["status_text"] == status_text
    assert response.data["execution_start_ts"] is not None
    assert response.data["execution_end_ts"] is not None

    __assert_run_serialized_structure_and_values(
        response.data, run=run, status_text=status_text
    )


@pytest.mark.api("run-detail")
def test_retrieve__run__status__failed(seed_authenticated_api):
    """Run Retrieve: with status = failed"""

    run = RunFactory(job__account=seed_authenticated_api.account)
    run.record_execution_start()
    run.record_failure()

    seed_authenticated_api.api.set_url_params(pk=run.id)

    response = seed_authenticated_api.api.get()

    status_text = get_status_text(4)

    assert response.status_code == status.HTTP_200_OK
    assert response.data["status"] == run.status
    assert response.data["status_text"] == status_text
    assert response.data["execution_start_ts"] is not None
    assert response.data["execution_end_ts"] is not None

    __assert_run_serialized_structure_and_values(
        response.data, run=run, status_text=status_text
    )


@pytest.mark.api("run-detail")
def test_retrieve__run__group_discovered_files(seed_authenticated_api):
    run = RunFactory.create(job__account=seed_authenticated_api.account)
    DiscoveredFileFactory.create(
        document_type=DocumentType.INVOICE.ident,
        run=run,
        url="https://something/",
        content_hash=str(uuid.uuid4()),
        document_properties={"version": 1, "customer_number": "123"},
    )
    DiscoveredFileFactory.create(
        document_type=DocumentType.INVOICE.ident,
        run=run,
        content_hash=str(uuid.uuid4()),
        url="https://something/",
        document_properties={"version": 1, "customer_number": "123"},
    )
    DiscoveredFileFactory.create(
        document_type=DocumentType.INVOICE.ident,
        run=run,
        content_hash=str(uuid.uuid4()),
        url="https://something/",
        document_properties={"version": 1, "customer_number": "456"},
    )

    # csv file, should appear in API response
    DiscoveredFileFactory.create(
        document_type=DocumentType.INVOICE.ident,
        run=run,
        content_hash=str(uuid.uuid4()),
        url="https://something/",
        file_format=FileFormat.CSV.ident,
        document_properties={"version": 1, "customer_number": "123"},
    )
    # URL none, should not appear in API response
    DiscoveredFileFactory.create(
        document_type=DocumentType.INVOICE.ident,
        run=run,
        url=None,
        content_hash=str(uuid.uuid4()),
        original_file=None,
        document_properties={"version": 1, "customer_number": "123"},
    )
    # customer_number none, *should* appear in API response
    DiscoveredFileFactory.create(
        document_type=DocumentType.INVOICE.ident,
        run=run,
        content_hash=str(uuid.uuid4()),
        url="https://something/",
        document_properties={"version": 1, "customer_number": None},
    )

    run.record_execution_start()
    run.record_success()

    run.refresh_from_db()

    seed_authenticated_api.api.set_url_params(pk=run.id)

    response = seed_authenticated_api.api.get()

    status_text = get_status_text(RunStatus.SUCCEEDED)

    assert response.status_code == status.HTTP_200_OK
    assert response.data["status"] == run.status
    assert response.data["status_text"] == status_text
    assert response.data["execution_start_ts"] is not None
    assert response.data["execution_end_ts"] is not None

    grouped_discovered_file = response.data.get("grouped_discovered_files")
    assert len(grouped_discovered_file) == 3
    assert len(grouped_discovered_file.get("123")) == 3
    assert len(grouped_discovered_file.get("456")) == 1
    assert len(grouped_discovered_file.get(None)) == 1

    __assert_run_serialized_structure_and_values(
        response.data, run=run, status_text=status_text
    )


@pytest.mark.api("run-detail")
def test_retrieve__run__status__failed_with_auth_error(seed_authenticated_api):
    """Run Retrieve: with status = failed with auth error"""

    run = RunFactory(job__account=seed_authenticated_api.account)
    run.record_execution_start()
    run.record_failure(
        ContextualError(
            code=ErrorCode.AUTHENTICATION_FAILED_WEB.ident,  # pylint: disable=no-member
            message=ErrorCode.AUTHENTICATION_FAILED_WEB.message.format(  # pylint: disable=no-member
                username=run.job.username
            ),
            params={"username": run.job.username},
        )
    )

    seed_authenticated_api.api.set_url_params(pk=run.id)

    response = seed_authenticated_api.api.get()

    status_text = get_status_text(4)

    assert response.status_code == status.HTTP_200_OK
    assert response.data["status"] == run.status
    assert response.data["status_text"] == status_text
    assert response.data["execution_start_ts"] is not None
    assert response.data["execution_end_ts"] is not None

    __assert_run_serialized_structure_and_values(
        response.data, run=run, status_text=status_text
    )


@pytest.mark.api("run-post-process")
def test__run__post_process___run_status__success(seed_authenticated_api):
    connector = ConnectorFactory()
    ConnectorCapabilityFactory(connector=connector, type="internal.web_login")
    run = RunFactory.create(
        job__account=seed_authenticated_api.account, job__connector=connector
    )
    DiscoveredFileFactory.create(
        document_type=DocumentType.INVOICE.ident,
        run=run,
        content_hash=str(uuid.uuid4()),
        document_properties={"version": 1, "customer_number": "123"},
    )
    DiscoveredFileFactory.create(
        document_type=DocumentType.INVOICE.ident,
        run=run,
        content_hash=str(uuid.uuid4()),
        document_properties={"version": 1, "customer_number": "123"},
    )
    DiscoveredFileFactory.create(
        document_type=DocumentType.INVOICE.ident,
        run=run,
        content_hash=str(uuid.uuid4()),
        document_properties={"version": 1, "customer_number": "456"},
    )

    run.record_execution_start()
    run.record_success()
    run.refresh_from_db()

    seed_authenticated_api.api.set_url_params(pk=run.id)

    response = seed_authenticated_api.api.post()
    assert response.status_code == status.HTTP_200_OK


@pytest.mark.api("run-post-process")
def test__run__post_process___run_status__failed(seed_authenticated_api):
    run = RunFactory.create(job__account=seed_authenticated_api.account)
    DiscoveredFileFactory.create(
        document_type=DocumentType.INVOICE.ident,
        run=run,
        content_hash=str(uuid.uuid4()),
        document_properties={"version": 1, "customer_number": "123"},
    )
    DiscoveredFileFactory.create(
        document_type=DocumentType.INVOICE.ident,
        run=run,
        content_hash=str(uuid.uuid4()),
        document_properties={"version": 1, "customer_number": "123"},
    )
    DiscoveredFileFactory.create(
        document_type=DocumentType.INVOICE.ident,
        run=run,
        content_hash=str(uuid.uuid4()),
        document_properties={"version": 1, "customer_number": "456"},
    )

    run.record_execution_start()
    run.record_failure()
    run.refresh_from_db()

    seed_authenticated_api.api.set_url_params(pk=run.id)

    response = seed_authenticated_api.api.post()
    assert response.status_code == status.HTTP_412_PRECONDITION_FAILED


@pytest.mark.api("run-post-process")
@mock.patch.dict(os.environ, {"MANDRILL_OUTBOUND_KEY": "dummy_key"})
def test__run__post_process___validate_initial_call(seed_authenticated_api):
    run = RunFactory.create(
        job__account=seed_authenticated_api.account,
        request_parameters={
            "version": 1,
            "end_date": "2020-03-26",
            "start_date": "2020-03-19",
            "import_entities": [],
            "suppress_invoices": True,
        },
        job__created_user=seed_authenticated_api.user,
    )

    run.record_execution_start()
    with patch("apps.runs.tasks.send_email.delay") as mock_task:
        run.record_success()
        mock_task.assert_called()
