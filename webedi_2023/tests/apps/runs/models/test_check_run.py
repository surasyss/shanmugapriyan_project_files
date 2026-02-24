import random
import uuid
from unittest import TestCase

import pytest
from spices.django3.testing.factory.shared_core_object_model import (
    AccountSharedCoreObjectFactory,
)
from spices.documents import DocumentType

from apps import error_codes
from apps.error_codes import ErrorCode
from apps.runs.models import (
    FileFormat,
    DiscoveredFile,
    CheckRun,
    CheckRunExists,
    CheckRunDisabled,
)
from tests.apps.jobconfig.factories import JobFactory
from tests.apps.runs.factories import RunFactory, DiscoveredFileFactory


class CheckRunModelTests(TestCase):
    def test_already_exists_exception_success_patch(self):
        account1 = AccountSharedCoreObjectFactory(remote_id="12345", type="fkracc")
        job1 = JobFactory(enabled=True, account=account1)
        run1 = RunFactory(job=job1)
        chequerun_id = random.randint(111111, 100000000)
        ch = CheckRun.create_unique(run1, chequerun_id)
        ch.is_patch_success = True
        ch.is_checkrun_success = True
        ch.save()
        with pytest.raises(CheckRunExists) as exc:
            CheckRun.create_unique(run1, chequerun_id)
        self.assertTrue(exc.value.previous_checkrun.is_patch_success)
        assert exc.value.code == ErrorCode.PE_CHECKRUN_ALREADY_EXISTS.value

    def test_already_exists_exception_failed_patch(self):
        account1 = AccountSharedCoreObjectFactory(remote_id="12345", type="fkracc")
        job1 = JobFactory(enabled=True, account=account1)
        run1 = RunFactory(job=job1)
        chequerun_id = random.randint(111111, 100000000)
        ch = CheckRun.create_unique(run1, chequerun_id)
        ch.is_patch_success = False
        ch.is_checkrun_success = True
        ch.save()
        with pytest.raises(CheckRunExists) as exc:
            CheckRun.create_unique(run1, chequerun_id)
        self.assertFalse(exc.value.previous_checkrun.is_patch_success)
        assert exc.value.code == ErrorCode.PE_CHECKRUN_ALREADY_EXISTS.value

    def test_disabled_checkrun_exists_exception(self):
        account1 = AccountSharedCoreObjectFactory(remote_id="12345", type="fkracc")
        job1 = JobFactory(enabled=True, account=account1)
        run1 = RunFactory(job=job1)
        chequerun_id = random.randint(111111, 100000000)
        ch = CheckRun.create_unique(run1, chequerun_id)
        ch.is_disabled = True
        ch.save()
        with pytest.raises(CheckRunDisabled) as exc:
            CheckRun.create_unique(run1, chequerun_id)
        self.assertTrue(exc.value.previous_checkrun.is_disabled)
        assert (
            exc.value.args[0]
            == f"Check run {exc.value.previous_checkrun.id} is disabled, hence skipping"
        )
