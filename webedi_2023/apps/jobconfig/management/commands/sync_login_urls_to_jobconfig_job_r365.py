from django.core.management.base import BaseCommand

from apps.definitions.models import Connector, ConnectorType
from apps.jobconfig.models import Job
from apps.runs.management.commands import LOGGER


class Command(BaseCommand):
    help = "Copy all login urls from connectors to jobs for r365."

    def handle(self, *args, **options):
        LOGGER.info("Beginning to get all login urls from connectors for r365")
        connectors = Connector.objects.filter(
            type=ConnectorType.ACCOUNTING.value,  # pylint: disable=no-member
            adapter_code__contains="r365",
        )
        for connector in connectors:
            LOGGER.info(
                f"Copying login url for connector : {connector.id} with name : {connector.name}"
            )
            jobs = Job.objects.filter(connector_id=connector.id)
            LOGGER.info(f"No of jobs to be updated : {len(jobs)}")
            for job in jobs:
                job.login_url = connector.login_url
                job.save()
            LOGGER.info(f"Jobs updated successfully for connector : {connector.id}")
