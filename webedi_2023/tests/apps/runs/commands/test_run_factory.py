from datetime import datetime
from unittest import mock
from unittest.mock import patch

import pytest
from django.utils import timezone
from spices.django3.testing.factory.shared_core_object_model import (
    CompanySharedCoreObjectFactory,
    LocationSharedCoreObjectFactory,
)

from apps.jobconfig.models import Frequency, DaysOfWeek
from apps.runs import run_factory
from apps.runs.models import ConnectorCapabilityTypes, RunCreatedVia
from tests.apps.definitions.factories import (
    ConnectorFactory,
    ConnectorCapabilityFactory,
)
from tests.apps.jobconfig.factories import JobFactory, JobScheduleFactory
from tests.apps.runs.factories import RunFactory


def test__connector_not_enabled_run_factory():
    connector = ConnectorFactory(enabled=False)
    job = JobFactory(connector=connector)
    with pytest.raises(Exception) as exception:
        run_factory.create_run(
            job, ConnectorCapabilityTypes.INTERNAL__WEB_LOGIN, RunCreatedVia.SCHEDULED
        )

    assert str(exception.value) == "This connector is not enabled yet"


@pytest.mark.parametrize(
    "current_date, result",
    [
        ("2021-05-31", True),  # Monday
        ("2021-06-04", True),  # Friday
        ("2021-06-03", True),  # Thursday
    ],
)
def test__scheduled__run_factory__daily(current_date, result):
    job = JobFactory.create()
    job_schedule = JobScheduleFactory.create(job=job, frequency=Frequency.DAILY.ident)

    current_date = datetime.strptime(current_date, "%Y-%m-%d")
    with mock.patch.object(timezone, "now", return_value=current_date):
        assert result == job_schedule.match(current_date)


# def test__scheduled__run_factory__daily__not_create_run_if_already_created_for_the_day():
#     job = JobFactory.create()
#     RunFactory.create(job=job)
#     JobScheduleFactory.create(job=job, frequency=Frequency.DAILY.ident)
#     assert not __should_create_run(job)


@pytest.mark.parametrize(
    "current_date, result",
    [
        ("2021-05-31", True),  # Monday
        ("2021-06-04", True),  # Friday
        ("2021-06-03", True),  # Thursday
    ],
)
def test__scheduled__run_factory__daily__ignore_day_of_week(current_date, result):
    job = JobFactory.create()
    job_schedule = JobScheduleFactory.create(
        job=job,
        frequency=Frequency.DAILY.ident,
        day_of_week=[DaysOfWeek.MONDAY.ident, DaysOfWeek.FRIDAY.ident],
    )

    current_date = datetime.strptime(current_date, "%Y-%m-%d")
    with mock.patch.object(timezone, "now", return_value=current_date):
        assert result == job_schedule.match(current_date)


@pytest.mark.parametrize(
    "current_date, result",
    [
        ("2021-05-31", True),  # Monday
        ("2021-06-04", True),  # Friday
        ("2021-06-03", False),  # Thursday
    ],
)
def test__scheduled__run_factory__weekly__day_of_week(current_date, result):
    job = JobFactory.create()
    job_schedule = JobScheduleFactory.create(
        job=job,
        frequency=Frequency.WEEKLY.ident,
        day_of_week=[DaysOfWeek.MONDAY.ident, DaysOfWeek.FRIDAY.ident],
    )

    current_date = datetime.strptime(current_date, "%Y-%m-%d")
    with mock.patch.object(timezone, "now", return_value=current_date):
        assert result == job_schedule.match(current_date)


@pytest.mark.parametrize(
    "current_date, result",
    [
        ("2021-06-01", True),  # Tuesday - 1st Week
        ("2021-06-04", True),  # Friday - 1st Week
        ("2021-06-11", False),  # Friday - 2nd Week
    ],
)
def test__scheduled__run_factory__weekly__day_of_week_and_week_of_month(
    current_date, result
):
    job = JobFactory.create()
    job_schedule = JobScheduleFactory.create(
        job=job,
        frequency=Frequency.WEEKLY.ident,
        day_of_week=[
            DaysOfWeek.MONDAY.ident,
            DaysOfWeek.FRIDAY.ident,
            DaysOfWeek.TUESDAY.ident,
        ],
        week_of_month=[1, 4],
    )

    current_date = datetime.strptime(current_date, "%Y-%m-%d")
    with mock.patch.object(timezone, "now", return_value=current_date):
        assert result == job_schedule.match(current_date)


@pytest.mark.parametrize(
    "current_date, result",
    [
        ("2021-05-31", True),  # Monday - 5th Week
        ("2021-06-04", True),  # Friday - 1st Week
        ("2021-06-12", False),  # Friday - 2nt Week
    ],
)
def test__scheduled__run_factory__monthly__day_of_month(current_date, result):
    job = JobFactory.create()
    job_schedule = JobScheduleFactory.create(
        job=job, frequency=Frequency.MONTHLY.ident, date_of_month=[31, 4]
    )

    current_date = datetime.strptime(current_date, "%Y-%m-%d")
    with mock.patch.object(timezone, "now", return_value=current_date):
        assert result == job_schedule.match(current_date)


@pytest.mark.parametrize(
    "current_date, result",
    [
        ("2021-05-01", True),  # Monday
        ("2021-06-04", True),  # Friday
        ("2021-06-03", True),  # Thursday
        ("2021-06-02", False),  # Wednesday
    ],
)
def test__scheduled__run_factory__monthly__day_of_month_and_day_of_week(
    current_date, result
):
    job = JobFactory.create()
    job_schedule = JobScheduleFactory.create(
        job=job,
        frequency=Frequency.MONTHLY.ident,
        day_of_week=[DaysOfWeek.MONDAY.ident, DaysOfWeek.THURSDAY.ident],
        date_of_month=[1, 4],
    )

    current_date = datetime.strptime(current_date, "%Y-%m-%d")
    with mock.patch.object(timezone, "now", return_value=current_date):
        assert result == job_schedule.match(current_date)


def test__connector_not_have_capability_run_factory():
    connector = ConnectorFactory(enabled=True)
    job = JobFactory(connector=connector)
    with pytest.raises(Exception) as exception:
        run_factory.create_run(
            job, ConnectorCapabilityTypes.INTERNAL__WEB_LOGIN, RunCreatedVia.SCHEDULED
        )

    assert (
        str(exception.value)
        == f"This connection doesn't support the operation: {ConnectorCapabilityTypes.INTERNAL__WEB_LOGIN}"
    )


@pytest.mark.parametrize("created_via", RunCreatedVia.as_ident_enum_dict())
@pytest.mark.parametrize(
    "capability",
    [
        ConnectorCapabilityTypes.INVOICE__EXPORT,
        ConnectorCapabilityTypes.PO_DOWNLOAD,
        ConnectorCapabilityTypes.STATEMENT__DOWNLOAD,
        ConnectorCapabilityTypes.ORDER_GUIDE__DOWNLOAD,
    ],
)
def test__run_factory_for_unsupported(created_via, capability):
    connector = ConnectorFactory(enabled=True)
    ConnectorCapabilityFactory(connector=connector, type=capability)
    job = JobFactory(connector=connector)

    with pytest.raises(Exception) as exception:
        run_factory.create_run(job, capability, RunCreatedVia.SCHEDULED)
    assert str(exception.value) == f"Unsupported operation: {capability}"


@pytest.mark.parametrize("created_via", RunCreatedVia.as_ident_enum_dict())
@pytest.mark.parametrize(
    "capability",
    [
        ConnectorCapabilityTypes.INTERNAL__WEB_LOGIN,
        ConnectorCapabilityTypes.BANK_ACCOUNT__IMPORT_LIST,
        ConnectorCapabilityTypes.GL__IMPORT_LIST,
        ConnectorCapabilityTypes.INVOICE__DOWNLOAD,
        ConnectorCapabilityTypes.PAYMENT__IMPORT_INFO,
        ConnectorCapabilityTypes.PAYMENT__PAY,
        ConnectorCapabilityTypes.PAYMENT__EXPORT_INFO,
        ConnectorCapabilityTypes.ACCOUNTING__IMPORT_MULTIPLE_ENTITIES,
        ConnectorCapabilityTypes.VENDOR__IMPORT_LIST,
    ],
)
@patch("apps.runs.run_factory.__construct_parsed_json_for_making_payments")
@patch("apps.runs.run_factory.settings.PIQ_CORE_CLIENT.billpay_export_dry_run")
@patch("spices.django3.coreobjects.base.CoreObjectMixin.retrieve")
def test__run_factory_for_supported(
    mocked_retrieve,
    mocked__billpay_export_dry_run,
    mocked_convert_json,
    capability,
    created_via,
):
    connector = ConnectorFactory(enabled=True)
    ConnectorCapabilityFactory(connector=connector, type=capability)
    job = JobFactory(connector=connector)
    if capability == ConnectorCapabilityTypes.PAYMENT__EXPORT_INFO:
        company1 = CompanySharedCoreObjectFactory.create()
        job.companies.add(company1)
        location_1 = {"id": LocationSharedCoreObjectFactory.create().remote_id}
        location_2 = {"id": LocationSharedCoreObjectFactory.create().remote_id}
        company1.restaurants = [location_1, location_2]
        mocked_retrieve.return_value = company1

    run_factory.create_run(job, capability, RunCreatedVia.from_ident(created_via))
