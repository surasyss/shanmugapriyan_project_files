from unittest import mock

import pytest

from spices.django3.testing.factory.shared_core_object_model import (
    AccountSharedCoreObjectFactory,
)
from spices.django3.testing.factory.user import UserWithBearerTokenFactory
from spices.django3.thread_local import reset_request_thread_local

pytest_plugins = [
    "spices.django3.testing.pytest_fixtures",
]


@pytest.fixture(autouse=True)
def enable_db_access_for_all_tests(db):
    pass


@pytest.fixture(autouse=True)
def request_thread_local():
    reset_request_thread_local()


@pytest.fixture
def seed_account():
    with mock.patch(
        "apps.utils.base.settings.PIQ_CORE_CLIENT.get_accessible_account_ids_for"
    ) as mock_get:
        seed_account.account = AccountSharedCoreObjectFactory.create()
        seed_account.mock_get_accessible_account_ids_for = mock_get
        seed_account.mock_get_accessible_account_ids_for.return_value = [
            seed_account.account.remote_id
        ]
        yield seed_account


@pytest.fixture
def seed_authenticated_api(api):
    """Seeds user, account, credentials for API call, and sets up the a patcher for valid authentication"""
    with mock.patch(
        "apps.utils.base.settings.PIQ_CORE_CLIENT.get_accessible_account_ids_for"
    ) as mock_get:
        account = AccountSharedCoreObjectFactory.create()
        mock_get.return_value = [account.remote_id]

        seed_authenticated_api.account = account
        seed_authenticated_api.mock_get_accessible_account_ids_for = mock_get
        seed_authenticated_api.user = UserWithBearerTokenFactory.create()

        seed_authenticated_api.api = api
        seed_authenticated_api.api.set_credentials(
            seed_authenticated_api.user, bearer=True
        )

        yield seed_authenticated_api
