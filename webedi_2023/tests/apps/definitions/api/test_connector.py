import copy

import pytest
from rest_framework import status
from spices.django3.testing.factory.shared_core_object_model import (
    VendorSharedCoreObjectFactory,
    VendorGroupSharedCoreObjectFactory,
)
from spices.django3.testing.factory.user import UserWithBearerTokenFactory

from apps.definitions.models import ConnectorCapabilityTypes
from tests.apps.definitions.factories import (
    ConnectorFactory,
    ConnectorVendorInfoFactory,
    ConnectorCapabilityFactory,
)


def __assert_connector_serialized_structure(connector_dict: dict):
    connector_dict = copy.copy(connector_dict)
    connector_list = connector_dict.pop("results")

    assert isinstance(connector_list, list)
    assert isinstance(connector_dict.pop("count"), int)
    assert connector_dict.pop("next") is None
    assert connector_dict.pop("previous") is None
    assert not connector_dict

    connector = connector_list[0]
    assert isinstance(connector.pop("id"), str)
    assert isinstance(connector.pop("adapter_code"), str)
    assert isinstance(connector.pop("name"), str)
    assert isinstance(connector.pop("enabled"), bool)
    assert isinstance(connector.pop("type"), str)
    assert isinstance(connector.pop("icon_url"), str)

    login_url = connector.pop("login_url")
    registration_url = connector.pop("registration_url")
    connector_vendor_info = connector.pop("connector_vendor_info")
    capabilities = connector.pop("capabilities")

    if login_url:
        assert isinstance(login_url, str)

    if registration_url:
        assert isinstance(registration_url, str)

    if connector_vendor_info:
        assert isinstance(connector_vendor_info, dict)

    if capabilities:
        assert isinstance(capabilities, list)

    assert not connector


def __assert_connector_serialized_structure_and_values(connector_dict: dict, **kwargs):
    connector_dict = copy.copy(connector_dict)

    login_url = connector_dict.pop("login_url")
    registration_url = connector_dict.pop("registration_url")
    connector_vendor_info = connector_dict.pop("connector_vendor_info")
    capabilities = connector_dict.pop("capabilities")

    assert connector_dict.pop("id") == kwargs["connector"].id
    assert connector_dict.pop("adapter_code") == kwargs["connector"].adapter_code
    assert connector_dict.pop("name") == kwargs["connector"].name
    assert connector_dict.pop("enabled") == kwargs["connector"].enabled
    assert connector_dict.pop("type") == kwargs["connector"].type
    assert connector_dict.pop("icon_url") == kwargs["connector"].icon.url

    if login_url:
        assert login_url == kwargs["connector"].login_url

    if registration_url:
        assert registration_url == kwargs["connector"].registration_url

    if connector_vendor_info:
        __assert_connector_vendor_info(
            connector_vendor_info, kwargs["connector"].connector_vendor
        )

    if capabilities:
        __assert_capabilities(capabilities, kwargs["capabilities"])

    assert not connector_dict


def __assert_capabilities(capabilities: list, expected_capabilities: list):
    capability_dict = {
        capability.type: capability for capability in expected_capabilities
    }

    for capability in capabilities:
        capability = copy.copy(capability)
        type = capability.pop("type")
        supported_file_format = capability.pop("supported_file_format")
        if type in capability_dict:
            assert type == capability_dict[type].type
            assert supported_file_format == capability_dict[type].supported_file_format
            assert not capability
        else:
            assert False


def __assert_connector_vendor_info(
    connector_vendor_info: dict, expected_connector_vendor_info: dict
):
    connector_vendor_info = copy.copy(connector_vendor_info)
    assert (
        connector_vendor_info.pop("contains_support_document")
        == expected_connector_vendor_info.contains_support_document
    )
    assert (
        connector_vendor_info.pop("requires_account_number")
        == expected_connector_vendor_info.requires_account_number
    )
    vendor = connector_vendor_info.pop("vendor")
    vendor_group = connector_vendor_info.pop("vendor_group")

    if expected_connector_vendor_info.vendor:
        assert connector_vendor_info.pop("vendor_id") == int(
            expected_connector_vendor_info.vendor.remote_id
        )
        assert vendor["id"] == str(expected_connector_vendor_info.vendor.remote_id)
        assert vendor["name"] == expected_connector_vendor_info.vendor.display_name

    if expected_connector_vendor_info.vendor_group:
        assert connector_vendor_info.pop("vendor_group_id") == int(
            expected_connector_vendor_info.vendor_group.remote_id
        )
        assert vendor_group["id"] == str(
            expected_connector_vendor_info.vendor_group.remote_id
        )
        assert (
            vendor_group["name"]
            == expected_connector_vendor_info.vendor_group.display_name
        )

    assert not connector_vendor_info


@pytest.mark.api("connector-list")
@pytest.mark.parametrize("connector_enabled", [False, True])
def test_list__connector__enabled(api, connector_enabled):
    """Connector & Adapter - Field Enable"""
    ConnectorFactory(enabled=connector_enabled)

    user = UserWithBearerTokenFactory.create()
    api.set_credentials(user, bearer=True)
    api.set_url_params()
    response = api.get()

    assert response.status_code == status.HTTP_200_OK
    assert response.data["results"][0]["enabled"] == connector_enabled
    __assert_connector_serialized_structure(response.data)


@pytest.mark.api("connector-list")
@pytest.mark.parametrize("connector_type", ["VENDOR", "ACCOUNTING"])
def test_list__connector__filter__type(api, connector_type):
    """Applying Filters: Type"""

    ConnectorFactory(type="VENDOR")
    ConnectorFactory(type="ACCOUNTING")

    user = UserWithBearerTokenFactory.create()
    api.set_credentials(user, bearer=True)
    api.set_url_params()

    query_params = {"type": connector_type}
    response = api.get(data=query_params)

    assert response.status_code == status.HTTP_200_OK
    assert response.data["count"] == 1
    assert response.data["results"][0]["type"] == connector_type
    __assert_connector_serialized_structure(response.data)


@pytest.mark.api("connector-list")
@pytest.mark.parametrize("enabled", [True, False])
def test_list__connector__filter__enabled(api, enabled):
    """Applying Filters: Enabled"""

    ConnectorFactory(enabled=True)
    ConnectorFactory(enabled=False)

    user = UserWithBearerTokenFactory.create()
    api.set_credentials(user, bearer=True)
    api.set_url_params()

    query_params = {"enabled": enabled}
    response = api.get(data=query_params)

    assert response.status_code == status.HTTP_200_OK
    assert response.data["count"] == 1
    assert response.data["results"][0]["enabled"] == enabled
    __assert_connector_serialized_structure(response.data)


@pytest.mark.api("connector-list")
def test_list__connector__filter__adapter_code(api):
    connector = ConnectorFactory()
    ConnectorFactory()

    user = UserWithBearerTokenFactory.create()
    api.set_credentials(user, bearer=True)
    api.set_url_params()

    query_params = {"adapter_code": connector.adapter_code}
    response = api.get(data=query_params)

    assert response.status_code == status.HTTP_200_OK
    assert response.data["count"] == 1
    assert response.data["results"][0]["id"] == connector.id
    assert response.data["results"][0]["adapter_code"] == connector.adapter_code
    __assert_connector_serialized_structure(response.data)


@pytest.mark.api("connector-list")
@pytest.mark.parametrize(
    "ordering, connector_name",
    [
        ("name", ["fake_connector_01", "fake_connector_02"]),
        ("-name", ["fake_connector_02", "fake_connector_01"]),
    ],
)
def test_list__connector__ordering__name(api, ordering, connector_name):
    """Applying Ordering: by name"""

    ConnectorFactory(name="fake_connector_01")
    ConnectorFactory(name="fake_connector_02")

    user = UserWithBearerTokenFactory.create()
    api.set_credentials(user, bearer=True)
    api.set_url_params()

    query_params = {"ordering": ordering}
    response = api.get(data=query_params)

    assert response.status_code == status.HTTP_200_OK
    assert response.data["count"] == 2
    assert response.data["results"][0]["name"] == connector_name[0]
    assert response.data["results"][1]["name"] == connector_name[1]
    __assert_connector_serialized_structure(response.data)


@pytest.mark.api("connector-list")
@pytest.mark.parametrize("connector_type", ["VENDOR", "ACCOUNTING"])
def test_list__connector__filtering_by__name(api, connector_type):
    """Filtering Ordering: by name"""

    user = UserWithBearerTokenFactory.create()
    api.set_credentials(user, bearer=True)
    api.set_url_params()

    ConnectorFactory(name="fake_connector_01", type=connector_type)
    ConnectorFactory(name="dummy_connector_02", type=connector_type)
    ConnectorFactory(name="fake_connector_03", type=connector_type)
    ConnectorFactory(name="dummy_connector_04", type=connector_type)

    query_params = {"name": "fake"}
    response = api.get(data=query_params)

    assert response.status_code == status.HTTP_200_OK
    assert response.data["count"] == 2
    assert response.data["results"][0]["name"] == "fake_connector_01"
    assert response.data["results"][1]["name"] == "fake_connector_03"
    __assert_connector_serialized_structure(response.data)


@pytest.mark.api("connector-list")
@pytest.mark.parametrize(
    "capability",
    [
        "vendor.import_list",
        "gl.import_list",
        "bank.import_list",
        "order_guide.download",
    ],
)
def test_list__connector__filter__capability(api, capability):
    """Applying Filters: Capability"""

    connector = ConnectorFactory.create_batch(size=4)

    ConnectorCapabilityFactory(
        connector=connector[0], type=ConnectorCapabilityTypes.VENDOR__IMPORT_LIST
    )
    ConnectorCapabilityFactory(
        connector=connector[1], type=ConnectorCapabilityTypes.GL__IMPORT_LIST
    )
    ConnectorCapabilityFactory(
        connector=connector[2], type=ConnectorCapabilityTypes.BANK_ACCOUNT__IMPORT_LIST
    )
    ConnectorCapabilityFactory(
        connector=connector[3], type=ConnectorCapabilityTypes.ORDER_GUIDE__DOWNLOAD
    )

    user = UserWithBearerTokenFactory.create()
    api.set_credentials(user, bearer=True)
    api.set_url_params()

    query_params = {"capability": capability}
    response = api.get(data=query_params)

    assert response.status_code == status.HTTP_200_OK
    assert response.data["count"] == 1
    assert response.data["results"][0]["capabilities"][0]["type"] == capability
    __assert_connector_serialized_structure(response.data)


@pytest.mark.api("connector-detail")
@pytest.mark.parametrize("enabled", [True, False])
def test_retrieve__enabled(api, enabled):
    """Retrieve connector: Field = Enabled"""

    connector = ConnectorFactory(enabled=enabled)

    user = UserWithBearerTokenFactory.create()
    api.set_credentials(user, bearer=True)
    api.set_url_params(pk=connector.id)
    response = api.get()

    assert response.status_code == status.HTTP_200_OK
    __assert_connector_serialized_structure_and_values(
        response.data, connector=connector
    )


@pytest.mark.api("connector-detail")
@pytest.mark.parametrize("type", ["VENDOR", "ACCOUNTING"])
def test_retrieve__type(api, type):
    """Retrieve connector: Field = Type"""

    connector = ConnectorFactory(type=type)

    user = UserWithBearerTokenFactory.create()
    api.set_credentials(user, bearer=True)
    api.set_url_params(pk=connector.id)
    response = api.get()

    assert response.status_code == status.HTTP_200_OK
    __assert_connector_serialized_structure_and_values(
        response.data, connector=connector
    )


@pytest.mark.api("connector-detail")
def test_retrieve__connector_vendor_info(api):
    """Retrieve connector with connector_vendor_info Object"""

    vendor = VendorSharedCoreObjectFactory(remote_id=12)
    vendor_group = VendorGroupSharedCoreObjectFactory(remote_id=13)
    connector = ConnectorFactory()
    ConnectorVendorInfoFactory(
        connector=connector, vendor_group=vendor_group, vendor=vendor
    )

    user = UserWithBearerTokenFactory.create()
    api.set_credentials(user, bearer=True)
    api.set_url_params(pk=connector.id)
    response = api.get()

    assert response.status_code == status.HTTP_200_OK
    __assert_connector_serialized_structure_and_values(
        response.data, connector=connector
    )


@pytest.mark.api("connector-detail")
def test_retrieve__capabilities(api):
    """Retrieve connector with connector_vendor_info & cei Object"""

    connector = ConnectorFactory()
    ConnectorVendorInfoFactory(connector=connector)
    cap01 = ConnectorCapabilityFactory(
        connector=connector, type=ConnectorCapabilityTypes.VENDOR__IMPORT_LIST.ident
    )
    cap02 = ConnectorCapabilityFactory(
        connector=connector, type=ConnectorCapabilityTypes.GL__IMPORT_LIST.ident
    )
    cap03 = ConnectorCapabilityFactory(
        connector=connector,
        type=ConnectorCapabilityTypes.BANK_ACCOUNT__IMPORT_LIST.ident,
    )
    cap04 = ConnectorCapabilityFactory(
        connector=connector, type=ConnectorCapabilityTypes.ORDER_GUIDE__DOWNLOAD.ident
    )
    capabilities = [cap01, cap02, cap03, cap04]

    user = UserWithBearerTokenFactory.create()
    api.set_credentials(user, bearer=True)
    api.set_url_params(pk=connector.id)
    response = api.get()

    assert response.status_code == status.HTTP_200_OK
    __assert_connector_serialized_structure_and_values(
        response.data, connector=connector, capabilities=capabilities
    )


@pytest.mark.api("connector-list")
@pytest.mark.parametrize("method", ["post", "put", "patch", "delete"])
def test_connector__list__methods(api, method):
    """Connector list: Not allowed methods"""

    user = UserWithBearerTokenFactory.create()
    api.set_credentials(user, bearer=True)
    api.set_url_params()
    body = {
        "name": "fake_user",
        "type": "fake_password",
        "enabled": True,
        "login_url": "http://fake.webedi.plateiq.com/login",
        "registration_url": "http://fake.webedi.plateiq.com/register",
    }
    response = getattr(api, method)(data=body, format="json")
    assert response.status_code == status.HTTP_405_METHOD_NOT_ALLOWED


@pytest.mark.api("connector-detail")
@pytest.mark.parametrize("method", ["put", "patch", "delete"])
def test_connector__detail__methods(api, method):
    """connector details: Not allowed methods"""
    connector = ConnectorFactory()

    user = UserWithBearerTokenFactory.create()
    api.set_credentials(user, bearer=True)
    api.set_url_params(pk=connector.id)
    body = {
        "name": "fake_user",
        "type": "fake_password",
        "enabled": True,
        "login_url": "http://fake.webedi.plateiq.com/login",
        "registration_url": "http://fake.webedi.plateiq.com/register",
    }
    response = getattr(api, method)(data=body, format="json")
    assert response.status_code == status.HTTP_405_METHOD_NOT_ALLOWED
