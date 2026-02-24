import copy

import pytest
from rest_framework import status

from apps.definitions.models import ConnectorCapabilityTypes
from apps.runs.models import RunStatus, Run
from tests.apps.definitions.factories import (
    ConnectorFactory,
    ConnectorCapabilityFactory,
)
from tests.apps.jobconfig.factories import JobFactory


def __assert_run_job_serialized_structure_and_values(run_job_dict: dict, **kwargs):
    run_job_dict = copy.copy(run_job_dict)
    run = run_job_dict.pop("run")

    assert isinstance(run, dict)
    assert isinstance(run["id"], str)
    assert isinstance(run["status"], int)
    assert isinstance(run["status_text"], str)

    assert run.pop("id") == kwargs["run_job"]["id"]
    assert run.pop("status") == kwargs["run_job"]["status"]
    assert run.pop("status_text") == kwargs["run_job"]["status_text"]

    assert not run
    assert not run_job_dict


@pytest.mark.api("job-run")
@pytest.mark.parametrize("job_enabled", [True, False])
def test_detail__run_job(seed_authenticated_api, job_enabled):
    """DiscoveredFile List: Happy case"""
    connector = ConnectorFactory()
    ConnectorCapabilityFactory(
        connector=connector, type=ConnectorCapabilityTypes.INVOICE__DOWNLOAD
    )
    job = JobFactory(
        account=seed_authenticated_api.account, enabled=job_enabled, connector=connector
    )
    seed_authenticated_api.api.set_url_params(pk=job.id)
    response = seed_authenticated_api.api.post()

    run_job = {
        "id": response.data["run"]["id"],
        "status": response.data["run"]["status"],
        "status_text": RunStatus(response.data["run"]["status"]).message,
    }

    assert response.status_code == status.HTTP_200_OK
    __assert_run_job_serialized_structure_and_values(response.data, run_job=run_job)


@pytest.mark.api("job-run")
def test_detail__run_job__with_optional_params(seed_authenticated_api):
    """DiscoveredFile List: Happy case"""
    connector = ConnectorFactory()
    ConnectorCapabilityFactory(
        connector=connector, type=ConnectorCapabilityTypes.INTERNAL__WEB_LOGIN
    )
    job = JobFactory(account=seed_authenticated_api.account, connector=connector)

    seed_authenticated_api.api.set_url_params(pk=job.id)
    response = seed_authenticated_api.api.post(
        data={
            "suppress_invoices": True,
            "dry_run": True,
        }
    )
    assert response.status_code == status.HTTP_200_OK

    run = Run.objects.get(pk=response.data["run"]["id"])
    assert run.dry_run is True
    assert run.is_manual is False
    assert run.request_parameters["suppress_invoices"] is True


@pytest.mark.api("job-run")
def test_detail__run_job__non_existing_job(seed_authenticated_api):
    """DiscoveredFile List: Non Existing Job"""

    seed_authenticated_api.api.set_url_params(pk=999999)
    response = seed_authenticated_api.api.post()

    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert response.data["detail"] == "Not found."


@pytest.mark.api("job-run")
def test_detail__run_job__inactive_connector(seed_authenticated_api):
    """DiscoveredFile List: Inactive Job"""
    connector = ConnectorFactory(enabled=False)
    job = JobFactory(
        connector=connector, account=seed_authenticated_api.account, enabled=False
    )

    seed_authenticated_api.api.set_url_params(pk=job.id)
    response = seed_authenticated_api.api.post()
    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert response.data["error"]["code"] == "DISABLED"
    assert response.data["error"]["message"] == "Connector is disabled"


@pytest.mark.api("job-run")
@pytest.mark.parametrize("method", ["patch", "put", "delete"])
def test_detail__run_job__unallowed(seed_authenticated_api, method):
    """DiscoveredFile Detail: Patch"""
    job = JobFactory(account=seed_authenticated_api.account)
    seed_authenticated_api.api.set_url_params(pk=job.id)
    response = getattr(seed_authenticated_api.api, method)()
    assert response.status_code == status.HTTP_405_METHOD_NOT_ALLOWED
