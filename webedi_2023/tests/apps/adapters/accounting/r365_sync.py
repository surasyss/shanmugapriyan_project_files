from unittest.mock import patch

import pytest
from spices.django3.testing.factory.shared_core_object_model import (
    CompanySharedCoreObjectFactory,
)

from apps.adapters.accounting.r365_sync import R365SyncRunner
from apps.adapters.engine import _get_accounting_importer_runner
from tests.apps.definitions.factories import ConnectorFactory
from tests.apps.jobconfig.factories import JobFactory
from tests.apps.runs.factories import RunFactory


def test__r365__fetch_piq_details__fail():
    connector = ConnectorFactory(adapter_code="r365")
    job = JobFactory(connector=connector)
    run = RunFactory.create(job=job)
    runner = _get_accounting_importer_runner(run)
    with pytest.raises(Exception) as exception:
        runner._fetch_piq_details()

    assert (
        str(exception.value)
        == "[tag:WEWARAC2] companies cannot be : None or Empty list"
    )


@patch.object(R365SyncRunner, "_get_all_rest_sub_accounts")
@patch.object(R365SyncRunner, "_fetch_unique_restaurant_ids")
def test__r365__fetch_piq_details__success(
    patched___fetch_unique_restaurant_ids, patched__get_all_rest_sub_accounts
):
    connector = ConnectorFactory(adapter_code="r365")
    company1 = CompanySharedCoreObjectFactory.create()
    company2 = CompanySharedCoreObjectFactory.create()

    job = JobFactory(connector=connector)
    job.companies.add(company1)
    job.companies.add(company2)

    run = RunFactory.create(
        job=job, request_parameters={"import_entities": ["gl_account", "bank_account"]}
    )
    runner = _get_accounting_importer_runner(run)
    runner._fetch_piq_details()

    assert patched__get_all_rest_sub_accounts.call_count == 2
    assert patched___fetch_unique_restaurant_ids.call_count == 1
