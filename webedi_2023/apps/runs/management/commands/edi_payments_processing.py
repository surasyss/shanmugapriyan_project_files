from django.core.management.base import BaseCommand

from apps.adapters import engine
from apps.definitions.models import ConnectorType, ConnectorCapabilityTypes
from apps.jobconfig.models import Job
from apps.runs.management.commands import LOGGER
from apps.runs.models import RunCreatedVia
from apps.runs.run_factory import create_run


class Command(BaseCommand):
    def handle(self, *args, **options):
        LOGGER.info("Beginning to look for Jobs that must be run")

        # pylint: disable=no-member
        jobs = Job.objects.filter(
            enabled=True,
            connector__enabled=True,
            connector__type=ConnectorType.VENDOR.ident,
        )
        counter = 0
        for counter, job in enumerate(jobs, start=1):
            LOGGER.info(f"Run requested for Job id {job.id}")
            run = create_run(
                job,
                ConnectorCapabilityTypes.PAYMENT__IMPORT_INFO,
                RunCreatedVia.SCHEDULED,
                dry_run=False,
            )
            LOGGER.info(f"Processing files for run {run.id} and Job id {job.id}")
            engine.process_payments(run)

        LOGGER.info(
            f"Submitted total {counter} Job.run_now requests for async processing"
        )
