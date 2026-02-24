from django.db import migrations


def migrate_connector_entity_to_capabilities(apps, schema_editor):
    pass


class Migration(migrations.Migration):
    dependencies = [
        ("definitions", "0010_auto_20210414_1252"),
    ]

    operations = [
        migrations.RunPython(migrate_connector_entity_to_capabilities, atomic=True)
    ]
