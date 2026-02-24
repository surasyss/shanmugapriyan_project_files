from django.db import migrations
from django.db import models

from apps.definitions.models import (
    ConnectorCapability,
    ConnectorCapabilityTypes,
)
from apps.runs.management.commands import LOGGER


def add_dry_run_capability_to_connector(apps, schema_editor):
    Connector = apps.get_model("definitions", "Connector")
    objects = models.Manager()
    objects.model = Connector
    LOGGER.info("[STARTED] Migration of connectors for internal.web_login capability")

    connectors = list(objects.filter(enabled=True))
    for index, connector in enumerate(connectors):
        cc, created = ConnectorCapability.objects.get_or_create(
            connector=connector, type=ConnectorCapabilityTypes.INTERNAL__WEB_LOGIN
        )
        cc.save()
    LOGGER.info("[COMPLETED] Migration of connectors for internal.web_login capability")


class Migration(migrations.Migration):
    dependencies = [
        ("definitions", "0012_auto_20210510_0916"),
    ]

    operations = [
        migrations.RunPython(add_dry_run_capability_to_connector, atomic=True)
    ]
