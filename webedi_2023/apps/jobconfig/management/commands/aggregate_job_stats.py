import datetime
import random
import string

from django.core.management.base import BaseCommand
from django.db.models import Count, Q
from django.utils import timezone

from apps.definitions.models import ConnectorType
from apps.jobconfig.management.commands import LOGGER
from apps.jobconfig.models import JobStat, Job
from apps.runs.models import DiscoveredFile, Run, RunStatus


class Command(BaseCommand):
    help = "Aggregate discovered file details on job level per day"

    def handle(self, *args, **options):
        now = timezone.now()
        previous_day = now - datetime.timedelta(days=1)

        previous_day_date = previous_day.date()
        previous_day_start = previous_day.replace(
            hour=0, minute=0, second=0, microsecond=0
        )
        previous_day_end = now.replace(hour=0, minute=0, second=0, microsecond=0)

        LOGGER.info(f"Populating JobStats for date {previous_day_date}")

        jobs = Job.objects.filter(enabled=True, connector__enabled=True)
        for job in jobs:
            base_condition = Q(
                job=job,
                created_date__gte=previous_day_start,
                created_date__lt=previous_day_end,
            )

            run_counts = Run.objects.aggregate(
                run_total_count=Count("pk", filter=base_condition),
                run_success_count=Count(
                    "pk", filter=base_condition & Q(status=RunStatus.SUCCEEDED.ident)
                ),
                run_manual_all_count=Count(
                    "pk",
                    filter=base_condition & Q(is_manual=True),
                ),
                run_login_failure_count=Count(
                    "pk",
                    filter=base_condition
                    & Q(failure_issue__code="intgrt.auth_failed.web"),
                ),
            )
            run_counts["job"] = job
            run_counts["date"] = previous_day_date
            if job.connector.type == ConnectorType.VENDOR.ident:
                run_counts["df_count"] = DiscoveredFile.objects.filter(
                    run__job=job,
                    run__created_date__gte=previous_day_start,
                    run__created_date__lt=previous_day_end,
                ).count()
            JobStat.objects.create(**run_counts)

        LOGGER.info(f"Done populating JobStats for date {previous_day_date}")
