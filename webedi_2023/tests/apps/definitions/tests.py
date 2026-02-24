from django.core.exceptions import ValidationError
from django.test import TestCase
from spices.django3.testing.factory.shared_core_object_model import (
    VendorGroupSharedCoreObjectFactory,
    VendorSharedCoreObjectFactory,
)

from tests.apps.definitions.factories import (
    ConnectorFactory,
    ConnectorVendorInfoFactory,
)


class ConnectorModelTests(TestCase):
    def test_save__insert_disabled(self):
        connector = ConnectorFactory(enabled=False)
        self.assertFalse(connector.enabled)

    def test_save__insert_enabled(self):
        connector = ConnectorFactory(enabled=True)
        self.assertTrue(connector.enabled)

    def test_save__update(self):
        # first both enabled
        connector = ConnectorFactory(enabled=True)

        # then change connector WITHOUT changing enabled flag
        connector.vendor_id = 2
        connector.enabled = False
        connector.save()

        self.assertEqual(2, connector.vendor_id)
        self.assertFalse(connector.enabled)

    def test_save__without_vendor_or_group(self):
        with self.assertRaises(ValidationError):
            ConnectorVendorInfoFactory(vendor_group=None, vendor=None)

    def test_save__with_vendor_group(self):
        vendor_group = VendorGroupSharedCoreObjectFactory()
        connector_vendor_info = ConnectorVendorInfoFactory(
            vendor_group=vendor_group, vendor=None, contains_support_document=True
        )
        self.assertEqual(
            connector_vendor_info.vendor_group.remote_id, vendor_group.remote_id
        )
        self.assertEqual(connector_vendor_info.vendor, None)
        self.assertTrue(connector_vendor_info.contains_support_document)

    def test_save__with_vendor(self):
        vendor = VendorSharedCoreObjectFactory()
        connector_vendor_info = ConnectorVendorInfoFactory(
            vendor_group=None, vendor=vendor, contains_support_document=False
        )
        self.assertEqual(connector_vendor_info.vendor.remote_id, vendor.remote_id)
        self.assertEqual(connector_vendor_info.vendor_group, None)
        self.assertFalse(connector_vendor_info.contains_support_document)
