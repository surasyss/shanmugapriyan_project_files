from unittest import mock
from unittest.mock import patch
import uuid

import pytest
from django.core.exceptions import ValidationError
from django.test import TestCase
from django.utils import timezone
from spices.django3.testing.factory.shared_core_object_model import (
    LocationSharedCoreObjectFactory,
)
from spices.services import ContextualError

from apps.definitions.models import ConnectorCapabilityTypes
from apps.runs.models import RunStatus, Run, RunCreatedVia
from apps.runs.run_factory import create_run
from tests.apps.adapters.accounting.r365_sync import CompanySharedCoreObjectFactory
from tests.apps.definitions.factories import (
    ConnectorFactory,
    ConnectorCapabilityFactory,
)
from tests.apps.jobconfig.factories import JobFactory
from tests.apps.runs.factories import RunFactory


class RunStatusTests(TestCase):
    def test_as_choices(self):
        """
        Test to prevent human error of adding/removing a RunStatus without corresponding update in `as_choices()`
        """
        class_vars = {k for k in RunStatus.as_ident_message_dict()}
        self.assertEqual(class_vars, {t[0] for t in RunStatus.as_tuples()})


class RunModelTests(TestCase):
    def test_init__default_status(self):
        run = RunFactory()  # type: Run
        self.assertEqual(RunStatus.CREATED.ident, run.status)

    def test_record_execution_start__success(self):
        before = timezone.now()
        run = RunFactory()  # type: Run
        self.assertIsNone(run.execution_start_ts)

        run.record_execution_start()
        self.assertTrue(before < run.execution_start_ts)

    def test_record_success__success(self):
        before = timezone.now()
        run = RunFactory()  # type: Run
        self.assertIsNone(run.execution_end_ts)

        run.record_success()
        self.assertEqual(RunStatus.SUCCEEDED.ident, run.status)
        self.assertTrue(before < run.execution_end_ts)

    def test_record_success__already_complete(self):
        # previously succeeded
        run = RunFactory()  # type: Run
        run.record_success()
        with self.assertRaises(ValidationError):
            run.record_success()

        # previously failed
        run = RunFactory()  # type: Run
        run.record_failure()
        with self.assertRaises(ValidationError):
            run.record_success()

    def test_record_failure__with_exception__success(self):
        before = timezone.now()
        run = RunFactory()  # type: Run
        self.assertIsNone(run.execution_end_ts)

        exc = ContextualError(code="code123", message="message123", params={})
        run.record_failure(exc)

        self.assertEqual(RunStatus.FAILED.ident, run.status)
        self.assertTrue(before < run.execution_end_ts)
        self.assertIsNotNone(run.failure_issue)
        self.assertEqual("code123", run.failure_issue.code)
        self.assertEqual("message123", run.failure_issue.message)

    def test_record_failure__without_exception__success(self):
        before = timezone.now()
        run = RunFactory()  # type: Run
        self.assertIsNone(run.execution_end_ts)

        run.record_failure()
        self.assertEqual(RunStatus.FAILED.ident, run.status)
        self.assertTrue(before < run.execution_end_ts)
        self.assertIsNone(run.failure_issue)

    def test_record_failure__already_complete(self):
        # previously succeeded
        run = RunFactory()  # type: Run
        run.record_success()
        with self.assertRaises(ValidationError):
            run.record_failure()

        # previously failed
        run = RunFactory()  # type: Run
        run.record_failure()
        with self.assertRaises(ValidationError):
            run.record_failure()

    def test_save__insert_with_incorrect_initial_status(self):
        with self.assertRaises(ValidationError):
            RunFactory(status=RunStatus.SUCCEEDED.ident)

    def test_save__insert_with_disabled_job(self):
        run = RunFactory(job__enabled=False)  # should not throw
        self.assertIsNotNone(run)

    def test_save__record_complete_without_timestamp(self):
        run = RunFactory()  # type: Run
        run.status = RunStatus.SUCCEEDED.ident
        with self.assertRaises(ValidationError):
            run.save()

    def test_parameters(self):
        run = RunFactory()  # type: Run
        self.assertIsInstance(run.request_parameters, dict)

    def test_execute_async__celery_on_demand(self):
        run = RunFactory()  # type: Run
        celery_on_demand = mock.Mock()
        celery_on_demand.execute_run_on_demand.return_value = run.job.id

        with patch("apps.runs.tasks.execute_run_on_demand.delay") as mock_task:
            run.execute_async(on_demand=True)
            mock_task.assert_called()

    def test_execute_async__celery(self):
        run = RunFactory()  # type: Run
        celery_on_demand = mock.Mock()
        celery_on_demand.execute_run_on_demand.return_value = run.job.id

        with patch("apps.runs.tasks.execute_run.delay") as mock_task:
            run.execute_async()
            mock_task.assert_called()

    def test_duplicate(self):
        connector = ConnectorFactory()
        ConnectorCapabilityFactory(
            connector=connector, type=ConnectorCapabilityTypes.INTERNAL__WEB_LOGIN
        )
        run = RunFactory(job__connector=connector)  # type: Run
        new_run = run.duplicate()
        self.assertNotEqual(run.id, new_run.id)
        self.assertEqual(run.status, new_run.status)

        run.record_success()

        new_run = run.duplicate()
        self.assertNotEqual(run.id, new_run.id)
        self.assertEqual(RunStatus.CREATED.ident, new_run.status)

    def test_record_partially_success__success(self):
        before = timezone.now()
        run = RunFactory()  # type: Run
        self.assertIsNone(run.execution_end_ts)

        run.record_partial_success()
        self.assertEqual(RunStatus.PARTIALLY_SUCCEEDED.ident, run.status)
        self.assertTrue(before < run.execution_end_ts)

    def test_record_partially_success__already_complete(self):
        # previously partially succeeded
        run = RunFactory()  # type: Run
        run.record_success()
        with self.assertRaises(ValidationError):
            run.record_partial_success()

        # previously failed
        run = RunFactory()  # type: Run
        run.record_failure()
        with self.assertRaises(ValidationError):
            run.record_partial_success()

    def test_execute_async__without_force__aws_switch_enabled(self):
        run = RunFactory()  # type: Run
        aws_batch_client = mock.Mock()
        mock_job_id = str(uuid.uuid4())
        mock_response = {"jobId": mock_job_id}
        aws_batch_client.submit_job.return_value = mock_response
        self.assertEqual(RunStatus.CREATED.ident, run.status)

        with self.settings(
            RUN_SUBMIT_TO_AWS_BATCH=True, AWS_BATCH_CLIENT=aws_batch_client
        ):
            run.execute_async()
            aws_batch_client.submit_job.assert_called_once()
            self.assertEqual(RunStatus.SCHEDULED.ident, run.status)
            self.assertEqual(mock_job_id, run.aws_batch_job_id)

            # second try
            aws_batch_client.submit_job.reset_mock()
            mock_job_id2 = str(uuid.uuid4())
            mock_response = {"jobId": mock_job_id2}
            aws_batch_client.submit_job.return_value = mock_response

            aws_batch_client.submit_job.reset_mock()
            run.execute_async()
            aws_batch_client.submit_job.assert_not_called()
            self.assertEqual(RunStatus.SCHEDULED.ident, run.status)
            self.assertEqual(
                mock_job_id, run.aws_batch_job_id, "Value should remain unchanged"
            )

    def test_execute_async__with_force__aws_switch_enabled(self):
        run = RunFactory()  # type: Run
        aws_batch_client = mock.Mock()
        mock_job_id = str(uuid.uuid4())
        mock_response = {"jobId": mock_job_id}
        aws_batch_client.submit_job.return_value = mock_response

        self.assertEqual(RunStatus.CREATED.ident, run.status)

        with self.settings(
            RUN_SUBMIT_TO_AWS_BATCH=True, AWS_BATCH_CLIENT=aws_batch_client
        ):
            run.execute_async()
            aws_batch_client.submit_job.assert_called_once()
            self.assertEqual(RunStatus.SCHEDULED.ident, run.status)
            self.assertEqual(mock_job_id, run.aws_batch_job_id)

            # second try
            aws_batch_client.submit_job.reset_mock()
            mock_job_id2 = str(uuid.uuid4())
            mock_response = {"jobId": mock_job_id2}
            aws_batch_client.submit_job.return_value = mock_response

            run.execute_async(force=True)
            aws_batch_client.submit_job.assert_called_once()
            self.assertEqual(mock_job_id2, run.aws_batch_job_id)

    def test_execute_async__aws_switch_disabled(self):
        run = RunFactory()  # type: Run
        aws_batch_client = mock.Mock()
        mock_job_id = str(uuid.uuid4())
        mock_response = {"jobId": mock_job_id}
        aws_batch_client.submit_job.return_value = mock_response

        with self.settings(
            RUN_SUBMIT_TO_AWS_BATCH=False, AWS_BATCH_CLIENT=aws_batch_client
        ):
            run.execute_async()

        aws_batch_client.submit_job.assert_not_called()
        self.assertIsNone(run.aws_batch_job_id)


def test__create_acct_run__fail():
    connector = ConnectorFactory(adapter_code="r365")
    ConnectorCapabilityFactory(
        connector=connector, type=ConnectorCapabilityTypes.PAYMENT__EXPORT_INFO
    )
    job = JobFactory(connector=connector)
    with pytest.raises(Exception) as exception:
        create_run(
            job,
            ConnectorCapabilityTypes.PAYMENT__EXPORT_INFO,
            RunCreatedVia.SCHEDULED,
            dry_run=True,
        )

    assert str(exception.value) == "[tag:RUNS01] companies cannot be : None"


@patch("apps.runs.run_factory.create_run")
@patch("apps.runs.run_factory.__construct_parsed_json_for_making_payments")
@patch("apps.runs.run_factory.settings.PIQ_CORE_CLIENT.billpay_export_dry_run")
@patch("spices.django3.coreobjects.base.CoreObjectMixin.retrieve")
def test__create_acct_run__success(
    mocked_retrieve, mocked__billpay_export_dry_run, mocked_convert_json, mocked_run
):
    connector = ConnectorFactory(adapter_code="r365")
    ConnectorCapabilityFactory(
        connector=connector, type=ConnectorCapabilityTypes.PAYMENT__EXPORT_INFO
    )
    company1 = CompanySharedCoreObjectFactory.create()

    job = JobFactory(connector=connector)
    job.companies.add(company1)

    location_1 = {"id": LocationSharedCoreObjectFactory.create().remote_id}
    location_2 = {"id": LocationSharedCoreObjectFactory.create().remote_id}
    company1.restaurants = [location_1, location_2]
    mocked_retrieve.return_value = company1
    create_run(
        job,
        ConnectorCapabilityTypes.PAYMENT__EXPORT_INFO,
        RunCreatedVia.SCHEDULED,
        dry_run=True,
    )
    assert mocked_run.called_once()
