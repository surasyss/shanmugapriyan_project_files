import factory
from django.conf import settings

from apps.definitions.models import ConnectorCapabilityTypes
from tests.apps.definitions.factories import ConnectorFactory
from tests.apps.jobconfig.factories import JobFactory

from apps.runs.models import Run, DiscoveredFile, RunCreatedVia


class RunFactory(factory.DjangoModelFactory):
    job = factory.SubFactory(JobFactory)
    status = 0
    request_parameters = {
        "version": 1,
        "end_date": str(settings.RUN_DEFAULT_START_DATE.today()),
        "start_date": str(settings.RUN_DEFAULT_START_DATE),
        "import_entities": [],
        "suppress_invoices": False,
    }
    dry_run = False
    action = ConnectorCapabilityTypes.INTERNAL__WEB_LOGIN
    created_via = RunCreatedVia.SCHEDULED

    class Meta:
        model = Run


class DiscoveredFileFactory(factory.DjangoModelFactory):
    connector = factory.SubFactory(ConnectorFactory)
    run = factory.SubFactory(RunFactory)
    original_filename = "fake_original_filename"
    original_download_url = "http://fake_original_url.com/"
    file_format = "pdf"
    document_type = "invoice"
    document_properties = {
        "version": 1,
    }

    class Meta:
        model = DiscoveredFile
