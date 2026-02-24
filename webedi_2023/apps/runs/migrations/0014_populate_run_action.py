from django.db import migrations
from django.db import models
from apps.definitions.models import ConnectorCapabilityTypes, ConnectorType


def guess_operation(run):
    job = run.job
    connector = job.connector
    request_parameters = run.request_parameters or {}
    if run.dry_run:
        return ConnectorCapabilityTypes.INTERNAL__WEB_LOGIN
    elif connector.type == ConnectorType.ACCOUNTING.ident:
        if "import_payments" in request_parameters:
            return ConnectorCapabilityTypes.PAYMENT__IMPORT_INFO
        elif "import_entities" in request_parameters:
            return ConnectorCapabilityTypes.ACCOUNTING__IMPORT_MULTIPLE_ENTITIES
        elif "accounting" in request_parameters:
            return ConnectorCapabilityTypes.PAYMENT__EXPORT_INFO
        else:
            # random default
            return ConnectorCapabilityTypes.INTERNAL__WEB_LOGIN
    elif connector.type == ConnectorType.VENDOR.ident:
        return ConnectorCapabilityTypes.INVOICE__DOWNLOAD
    else:
        # random default
        return ConnectorCapabilityTypes.INTERNAL__WEB_LOGIN


def populate_run_action(apps, schema_editor):
    Run = apps.get_model("runs", "Run")
    objects = models.Manager()
    objects.model = Run
    runs = objects.filter(action__isnull=True)
    for run in runs:
        run.action = guess_operation(run)
        run.save()


class Migration(migrations.Migration):
    dependencies = [
        ("runs", "0013_auto_20210421_0434"),
    ]

    operations = [
        migrations.RunPython(populate_run_action, atomic=True),
    ]
