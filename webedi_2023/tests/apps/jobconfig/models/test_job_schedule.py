import pytest
from django.core.exceptions import ValidationError

from apps.jobconfig.models import JobSchedule, Frequency, DaysOfWeek
from tests.apps.jobconfig.factories import JobFactory


def test__job_schedule__day_of_week__save__fail():
    job = JobFactory.create()

    with pytest.raises(ValidationError) as exc_info:
        JobSchedule.objects.create(job=job, frequency=Frequency.WEEKLY.ident)

    assert (
        exc_info.value.message
        == "When the frequency is weekly, specifying day of week is mandatory"
    )


def test__job_schedule__day_of_week__save__success():
    job = JobFactory.create()

    js = JobSchedule.objects.create(
        job=job, frequency=Frequency.WEEKLY.ident, day_of_week=[DaysOfWeek.MONDAY.ident]
    )

    assert js.id


@pytest.mark.parametrize("date_of_month", [-1, 32])
def test__job_schedule__date_of_month__save__fail(date_of_month):
    job = JobFactory.create()

    with pytest.raises(ValidationError) as exc_info:
        JobSchedule.objects.create(
            job=job, frequency=Frequency.MONTHLY.ident, date_of_month=[date_of_month]
        )

    assert exc_info.value.message == "Date of a month must be between 1 and 31"


def test__job_schedule__date_of_month__save__success():
    job = JobFactory.create()

    js = JobSchedule.objects.create(
        job=job, frequency=Frequency.MONTHLY.ident, date_of_month=[1, 23]
    )

    assert js.date_of_month == [1, 23]
