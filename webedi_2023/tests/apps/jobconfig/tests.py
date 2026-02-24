import pytest
from django.db import IntegrityError
from django.test import TestCase
from spices.django3.testing.factory.shared_core_object_model import (
    LocationSharedCoreObjectFactory,
)

from apps.jobconfig.models import PIQMapping, Job, JobDisabledReason
from apps.runs.models import DiscoveredFile
from tests.apps.definitions.factories import ConnectorFactory
from tests.apps.jobconfig.factories import (
    JobFactory,
    PIQMappingFactory,
    ConnectorRequestFactory,
)
from tests.apps.runs.factories import DiscoveredFileFactory


class JobModelTests(TestCase):
    def test_save__insert_disabled(self):
        job = JobFactory(enabled=False)
        self.assertTrue(job.connector.enabled)
        self.assertFalse(job.enabled)

    def test_save__insert_enabled_with_connector_enabled(self):
        job = JobFactory(enabled=True)
        self.assertTrue(job.enabled)

    def test_save__insert_enabled_with_connector_disabled(self):
        connector = ConnectorFactory(enabled=False)
        job = JobFactory(connector=connector, enabled=True)
        self.assertTrue(job.enabled)

    def test_soft_delete(self):
        connector = ConnectorFactory()
        job = JobFactory(connector=connector, enabled=True)
        old_username = job.username
        job.delete()
        self.assertTrue(job.is_deleted)
        self.assertIn(old_username, job.username)
        self.assertIn("deleted", job.username)
        with pytest.raises(Job.DoesNotExist):
            Job.objects.get(pk=job.id)

    def test_soft_delete_already_deleted_object(self):
        connector = ConnectorFactory()
        job = JobFactory(connector=connector, enabled=True)
        # deleting once
        job.delete()
        old_username = job.username
        # deleting same object again
        job.delete()
        self.assertTrue(job.is_deleted)
        self.assertEqual(old_username, job.username)

    def test_soft_delete_with_discovered_file(self):
        connector = ConnectorFactory()
        job = JobFactory(connector=connector)
        df1 = DiscoveredFileFactory(
            content_hash="content-hash-for-run1",
            run__job=job,
        )
        df2 = DiscoveredFileFactory(
            content_hash="content-hash-for-run2",
            run__job=job,
        )
        df3 = DiscoveredFileFactory(
            content_hash="content-hash-for-run3",
            run__job=job,
        )
        job.delete()
        self.assertTrue(job.is_deleted)
        self.assertEqual(0, DiscoveredFile.objects.filter(run__job=job).count())
        deleted_dfs = DiscoveredFile.objects.all_with_deleted().filter(run__job=job)
        self.assertEqual(3, deleted_dfs.count())
        assert {df1.id, df2.id, df3.id} == {df.id for df in deleted_dfs}
        assert all(df.is_deleted for df in deleted_dfs)

    def test_save__update(self):
        job = JobFactory(enabled=True)

        job.restaurant_id = 2
        job.enabled = False
        job.save()

        self.assertEqual(2, job.restaurant_id)
        self.assertFalse(job.enabled)

    def test_save__unset_disabled_reason(self):
        job = JobFactory(disabled_reason=JobDisabledReason.INCORRECT_CREDENTIALS.ident)
        job.username = "test"
        job.save()
        self.assertIsNone(job.disabled_reason)


class RestaurantMappingTests(TestCase):
    def test_save__name_in_lowercase(self):
        location = LocationSharedCoreObjectFactory(
            remote_id="2", display_name="location1234"
        )
        piq_mapping = PIQMappingFactory(piq_data=location, mapping_data="REST123")
        self.assertEqual(piq_mapping.piq_data.remote_id, "2")
        self.assertEqual(piq_mapping.mapping_data, "rest123")

    def test__get_restaurant_id__by_name_case_insensitive(self):
        location = LocationSharedCoreObjectFactory(
            remote_id=3, display_name="location1234"
        )
        job = JobFactory(enabled=True, location=location)
        piq_mapping = PIQMappingFactory(
            job=job, piq_data=location, mapping_data="rest1234"
        )
        self.assertEqual(
            PIQMapping.get_piq_mapped_data(job, "REST1234", "r"),
            piq_mapping.piq_data.remote_id,
        )
        self.assertEqual(
            PIQMapping.get_piq_mapped_data(job, "Rest1234", "r"),
            piq_mapping.piq_data.remote_id,
        )
        self.assertEqual(
            PIQMapping.get_piq_mapped_data(job, "rest1234", "r"),
            piq_mapping.piq_data.remote_id,
        )

    def test__none_get_restaurant_id__by_name(self):
        job = JobFactory(enabled=True)
        self.assertIsNone(
            PIQMapping.get_piq_mapped_data(job, "non-existing-location", "r")
        )

    # def test_save__null_location_id(self):
    #     with self.assertRaises(IntegrityError):
    #         RestaurantMappingFactory(location=None)

    def test_save__null_job(self):
        with self.assertRaises(IntegrityError):
            PIQMappingFactory(job=None)

    def test_save__null_name(self):
        with self.assertRaises(IntegrityError):
            PIQMappingFactory(mapping_data=None)

    def test_save__null_job_id(self):
        with self.assertRaises(IntegrityError):
            PIQMappingFactory(job_id=None)

    def test_create__duplicate_rest_mapping(self):
        rest_mapping = PIQMappingFactory(piq_data_id=1, mapping_data="Rest123")

        with self.assertRaises(IntegrityError):
            PIQMappingFactory(
                job=rest_mapping.job, piq_data_id=1, mapping_data="Rest123"
            )

    def test_create__duplicate_rest_mapping__case_sensitive(self):
        rest_mapping = PIQMappingFactory(piq_data_id=1, mapping_data="rest123")

        with self.assertRaises(IntegrityError):
            PIQMappingFactory(
                job=rest_mapping.job, piq_data_id=1, mapping_data="REST123"
            )

    def test_save__duplicate_rest_mapping__name(self):
        rest_mapping_1 = PIQMappingFactory(piq_data_id=1, mapping_data="Rest123")
        rest_mapping_2 = PIQMappingFactory(
            job=rest_mapping_1.job, piq_data_id=1, mapping_data="Rest"
        )

        with self.assertRaises(IntegrityError):
            rest_mapping_2.mapping_data = "Rest123"
            rest_mapping_2.save()

    def test_save__duplicate_rest_mapping__rest_id(self):
        rest_mapping_1 = PIQMappingFactory(piq_data_id=1, mapping_data="Rest")
        rest_mapping_2 = PIQMappingFactory(
            job=rest_mapping_1.job, piq_data_id=2, mapping_data="Rest"
        )

        with self.assertRaises(IntegrityError):
            rest_mapping_2.piq_data_id = 1
            rest_mapping_2.save()


class ConnectorRequestModelTests(TestCase):
    def test_save_null_converted_to_connector(self):
        cr = ConnectorRequestFactory()
        self.assertIsNone(cr.converted_to_connector)
        self.assertIsNone(cr.converted_to_job)

    def test_save_null_converted_to_job(self):
        cr = ConnectorRequestFactory()
        self.assertIsNone(cr.converted_to_job)

    def test_save_valid_converted_to_job(self):
        connector = ConnectorFactory()
        cr = ConnectorRequestFactory(converted_to_connector=connector)
        old_password = cr.password
        cr.convert_to_job()
        self.assertIsNotNone(cr.converted_to_job)
        self.assertTrue(cr.converted_to_job.enabled)
        self.assertEqual(old_password, cr.converted_to_job.password)
        self.assertEqual(cr.password, "")
        self.assertTrue(cr.is_deleted)
