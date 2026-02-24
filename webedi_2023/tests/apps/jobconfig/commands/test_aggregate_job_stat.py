from datetime import timedelta
from unittest import mock

from django.core.management import call_command
from django.utils import timezone

from apps.definitions.models import ConnectorType
from apps.jobconfig.models import JobStat
from tests.apps.jobconfig.factories import JobFactory
from tests.apps.runs.factories import DiscoveredFileFactory, RunFactory


def test__job_stat():
    job1 = JobFactory(connector__type=ConnectorType.VENDOR.ident)
    job2 = JobFactory(connector__type=ConnectorType.VENDOR.ident)
    job3 = JobFactory(connector__type=ConnectorType.ACCOUNTING.ident)

    run1 = RunFactory(job=job1)
    run1.record_success()
    run2 = RunFactory(job=job2, is_manual=True)
    run2.record_failure()

    df1 = DiscoveredFileFactory(
        content_hash="content-hash-for-run1",
        run__job=job1,
    )
    df2 = DiscoveredFileFactory(
        content_hash="content-hash-for-run2",
        run__job=job1,
    )
    df3 = DiscoveredFileFactory(
        content_hash="content-hash-for-run3",
        run__job=job2,
    )

    # As this discovered file has created_date = now - 2, this should not be part of job stats as that
    # is calculated for the previous day only
    with mock.patch.object(
        timezone, "now", return_value=timezone.now() - timedelta(days=2)
    ):
        df4 = DiscoveredFileFactory(
            content_hash="content-hash-for-run4",
            run__job=job2,
        )

    date = timezone.now() + timedelta(days=1)
    with mock.patch.object(timezone, "now", return_value=date):
        call_command("aggregate_job_stats")

    job_stat1 = JobStat.objects.filter(job=job1).first()
    assert job_stat1.df_count == 2
    assert job_stat1.run_total_count == 3
    assert job_stat1.run_success_count == 1
    assert job_stat1.run_manual_all_count == 0
    assert job_stat1.run_login_failure_count == 0

    job_stat2 = JobStat.objects.filter(job=job2).first()
    assert job_stat2.df_count == 1
    assert job_stat2.run_total_count == 2
    assert job_stat2.run_success_count == 0
    assert job_stat2.run_manual_all_count == 1
    assert job_stat2.run_login_failure_count == 0

    job_stat3 = JobStat.objects.filter(job=job3).first()
    assert job_stat3.df_count is None
    assert job_stat3.run_total_count == 0
    assert job_stat3.run_success_count == 0
    assert job_stat3.run_manual_all_count == 0
    assert job_stat3.run_login_failure_count == 0
