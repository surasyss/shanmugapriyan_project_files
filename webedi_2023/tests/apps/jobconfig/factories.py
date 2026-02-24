import factory
from spices.django3.credentials.models import FTPCredential
from spices.django3.testing.factory.shared_core_object_model import (
    LocationSharedCoreObjectFactory,
    LocationGroupSharedCoreObjectFactory,
    AccountSharedCoreObjectFactory,
    SharedCoreObjectModelFactory,
)
from spices.ftp import FTPType

from apps.definitions.models import ConnectorType
from apps.jobconfig.models import (
    Job,
    PIQMapping,
    FileDiscoveryActionType,
    FileDiscoveryAction,
    ConnectorRequest,
    JobSchedule,
    JobStat,
    JobAlertRule,
)
from tests.apps.definitions.factories import ConnectorFactory


class JobFactory(factory.DjangoModelFactory):
    connector = factory.SubFactory(ConnectorFactory)
    username = factory.Sequence("fake_username-{}".format)
    password = "fake_password"
    account = factory.SubFactory(AccountSharedCoreObjectFactory)
    location = factory.SubFactory(LocationSharedCoreObjectFactory)
    location_group = factory.SubFactory(LocationGroupSharedCoreObjectFactory)
    candidate_restaurant_ids = []
    enabled = True

    class Meta:
        model = Job

    @factory.post_generation
    def companies(self, create, extracted, **kwargs):
        if not create:
            return

        if extracted:
            for company in extracted:
                self.companies.add(company)
                self.save()


class PIQMappingFactory(factory.DjangoModelFactory):
    job = factory.SubFactory(JobFactory)
    piq_data = factory.SubFactory(SharedCoreObjectModelFactory)
    mapping_data = factory.Sequence("mapping_data-{}".format)

    class Meta:
        model = PIQMapping


class FileDiscoveryActionFactory(factory.DjangoModelFactory):
    job = factory.SubFactory(JobFactory)
    document_type = "invoice"
    action_type = FileDiscoveryActionType.NONE.ident
    edi_parser_code = None

    class Meta:
        model = FileDiscoveryAction


class ConnectorRequestFactory(factory.DjangoModelFactory):
    account = factory.SubFactory(AccountSharedCoreObjectFactory)
    name = factory.Sequence("connector_request.name-{}".format)
    login_url = factory.Sequence("connector_request.login_url-{}".format)
    username = factory.Sequence("connector_request.username-{}".format)
    password = "connector_request.fake_password"
    type = ConnectorType.VENDOR
    is_deleted = False

    class Meta:
        model = ConnectorRequest


class FTPCredentialFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = FTPCredential

    server_address = factory.LazyAttributeSequence(
        lambda o, n: f"{factory.Faker('hostname').generate()}"
    )
    ftp_type = FTPType.SFTP
    upload_folder = "tmp"


class JobScheduleFactory(factory.django.DjangoModelFactory):
    job = factory.SubFactory(JobFactory)

    class Meta:
        model = JobSchedule


class JobAlertRuleFactory(factory.django.DjangoModelFactory):
    job = factory.SubFactory(JobFactory)

    class Meta:
        model = JobAlertRule


class JobStatFactory(factory.django.DjangoModelFactory):
    id = factory.Sequence("jobstat-{}".format)
    job = factory.SubFactory(JobFactory)

    class Meta:
        model = JobStat
