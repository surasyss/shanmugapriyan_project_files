import pytest

from apps.adapters.base import TEMP_DOWNLOAD_DIR
from apps.adapters.engine import (
    get_vendor_runner,
    get_accounting_runner,
    RUNNER_CLASSES,
)
from apps.adapters.framework.registry import connectors
from tests.apps.definitions.factories import ConnectorFactory
from tests.apps.runs.factories import RunFactory


def test__get_vendor_runner_invalid_adapter_code():
    run = RunFactory()
    with pytest.raises(ValueError) as exc:
        get_vendor_runner(run)
    assert str(exc.value) == f"Unknown adapter: {run.job.connector.adapter_code}"


@pytest.mark.parametrize("adapter_code", RUNNER_CLASSES)
def test__get_vendor_runner_valid_adapter_code_older_framework(adapter_code):
    connector = ConnectorFactory(adapter_code=adapter_code)
    run = RunFactory(job__connector=connector)
    runner_cls = get_vendor_runner(run)
    assert runner_cls.run == run
    assert runner_cls.download_location == f"{TEMP_DOWNLOAD_DIR}/runs/{run.id}"


@pytest.mark.parametrize("adapter_code", connectors._registry.keys())
def test__get_vendor_runner_valid_adapter_code_with_new_framework(adapter_code):
    connector = ConnectorFactory(adapter_code=adapter_code)
    run = RunFactory(job__connector=connector)
    runner_cls = get_vendor_runner(run)
    assert runner_cls.run == run
    assert runner_cls.download_location == f"{TEMP_DOWNLOAD_DIR}/runs/{run.id}"


def test__get_accounting_runner_invalid_adapter_code():
    run = RunFactory()
    with pytest.raises(ValueError) as exc:
        get_accounting_runner(run)
    assert str(exc.value) == f"Unknown adapter: {run.job.connector.adapter_code}"


@pytest.mark.parametrize("adapter_code", ["r365_v1"])
def test__get_accounting_runner_valid_adapter_code(adapter_code):
    connector = ConnectorFactory(adapter_code=adapter_code)
    run = RunFactory(job__connector=connector)
    runner_cls = get_accounting_runner(run)
    assert runner_cls.run == run
