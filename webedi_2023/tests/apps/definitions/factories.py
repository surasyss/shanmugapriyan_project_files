import factory
from spices.django3.testing.factory.shared_core_object_model import (
    VendorGroupSharedCoreObjectFactory,
    VendorSharedCoreObjectFactory,
)

from apps.definitions.models import (
    Connector,
    ConnectorVendorInfo,
    ConnectorCapability,
    ConnectorCapabilityTypes,
)


class ConnectorFactory(factory.DjangoModelFactory):
    name = factory.Sequence("fake_connector-{}".format)
    type = "VENDOR"
    enabled = True
    icon = "media/site/test.svg"
    adapter_code = factory.Sequence("code-{}".format)
    login_url = "http://faker.adapter.webedi.com"
    channel = "WEB"

    class Meta:
        model = Connector


class ConnectorVendorInfoFactory(factory.DjangoModelFactory):
    connector = factory.SubFactory(ConnectorFactory)
    vendor_group = factory.SubFactory(VendorGroupSharedCoreObjectFactory)
    vendor = factory.SubFactory(VendorSharedCoreObjectFactory)
    contains_support_document = False
    requires_account_number = True

    class Meta:
        model = ConnectorVendorInfo


class ConnectorCapabilityFactory(factory.DjangoModelFactory):
    connector = factory.SubFactory(ConnectorFactory)
    type = ConnectorCapabilityTypes.INTERNAL__WEB_LOGIN
    supported_file_format = "pdf"

    class Meta:
        model = ConnectorCapability
