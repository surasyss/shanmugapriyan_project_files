from django.core.management.base import BaseCommand

from apps.definitions.models import Connector, ConnectorType, ConnectorVendorInfo
from apps.jobconfig.models import Job
from apps.runs.management.commands import LOGGER


class Command(BaseCommand):
    help = "Consolidate connectors for r365 to single connector."

    def handle(self, *args, **options):
        LOGGER.info("Beginning to get all connectors for r365")
        # pylint: disable=no-member
        connectors = list(
            Connector.objects.filter(
                type=ConnectorType.ACCOUNTING.value, adapter_code__contains="r365"
            )
        )
        keeping_connector = connectors[0]
        LOGGER.info(f"Keeping Connector with name : {str(keeping_connector)}.")
        for connector in connectors[1:]:
            jobs = Job.objects.filter(connector_id=connector.id)
            LOGGER.info(
                f"No of jobs to be updated : {len(jobs)} for connector with name : {str(connector)}"
            )
            for job in jobs:
                job.connector = keeping_connector
                job.save()

            cvi_list = ConnectorVendorInfo.objects.filter(connector=connector)
            for cvi in cvi_list:
                cvi.delete()

            LOGGER.info(
                f"ConnectorVendorInfo is deleted "
                f"for connector with name : {str(connector)}"
            )
            connector.delete()
            LOGGER.info(f"Connector with name : {str(connector)} marked as deleted.")

        keeping_connector.name = "Restaurant 365"
        keeping_connector.login_url = "https://www.restaurant365.com/"
        keeping_connector.save()
