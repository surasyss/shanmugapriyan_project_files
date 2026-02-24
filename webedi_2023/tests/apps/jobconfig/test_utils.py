from datetime import datetime, timedelta
from unittest import mock

import pytest
from django.conf import settings
from django.test import override_settings
from django.utils import timezone

from apps.jobconfig.models import Frequency, DaysOfWeek
from apps.runs.models import RunStatus
from tests.apps.jobconfig.factories import JobFactory, JobScheduleFactory
from tests.apps.runs.factories import RunFactory


@pytest.mark.parametrize(
    "current_date, result",
    [
        ("2021-05-31", True),  # Monday
        ("2021-06-04", True),  # Friday
        ("2021-06-03", True),  # Thursday
    ],
)
def test__can_schedule__daily(current_date, result):
    job = JobFactory.create()
    schedule = JobScheduleFactory.create(job=job, frequency=Frequency.DAILY.ident)

    current_date = datetime.strptime(current_date, "%Y-%m-%d")
    assert result == schedule.match(current_date)


# def test__can_schedule__daily__true__when_no_job_schedule():
#     """
#     Test - __can_schedule when no job_schedule entry for the job.
#     """
#     job = JobFactory.create()
#     RunFactory.create(job=job)
#     assert __can_schedule(job)


@pytest.mark.parametrize(
    "current_date, result",
    [
        ("2021-05-31", True),  # Monday
        ("2021-06-04", True),  # Friday
        ("2021-06-03", True),  # Thursday
    ],
)
def test__can_schedule__daily__ignore_day_of_week(current_date, result):
    job = JobFactory.create()
    schedule = JobScheduleFactory.create(
        job=job,
        frequency=Frequency.DAILY.ident,
        day_of_week=[DaysOfWeek.MONDAY.ident, DaysOfWeek.FRIDAY.ident],
    )

    current_date = datetime.strptime(current_date, "%Y-%m-%d")
    assert result == schedule.match(current_date)


@pytest.mark.parametrize(
    "current_date, result",
    [
        ("2021-05-31", True),  # Monday
        ("2021-06-04", True),  # Friday
        ("2021-06-03", False),  # Thursday
    ],
)
def test__can_schedule__weekly__day_of_week(current_date, result):
    job = JobFactory.create()
    schedule = JobScheduleFactory.create(
        job=job,
        frequency=Frequency.WEEKLY.ident,
        day_of_week=[DaysOfWeek.MONDAY.ident, DaysOfWeek.FRIDAY.ident],
    )

    current_date = datetime.strptime(current_date, "%Y-%m-%d")
    assert result == schedule.match(current_date)


@pytest.mark.parametrize(
    "current_date, result",
    [
        ("2021-06-01", True),  # Tuesday - 1st Week
        ("2021-06-04", True),  # Friday - 1st Week
        ("2021-06-11", False),  # Friday - 2nd Week
    ],
)
def test__can_schedule__weekly__day_of_week_and_week_of_month(current_date, result):
    job = JobFactory.create()
    schedule = JobScheduleFactory.create(
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
    assert result == schedule.match(current_date)


@pytest.mark.parametrize(
    "current_date, result",
    [
        ("2021-05-31", True),  # Monday - 5th Week
        ("2021-06-04", True),  # Friday - 1st Week
        ("2021-06-12", False),  # Friday - 2nt Week
    ],
)
def test__can_schedule__monthly__day_of_month(current_date, result):
    job = JobFactory.create()
    schedule = JobScheduleFactory.create(
        job=job, frequency=Frequency.MONTHLY.ident, date_of_month=[31, 4]
    )

    current_date = datetime.strptime(current_date, "%Y-%m-%d")
    assert result == schedule.match(current_date)


@pytest.mark.parametrize(
    "current_date, result",
    [
        ("2021-05-01", True),  # Monday
        ("2021-06-04", True),  # Friday
        ("2021-06-03", True),  # Thursday
        ("2021-06-02", False),  # Wednesday
    ],
)
def test__can_schedule__monthly__day_of_month_and_day_of_week(current_date, result):
    job = JobFactory.create()
    schedule = JobScheduleFactory.create(
        job=job,
        frequency=Frequency.MONTHLY.ident,
        day_of_week=[DaysOfWeek.MONDAY.ident, DaysOfWeek.THURSDAY.ident],
        date_of_month=[1, 4],
    )

    current_date = datetime.strptime(current_date, "%Y-%m-%d")
    assert result == schedule.match(current_date)


# def test___can_create_scheduled_run__when_no_run_exsits():
#     """
#     Test - _can_create_schedule_run should return True, when no runs exists for the job
#     """
#     job = JobFactory.create()
#     assert _can_create_scheduled_run(job)
#
#
# @pytest.mark.parametrize('days, result', [
#     (1, True),
#     (0, False),
# ])
# @mock.patch('apps.jobconfig.utils.__can_schedule')
# def test___can_create_scheduled_run__can_schedule_output_true(mock_can_schedule, days, result):
#     """
#     Test - _can_create_schedule_run should return True only when the last run (success) time is greater than 24 hours,
#      when the __can_shedule returns True
#     """
#
#     mock_can_schedule.return_value = True
#
#     current_date = timezone.now()
#     time_gap = current_date - timedelta(days=days, hours=1)
#
#     with mock.patch.object(timezone, "now", return_value=time_gap):
#         job = JobFactory.create()
#         run = RunFactory.create(job=job)
#
#     assert result == _can_create_scheduled_run(job)
#
#
# @override_settings(RUN_RETRY_COUNT=2)
# @mock.patch('apps.jobconfig.utils.__can_schedule')
# def test___can_create_scheduled_run__when_last_run_is_failed(mock_can_schedule):
#     mock_can_schedule.return_value = True
#
#     for i in range(1, settings.RUN_RETRY_COUNT + 1):
#         job = JobFactory.create()
#         run = RunFactory.create(job=job, status=RunStatus.CREATED.ident)
#         run.record_failure()
#
#         if i >= settings.RUN_RETRY_COUNT:
#             assert not _can_create_scheduled_run(job)
#         else:
#             assert _can_create_scheduled_run(job)
#
#
# @override_settings(RUN_RETRY_COUNT=2)
# @mock.patch('apps.jobconfig.utils.__can_schedule')
# def test___can_create_scheduled_run__when_last_run_is_incomplete(mock_can_schedule):
#     mock_can_schedule.return_value = True
#
#     for i in range(1, settings.RUN_RETRY_COUNT + 1):
#         job = JobFactory.create()
#         RunFactory.create(job=job, status=RunStatus.CREATED.ident)
#
#         if i >= settings.RUN_RETRY_COUNT:
#             assert not _can_create_scheduled_run(job)
#         else:
#             assert _can_create_scheduled_run(job)
