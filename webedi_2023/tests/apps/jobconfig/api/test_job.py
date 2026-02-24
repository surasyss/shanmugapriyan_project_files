import copy
import uuid
from unittest.mock import patch

import pytest
from rest_framework import status
from spices.django3.coreobjects.models import Location, LocationGroup
from spices.django3.testing.factory.shared_core_object_model import (
    LocationGroupSharedCoreObjectFactory,
    LocationSharedCoreObjectFactory,
    AccountSharedCoreObjectFactory,
    CompanySharedCoreObjectFactory,
)
from spices.django3.testing.factory.user import UserWithBearerTokenFactory

from apps.jobconfig.models import FileDiscoveryAction, Job, FileDiscoveryActionType
from tests.apps.definitions.api.test_connector import (
    __assert_connector_serialized_structure_and_values,
)
from tests.apps.definitions.factories import ConnectorFactory
from tests.apps.jobconfig.factories import JobFactory, PIQMappingFactory
from tests.apps.runs.factories import RunFactory


def __assert_job_serialized_structure(job_dict: dict):
    job_dict = copy.copy(job_dict)
    job_list = job_dict.pop("results")

    assert isinstance(job_list, list)
    assert isinstance(job_dict.pop("count"), int)
    assert job_dict.pop("next") is None
    assert job_dict.pop("previous") is None
    assert not job_dict

    job = job_list[0]
    account = job.pop("account")
    location = job.pop("location")
    location_group = job.pop("location_group")
    last_run = job.pop("last_run")
    login_url = job.pop("login_url")

    assert isinstance(job.pop("id"), str)
    assert isinstance(job.pop("connector"), dict)
    assert isinstance(job.pop("username"), str)
    assert isinstance(job.pop("enabled"), bool)
    assert isinstance(job.pop("piq_mappings"), list)
    assert isinstance(job.pop("schedules"), list)
    assert isinstance(job.pop("companies"), list)

    if account:
        assert isinstance(account, dict)

    if location:
        assert isinstance(location, dict)

    if location_group:
        assert isinstance(location_group, dict)

    if last_run:
        assert isinstance(last_run, dict)
        assert isinstance(last_run["id"], str)

    if login_url:
        assert isinstance(login_url, str)

    assert not job


def __assert_job_serialized_structure_and_values(job_dict: dict, **kwargs):
    job_dict = copy.copy(job_dict)
    account = job_dict.pop("account")
    location = job_dict.pop("location")
    location_group = job_dict.pop("location_group")
    last_run = job_dict.pop("last_run")
    login_url = job_dict.pop("login_url")

    assert job_dict.pop("id") == kwargs["job"].id
    assert job_dict.pop("username") == kwargs["job"].username
    assert job_dict.pop("enabled") == kwargs["job"].enabled
    assert job_dict.pop("companies") == list(kwargs["job"].companies.all())

    if account:
        assert account["id"] == kwargs["job"].account.remote_id
        assert account["name"] == kwargs["job"].account.display_name

    if location:
        assert location["id"] == kwargs["job"].location.remote_id
        assert location["name"] == kwargs["job"].location.display_name

    if location_group:
        assert location_group["id"] == kwargs["job"].location_group.remote_id
        assert location_group["name"] == kwargs["job"].location_group.display_name

    if last_run:
        assert isinstance(last_run, dict)
        assert isinstance(last_run["id"], str)

    if login_url:
        assert login_url == kwargs["job"].login_url

    __assert_connector_serialized_structure_and_values(
        job_dict.pop("connector"), connector=kwargs["job"].connector
    )

    piq_mapping = job_dict.pop("piq_mappings")
    if piq_mapping:
        __assert_piq_mapping(piq_mapping, kwargs["piq_mappings"])

    schedules = job_dict.pop("schedules")

    assert not job_dict


def __assert_piq_mapping(piq_mappings: list, expected_piq_mappings: list):
    piq_mapping_dict = {
        f"{piq_mapping.piq_data.remote_id}_{piq_mapping.mapping_data}": piq_mapping
        for piq_mapping in expected_piq_mappings
    }

    for piq_mapping in piq_mappings:
        piq_mapping = copy.copy(piq_mapping)
        piq_map_id = piq_mapping.pop("id")
        job = piq_mapping.pop("job")
        piq_data = piq_mapping.pop("piq_data")
        piq_restaurant_id = piq_mapping.pop("piq_restaurant_id")
        mapping_data = piq_mapping.pop("mapping_data")
        name = piq_mapping.pop("name")
        mapped_to = piq_mapping.pop("mapped_to")
        unique_key = f'{piq_data["id"]}_{name}'

        if unique_key in piq_mapping_dict:
            assert piq_map_id == piq_mapping_dict[unique_key].id
            assert job == piq_mapping_dict[unique_key].job_id

            if piq_restaurant_id:
                assert piq_restaurant_id == int(
                    piq_mapping_dict[unique_key].piq_data.remote_id
                )
            else:
                assert piq_restaurant_id is None

            if mapped_to:
                assert mapped_to == piq_mapping_dict[unique_key].mapped_to
            else:
                assert mapped_to is None
            assert name == piq_mapping_dict[unique_key].mapping_data
            assert mapping_data == piq_mapping_dict[unique_key].mapping_data

            if piq_data:
                assert piq_data["id"] == piq_mapping_dict[unique_key].piq_data.remote_id
                assert (
                    piq_data["name"]
                    == piq_mapping_dict[unique_key].piq_data.display_name
                )

            assert not piq_mapping
        else:
            assert False


@pytest.mark.api("job-list")
@pytest.mark.parametrize(
    "connector_enabled, job_enabled",
    [
        (False, False),
        (False, True),
        (True, False),
        (True, True),
    ],
)
def test_list__enabled_combinations(
    seed_authenticated_api, connector_enabled, job_enabled
):
    """Connector, Job - Field Enable"""
    connector = ConnectorFactory()
    job = JobFactory(
        connector=connector, enabled=job_enabled, account=seed_authenticated_api.account
    )

    connector.enabled = connector_enabled
    connector.save()

    response = seed_authenticated_api.api.get()

    assert response.status_code == status.HTTP_200_OK
    assert response.data["results"][0]["enabled"] == (connector_enabled and job_enabled)
    __assert_job_serialized_structure(response.data)


@pytest.mark.api("job-list")
def test_list__filter__connector_id(seed_authenticated_api):
    """Job List: Filter - connector_id"""

    JobFactory.create_batch(size=2)
    connector = ConnectorFactory(name="fake_connector_id")
    job = JobFactory(connector=connector, account=seed_authenticated_api.account)

    response = seed_authenticated_api.api.get(data={"connector_id": job.connector.id})

    assert response.status_code == status.HTTP_200_OK
    assert response.data["count"] == 1

    assert response.data["results"][0]["connector"]["id"] == job.connector.id
    assert response.data["results"][0]["connector"]["name"] == job.connector.name
    __assert_job_serialized_structure(response.data)


@pytest.mark.api("job-list")
def test_list__filter__account_ids(seed_authenticated_api):
    """Job List: Filter - account_ids"""

    JobFactory.create_batch(size=2)
    account1 = AccountSharedCoreObjectFactory(remote_id="12345", type="acct")
    account2 = AccountSharedCoreObjectFactory(remote_id="98765", type="acct")
    job_01 = JobFactory(account=account1)
    job_02 = JobFactory(account=account2)

    response = seed_authenticated_api.api.get(
        data={"account_id": f"{account1.remote_id},{account2.remote_id}"}
    )

    assert response.status_code == status.HTTP_200_OK
    assert response.data["count"] == 2

    acc_ids = {response.data["results"][x]["account"]["id"] for x in range(2)}
    assert acc_ids == {account1.remote_id, account2.remote_id}

    __assert_job_serialized_structure(response.data)


@pytest.mark.api("job-list")
def test_list__filter__location_id(seed_authenticated_api):
    """Job List: Filter - location_id"""

    JobFactory.create_batch(size=2)
    location = LocationSharedCoreObjectFactory(remote_id="123", type="r")
    job = JobFactory(location=location, account=seed_authenticated_api.account)

    response = seed_authenticated_api.api.get(
        data={"location_id": job.location.remote_id}
    )

    assert response.status_code == status.HTTP_200_OK
    assert response.data["count"] == 1

    assert response.data["results"][0]["connector"]["id"] == job.connector.id
    assert response.data["results"][0]["location"]["id"] == location.remote_id
    __assert_job_serialized_structure(response.data)


@pytest.mark.api("job-list")
def test_list__filter__location_group_id(seed_authenticated_api):
    """Job List: Filter - location_group_id"""

    JobFactory.create_batch(size=2)
    location_group = LocationGroupSharedCoreObjectFactory(
        remote_id="123", type="locgrp"
    )
    job = JobFactory(location_group=location_group)

    response = seed_authenticated_api.api.get(
        data={"location_group_id": job.location_group.remote_id}
    )

    assert response.status_code == status.HTTP_200_OK
    assert response.data["count"] == 1

    assert response.data["results"][0]["connector"]["id"] == job.connector.id
    assert (
        response.data["results"][0]["location_group"]["id"] == location_group.remote_id
    )
    __assert_job_serialized_structure(response.data)


@pytest.mark.api("job-list")
def test_list__filter__location_group_id(seed_authenticated_api):
    """Job List: Filter - location_group_id"""

    JobFactory.create_batch(size=2)
    location_group = LocationGroupSharedCoreObjectFactory(remote_id="123", type="fklgp")
    job = JobFactory(
        location_group=location_group, account=seed_authenticated_api.account
    )

    response = seed_authenticated_api.api.get(
        data={"restaurant_group_id": job.location_group.remote_id}
    )

    assert response.status_code == status.HTTP_200_OK
    assert response.data["count"] == 1

    assert response.data["results"][0]["connector"]["id"] == job.connector.id
    assert (
        response.data["results"][0]["location_group"]["id"] == location_group.remote_id
    )
    __assert_job_serialized_structure(response.data)


@pytest.mark.api("job-list")
def test_list__filter__restaurant_id(seed_authenticated_api):
    """Job List: Filter - location_id"""

    JobFactory.create_batch(size=2)
    location = LocationSharedCoreObjectFactory(remote_id="123", type="fkl")
    job = JobFactory(location=location, account=seed_authenticated_api.account)

    response = seed_authenticated_api.api.get(
        data={"restaurant_id": job.location.remote_id}
    )

    assert response.status_code == status.HTTP_200_OK
    assert response.data["count"] == 1

    assert response.data["results"][0]["connector"]["id"] == job.connector.id
    assert response.data["results"][0]["location"]["id"] == location.remote_id
    __assert_job_serialized_structure(response.data)


@pytest.mark.api("job-list")
@patch("apps.utils.base.settings.PIQ_CORE_CLIENT.get_accessible_account_ids_for")
def test_list__filter__account_ids(mock_patcher, api):
    """Job List: Filter - account_ids"""

    JobFactory.create_batch(size=2)
    account1 = AccountSharedCoreObjectFactory(remote_id="12345", type="fkracc")
    account2 = AccountSharedCoreObjectFactory(remote_id="98765", type="fkracc")
    job_01 = JobFactory(account=account1)
    job_02 = JobFactory(account=account2)

    user = UserWithBearerTokenFactory.create()
    api.set_credentials(user, bearer=True)
    api.set_url_params()

    rest_acc_ids = [job_01.account.remote_id, job_02.account.remote_id]
    mock_patcher.return_value = rest_acc_ids

    response = api.get(
        data={"restaurant_account_id": [account1.remote_id, account2.remote_id]}
    )

    assert response.status_code == status.HTTP_200_OK
    assert response.data["count"] == 2

    acc_ids = {response.data["results"][x]["account"]["id"] for x in range(2)}
    assert acc_ids == {account1.remote_id, account2.remote_id}

    __assert_job_serialized_structure(response.data)


@pytest.mark.api("job-list")
@patch("apps.utils.base.settings.PIQ_CORE_CLIENT.get_accessible_account_ids_for")
def test_list__filter_by__connector_name(mock_patcher, api):
    """Job List: Filter - Connector name"""

    user = UserWithBearerTokenFactory.create()
    api.set_credentials(user, bearer=True)
    api.set_url_params()

    account1 = AccountSharedCoreObjectFactory(remote_id="12345", type="fkracc")
    account2 = AccountSharedCoreObjectFactory(remote_id="98765", type="fkracc")

    # Total 4 jobs in system
    JobFactory.create_batch(size=2)
    job_01 = JobFactory(
        account=account1, connector=ConnectorFactory.create(name="Test1")
    )
    job_02 = JobFactory(
        account=account2, connector=ConnectorFactory.create(name="Test2")
    )

    rest_acc_ids = [job_01.account.remote_id, job_02.account.remote_id]
    mock_patcher.return_value = rest_acc_ids

    response = api.get(data={"name": "2"})

    assert response.status_code == status.HTTP_200_OK
    assert response.data["count"] == 1
    assert response.data["results"][0]["connector"]["name"] == "Test2"

    __assert_job_serialized_structure(response.data)


@pytest.mark.api("job-list")
def test_list__filter_by__adapter_code(seed_authenticated_api):
    """Job List: Filter - Connector name"""
    job1 = JobFactory(account=seed_authenticated_api.account)
    JobFactory(account=seed_authenticated_api.account)

    seed_authenticated_api.api.set_url_params()
    response = seed_authenticated_api.api.get(
        data={"adapter_code": job1.connector.adapter_code}
    )

    assert response.status_code == status.HTTP_200_OK
    assert response.data["count"] == 1
    assert response.data["results"][0]["id"] == job1.id

    __assert_job_serialized_structure(response.data)


@pytest.mark.skip("This is currently non-deterministic, needs to be fixed")
@pytest.mark.api("job-list")
def test_list__order_by_connector_id(seed_authenticated_api):
    """Job List: ordering - connector_id"""
    jobs = JobFactory.create_batch(size=2)
    expected = [job.id for job in sorted(jobs, key=lambda j: j.connector_id)]

    response = seed_authenticated_api.api.get(data={"ordering": "connector_id"})

    assert response.status_code == status.HTTP_200_OK
    assert response.data["count"] == 2

    assert expected == [
        response.data["results"][0]["id"],
        response.data["results"][1]["id"],
    ]

    __assert_job_serialized_structure(response.data)


@pytest.mark.api("job-detail")
@pytest.mark.parametrize("enabled", [True, False])
def test_retrieve__enabled(seed_authenticated_api, enabled):
    """Job Retrieve - Field Enable"""

    job = JobFactory(enabled=enabled, account=seed_authenticated_api.account)

    api = seed_authenticated_api.api
    api.set_url_params(pk=job.id)
    response = api.get()

    assert response.status_code == status.HTTP_200_OK
    assert response.data["enabled"] == enabled
    __assert_job_serialized_structure_and_values(response.data, job=job)


@pytest.mark.api("job-detail")
def test_retrieve__last_run(seed_authenticated_api):
    """Job Retrieve - Field Enable"""

    job = JobFactory(enabled=True, account=seed_authenticated_api.account)

    run = RunFactory.create(job=job)
    run.record_execution_start()
    run.record_success()

    api = seed_authenticated_api.api
    api.set_url_params(pk=job.id)
    response = api.get()

    assert response.status_code == status.HTTP_200_OK
    __assert_job_serialized_structure_and_values(response.data, job=job)


@pytest.mark.api("job-detail")
def test_retrieve__piiq_mappings(seed_authenticated_api):
    """Job Retrieve - Field PIQ Location Mapping"""

    job = JobFactory(account=seed_authenticated_api.account)
    piq_mappings = PIQMappingFactory.create_batch(size=2, job=job)

    api = seed_authenticated_api.api
    api.set_url_params(pk=job.id)
    response = api.get()

    assert response.status_code == status.HTTP_200_OK
    assert len(response.data["piq_mappings"]) == 2
    __assert_job_serialized_structure_and_values(
        response.data, job=job, piq_mappings=piq_mappings
    )


@pytest.mark.api("job-list")
@pytest.mark.parametrize("method", ["put", "patch", "delete"])
def test_list__disallowed_http_methods(seed_authenticated_api, method):
    """Job List Methods - Not allowed"""

    body = {
        "connector": 999999,
        "username": "fake_user",
        "password": "fake_password",
        "enabled": False,
        "restaurant_account_id": "fake_restaurant_account_id",
        "restaurant_group_id": 999999,
        "restaurant_id": 8888888,
        "candidate_restaurant_ids": [],
    }
    api = seed_authenticated_api.api
    api.set_url_params()

    response = getattr(api, method)(data=body, format="json")

    assert response.status_code == status.HTTP_405_METHOD_NOT_ALLOWED


@pytest.mark.api("job-detail")
@pytest.mark.parametrize("method", ["post", "put"])
def test_detail__disallowed_http_methods(seed_authenticated_api, method):
    """Job Detail Methods - Not allowed"""

    connector = ConnectorFactory()

    body = {
        "connector": connector.id,
        "username": "fake_user",
        "password": "fake_password",
        "enabled": False,
        "restaurant_account_id": seed_authenticated_api.account.remote_id,
        "restaurant_group_id": 999999,
        "restaurant_id": 8888888,
        "candidate_restaurant_ids": [],
    }
    api = seed_authenticated_api.api
    api.set_url_params(pk=None)

    response = getattr(api, method)(data=body, format="json")

    assert response.status_code == status.HTTP_405_METHOD_NOT_ALLOWED


@pytest.mark.api("job-list")
@pytest.mark.parametrize(
    "connector_enabled,enabled",
    [
        (
            True,
            "True",
        ),
        (
            True,
            "False",
        ),
        (
            False,
            "True",
        ),
        (
            False,
            "False",
        ),
    ],
)
def test_post__enabled__success(seed_authenticated_api, connector_enabled, enabled):
    """Job List Post Job: Field Enabled"""
    account = seed_authenticated_api.account
    connector = ConnectorFactory(enabled=connector_enabled)
    job = JobFactory(account=account, enabled=enabled)
    seed_authenticated_api.api.set_url_params()

    location = Location.create_local_object(
        {
            "id": 1235,
            "url": "http://location/123",
            "display_name": "fake_location 123",
        }
    )

    location_group = LocationGroup.create_local_object(
        {
            "id": 1236,
            "url": "http://location_group/123",
            "display_name": "fake_location_group 123",
        }
    )

    body = {
        "connector": connector.id,
        "username": "fake_user",
        "password": "fake_password",
        "enabled": enabled,
        "restaurant_account_id": account.remote_id,
        "restaurant_group_id": location_group.remote_id,
        "restaurant_id": location.remote_id,
        "candidate_restaurant_ids": [],
        "file_discovery_action": {"document_type": "invoice", "action_type": "none"},
    }

    mock_location_grp_patcher = patch(
        "spices.django3.coreobjects.models.Location.try_retrieve"
    )
    mock_location_grp = mock_location_grp_patcher.start()
    mock_location_grp.return_value = location_group

    mock_location_patcher = patch(
        "spices.django3.coreobjects.models.LocationGroup.try_retrieve"
    )
    mock_location = mock_location_patcher.start()
    mock_location.return_value = location

    response = seed_authenticated_api.api.post(data=body, format="json")

    mock_location_grp_patcher.stop()
    mock_location_patcher.stop()

    assert response.status_code == status.HTTP_201_CREATED


@pytest.mark.api("job-list")
@pytest.mark.parametrize(
    "username, expected_error_code, expected_error_dict",
    [(None, "null", {"username": ["This field may not be null."]})],
)
def test_post__invalid_username(
    seed_authenticated_api, username, expected_error_code, expected_error_dict
):
    """Job List Post Job: Field username"""

    job = JobFactory(
        username="existing_username", account=seed_authenticated_api.account
    )

    body = {
        "connector": job.connector.id,
        "username": username,
        "password": "fake_password",
        "enabled": True,
        "restaurant_account_id": job.account.remote_id,
        "restaurant_group_id": 999999,
        "restaurant_id": 8888888,
        "candidate_restaurant_ids": [],
        "file_discovery_action": {"document_type": "invoice", "action_type": "none"},
    }

    api = seed_authenticated_api.api
    api.set_url_params()
    response = api.post(data=body, format="json")

    assert response.status_code == status.HTTP_400_BAD_REQUEST
    body = dict(response.json())
    error = body.pop("error")
    assert expected_error_dict == body
    assert expected_error_dict == error["params"]
    assert expected_error_code == error["code"]


@pytest.mark.api("job-list")
@pytest.mark.parametrize(
    "enabled, expected_error_code, expected_error_dict",
    [
        (None, "null", {"enabled": ["This field may not be null."]}),
        (-9999, "invalid", {"enabled": ["Must be a valid boolean."]}),
        ("RANDOM", "invalid", {"enabled": ["Must be a valid boolean."]}),
    ],
)
def test_post__invalid_enabled(
    seed_authenticated_api, enabled, expected_error_code, expected_error_dict
):
    """Job List Post Job: Field Enabled with Invalid values"""

    connector = ConnectorFactory()
    job = JobFactory(account=seed_authenticated_api.account)

    body = {
        "connector": connector.id,
        "username": "fake_username",
        "password": "fake_password",
        "enabled": enabled,
        "account_id": job.account.remote_id,
        "restaurant_group_id": 999999,
        "restaurant_id": 8888888,
        "candidate_restaurant_ids": [],
        "file_discovery_action": {"document_type": "invoice", "action_type": "none"},
    }

    api = seed_authenticated_api.api
    api.set_url_params()
    response = api.post(data=body, format="json")

    assert response.status_code == status.HTTP_400_BAD_REQUEST
    body = dict(response.json())
    error = body.pop("error")
    assert expected_error_dict == body
    assert expected_error_dict == error["params"]
    assert expected_error_code == error["code"]


@pytest.mark.api("job-list")
def test_post__create_with_location_group_id_as_none(seed_authenticated_api):
    """Job Details Post Job: Mandatory Fields Only"""

    connector = ConnectorFactory()

    account = seed_authenticated_api.account
    body = {
        "connector": connector.id,
        "username": "fake_user",
        "password": "fake_password",
        "enabled": True,
        "location_group_id": None,
        "restaurant_account_id": account.remote_id,
    }

    api = seed_authenticated_api.api
    api.set_url_params()
    response = api.post(data=body, format="json")

    assert response.status_code == status.HTTP_201_CREATED


@pytest.mark.api("job-list")
def test_post__create_with_location_id_as_none(seed_authenticated_api):
    """Job Details Post Job: Mandatory Fields Only"""

    connector = ConnectorFactory()

    account = seed_authenticated_api.account
    body = {
        "connector": connector.id,
        "username": "fake_user",
        "password": "fake_password",
        "enabled": True,
        "location_id": None,
        "restaurant_account_id": account.remote_id,
    }

    api = seed_authenticated_api.api
    api.set_url_params()
    response = api.post(data=body, format="json")

    assert response.status_code == status.HTTP_201_CREATED


@pytest.mark.api("job-list")
def test_post__create_with_mandatory_fields_only(seed_authenticated_api):
    """Job Details Post Job: Mandatory Fields Only"""

    connector = ConnectorFactory()

    location = Location.create_local_object(
        {
            "id": 1235,
            "url": "http://location/123",
            "display_name": "fake_location 123",
        }
    )

    location_group = LocationGroup.create_local_object(
        {
            "id": 1236,
            "url": "http://location_group/123",
            "display_name": "fake_location_group 123",
        }
    )

    account = seed_authenticated_api.account
    body = {
        "connector": connector.id,
        "username": "fake_user",
        "password": "fake_password",
        "enabled": True,
        "restaurant_account_id": account.remote_id,
    }

    mock_location_grp_patcher = patch(
        "spices.django3.coreobjects.models.Location.try_retrieve"
    )
    mock_location_grp = mock_location_grp_patcher.start()
    mock_location_grp.return_value = location_group

    mock_location_patcher = patch(
        "spices.django3.coreobjects.models.LocationGroup.try_retrieve"
    )
    mock_location = mock_location_patcher.start()
    mock_location.return_value = location

    api = seed_authenticated_api.api
    api.set_url_params()
    response = api.post(data=body, format="json")

    mock_location_grp_patcher.stop()
    mock_location_patcher.stop()

    assert response.status_code == status.HTTP_201_CREATED


@pytest.mark.api("job-list")
def test_post__create_with_file_discovery_action(seed_authenticated_api):
    """Job Details Post Job: Mandatory Fields Only"""

    connector = ConnectorFactory()

    account = seed_authenticated_api.account

    location = Location.create_local_object(
        {
            "id": 1235,
            "url": "http://location/123",
            "display_name": "fake_location 123",
        }
    )

    location_group = LocationGroup.create_local_object(
        {
            "id": 1236,
            "url": "http://location_group/123",
            "display_name": "fake_location_group 123",
        }
    )

    body = {
        "connector": connector.id,
        "username": "fake_user",
        "password": "fake_password",
        "enabled": True,
        "restaurant_account_id": account.remote_id,
        "file_discovery_action": {"document_type": "invoice", "action_type": "none"},
    }

    mock_location_grp_patcher = patch(
        "spices.django3.coreobjects.models.Location.try_retrieve"
    )
    mock_location_grp = mock_location_grp_patcher.start()
    mock_location_grp.return_value = location_group

    mock_location_patcher = patch(
        "spices.django3.coreobjects.models.LocationGroup.try_retrieve"
    )
    mock_location = mock_location_patcher.start()
    mock_location.return_value = location

    response = seed_authenticated_api.api.post(data=body, format="json")

    mock_location_grp_patcher.stop()
    mock_location_patcher.stop()

    assert response.status_code == status.HTTP_201_CREATED

    job_id = response.data.get("id")

    job = Job.objects.get(id=job_id)
    discovery_action: FileDiscoveryAction = job.document_discovery_actions.filter(
        document_type="invoice"
    ).first()

    assert discovery_action.action_type == FileDiscoveryActionType.NONE.ident


@pytest.mark.api("job-list")
def test_post__create_with_companies_with_remote_ids__success(seed_authenticated_api):
    """Job List: Filter - company_id"""

    connector = ConnectorFactory()
    company1 = CompanySharedCoreObjectFactory.create()
    company2 = CompanySharedCoreObjectFactory.create()
    account = seed_authenticated_api.account

    location = Location.create_local_object(
        {
            "id": 1235,
            "url": "http://location/123",
            "display_name": "fake_location 123",
        }
    )

    location_group = LocationGroup.create_local_object(
        {
            "id": 1236,
            "url": "http://location_group/123",
            "display_name": "fake_location_group 123",
        }
    )
    body = {
        "companies": [company1.remote_id, company2.remote_id],
        "login_url": "https://aeportasdavia.restaurant365.com/",
        "connector": connector.id,
        "username": "fake_user1",
        "password": "fake_password1",
        "enabled": True,
        "restaurant_account_id": seed_authenticated_api.account.remote_id,
    }

    mock_location_grp_patcher = patch(
        "spices.django3.coreobjects.models.Location.try_retrieve"
    )
    mock_location_grp = mock_location_grp_patcher.start()
    mock_location_grp.return_value = location_group

    mock_location_patcher = patch(
        "spices.django3.coreobjects.models.LocationGroup.try_retrieve"
    )
    mock_location = mock_location_patcher.start()
    mock_location.return_value = location

    response = seed_authenticated_api.api.post(data=body, format="json")
    mock_location_grp_patcher.stop()
    mock_location_patcher.stop()

    assert response.status_code == status.HTTP_201_CREATED
    company_ids = {response.data["companies"][x] for x in range(2)}
    assert company_ids == {company1.remote_id, company2.remote_id}


@pytest.mark.api("job-list")
def test_post__create_with_optional_fields_as_none__success(seed_authenticated_api):
    """Job Details Post Job: Optional Fields None"""

    connector = ConnectorFactory()

    account = seed_authenticated_api.account

    location = Location.create_local_object(
        {
            "id": 1235,
            "url": "http://location/123",
            "display_name": "fake_location 123",
        }
    )

    location_group = LocationGroup.create_local_object(
        {
            "id": 1236,
            "url": "http://location_group/123",
            "display_name": "fake_location_group 123",
        }
    )

    body = {
        "connector": connector.id,
        "username": "fake_user",
        "password": "fake_password",
        "enabled": True,
        "restaurant_account_id": account.remote_id,
        "restaurant_group_id": None,
        "restaurant_id": None,
        "candidate_restaurant_ids": [],
        "companies": [],
        "file_discovery_action": None,
    }

    mock_location_grp_patcher = patch(
        "spices.django3.coreobjects.models.Location.try_retrieve"
    )
    mock_location_grp = mock_location_grp_patcher.start()
    mock_location_grp.return_value = location_group

    mock_location_patcher = patch(
        "spices.django3.coreobjects.models.LocationGroup.try_retrieve"
    )
    mock_location = mock_location_patcher.start()
    mock_location.return_value = location

    response = seed_authenticated_api.api.post(data=body, format="json")

    mock_location_grp_patcher.stop()
    mock_location_patcher.stop()

    assert response.status_code == status.HTTP_201_CREATED


@pytest.mark.api("job-list")
def test_post__create_job_conflict_unique_same_account__success(seed_authenticated_api):
    """Job Details Post Job: Unique fields constraint : connector, login_url, username for same account"""

    connector = ConnectorFactory()

    account = seed_authenticated_api.account

    location = Location.create_local_object(
        {
            "id": "1235",
            "url": "http://location/123",
            "display_name": "fake_location 123",
        }
    )

    location_group = LocationGroup.create_local_object(
        {
            "id": "1236",
            "url": "http://location_group/123",
            "display_name": "fake_location_group 123",
        }
    )

    body = {
        "connector": connector.id,
        "username": "fake_user",
        "password": "fake_password",
        "enabled": True,
        "restaurant_account_id": account.remote_id,
        "restaurant_group_id": None,
        "restaurant_id": None,
        "candidate_restaurant_ids": [],
        "companies": [],
        "file_discovery_action": None,
    }

    job = JobFactory(
        connector=connector, account=account, username="fake_user", login_url=""
    )

    mock_location_grp_patcher = patch(
        "spices.django3.coreobjects.models.Location.try_retrieve"
    )
    mock_location_grp = mock_location_grp_patcher.start()
    mock_location_grp.return_value = location_group

    mock_location_patcher = patch(
        "spices.django3.coreobjects.models.LocationGroup.try_retrieve"
    )
    mock_location = mock_location_patcher.start()
    mock_location.return_value = location

    response = seed_authenticated_api.api.post(data=body, format="json")

    mock_location_grp_patcher.stop()
    mock_location_patcher.stop()

    assert response.status_code == status.HTTP_409_CONFLICT
    __assert_job_serialized_structure_and_values(response.data, job=job)


@pytest.mark.api("job-list")
def test_post__create_job_conflict_unique_different_account__success(
    seed_authenticated_api,
):
    """Job Details Post Job: Unique fields constraint : connector, login_url, username for different account"""

    connector = ConnectorFactory()

    account = seed_authenticated_api.account

    location = Location.create_local_object(
        {
            "id": "1235",
            "url": "http://location/123",
            "display_name": "fake_location 123",
        }
    )

    location_group = LocationGroup.create_local_object(
        {
            "id": "1236",
            "url": "http://location_group/123",
            "display_name": "fake_location_group 123",
        }
    )

    body = {
        "connector": connector.id,
        "username": "fake_user",
        "password": "fake_password",
        "enabled": True,
        "restaurant_account_id": account.remote_id,
        "restaurant_group_id": None,
        "restaurant_id": None,
        "candidate_restaurant_ids": [],
        "companies": [],
        "file_discovery_action": None,
    }

    job = JobFactory(connector=connector, username="fake_user", login_url="")

    mock_location_grp_patcher = patch(
        "spices.django3.coreobjects.models.Location.try_retrieve"
    )
    mock_location_grp = mock_location_grp_patcher.start()
    mock_location_grp.return_value = location_group

    mock_location_patcher = patch(
        "spices.django3.coreobjects.models.LocationGroup.try_retrieve"
    )
    mock_location = mock_location_patcher.start()
    mock_location.return_value = location

    response = seed_authenticated_api.api.post(data=body, format="json")

    mock_location_grp_patcher.stop()
    mock_location_patcher.stop()

    assert response.status_code == status.HTTP_409_CONFLICT


@pytest.mark.api("job-detail")
@patch("spices.django3.coreobjects.models.LocationGroup.try_retrieve")
@patch("spices.django3.coreobjects.models.Location.try_retrieve")
def test_patch__conflict_unique_same_account__success(
    mock_loc, mock_loc_grp, seed_authenticated_api
):
    """Job Details Patch Job: Mandatory Fields only"""

    connector = ConnectorFactory()
    username = str(uuid.uuid4())
    job1 = JobFactory(
        connector=connector,
        username=username,
        login_url="",
        account=seed_authenticated_api.account,
    )
    job = JobFactory(
        connector=connector,
        username=str(uuid.uuid4()),
        login_url="",
        account=seed_authenticated_api.account,
    )

    body = {
        "username": username,
        "password": "fake_password1",
        "enabled": True,
        "restaurant_account_id": job.account.remote_id,
    }

    mock_loc_grp.return_value = None
    mock_loc.return_value = None

    api = seed_authenticated_api.api
    api.set_url_params(pk=job.id)
    response = api.patch(data=body, format="json")

    assert response.status_code == status.HTTP_409_CONFLICT
    __assert_job_serialized_structure_and_values(response.data, job=job1)


@pytest.mark.api("job-detail")
@patch("spices.django3.coreobjects.models.LocationGroup.try_retrieve")
@patch("spices.django3.coreobjects.models.Location.try_retrieve")
def test_patch__success_with_different_params(
    mock_loc, mock_loc_grp, seed_authenticated_api
):
    """Job Details Patch Job: Mandatory Fields only"""

    connector = ConnectorFactory()
    job = JobFactory(
        connector=connector,
        username=str(uuid.uuid4()),
        login_url="",
        account=seed_authenticated_api.account,
    )

    mock_loc_grp.return_value = None
    mock_loc.return_value = None

    api = seed_authenticated_api.api
    api.set_url_params(pk=job.id)
    body = {"enabled": True, "restaurant_account_id": job.account.remote_id}
    response = api.patch(data=body, format="json")

    assert response.status_code == status.HTTP_200_OK


@pytest.mark.api("job-detail")
@patch("spices.django3.coreobjects.models.LocationGroup.try_retrieve")
@patch("spices.django3.coreobjects.models.Location.try_retrieve")
def test_patch__success_for_login_url(mock_loc, mock_loc_grp, seed_authenticated_api):
    """Job Details Patch Job: Mandatory Fields only"""

    connector = ConnectorFactory(
        adapter_code="r365_v1"
    )  # login can only be considered for r365
    job = JobFactory(
        connector=connector,
        username=str(uuid.uuid4()),
        login_url="",
        account=seed_authenticated_api.account,
    )

    mock_loc_grp.return_value = None
    mock_loc.return_value = None

    api = seed_authenticated_api.api
    api.set_url_params(pk=job.id)
    body = {
        "login_url": str(uuid.uuid4()),
        "restaurant_account_id": job.account.remote_id,
    }
    response = api.patch(data=body, format="json")

    assert response.status_code == status.HTTP_200_OK


@pytest.mark.api("job-detail")
@patch("spices.django3.coreobjects.models.LocationGroup.try_retrieve")
@patch("spices.django3.coreobjects.models.Location.try_retrieve")
def test_patch__mandatory_fields_only(mock_loc, mock_loc_grp, seed_authenticated_api):
    """Job Details Patch Job: Mandatory Fields only"""

    connector = ConnectorFactory()
    username = str(uuid.uuid4())
    job = JobFactory(
        username=username, connector=connector, account=seed_authenticated_api.account
    )

    body = {
        "username": username,
        "restaurant_account_id": job.account.remote_id,
    }

    mock_loc_grp.return_value = None
    mock_loc.return_value = None

    api = seed_authenticated_api.api
    api.set_url_params(pk=job.id)
    response = api.patch(data=body, format="json")

    assert response.status_code == status.HTTP_200_OK


@pytest.mark.api("job-detail")
@patch("spices.django3.coreobjects.models.LocationGroup.try_retrieve")
@patch("spices.django3.coreobjects.models.Location.try_retrieve")
def test_patch__optional_fields__none(mock_loc, mock_loc_grp, seed_authenticated_api):
    """Job Details Patch Job: Optional Fields None"""

    connector = ConnectorFactory()
    username = str(uuid.uuid4())
    job = JobFactory(
        username=username, connector=connector, account=seed_authenticated_api.account
    )

    body = {
        "connector": connector.id,
        "username": username,
        "password": "fake_password",
        "enabled": True,
        "restaurant_account_id": job.account.remote_id,
        "restaurant_group_id": None,
        "restaurant_id": None,
        "candidate_restaurant_ids": None,
    }

    mock_loc_grp.return_value = None
    mock_loc.return_value = None

    api = seed_authenticated_api.api
    api.set_url_params(pk=job.id)
    response = api.patch(data=body, format="json")

    assert response.status_code == status.HTTP_200_OK


@pytest.mark.api("job-detail")
def test_delete_job__invalid_account(seed_authenticated_api):
    """Job Details delete"""

    connector = ConnectorFactory()
    job = JobFactory(connector=connector)
    api = seed_authenticated_api.api
    api.set_url_params(pk=job.id)
    response = api.delete()

    assert response.status_code == status.HTTP_404_NOT_FOUND


@pytest.mark.api("job-detail")
def test_delete_job__invalid_job_id(seed_authenticated_api):
    """Job Details delete"""

    api = seed_authenticated_api.api
    api.set_url_params(pk="invalidjobid")
    response = api.delete()

    assert response.status_code == status.HTTP_404_NOT_FOUND


@pytest.mark.api("job-detail")
def test_delete_job__deleted_job(seed_authenticated_api):
    """Job Details delete"""

    connector = ConnectorFactory()
    job = JobFactory(connector=connector)
    job.delete()
    api = seed_authenticated_api.api
    api.set_url_params(pk=job.id)
    response = api.delete()

    assert response.status_code == status.HTTP_404_NOT_FOUND


@pytest.mark.api("job-detail")
def test_delete_job__success(seed_authenticated_api):
    """Job Details delete"""

    connector = ConnectorFactory()
    job = JobFactory(connector=connector, account=seed_authenticated_api.account)
    api = seed_authenticated_api.api
    api.set_url_params(pk=job.id)
    response = api.delete()

    assert response.status_code == status.HTTP_204_NO_CONTENT


@pytest.mark.api("job-list")
def test_list__filter__company_id(seed_authenticated_api):
    """Job List: Filter - company_id"""

    connector = ConnectorFactory(adapter_code="r365")
    company1 = CompanySharedCoreObjectFactory.create()
    # for validating the whether other jobs are filtered out or not
    JobFactory.create(connector=connector, account=seed_authenticated_api.account)

    job = JobFactory.create(connector=connector, account=seed_authenticated_api.account)
    job.companies.add(company1)
    response = seed_authenticated_api.api.get(data={"company_id": company1.remote_id})

    assert response.status_code == status.HTTP_200_OK
    assert response.data["count"] == 1

    company_ids = {response.data["results"][x]["companies"][0] for x in range(1)}
    assert company_ids == {company1.id}

    __assert_job_serialized_structure(response.data)
