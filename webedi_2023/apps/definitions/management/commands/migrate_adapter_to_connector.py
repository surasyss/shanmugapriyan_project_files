from django.core.management.base import BaseCommand

from apps.definitions.models import Connector
from apps.runs.management.commands import LOGGER


class Command(BaseCommand):
    help = "Migrate adapters to connectors and delete the adapter"

    def handle(self, *args, **options):
        LOGGER.info("Beginning to get all connectors for updating.")
        connectors = list(Connector.objects.all())
        LOGGER.info(f"Total No of Connectors  : {len(connectors)}.")
        for index, connector in enumerate(connectors):
            connector.adapter_code = connector.adapter.code
            if not connector.login_url:
                connector.login_url = connector.adapter.url
            connector.channel = connector.adapter.channel
            connector.save()
            LOGGER.info(
                f"[SUCCESS] Updated [{connector}], completed [{index + 1}] connectors."
            )
