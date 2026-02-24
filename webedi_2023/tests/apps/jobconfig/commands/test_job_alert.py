from datetime import datetime
from unittest import mock

import pytest
from django.conf import settings
from django.core.management import call_command
from django.utils import timezone

from apps.jobconfig.models import Period
from tests.apps.jobconfig.factories import (
    JobStatFactory,
    JobFactory,
    JobAlertRuleFactory,
)


@pytest.mark.parametrize("expected_document_count, result", [(1, True), (2, False)])
def test__alert_job__day_rule(expected_document_count, result):
    job = JobFactory.create()
    JobAlertRuleFactory.create(
        job=job,
        expected_document_count=expected_document_count,
        period=Period.DAY.ident,
        period_count=1,
        enabled=True,
    )

    JobStatFactory.create(
        job=job, date=datetime.strptime("2021-06-06", "%Y-%m-%d"), df_count=1
    )

    current_date = datetime.strptime("2021-06-07", "%Y-%m-%d")
    with mock.patch.object(timezone, "now", return_value=current_date):
        with mock.patch.object(settings.SLACK_CLIENT, "message") as mock_slack:
            call_command("job_alert", period="day")

            if result:
                # Result = True: Expected document count matches with the JobStat document count
                assert mock_slack.call_count == 0
            else:
                assert mock_slack.call_count == 1


@pytest.mark.parametrize("expected_document_count, result", [(4, True), (6, False)])
def test__alert_job__week_rule(expected_document_count, result):
    job = JobFactory.create()
    JobAlertRuleFactory.create(
        job=job,
        expected_document_count=expected_document_count,
        period=Period.WEEK.ident,
        period_count=1,
        enabled=True,
    )

    JobStatFactory.create(
        job=job, date=datetime.strptime("2021-06-05", "%Y-%m-%d"), df_count=1
    )
    JobStatFactory.create(
        job=job, date=datetime.strptime("2021-06-05", "%Y-%m-%d"), df_count=1
    )

    # Start of week for June 05, 2021
    JobStatFactory.create(
        job=job, date=datetime.strptime("2021-05-31", "%Y-%m-%d"), df_count=1
    )

    # End of week for June 05, 2021
    JobStatFactory.create(
        job=job, date=datetime.strptime("2021-06-06", "%Y-%m-%d"), df_count=1
    )

    current_date = datetime.strptime("2021-06-10", "%Y-%m-%d")
    with mock.patch.object(timezone, "now", return_value=current_date):
        with mock.patch.object(settings.SLACK_CLIENT, "message") as mock_slack:
            call_command("job_alert", period="week")

            if result:
                # Result = True: Expected document count matches with the JobStat document count
                assert mock_slack.call_count == 0
            else:
                assert mock_slack.call_count == 1


@pytest.mark.parametrize("expected_document_count, result", [(4, True), (6, False)])
def test__alert_job__month_rule(expected_document_count, result):
    job = JobFactory.create()
    JobAlertRuleFactory.create(
        job=job,
        expected_document_count=expected_document_count,
        period=Period.MONTH.ident,
        period_count=1,
        enabled=True,
    )

    JobStatFactory.create(
        job=job, date=datetime.strptime("2021-05-01", "%Y-%m-%d"), df_count=1
    )
    JobStatFactory.create(
        job=job, date=datetime.strptime("2021-05-05", "%Y-%m-%d"), df_count=1
    )

    # Start of month for June 05, 2021
    JobStatFactory.create(
        job=job, date=datetime.strptime("2021-05-01", "%Y-%m-%d"), df_count=1
    )

    # End of month for June 05, 2021
    JobStatFactory.create(
        job=job, date=datetime.strptime("2021-05-31", "%Y-%m-%d"), df_count=1
    )

    current_date = datetime.strptime("2021-06-05", "%Y-%m-%d")
    with mock.patch.object(timezone, "now", return_value=current_date):
        with mock.patch.object(settings.SLACK_CLIENT, "message") as mock_slack:
            call_command("job_alert", period="month")

            if result:
                # Result = True: Expected document count matches with the JobStat document count
                assert mock_slack.call_count == 0
            else:
                assert mock_slack.call_count == 1
