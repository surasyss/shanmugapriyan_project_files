import copy
from unittest import mock
from unittest.mock import patch

import pytest
from rest_framework import status
from spices.django3.coreobjects.models import Location

from spices.django3.testing.factory.user import UserWithBearerTokenFactory

from spices.django3.testing.factory.shared_core_object_model import (
    LocationSharedCoreObjectFactory,
)
from tests.apps.jobconfig.factories import PIQMappingFactory, JobFactory


def __assert_site_serialized_structure(piq_map_dict: dict):
    piq_map_dict = copy.copy(piq_map_dict)
    piq_map_list = piq_map_dict.pop("results")

    assert isinstance(piq_map_list, list)
    assert isinstance(piq_map_dict.pop("count"), int)
    assert piq_map_dict.pop("next") is None
    assert piq_map_dict.pop("previous") is None
    assert not piq_map_dict

    if piq_map_list:
        piq_map = piq_map_list[0]
        piq_data = piq_map.pop("piq_data")
        piq_restaurant_id = piq_map.pop("piq_restaurant_id")
        mapped_to = piq_map.pop("mapped_to")
        assert isinstance(piq_map.pop("id"), str)
        if piq_restaurant_id:
            assert isinstance(piq_restaurant_id, int)
        assert isinstance(piq_map.pop("name"), str)
        assert isinstance(piq_map.pop("mapping_data"), str)
        assert isinstance(piq_map.pop("job"), str)
        if mapped_to:
            assert isinstance(mapped_to, int)
        if piq_data:
            assert isinstance(piq_data, dict)

        assert not piq_map


def __assert_site_serialized_structure_and_values(piq_map_dict: dict, **kwargs):
    piq_map_dict = copy.copy(piq_map_dict)
    piq_data = piq_map_dict.pop("piq_data")
    mapped_to = piq_map_dict.pop("mapped_to")

    assert piq_map_dict.pop("id") == kwargs["piq_mapping"].id
    assert piq_map_dict.pop("piq_restaurant_id") == int(
        kwargs["piq_mapping"].piq_data.remote_id
    )
    assert piq_map_dict.pop("name") == kwargs["piq_mapping"].mapping_data
    assert piq_map_dict.pop("mapping_data") == kwargs["piq_mapping"].mapping_data
    assert piq_map_dict.pop("job") == kwargs["piq_mapping"].job.id

    if mapped_to:
        assert mapped_to == kwargs["piq_mapping"].mapped_to
    else:
        assert mapped_to is None

    if piq_data:
        assert piq_data["id"] == str(kwargs["piq_mapping"].piq_data.remote_id)
        assert piq_data["name"] == kwargs["piq_mapping"].piq_data.display_name

    assert not piq_map_dict


@pytest.mark.api("job-piq_mappings-list")
@pytest.mark.parametrize("count", [0, 1, 2])
@patch("apps.utils.base.settings.PIQ_CORE_CLIENT.get_accessible_account_ids_for")
def test_list__piq_mapping__happy_case(mock_patcher, api, count):
    """Listing piq location mappings for a particular job with 'x' no. of results"""

    PIQMappingFactory()
    job = JobFactory()
    for index in range(count):
        PIQMappingFactory(job=job)

    user = UserWithBearerTokenFactory.create()
    api.set_credentials(user, bearer=True)
    api.set_url_params(job_id=job.id)
    mock_patcher.return_value = [job.account.remote_id]
    response = api.get()

    assert response.status_code == status.HTTP_200_OK
    assert response.data["count"] == count
    assert len(response.data["results"]) == count
    __assert_site_serialized_structure(response.data)


@pytest.mark.api("job-piq_mappings-list")
@patch("apps.utils.base.settings.PIQ_CORE_CLIENT.get_accessible_account_ids_for")
def test_list__piq_mapping__job__not_existing(mock_patcher, api):
    """Listing piq location mappings for an NonExisting job"""

    piq_mapping = PIQMappingFactory()

    user = UserWithBearerTokenFactory.create()
    api.set_credentials(user, bearer=True)
    api.set_url_params(job_id=999999)
    mock_patcher.return_value = [piq_mapping.job.account.remote_id]
    response = api.get()

    assert response.status_code == status.HTTP_200_OK
    assert response.data["count"] == 0
    assert len(response.data["results"]) == 0
    __assert_site_serialized_structure(response.data)


@pytest.mark.api("job-piq_mappings-list")
@pytest.mark.parametrize("piq_data_id, result_count", [(1, 1), (10, 1), (-1, 0)])
@patch("apps.utils.base.settings.PIQ_CORE_CLIENT.get_accessible_account_ids_for")
def test_list__piq_mapping__filters__piq_restaurant_id(
    mock_patcher, api, piq_data_id, result_count
):
    """Listing piq location mappings after piq_data_id filter is applied"""

    job = JobFactory()
    location1 = LocationSharedCoreObjectFactory(remote_id=1)
    location2 = LocationSharedCoreObjectFactory(remote_id=10)
    PIQMappingFactory(job=job, piq_data=location1)
    PIQMappingFactory(job=job, piq_data=location2)

    user = UserWithBearerTokenFactory.create()
    api.set_credentials(user, bearer=True)
    api.set_url_params(job_id=job.id)
    mock_patcher.return_value = [job.account.remote_id]
    response = api.get(data={"piq_restaurant_id": piq_data_id})

    assert response.status_code == status.HTTP_200_OK
    assert response.data["count"] == result_count
    assert len(response.data["results"]) == result_count
    if result_count != 0:
        assert response.data["results"][0]["piq_restaurant_id"] == piq_data_id
        assert response.data["results"][0]["piq_data"]["id"] == str(piq_data_id)
    __assert_site_serialized_structure(response.data)


@pytest.mark.api("job-piq_mappings-list")
@pytest.mark.parametrize(
    "name, result_count",
    [("fake_name_01", 1), ("fake_name_02", 1), ("non-existing", 0)],
)
@patch("apps.utils.base.settings.PIQ_CORE_CLIENT.get_accessible_account_ids_for")
def test_list__piq_mapping__filters__name(mock_patcher, api, name, result_count):
    """Listing piq location mappings after piq_restaurant_id filter is applied"""

    job = JobFactory()
    PIQMappingFactory(job=job, mapping_data="fake_name_01")
    PIQMappingFactory(job=job, mapping_data="fake_name_02")

    user = UserWithBearerTokenFactory.create()
    api.set_credentials(user, bearer=True)
    api.set_url_params(job_id=job.id)
    mock_patcher.return_value = [job.account.remote_id]
    response = api.get(data={"name": name})

    assert response.status_code == status.HTTP_200_OK
    assert response.data["count"] == result_count
    assert len(response.data["results"]) == result_count
    if result_count != 0:
        assert response.data["results"][0]["name"] == name
        assert response.data["results"][0]["mapping_data"] == name
    __assert_site_serialized_structure(response.data)


@pytest.mark.api("job-piq_mappings-list")
@pytest.mark.parametrize(
    "order, expected_order",
    [("piq_data__remote_id", [1, 10]), ("-piq_data__remote_id", [10, 1])],
)
@patch("apps.utils.base.settings.PIQ_CORE_CLIENT.get_accessible_account_ids_for")
def test_list__piq_mapping__orders__location_id(
    mock_patcher, api, order, expected_order
):
    """Listing piq location mappings Order by piq_data_id"""

    job = JobFactory()
    location1 = LocationSharedCoreObjectFactory(remote_id=1)
    location2 = LocationSharedCoreObjectFactory(remote_id=10)
    PIQMappingFactory(job=job, piq_data=location1)
    PIQMappingFactory(job=job, piq_data=location2)

    user = UserWithBearerTokenFactory.create()
    api.set_credentials(user, bearer=True)
    api.set_url_params(job_id=job.id)
    mock_patcher.return_value = [job.account.remote_id]
    response = api.get(data={"ordering": order})

    assert response.status_code == status.HTTP_200_OK
    assert response.data["count"] == 2
    assert len(response.data["results"]) == 2
    assert response.data["results"][0]["piq_data"]["id"] == str(expected_order[0])
    assert response.data["results"][1]["piq_data"]["id"] == str(expected_order[1])
    assert response.data["results"][0]["piq_restaurant_id"] == expected_order[0]
    assert response.data["results"][1]["piq_restaurant_id"] == expected_order[1]
    __assert_site_serialized_structure(response.data)


@pytest.mark.api("job-piq_mappings-list")
@pytest.mark.parametrize(
    "order, expected_order",
    [
        ("mapping_data", ["fake_piq_mapping_01", "fake_piq_mapping_02"]),
        ("-mapping_data", ["fake_piq_mapping_02", "fake_piq_mapping_01"]),
    ],
)
@patch("apps.utils.base.settings.PIQ_CORE_CLIENT.get_accessible_account_ids_for")
def test_list__piq_mapping__orders__name(mock_patcher, api, order, expected_order):
    """Listing piq location mappings Order by name"""

    job = JobFactory()
    PIQMappingFactory(job=job, mapping_data="Fake_piq_mapping_01")
    PIQMappingFactory(job=job, mapping_data="Fake_piq_mapping_02")

    user = UserWithBearerTokenFactory.create()
    api.set_credentials(user, bearer=True)
    api.set_url_params(job_id=job.id)
    mock_patcher.return_value = [job.account.remote_id]
    response = api.get(data={"ordering": order})

    assert response.status_code == status.HTTP_200_OK
    assert response.data["count"] == 2
    assert len(response.data["results"]) == 2
    assert response.data["results"][0]["name"] == expected_order[0]
    assert response.data["results"][1]["name"] == expected_order[1]
    assert response.data["results"][0]["mapping_data"] == expected_order[0]
    assert response.data["results"][1]["mapping_data"] == expected_order[1]
    __assert_site_serialized_structure(response.data)


@pytest.mark.api("job-piq_mappings-detail")
@patch("apps.utils.base.settings.PIQ_CORE_CLIENT.get_accessible_account_ids_for")
def test_details__piq_mapping__happy_case(mock_patcher, api):
    """Detail piq location mappings: Happy case"""

    location = LocationSharedCoreObjectFactory(type="r")
    piq_mapping = PIQMappingFactory(piq_data=location)

    user = UserWithBearerTokenFactory.create()
    api.set_credentials(user, bearer=True)
    api.set_url_params(job_id=piq_mapping.job.id, pk=piq_mapping.id)
    mock_patcher.return_value = [piq_mapping.job.account.remote_id]
    response = api.get()

    assert response.status_code == status.HTTP_200_OK
    __assert_site_serialized_structure_and_values(
        response.data, piq_mapping=piq_mapping
    )


@pytest.mark.api("job-piq_mappings-detail")
@patch("apps.utils.base.settings.PIQ_CORE_CLIENT.get_accessible_account_ids_for")
def test_details__piq_mapping__non_existing__job(mock_patcher, api):
    """Detail piq location mappings: Non Existing Job"""

    piq_mapping = PIQMappingFactory()

    user = UserWithBearerTokenFactory.create()
    api.set_credentials(user, bearer=True)
    api.set_url_params(job_id=99999, pk=piq_mapping.id)
    mock_patcher.return_value = [piq_mapping.job.account.remote_id]
    response = api.get()

    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert response.data["detail"] == "Not found."


@pytest.mark.api("job-piq_mappings-detail")
@patch("apps.utils.base.settings.PIQ_CORE_CLIENT.get_accessible_account_ids_for")
def test_details__piq_mapping__non_existing__piq_mapping(mock_patcher, api):
    """Detail piq location mappings: Non Existing Job"""

    piq_mapping = PIQMappingFactory()

    user = UserWithBearerTokenFactory.create()
    api.set_credentials(user, bearer=True)
    api.set_url_params(job_id=piq_mapping.job.id, pk=99999)
    mock_patcher.return_value = [piq_mapping.job.account.remote_id]
    response = api.get()

    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert response.data["detail"] == "Not found."


@pytest.mark.api("job-piq_mappings-list")
@patch("apps.utils.base.settings.PIQ_CORE_CLIENT.get_accessible_account_ids_for")
@patch("spices.django3.coreobjects.models.Location.try_retrieve")
def test_list__piq_mapping__post__success(mock_location, mock_patcher, api):
    """PIQ Location Mapping: POST request Success"""

    job = JobFactory()

    user = UserWithBearerTokenFactory.create()
    api.set_credentials(user, bearer=True)
    api.set_url_params(job_id=job.id)

    loc = Location.create_local_object(
        {
            "id": 123,
            "url": "http://location/123",
            "display_name": "Loc 123",
        }
    )

    body = {
        "piq_restaurant_id": loc.remote_id,
        "name": "fake_name",
    }

    mock_location.return_value = loc
    mock_patcher.return_value = [job.account.remote_id]
    response = api.post(data=body, format="json")

    assert response.status_code == status.HTTP_201_CREATED


@pytest.mark.api("job-piq_mappings-list")
@patch("spices.django3.coreobjects.models.Location.try_retrieve")
@patch("apps.utils.base.settings.PIQ_CORE_CLIENT.get_accessible_account_ids_for")
def test_list__piq_mapping__post__already_existing(mock_patcher, mock_location, api):
    """PIQ Location Mapping: POST request Success"""

    job = JobFactory()
    loc = Location.create_local_object(
        {
            "id": 123,
            "url": "http://location/123",
            "display_name": "Loc 123",
        }
    )
    PIQMappingFactory(job=job, piq_data=loc, mapping_data="fake_name")

    user = UserWithBearerTokenFactory.create()
    api.set_credentials(user, bearer=True)
    api.set_url_params(job_id=job.id)

    body = {
        "piq_restaurant_id": loc.remote_id,
        "name": "fake_name",
    }

    mock_patcher.return_value = [job.account.remote_id]
    mock_location.return_value = loc

    response = api.post(data=body, format="json")

    assert response.status_code == status.HTTP_409_CONFLICT
    assert (
        response.data["error"]
        == f"piq_data_id: {loc.remote_id}, mapping_data: fake_name already Exists"
    )


@pytest.mark.api("job-piq_mappings-list")
@patch("apps.utils.base.settings.PIQ_CORE_CLIENT.get_accessible_account_ids_for")
def test_list__piq_mapping__post__piq_restaurant_id__null(mock_patcher, api):
    """PIQ Location Mapping: POST request with piq_restaurant_id = None"""

    job = JobFactory()

    user = UserWithBearerTokenFactory.create()
    api.set_credentials(user, bearer=True)
    api.set_url_params(job_id=job.id)
    body = {
        "piq_restaurant_id": None,
        "name": "fake_name",
    }
    mock_patcher.return_value = [job.account.remote_id]
    response = api.post(data=body, format="json")

    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert (
        response.data["piq_data_id"][0] == "This field is required and may not be null"
    )


@pytest.mark.api("job-piq_mappings-list")
@patch("apps.utils.base.settings.PIQ_CORE_CLIENT.get_accessible_account_ids_for")
def test_list__piq_mapping__post__name__null(mock_patcher, api):
    """PIQ Location Mapping: POST request with Name = None"""

    job = JobFactory()

    user = UserWithBearerTokenFactory.create()
    api.set_credentials(user, bearer=True)
    api.set_url_params(job_id=job.id)
    body = {
        "piq_restaurant_id": 1,
        "name": None,
    }
    mock_patcher.return_value = [job.account.remote_id]
    response = api.post(data=body, format="json")

    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert response.data["mapping_data"][0] == "This field may not be null."


@pytest.mark.api("job-piq_mappings-list")
@patch("apps.utils.base.settings.PIQ_CORE_CLIENT.get_accessible_account_ids_for")
def test_list__piq_mapping__post__piq_restaurant_id__blank(mock_patcher, api):
    """PIQ Location Mapping: POST request with piq_restaurant_id = Blank"""

    job = JobFactory()

    user = UserWithBearerTokenFactory.create()
    api.set_credentials(user, bearer=True)
    api.set_url_params(job_id=job.id)
    body = {
        "piq_restaurant_id": "",
        "name": "fake_name",
    }
    mock_patcher.return_value = [job.account.remote_id]
    response = api.post(data=body, format="json")

    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert (
        response.data["piq_data_id"][0] == "This field is required and may not be null"
    )


@pytest.mark.api("job-piq_mappings-list")
@patch("apps.utils.base.settings.PIQ_CORE_CLIENT.get_accessible_account_ids_for")
def test_list__piq_mapping__post__name__blank(mock_patcher, api):
    """PIQ Location Mapping: POST request with Name = Blank"""

    job = JobFactory()

    user = UserWithBearerTokenFactory.create()
    api.set_credentials(user, bearer=True)
    api.set_url_params(job_id=job.id)
    body = {
        "piq_restaurant_id": 1,
        "name": "",
    }
    mock_patcher.return_value = [job.account.remote_id]
    response = api.post(data=body, format="json")

    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert response.data["mapping_data"][0] == "This field may not be blank."


@pytest.mark.api("job-piq_mappings-list")
@patch("apps.utils.base.settings.PIQ_CORE_CLIENT.get_accessible_account_ids_for")
def test_list__piq_mapping__post__job__non_existing(mock_patcher, api):
    """PIQ Location Mapping: POST request with Non Existing Job"""

    job = JobFactory()
    user = UserWithBearerTokenFactory.create()
    api.set_credentials(user, bearer=True)
    api.set_url_params(job_id=999999)
    body = {
        "piq_restaurant_id": 1,
        "name": "fake_name",
    }
    mock_patcher.return_value = [job.account.remote_id]
    response = api.post(data=body, format="json")

    assert response.status_code == status.HTTP_404_NOT_FOUND


@pytest.mark.api("job-piq_mappings-detail")
@patch("spices.django3.coreobjects.models.Location.retrieve")
@patch("apps.utils.base.settings.PIQ_CORE_CLIENT.get_accessible_account_ids_for")
def test_detail__piq_mapping__patch__success(mock_patcher, mock_account, api):
    """PIQ Location Mapping: Patch Success"""

    location = LocationSharedCoreObjectFactory()
    piq_mapping = PIQMappingFactory(piq_data=location)

    user = UserWithBearerTokenFactory.create()
    api.set_credentials(user, bearer=True)
    api.set_url_params(job_id=piq_mapping.job.id, pk=piq_mapping.id)

    body = {
        "piq_restaurant_id": piq_mapping.piq_data.remote_id,
        "name": "fake_name_updated",
    }

    mock_account.return_value = piq_mapping.piq_data
    mock_patcher.return_value = [piq_mapping.job.account.remote_id]
    response = api.patch(data=body, format="json")

    piq_mapping.piq_restaurant_id = body["piq_restaurant_id"]
    piq_mapping.name = body["name"]
    piq_mapping.mapping_data = body["name"]
    piq_mapping.piq_data = location

    assert response.status_code == status.HTTP_200_OK
    __assert_site_serialized_structure_and_values(
        response.data, piq_mapping=piq_mapping
    )


@pytest.mark.api("job-piq_mappings-detail")
@patch("spices.django3.coreobjects.models.Location.retrieve")
@patch("apps.utils.base.settings.PIQ_CORE_CLIENT.get_accessible_account_ids_for")
def test_detail__piq_mapping__patch__already_existing(mock_patcher, mock_account, api):
    """PIQ Location Mapping: Patch already existing job rest mapping"""

    job = JobFactory()

    location = LocationSharedCoreObjectFactory()
    PIQMappingFactory(job=job, piq_data=location, mapping_data="fake_name1")
    piq_mapping = PIQMappingFactory(piq_data=location, mapping_data="fake_name")

    user = UserWithBearerTokenFactory.create()
    api.set_credentials(user, bearer=True)
    api.set_url_params(job_id=job.id, pk=piq_mapping.id)
    body = {
        "piq_restaurant_id": location.remote_id,
        "name": "fake_name1",
    }

    mock_account.return_value = piq_mapping.piq_data
    mock_patcher.return_value = [piq_mapping.job.account.remote_id]

    response = api.patch(data=body, format="json")

    assert response.status_code == status.HTTP_409_CONFLICT
    assert (
        response.data["error"]
        == f"piq_data_id: {location.remote_id}, mapping_data: fake_name1 already Exists"
    )


@pytest.mark.api("job-piq_mappings-detail")
@patch("apps.utils.base.settings.PIQ_CORE_CLIENT.get_accessible_account_ids_for")
def test_detail__piq_mapping__patch__piq_restaurant_id__null(mock_patcher, api):
    """PIQ Location Mapping: PATCH request with piq_restaurant_id = None"""

    piq_mapping = PIQMappingFactory()

    user = UserWithBearerTokenFactory.create()
    api.set_credentials(user, bearer=True)
    api.set_url_params(job_id=piq_mapping.job.id, pk=piq_mapping.id)
    body = {
        "piq_restaurant_id": None,
        "name": "fake_name",
    }
    mock_patcher.return_value = [piq_mapping.job.account.remote_id]
    response = api.patch(data=body, format="json")

    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert (
        response.data["piq_data_id"][0] == "This field is required and may not be null"
    )


@pytest.mark.api("job-piq_mappings-detail")
@patch("apps.utils.base.settings.PIQ_CORE_CLIENT.get_accessible_account_ids_for")
def test_detail__piq_mapping__patch__name__null(mock_patcher, api):
    """PIQ Location Mapping: PATCH request with name = None"""

    piq_mapping = PIQMappingFactory()

    user = UserWithBearerTokenFactory.create()
    api.set_credentials(user, bearer=True)
    api.set_url_params(job_id=piq_mapping.job.id, pk=piq_mapping.id)
    body = {
        "piq_restaurant_id": 1,
        "name": None,
    }
    mock_patcher.return_value = [piq_mapping.job.account.remote_id]
    response = api.patch(data=body, format="json")

    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert response.data["mapping_data"][0] == "This field may not be null."


@pytest.mark.api("job-piq_mappings-detail")
@patch("apps.utils.base.settings.PIQ_CORE_CLIENT.get_accessible_account_ids_for")
def test_detail__piq_mapping__patch__piq_restaurant_id__blank(mock_patcher, api):
    """PIQ Location Mapping: PATCH request with piq_restaurant_id = Blank"""

    piq_mapping = PIQMappingFactory()

    user = UserWithBearerTokenFactory.create()
    api.set_credentials(user, bearer=True)
    api.set_url_params(job_id=piq_mapping.job.id, pk=piq_mapping.id)
    body = {
        "piq_restaurant_id": "",
        "name": "fake_name",
    }
    mock_patcher.return_value = [piq_mapping.job.account.remote_id]
    response = api.patch(data=body, format="json")

    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert (
        response.data["piq_data_id"][0] == "This field is required and may not be null"
    )


@pytest.mark.api("job-piq_mappings-detail")
@patch("apps.utils.base.settings.PIQ_CORE_CLIENT.get_accessible_account_ids_for")
def test_detail__piq_mapping__patch__name__blank(mock_patcher, api):
    """PIQ Location Mapping: PATCH request with name = Blank"""

    piq_mapping = PIQMappingFactory()

    user = UserWithBearerTokenFactory.create()
    api.set_credentials(user, bearer=True)
    api.set_url_params(job_id=piq_mapping.job.id, pk=piq_mapping.id)
    body = {
        "piq_restaurant_id": 1,
        "name": "",
    }
    mock_patcher.return_value = [piq_mapping.job.account.remote_id]
    response = api.patch(data=body, format="json")

    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert response.data["mapping_data"][0] == "This field may not be blank."


@pytest.mark.api("job-piq_mappings-detail")
@patch("apps.utils.base.settings.PIQ_CORE_CLIENT.get_accessible_account_ids_for")
def test_detail__piq_mapping__patch__job__non_existing(mock_patcher, api):
    """PIQ Location Mapping: PATCH request with Non Existing job"""

    piq_mapping = PIQMappingFactory()

    user = UserWithBearerTokenFactory.create()
    api.set_credentials(user, bearer=True)
    api.set_url_params(job_id=999999, pk=piq_mapping.id)
    body = {
        "piq_restaurant_id": 1,
        "name": "fake_name",
    }
    mock_patcher.return_value = [piq_mapping.job.account.remote_id]
    response = api.patch(data=body, format="json")

    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert response.json()["job"] == ['Invalid pk "999999" - object does not exist.']


@pytest.mark.api("job-piq_mappings-detail")
@patch("apps.utils.base.settings.PIQ_CORE_CLIENT.get_accessible_account_ids_for")
def test_detail__piq_mapping__delete__success(mock_patcher, api):
    """PIQ Location Mapping: Delete Success"""

    piq_mapping = PIQMappingFactory()

    user = UserWithBearerTokenFactory.create()
    api.set_credentials(user, bearer=True)
    api.set_url_params(job_id=piq_mapping.job.id, pk=piq_mapping.id)
    mock_patcher.return_value = [piq_mapping.job.account.remote_id]
    response = api.delete()

    assert response.status_code == status.HTTP_204_NO_CONTENT


@pytest.mark.api("job-piq_mappings-detail")
@patch("apps.utils.base.settings.PIQ_CORE_CLIENT.get_accessible_account_ids_for")
def test_detail__piq_mapping__delete__piq_mapping__non_existing(mock_patcher, api):
    """PIQ Location Mapping: Delete Non Existing PIQ Location Mapping"""

    piq_mapping = PIQMappingFactory()

    user = UserWithBearerTokenFactory.create()
    api.set_credentials(user, bearer=True)
    api.set_url_params(job_id=piq_mapping.job.id, pk=99999)
    mock_patcher.return_value = [piq_mapping.job.account.remote_id]
    response = api.delete()

    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert response.data["detail"] == "Not found."


@pytest.mark.api("job-piq_mappings-detail")
@patch("apps.utils.base.settings.PIQ_CORE_CLIENT.get_accessible_account_ids_for")
def test_detail__piq_mapping__delete__job__non_existing(mock_patcher, api):
    """PIQ Location Mapping: Delete Non Existing Job"""

    piq_mapping = PIQMappingFactory()

    user = UserWithBearerTokenFactory.create()
    api.set_credentials(user, bearer=True)
    api.set_url_params(job_id=99999, pk=piq_mapping.id)
    mock_patcher.return_value = [piq_mapping.job.account.remote_id]
    response = api.delete()

    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert response.data["detail"] == "Not found."
