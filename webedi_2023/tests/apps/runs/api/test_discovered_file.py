import copy
import uuid
from unittest.mock import patch

import pytest
from rest_framework import status
from spices.django3.testing.factory.user import UserWithBearerTokenFactory

from tests.apps.definitions.api.test_connector import (
    __assert_connector_serialized_structure_and_values,
)
from tests.apps.runs.factories import DiscoveredFileFactory, RunFactory


def __assert_discovered_file_serialized_structure(discovered_file_dict: dict):
    discovered_file_dict = copy.copy(discovered_file_dict)
    discovered_file_list = discovered_file_dict.pop("results")

    assert isinstance(discovered_file_list, list)
    assert isinstance(discovered_file_dict.pop("count"), int)
    assert discovered_file_dict.pop("next") is None
    assert discovered_file_dict.pop("previous") is None
    assert not discovered_file_dict

    if discovered_file_list:
        discovered_file = discovered_file_list[0]
        connector = discovered_file.pop("connector")
        document_properties = discovered_file.pop("document_properties")

        assert isinstance(document_properties, dict)
        assert isinstance(connector, dict)
        assert isinstance(discovered_file.pop("id"), str)
        assert isinstance(discovered_file.pop("run_id"), str)
        assert isinstance(discovered_file.pop("job_id"), str)
        assert isinstance(discovered_file.pop("url"), str)
        assert isinstance(discovered_file.pop("original_filename"), str)
        assert isinstance(discovered_file.pop("original_download_url"), str)
        assert isinstance(discovered_file.pop("file_format"), str)
        assert isinstance(discovered_file.pop("document_type"), str)
        assert isinstance(discovered_file.pop("downloaded_at"), str)
        assert isinstance(discovered_file.pop("downloaded_successfully"), bool)
        assert isinstance(discovered_file.pop("content_hash"), str)
        assert isinstance(discovered_file.pop("extracted_text_hash"), (str, type(None)))
        assert isinstance(discovered_file.pop("piq_container_id"), str)
        assert isinstance(discovered_file.pop("piq_upload_id"), str)

        assert not discovered_file


def __assert_discovered_file_serialized_structure_and_values(
    discovered_file_dict: dict, **kwargs
):
    discovered_file_dict = copy.copy(discovered_file_dict)
    connector = discovered_file_dict.pop("connector")

    assert discovered_file_dict.pop("id") == kwargs["discovered_file"].id
    assert discovered_file_dict.pop("run_id") == kwargs["discovered_file"].run.id
    assert discovered_file_dict.pop("job_id") == kwargs["discovered_file"].run.job.id
    assert discovered_file_dict.pop("url") == kwargs["discovered_file"].url
    assert (
        discovered_file_dict.pop("original_filename")
        == kwargs["discovered_file"].original_filename
    )
    assert (
        discovered_file_dict.pop("original_download_url")
        == kwargs["discovered_file"].original_download_url
    )
    assert (
        discovered_file_dict.pop("file_format") == kwargs["discovered_file"].file_format
    )
    assert (
        discovered_file_dict.pop("document_type")
        == kwargs["discovered_file"].document_type
    )
    assert (
        discovered_file_dict.pop("downloaded_at")
        == kwargs["discovered_file"].downloaded_at
    )
    assert (
        discovered_file_dict.pop("downloaded_successfully")
        == kwargs["discovered_file"].downloaded_successfully
    )
    assert (
        discovered_file_dict.pop("content_hash")
        == kwargs["discovered_file"].content_hash
    )
    assert (
        discovered_file_dict.pop("extracted_text_hash")
        == kwargs["discovered_file"].extracted_text_hash
    )
    assert (
        discovered_file_dict.pop("piq_container_id")
        == kwargs["discovered_file"].piq_container_id
    )
    assert (
        discovered_file_dict.pop("piq_upload_id")
        == kwargs["discovered_file"].piq_upload_id
    )
    assert (
        discovered_file_dict.pop("document_properties")
        == kwargs["discovered_file"].document_properties
    )

    __assert_connector_serialized_structure_and_values(
        connector, connector=kwargs["discovered_file"].connector
    )

    assert not discovered_file_dict


@pytest.mark.api("discoveredfile-list")
@pytest.mark.parametrize("count", [0, 1, 2])
@patch("apps.utils.base.settings.PIQ_CORE_CLIENT.get_accessible_account_ids_for")
def test_list__discovered_file(mock_patcher, api, count):
    """DiscoveredFile List: Happy case"""

    run = RunFactory()
    for index in range(count):
        discovered_file = DiscoveredFileFactory(
            run=run, content_hash=f"fake_content_hash_{index}"
        )
        discovered_file.url = "http://fake_url.com/extracted_text_hash/"
        discovered_file.downloaded_at = "2020-07-01 11:00:00.0000Z"
        discovered_file.downloaded_successfully = True
        discovered_file.piq_container_id = "fake_piq_container_id"
        discovered_file.piq_upload_id = "fake_piq_upload_id"
        discovered_file.save()

    user = UserWithBearerTokenFactory.create()
    api.set_credentials(user, bearer=True)
    api.set_url_params(run_id=run.id)

    rest_acc_ids = [run.job.account.remote_id]
    mock_patcher.return_value = rest_acc_ids
    response = api.get()

    assert response.status_code == status.HTTP_200_OK
    assert response.data["count"] == count
    assert len(response.data["results"]) == count
    __assert_discovered_file_serialized_structure(response.data)


@pytest.mark.api("discoveredfile-list")
@patch("apps.utils.base.settings.PIQ_CORE_CLIENT.get_accessible_account_ids_for")
def test_list__discovered_file__not_existing__run(mock_patcher, api):
    """Listing DiscoveredFile for an NonExisting run"""

    user = UserWithBearerTokenFactory.create()
    api.set_credentials(user, bearer=True)
    api.set_url_params(run_id=999999)

    mock_patcher.return_value = ["0"]
    response = api.get()

    assert response.status_code == status.HTTP_200_OK
    assert response.data["count"] == 0
    assert response.data["results"] == []


@pytest.mark.api("discoveredfile-list")
@patch("apps.utils.base.settings.PIQ_CORE_CLIENT.get_accessible_account_ids_for")
def test_detail__discovered_file__post(mock_patcher, api):
    """DiscoveredFile List: Post"""

    discovered_file = DiscoveredFileFactory(content_hash=str(uuid.uuid4()))

    user = UserWithBearerTokenFactory.create()
    api.set_credentials(user, bearer=True)
    api.set_url_params(run_id=discovered_file.run.id)

    rest_acc_ids = [discovered_file.run.job.account.remote_id]
    mock_patcher.return_value = rest_acc_ids
    response = api.post()

    assert response.status_code == status.HTTP_405_METHOD_NOT_ALLOWED


@pytest.mark.api("discoveredfile-list")
@patch("apps.utils.base.settings.PIQ_CORE_CLIENT.get_accessible_account_ids_for")
def test_detail__discovered_file__update(mock_patcher, api):
    """DiscoveredFile List: Update"""

    discovered_file = DiscoveredFileFactory(content_hash=str(uuid.uuid4()))

    user = UserWithBearerTokenFactory.create()
    api.set_credentials(user, bearer=True)
    api.set_url_params(run_id=discovered_file.run.id)

    rest_acc_ids = [discovered_file.run.job.account.remote_id]
    mock_patcher.return_value = rest_acc_ids
    response = api.put()

    assert response.status_code == status.HTTP_405_METHOD_NOT_ALLOWED


@pytest.mark.api("discoveredfile-list")
@patch("apps.utils.base.settings.PIQ_CORE_CLIENT.get_accessible_account_ids_for")
def test_detail__discovered_file__patch(mock_patcher, api):
    """DiscoveredFile List: Patch"""

    discovered_file = DiscoveredFileFactory(content_hash=str(uuid.uuid4()))

    user = UserWithBearerTokenFactory.create()
    api.set_credentials(user, bearer=True)
    api.set_url_params(run_id=discovered_file.run.id)

    rest_acc_ids = [discovered_file.run.job.account.remote_id]
    mock_patcher.return_value = rest_acc_ids
    response = api.patch()

    assert response.status_code == status.HTTP_405_METHOD_NOT_ALLOWED


@pytest.mark.api("discoveredfile-list")
@patch("apps.utils.base.settings.PIQ_CORE_CLIENT.get_accessible_account_ids_for")
def test_detail__discovered_file__delete(mock_patcher, api):
    """DiscoveredFile List: Delete"""

    discovered_file = DiscoveredFileFactory(content_hash=str(uuid.uuid4()))

    user = UserWithBearerTokenFactory.create()
    api.set_credentials(user, bearer=True)
    api.set_url_params(run_id=discovered_file.run.id)

    rest_acc_ids = [discovered_file.run.job.account.remote_id]
    mock_patcher.return_value = rest_acc_ids
    response = api.delete()

    assert response.status_code == status.HTTP_405_METHOD_NOT_ALLOWED


@pytest.mark.api("discoveredfile-detail")
@patch("apps.utils.base.settings.PIQ_CORE_CLIENT.get_accessible_account_ids_for")
def test_retrieve__discovered_file__happy_case(mock_patcher, api):
    """Retrieve DiscoveredFile happy case"""
    run = RunFactory()
    DiscoveredFileFactory(run=run, content_hash=str(uuid.uuid4()))
    discovered_file_2 = DiscoveredFileFactory(run=run, content_hash=str(uuid.uuid4()))

    user = UserWithBearerTokenFactory.create()
    api.set_credentials(user, bearer=True)
    api.set_url_params(run_id=run.id, pk=discovered_file_2.id)

    rest_acc_ids = [run.job.account.remote_id]
    mock_patcher.return_value = rest_acc_ids
    response = api.get()

    assert response.status_code == status.HTTP_200_OK
    __assert_discovered_file_serialized_structure_and_values(
        response.data, discovered_file=discovered_file_2
    )


@pytest.mark.api("discoveredfile-detail")
@patch("apps.utils.base.settings.PIQ_CORE_CLIENT.get_accessible_account_ids_for")
def test_retrieve__discovered_file__not_existing__run(mock_patcher, api):
    """Retrieve DiscoveredFile for an NonExisting run"""

    user = UserWithBearerTokenFactory.create()
    api.set_credentials(user, bearer=True)
    api.set_url_params(run_id=999999, pk=999999)

    mock_patcher.return_value = ["0"]
    response = api.get()

    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert response.data["detail"] == "Not found."


@pytest.mark.api("discoveredfile-detail")
@patch("apps.utils.base.settings.PIQ_CORE_CLIENT.get_accessible_account_ids_for")
def test_retrieve__discovered_file__not_existing__discovered_file(mock_patcher, api):
    """Retrieve DiscoveredFile for an NonExisting run"""

    discovered_file = DiscoveredFileFactory(content_hash=str(uuid.uuid4()))

    user = UserWithBearerTokenFactory.create()
    api.set_credentials(user, bearer=True)
    api.set_url_params(run_id=discovered_file.run.id, pk=999999)

    rest_acc_ids = [discovered_file.run.job.account.remote_id]
    mock_patcher.return_value = rest_acc_ids
    response = api.get()

    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert response.data["detail"] == "Not found."


@pytest.mark.api("discoveredfile-detail")
@patch("apps.utils.base.settings.PIQ_CORE_CLIENT.get_accessible_account_ids_for")
def test_retrieve__discovered_file__post(mock_patcher, api):
    """DiscoveredFile retrieve: Post"""

    discovered_file = DiscoveredFileFactory(content_hash=str(uuid.uuid4()))

    user = UserWithBearerTokenFactory.create()
    api.set_credentials(user, bearer=True)
    api.set_url_params(run_id=discovered_file.run.id, pk=999999)

    rest_acc_ids = [discovered_file.run.job.account.remote_id]
    mock_patcher.return_value = rest_acc_ids
    response = api.post()

    assert response.status_code == status.HTTP_405_METHOD_NOT_ALLOWED


@pytest.mark.api("discoveredfile-detail")
@patch("apps.utils.base.settings.PIQ_CORE_CLIENT.get_accessible_account_ids_for")
def test_retrieve__discovered_file__update(mock_patcher, api):
    """DiscoveredFile retrieve: Update"""

    discovered_file = DiscoveredFileFactory(content_hash=str(uuid.uuid4()))

    user = UserWithBearerTokenFactory.create()
    api.set_credentials(user, bearer=True)
    api.set_url_params(run_id=discovered_file.run.id, pk=999999)

    rest_acc_ids = [discovered_file.run.job.account.remote_id]
    mock_patcher.return_value = rest_acc_ids
    response = api.put()

    assert response.status_code == status.HTTP_405_METHOD_NOT_ALLOWED


@pytest.mark.api("discoveredfile-detail")
@patch("apps.utils.base.settings.PIQ_CORE_CLIENT.get_accessible_account_ids_for")
def test_retrieve__discovered_file__patch(mock_patcher, api):
    """DiscoveredFile retrieve: Patch"""

    discovered_file = DiscoveredFileFactory(content_hash=str(uuid.uuid4()))

    user = UserWithBearerTokenFactory.create()
    api.set_credentials(user, bearer=True)
    api.set_url_params(run_id=discovered_file.run.id, pk=999999)

    rest_acc_ids = [discovered_file.run.job.account.remote_id]
    mock_patcher.return_value = rest_acc_ids
    response = api.patch()

    assert response.status_code == status.HTTP_405_METHOD_NOT_ALLOWED


@pytest.mark.api("discoveredfile-detail")
@patch("apps.utils.base.settings.PIQ_CORE_CLIENT.get_accessible_account_ids_for")
def test_retrieve__discovered_file__delete(mock_patcher, api):
    """DiscoveredFile retrieve: Delete"""

    discovered_file = DiscoveredFileFactory(content_hash=str(uuid.uuid4()))

    user = UserWithBearerTokenFactory.create()
    api.set_credentials(user, bearer=True)
    api.set_url_params(run_id=discovered_file.run.id, pk=999999)

    rest_acc_ids = [discovered_file.run.job.account.remote_id]
    mock_patcher.return_value = rest_acc_ids
    response = api.delete()

    assert response.status_code == status.HTTP_405_METHOD_NOT_ALLOWED
