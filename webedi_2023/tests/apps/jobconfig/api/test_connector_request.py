import copy
import uuid

import pytest
from rest_framework import status
from spices.django3.coreobjects.structure_asserts import assert_structure__scom
from spices.django3.testing.factory.shared_core_object_model import (
    AccountSharedCoreObjectFactory,
)
from spices.django3.testing.structure_asserts import (
    assert_structure__drf_list_response,
    assert_structure__error_response,
)

from apps.definitions.models import ConnectorType
from apps.jobconfig.models import ConnectorRequest
from tests.apps.jobconfig.factories import ConnectorRequestFactory


def assert_structure__connector_request(
    connector_request_dict: dict, connector_request: ConnectorRequest = None
):
    if connector_request:
        assert connector_request_dict["id"] == connector_request.id
        assert connector_request_dict["name"] == connector_request.name
        assert connector_request_dict["login_url"] == connector_request.login_url
        assert connector_request_dict["username"] == connector_request.username
        assert_structure__scom(
            connector_request_dict.pop("account"), connector_request.account
        )

    else:
        connector_request_dict = copy.copy(connector_request_dict)
        assert isinstance(connector_request_dict.pop("id"), str)
        assert isinstance(connector_request_dict.pop("name"), str)
        assert isinstance(connector_request_dict.pop("login_url"), str)
        assert isinstance(connector_request_dict.pop("username"), str)
        assert_structure__scom(connector_request_dict.pop("account"))

        assert not connector_request_dict


@pytest.mark.api("connectorrequest-list")
def test_list__success(seed_authenticated_api):
    # should be returned in API
    cr_accessible = ConnectorRequestFactory(account=seed_authenticated_api.account)

    # should not be returned in API
    cr_accessible_deleted = ConnectorRequestFactory(
        account=seed_authenticated_api.account, is_deleted=True
    )
    cr_inaccessible = ConnectorRequestFactory()  # different account

    response = seed_authenticated_api.api.get()
    assert response.status_code == status.HTTP_200_OK
    assert_structure__drf_list_response(response.data)
    assert_structure__connector_request(response.data["results"][0], cr_accessible)
    assert len(response.data["results"]) == 1


@pytest.mark.api("connectorrequest-detail")
def test_retrieve__not_deleted(seed_authenticated_api):
    api = seed_authenticated_api.api
    connector_request = ConnectorRequestFactory(account=seed_authenticated_api.account)

    api.set_url_params(pk=connector_request.id)
    response = api.get()
    assert response.status_code == status.HTTP_200_OK
    assert_structure__connector_request(response.data, connector_request)


@pytest.mark.api("connectorrequest-detail")
def test_retrieve__deleted(seed_authenticated_api):
    api = seed_authenticated_api.api
    connector_request = ConnectorRequestFactory(
        account=seed_authenticated_api.account, is_deleted=True
    )

    api.set_url_params(pk=connector_request.id)
    response = api.get()
    assert response.status_code == status.HTTP_404_NOT_FOUND


@pytest.mark.api("connectorrequest-detail")
def test_retrieve__inaccessible_account(seed_authenticated_api):
    api = seed_authenticated_api.api
    connector_request = ConnectorRequestFactory()  # different account

    api.set_url_params(pk=connector_request.id)
    response = api.get()
    assert response.status_code == status.HTTP_404_NOT_FOUND


@pytest.mark.api("connectorrequest-list")
def test_post__success(seed_authenticated_api):
    body = {
        "type": "VENDOR",
        "name": str(uuid.uuid4().hex),
        "login_url": str(uuid.uuid4().hex),
        "username": str(uuid.uuid4().hex),
        "password": str(uuid.uuid4().hex),
        "account_id": seed_authenticated_api.account.remote_id,
    }

    response = seed_authenticated_api.api.post(data=body, format="json")
    assert response.status_code == status.HTTP_201_CREATED
    assert_structure__connector_request(response.data)


@pytest.mark.api("connectorrequest-list")
@pytest.mark.parametrize(
    "body_kwargs, expected_error_code, expected_error_dict",
    [
        ({"type": None}, "null", {"type": ["This field may not be null."]}),
        ({"type": ""}, "invalid_choice", {"type": ['"" is not a valid choice.']}),
        (
            {"type": "DoesNotExist"},
            "invalid_choice",
            {"type": ['"DoesNotExist" is not a valid choice.']},
        ),
        ({"name": None}, "null", {"name": ["This field may not be null."]}),
        ({"name": ""}, "blank", {"name": ["This field may not be blank."]}),
        ({"login_url": None}, "null", {"login_url": ["This field may not be null."]}),
        ({"login_url": ""}, "blank", {"login_url": ["This field may not be blank."]}),
        ({"username": None}, "null", {"username": ["This field may not be null."]}),
        ({"username": ""}, "blank", {"username": ["This field may not be blank."]}),
        # ({'password': None}, 'null', {'password': ['This field may not be null.']}),
    ],
)
def test_post__validation_errors(
    seed_authenticated_api, body_kwargs, expected_error_code, expected_error_dict
):
    body = {
        "type": "VENDOR",
        "name": str(uuid.uuid4().hex),
        "login_url": str(uuid.uuid4().hex),
        "username": str(uuid.uuid4().hex),
        "password": str(uuid.uuid4().hex),
        "account_id": seed_authenticated_api.account.remote_id,
    }
    body.update(body_kwargs)

    response = seed_authenticated_api.api.post(data=body, format="json")
    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert_structure__error_response(
        response.json(),
        expected_error_code=expected_error_code,
        expected_error_dict=expected_error_dict,
    )


@pytest.mark.api("connectorrequest-list")
def test_post__inaccessible_account(seed_authenticated_api):
    body = {
        "type": "VENDOR",
        "name": str(uuid.uuid4().hex),
        "login_url": str(uuid.uuid4().hex),
        "username": str(uuid.uuid4().hex),
        "password": str(uuid.uuid4().hex),
        "account_id": AccountSharedCoreObjectFactory.create().id,
    }

    response = seed_authenticated_api.api.post(data=body, format="json")
    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert_structure__error_response(
        response.data, expected_error_code="ACCOUNT_NOT_FOUND"
    )


@pytest.mark.api("connectorrequest-detail")
@pytest.mark.parametrize("field", ["name", "login_url", "username", "password"])
def test_patch__success(seed_authenticated_api, field):
    connector_request = ConnectorRequestFactory(account=seed_authenticated_api.account)

    body = {
        "type": ConnectorType.ACCOUNTING.ident,  # This should be ignored
        field: str(uuid.uuid4().hex),
    }

    seed_authenticated_api.api.set_url_params(pk=connector_request.id)
    response = seed_authenticated_api.api.patch(data=body, format="json")
    assert response.status_code == status.HTTP_200_OK

    connector_request.refresh_from_db()
    assert connector_request.type == ConnectorType.VENDOR
    assert connector_request.account.id == seed_authenticated_api.account.id
    assert getattr(connector_request, field) == body[field]
    assert_structure__connector_request(response.data, connector_request)


@pytest.mark.api("connectorrequest-detail")
def test_put__success(seed_authenticated_api):
    connector_request = ConnectorRequestFactory(account=seed_authenticated_api.account)
    another_account = AccountSharedCoreObjectFactory.create()

    body = {
        "type": ConnectorType.ACCOUNTING.ident,  # This should be ignored
        "account_id": another_account.remote_id,  # This should be ignored
        "name": str(uuid.uuid4().hex),
        "login_url": str(uuid.uuid4().hex),
        "username": str(uuid.uuid4().hex),
        "password": str(uuid.uuid4().hex),
    }

    seed_authenticated_api.api.set_url_params(pk=connector_request.id)
    response = seed_authenticated_api.api.put(data=body, format="json")
    assert response.status_code == status.HTTP_200_OK

    connector_request.refresh_from_db()
    assert connector_request.type == ConnectorType.VENDOR
    assert connector_request.account.id == seed_authenticated_api.account.id

    assert connector_request.name == body["name"]
    assert connector_request.login_url == body["login_url"]
    assert connector_request.username == body["username"]
    assert connector_request.password == body["password"]
    assert_structure__connector_request(response.data, connector_request)


@pytest.mark.api("connectorrequest-detail")
def test_delete__success(seed_authenticated_api):
    connector_request = ConnectorRequestFactory(account=seed_authenticated_api.account)
    another_account = AccountSharedCoreObjectFactory.create()

    seed_authenticated_api.api.set_url_params(pk=connector_request.id)
    response = seed_authenticated_api.api.delete()
    assert response.status_code == status.HTTP_204_NO_CONTENT

    connector_request.refresh_from_db()
    assert connector_request.is_deleted
