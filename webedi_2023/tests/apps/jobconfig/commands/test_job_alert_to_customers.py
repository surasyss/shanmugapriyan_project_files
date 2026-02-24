from datetime import datetime, timedelta
from unittest import mock

import pytest
from dateutil.relativedelta import relativedelta
from django.conf import settings
from django.core.management import call_command
from django.utils import timezone

from apps.definitions.models import ConnectorCapability, ConnectorCapabilityTypes
from apps.jobconfig.models import Period, JobSchedule, Frequency, DaysOfWeek
from apps.runs import sla
from apps.runs.models import Run
from tests.apps.definitions.factories import (
    ConnectorCapabilityFactory,
    ConnectorFactory,
)
from tests.apps.jobconfig.factories import (
    JobStatFactory,
    JobFactory,
    JobAlertRuleFactory,
)


def test__alert_job__monthly():
    connector = ConnectorFactory(enabled=True)
    ConnectorCapabilityFactory(
        connector=connector, type=ConnectorCapabilityTypes.INVOICE__DOWNLOAD
    )
    job = JobFactory(connector=connector)
    JobSchedule.objects.create(
        job=job,
        frequency=Frequency.MONTHLY,
        date_of_month=[6],
    )

    assert Run.objects.filter(is_manual=True, job=job).count() == 0

    current_date = datetime.strptime("2021-07-01", "%Y-%m-%d")
    with mock.patch.object(timezone, "now", return_value=current_date):
        call_command("job_alert_to_customers")

    assert Run.objects.filter(is_manual=True, job=job).count() == 1


def test__alert_job__monthly_not_create_manual_run():
    connector = ConnectorFactory(enabled=True)
    ConnectorCapabilityFactory(
        connector=connector, type=ConnectorCapabilityTypes.INVOICE__DOWNLOAD
    )
    job = JobFactory(connector=connector)
    JobSchedule.objects.create(
        job=job,
        frequency=Frequency.MONTHLY,
        date_of_month=[6],
    )

    JobStatFactory.create(
        job=job,
        date=datetime.strptime("2021-07-01", "%Y-%m-%d") - timedelta(days=1),
        df_count=1,
    )

    current_date = datetime.strptime("2021-07-01", "%Y-%m-%d")
    with mock.patch.object(timezone, "now", return_value=current_date):
        call_command("job_alert_to_customers")

    assert Run.objects.filter(is_manual=True, job=job).count() == 0


def test__alert_job__weekly():
    connector = ConnectorFactory(enabled=True)
    ConnectorCapabilityFactory(
        connector=connector, type=ConnectorCapabilityTypes.INVOICE__DOWNLOAD
    )
    job = JobFactory(connector=connector)
    JobSchedule.objects.create(
        job=job,
        frequency=Frequency.WEEKLY,
        day_of_week=[DaysOfWeek.TUESDAY],
    )

    current_date = datetime.strptime("2021-07-01", "%Y-%m-%d")
    with mock.patch.object(timezone, "now", return_value=current_date):
        call_command("job_alert_to_customers")

    assert Run.objects.filter(is_manual=True, job=job).count() == 1


def test__alert_job__weekly_not_create_manual_run():
    connector = ConnectorFactory(enabled=True)
    ConnectorCapabilityFactory(
        connector=connector, type=ConnectorCapabilityTypes.INVOICE__DOWNLOAD
    )
    job = JobFactory(connector=connector)
    JobSchedule.objects.create(
        job=job,
        frequency=Frequency.WEEKLY,
        day_of_week=[DaysOfWeek.TUESDAY],
    )
    JobStatFactory.create(
        job=job,
        date=datetime.strptime("2021-07-01", "%Y-%m-%d") - timedelta(days=1),
        df_count=1,
    )
    current_date = datetime.strptime("2021-07-01", "%Y-%m-%d")
    with mock.patch.object(timezone, "now", return_value=current_date):
        call_command("job_alert_to_customers")

    assert Run.objects.filter(is_manual=True, job=job).count() == 0


def test__get_total_df_count_date_type():
    connector = ConnectorFactory(enabled=True)
    ConnectorCapabilityFactory(
        connector=connector, type=ConnectorCapabilityTypes.INVOICE__DOWNLOAD
    )
    job = JobFactory(connector=connector)

    current_date = datetime.strptime("2021-07-01", "%Y-%m-%d")
    now = timezone.now()
    with pytest.raises(Exception) as exception:
        sla.get_total_df_count(job, str(current_date), now)
    assert (
        str(exception.value)
        == f"[SLAGTDC10] Invalid date type, start_date : {current_date}, end_date : {now}"
    )


def test__get_total_df_count_success():
    connector = ConnectorFactory(enabled=True)
    ConnectorCapabilityFactory(
        connector=connector, type=ConnectorCapabilityTypes.INVOICE__DOWNLOAD
    )
    job = JobFactory(connector=connector)
    JobStatFactory.create(
        job=job, date=datetime.strptime("2021-06-29", "%Y-%m-%d"), df_count=1
    )

    current_date = datetime.strptime("2021-06-01", "%Y-%m-%d")
    now = timezone.now()
    stat = sla.get_total_df_count(job, current_date, now)
    assert stat == 1


@pytest.mark.parametrize(
    "frequency, current_date",
    [
        (Frequency.MONTHLY, datetime.strptime("2021-07-01", "%Y-%m-%d")),
        (Frequency.WEEKLY, datetime.strptime("2021-07-01", "%Y-%m-%d")),
    ],
)
def test__get_total_df_count_for_current_period_type_exception(frequency, current_date):
    connector = ConnectorFactory(enabled=True)
    ConnectorCapabilityFactory(
        connector=connector, type=ConnectorCapabilityTypes.INVOICE__DOWNLOAD
    )
    job = JobFactory(connector=connector)

    with pytest.raises(Exception) as exception:
        sla.get_total_df_count_for_current_period(job, frequency, str(current_date))
    assert (
        str(exception.value)
        == f"[SLAGTDC10] Invalid datetime type, now : {current_date}"
    )


@pytest.mark.parametrize(
    "frequency, current_date",
    [
        (Frequency.MONTHLY, datetime.strptime("2021-06-30", "%Y-%m-%d")),
        (Frequency.WEEKLY, datetime.strptime("2021-06-29", "%Y-%m-%d")),
    ],
)
def test__get_total_df_count_for_current_period_success(frequency, current_date):
    connector = ConnectorFactory(enabled=True)
    ConnectorCapabilityFactory(
        connector=connector, type=ConnectorCapabilityTypes.INVOICE__DOWNLOAD
    )
    job = JobFactory(connector=connector)
    JobStatFactory.create(
        job=job, date=datetime.strptime("2021-06-28", "%Y-%m-%d"), df_count=1
    )

    stat = sla.get_total_df_count_for_current_period(job, frequency, current_date)
    assert stat == 1


@pytest.mark.parametrize(
    "frequency, current_date",
    [
        (Frequency.MONTHLY, datetime.strptime("2021-07-01", "%Y-%m-%d")),
        (Frequency.WEEKLY, datetime.strptime("2021-07-01", "%Y-%m-%d")),
    ],
)
def test__get_total_df_count_for_previous_period_type_exception(
    frequency, current_date
):
    connector = ConnectorFactory(enabled=True)
    ConnectorCapabilityFactory(
        connector=connector, type=ConnectorCapabilityTypes.INVOICE__DOWNLOAD
    )
    job = JobFactory(connector=connector)

    current_date = datetime.strptime("2021-07-01", "%Y-%m-%d")
    now = timezone.now()
    with pytest.raises(Exception) as exception:
        sla.get_total_df_count_for_previous_period(job, frequency, str(now))
    assert str(exception.value) == f"[SLAGTDC10] Invalid datetime type, now : {now}"


@pytest.mark.parametrize(
    "frequency, current_date",
    [
        (Frequency.MONTHLY, datetime.strptime("2021-07-01", "%Y-%m-%d")),
        (Frequency.WEEKLY, datetime.strptime("2021-07-01", "%Y-%m-%d")),
    ],
)
def test__get_total_df_count_for_previous_period_success(frequency, current_date):
    connector = ConnectorFactory(enabled=True)
    ConnectorCapabilityFactory(
        connector=connector, type=ConnectorCapabilityTypes.INVOICE__DOWNLOAD
    )
    job = JobFactory(connector=connector)
    JobStatFactory.create(
        job=job, date=datetime.strptime("2021-06-25", "%Y-%m-%d"), df_count=1
    )

    stat = sla.get_total_df_count_for_previous_period(job, frequency, current_date)
    assert stat == 1


@pytest.mark.parametrize(
    "frequency, current_date, is_breached",
    [
        (Frequency.MONTHLY, datetime.strptime("2021-07-01", "%Y-%m-%d"), True),
        (Frequency.MONTHLY, datetime.strptime("2021-07-01", "%Y-%m-%d"), False),
        (Frequency.WEEKLY, datetime.strptime("2021-07-01", "%Y-%m-%d"), True),
        (Frequency.WEEKLY, datetime.strptime("2021-07-01", "%Y-%m-%d"), False),
    ],
)
def test__is_sla_breached_success(frequency, current_date, is_breached):
    connector = ConnectorFactory(enabled=True)
    ConnectorCapabilityFactory(
        connector=connector, type=ConnectorCapabilityTypes.INVOICE__DOWNLOAD
    )
    job = JobFactory(connector=connector)
    if frequency == Frequency.WEEKLY:
        job_schedule = JobSchedule.objects.create(
            job=job,
            frequency=frequency.ident,
            day_of_week=[DaysOfWeek.TUESDAY],
        )
    else:
        job_schedule = JobSchedule.objects.create(
            job=job,
            frequency=frequency.ident,
            date_of_month=[6],
        )

    if not is_breached:
        JobStatFactory.create(
            job=job, date=current_date - timedelta(days=1), df_count=1
        )

    assert sla.is_sla_breached(job_schedule, current_date) == is_breached


@pytest.mark.parametrize(
    "frequency, current_date, is_valid_time",
    [
        (Frequency.MONTHLY, datetime.strptime("2021-07-05", "%Y-%m-%d"), True),
        (Frequency.MONTHLY, datetime.strptime("2021-07-01", "%Y-%m-%d"), False),
        (Frequency.WEEKLY, datetime.strptime("2021-07-03", "%Y-%m-%d"), True),
        (Frequency.WEEKLY, datetime.strptime("2021-07-01", "%Y-%m-%d"), False),
    ],
)
def test__is_valid_time_to_send_sla_breach_email(
    frequency, current_date, is_valid_time
):
    connector = ConnectorFactory(enabled=True)
    ConnectorCapabilityFactory(
        connector=connector, type=ConnectorCapabilityTypes.INVOICE__DOWNLOAD
    )
    job = JobFactory(connector=connector)
    if frequency == Frequency.WEEKLY:
        job_schedule = JobSchedule.objects.create(
            job=job,
            frequency=frequency.ident,
            day_of_week=[DaysOfWeek.TUESDAY],
        )
    else:
        job_schedule = JobSchedule.objects.create(
            job=job,
            frequency=frequency.ident,
            date_of_month=[6],
        )

    assert (
        sla.is_valid_time_to_send_sla_breach_email(job_schedule, current_date)
        == is_valid_time
    )
