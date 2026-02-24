from django.core.management.base import BaseCommand
from django.utils import timezone

from apps.definitions.models import ConnectorCapabilityTypes
from apps.jobconfig.models import JobSchedule, Job
from apps.runs.models import RunCreatedVia
from apps.runs.run_factory import create_run
from apps.runs.sla import get_sla_breach_email_content, is_sla_breached


class Command(BaseCommand):
    """
    For weekly alerts, run the job on Monday, this will give alert for the previous week.
        Example: Running the job on 14 June, 2021, will give result of June 7, 2021 to June 13, 2021
    For monthly alerts, run the job on 1st of every month, this will give alert for the previous month
        Example: Running the job on 05 June, 2021, will give result of May 01, 2021 to May 31, 2021
    """

    help = "Alert about job output"

    def handle(self, *args, **options):
        current_ts = timezone.now()
        job_schedules = JobSchedule.objects.filter(
            job__in=Job.objects.runnable(ConnectorCapabilityTypes.INVOICE__DOWNLOAD)
        )

        for schedule in job_schedules:
            if is_sla_breached(schedule, current_ts):
                create_run(
                    schedule.job,
                    ConnectorCapabilityTypes.INVOICE__DOWNLOAD,
                    RunCreatedVia.SCHEDULED,
                    is_manual=True,
                )
            from apps.runs import tasks

            tasks.send_email.delay(get_sla_breach_email_content(schedule, current_ts))
