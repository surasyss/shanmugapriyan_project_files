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
from apps.jobconfig.models import ConnectorRequest, Frequency, JobSchedule
from tests.apps.jobconfig.factories import (
    ConnectorRequestFactory,
    JobScheduleFactory,
    JobFactory,
)


def assert_structure__job_schedule(job_schedule_dict: dict):
    job_schedule_dict = copy.copy(job_schedule_dict)
    assert isinstance(job_schedule_dict.pop("id"), str)
    assert isinstance(job_schedule_dict.pop("frequency"), str)
    assert isinstance(job_schedule_dict.pop("job"), str)

    job_schedule_dict.pop("date_of_month")
    job_schedule_dict.pop("week_of_month")
    job_schedule_dict.pop("day_of_week")


@pytest.mark.api("schedule-list")
def test__job_schedule_create__success(seed_authenticated_api):
    job = JobFactory.create()

    data = {
        "job": job.id,
        "frequency": "weekly",
        "day_of_week": ["monday", "tuesday", "wednesday"],
    }

    response = seed_authenticated_api.api.post(data=data, format="json")
    assert response.status_code == status.HTTP_201_CREATED

    assert_structure__job_schedule(response.data)


@pytest.mark.api("schedule-detail")
def test__job_schedule_patch__success(seed_authenticated_api):
    job = JobFactory.create(account=seed_authenticated_api.account)
    job_schedule = JobScheduleFactory.create(job=job, frequency=Frequency.DAILY.ident)

    data = {
        "job": job.id,
        "frequency": "weekly",
        "day_of_week": ["monday", "tuesday", "wednesday"],
    }

    seed_authenticated_api.api.set_url_params(pk=job_schedule.id)
    response = seed_authenticated_api.api.patch(data=data, format="json")

    assert response.status_code == status.HTTP_200_OK

    job_schedule = JobSchedule.objects.get(id=job_schedule.id)
    assert job_schedule.day_of_week == ["monday", "tuesday", "wednesday"]

    assert job_schedule.frequency == Frequency.WEEKLY.ident
    assert_structure__job_schedule(response.data)


@pytest.mark.api("schedule-detail")
def test__job_schedule_get_job_sch__success(seed_authenticated_api):
    job = JobFactory.create(account=seed_authenticated_api.account)
    job_schedule = JobScheduleFactory.create(job=job, frequency=Frequency.DAILY.ident)

    seed_authenticated_api.api.set_url_params(pk=job_schedule.id)
    response = seed_authenticated_api.api.get()

    assert response.status_code == status.HTTP_200_OK
    assert response.data.get("frequency") == Frequency.DAILY.ident
    assert_structure__job_schedule(response.data)


@pytest.mark.api("schedule-list")
def test__job_schedule_get__success(seed_authenticated_api):
    job = JobFactory.create()
    job_schedule = JobScheduleFactory.create(job=job, frequency=Frequency.DAILY.ident)

    # seed_authenticated_api.api.set_url_params(pk=job_schedule.id)
    response = seed_authenticated_api.api.get()

    assert response.status_code == status.HTTP_200_OK
    assert len(response.data) > 0
