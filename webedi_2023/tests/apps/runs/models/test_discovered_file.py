import json
import tempfile
import uuid
from unittest import TestCase

import pytest
from django.core.exceptions import ValidationError
from django.db import IntegrityError

from apps.runs.models import FileFormat, DiscoveredFile
from integrator.conf import PROJECT_DIR
from spices.documents import DocumentType
from tests.apps.runs.factories import RunFactory, DiscoveredFileFactory

SAMPLE_FILE = f"{PROJECT_DIR.rstrip('/')}/tests/apps/runs/models/sample.pdf"
SAMPLE_EMPTY_FILE = (
    f"{PROJECT_DIR.rstrip('/')}/tests/apps/runs/models/sample_for_empty.pdf"
)
SAMPLE_UNICODE_DECODE_ERROR = (
    f"{PROJECT_DIR.rstrip('/')}/tests/apps/runs/models/sample_unicode_decode_error.pdf"
)
SAMPLE_JSON_WITH_EXECUTION_ID = f"{PROJECT_DIR.rstrip('/')}/tests/apps/runs/models/sample_json_with_execution_id.json"


class DiscoveredFileModelTests(TestCase):
    # def test_df__build_unique__duplicate_exception(self):
    #     account1 = AccountSharedCoreObjectFactory(remote_id="12345", type="fkracc")
    #     job1 = JobFactory(enabled=True, account=account1)
    #     run1 = RunFactory(job=job1)
    #     reference_code = str(uuid.uuid4())
    #     df = DiscoveredFile.build_unique(
    #         run1,
    #         reference_code,
    #         document_type=DocumentType.INVOICE.ident,
    #         file_format=FileFormat.PDF.ident,
    #         original_download_url=str(uuid.uuid4()),
    #         original_filename=f"{reference_code}.pdf",
    #         document_properties={},
    #     )
    #     df.save()
    #     with pytest.raises(Exception) as exc:
    #         DiscoveredFile.build_unique(
    #             run1,
    #             reference_code,
    #             document_type=DocumentType.INVOICE.ident,
    #             file_format=FileFormat.PDF.ident,
    #             original_download_url=str(uuid.uuid4()),
    #             original_filename=f"{reference_code}.pdf",
    #             document_properties={},
    #         )
    #     assert (
    #         exc.value.args[0]
    #         == "[IDFFISR] CRITICAL: Duplicate file found in the SAME run,"
    #         " indicates a bug in the code"
    #     )
    #
    # def test_df__build_unique__job_run_account_conflict(self):
    #     account1 = AccountSharedCoreObjectFactory(remote_id="12345", type="fkracc")
    #     account2 = AccountSharedCoreObjectFactory(remote_id="98765", type="fkracc")
    #     job1 = JobFactory(enabled=True, account=account1)
    #     job2 = JobFactory(enabled=True, account=account2, connector=job1.connector)
    #     run1 = RunFactory(job=job1)
    #     reference_code = str(uuid.uuid4())
    #     df = DiscoveredFile.build_unique(
    #         run1,
    #         reference_code,
    #         document_type=DocumentType.INVOICE.ident,
    #         file_format=FileFormat.PDF.ident,
    #         original_download_url=str(uuid.uuid4()),
    #         original_filename=f"{reference_code}.pdf",
    #         document_properties={},
    #     )
    #     df.save()
    #     run2 = RunFactory(job=job2)
    #     with pytest.raises(Exception) as exc:
    #         DiscoveredFile.build_unique(
    #             run2,
    #             reference_code,
    #             document_type=DocumentType.INVOICE.ident,
    #             file_format=FileFormat.PDF.ident,
    #             original_download_url=str(uuid.uuid4()),
    #             original_filename=f"{reference_code}.pdf",
    #             document_properties={},
    #         )
    #     assert (
    #         exc.value.args[0]
    #         == "[IDDFRJAC] CRITICAL: Duplicate file found from different job "
    #         "and account from the same connector"
    #     )

    def test_df__soft_delete(self):
        df = DiscoveredFileFactory(content_hash=str(uuid.uuid4()))
        old_content_hash = df.content_hash
        df.delete()
        self.assertTrue(df.is_deleted)
        self.assertIn(old_content_hash, df.content_hash)
        self.assertIn("deleted", df.content_hash)
        with pytest.raises(DiscoveredFile.DoesNotExist):
            DiscoveredFile.objects.get(pk=df.pk)

    def test_df__soft_delete_already_deleted(self):
        df = DiscoveredFileFactory(content_hash=str(uuid.uuid4()))
        # deleting once
        df.delete()
        old_content_hash = df.content_hash
        # deleting same object again
        df.delete()
        self.assertTrue(df.is_deleted)
        self.assertEqual(old_content_hash, df.content_hash)

    def test_df__save_content_for_already_created_df(self):
        const = str(uuid.uuid4())
        df = DiscoveredFileFactory(content_hash=const)
        with self.assertRaises(Exception):
            df.save_content(SAMPLE_FILE)

    def test_df__save_content_for_pdf_file__with_extract_text_hash(self):
        run = RunFactory(job__enabled=True)
        discovered_file = DiscoveredFile.build_unique(
            run,
            reference_code="",
            document_type=DocumentType.INVOICE.ident,
            file_format=FileFormat.PDF.ident,
            original_download_url=str(uuid.uuid4()),
            original_filename=f"test.pdf",
            document_properties={},
        )
        discovered_file.save_content(SAMPLE_FILE, compute_extracted_text_hash=True)
        assert discovered_file.content_hash is not None
        assert discovered_file.extracted_text_hash is not None

    def test_df__save_content_for_pdf_file__without_extract_text_hash(self):
        run = RunFactory(job__enabled=True)
        reference_code = str(uuid.uuid4())
        discovered_file = DiscoveredFile.build_unique(
            run,
            reference_code,
            document_type=DocumentType.INVOICE.ident,
            file_format=FileFormat.PDF.ident,
            original_download_url=str(uuid.uuid4()),
            original_filename=f"{reference_code}.pdf",
            document_properties={},
        )
        discovered_file.save_content(SAMPLE_FILE, compute_extracted_text_hash=False)
        assert discovered_file.content_hash is not None
        assert discovered_file.extracted_text_hash is None

    def test_df__save_content_for_pdf_file__with_extract_text_hash_empty_file(self):
        run = RunFactory(job__enabled=True)
        reference_code = str(uuid.uuid4())
        discovered_file = DiscoveredFile.build_unique(
            run,
            reference_code,
            document_type=DocumentType.INVOICE.ident,
            file_format=FileFormat.PDF.ident,
            original_download_url=str(uuid.uuid4()),
            original_filename=f"{reference_code}.pdf",
            document_properties={},
        )
        discovered_file.save_content(
            SAMPLE_EMPTY_FILE, compute_extracted_text_hash=True
        )
        assert discovered_file.content_hash is not None
        assert discovered_file.extracted_text_hash is ""

    def test_df__save_content_for_pdf_file__with_extract_text_hash_unicode_decode_error(
        self,
    ):
        run = RunFactory(job__enabled=True)
        reference_code = str(uuid.uuid4())
        discovered_file = DiscoveredFile.build_unique(
            run,
            reference_code,
            document_type=DocumentType.INVOICE.ident,
            file_format=FileFormat.PDF.ident,
            original_download_url=str(uuid.uuid4()),
            original_filename=f"{reference_code}.pdf",
            document_properties={},
        )
        discovered_file.save_content(
            SAMPLE_UNICODE_DECODE_ERROR, compute_extracted_text_hash=True
        )
        assert discovered_file.content_hash is not None
        assert discovered_file.extracted_text_hash is None

    def test_df__save_content_for_json_file__with_sample_json_with_execution_id(self):
        run = RunFactory(job__enabled=True)
        reference_code = str(uuid.uuid4())
        discovered_file = DiscoveredFile.build_unique(
            run,
            reference_code,
            document_type=DocumentType.INVOICE.ident,
            file_format=FileFormat.PDF.ident,
            original_download_url=str(uuid.uuid4()),
            original_filename=f"{reference_code}.json",
            document_properties={},
        )
        discovered_file.save_content(
            SAMPLE_JSON_WITH_EXECUTION_ID, compute_extracted_text_hash=True
        )
        assert discovered_file.content_hash is not None
        assert discovered_file.extracted_text_hash is None

    def test_df__save_content_for_json_file__with_sample_json_with_execution_id_duplicate(
        self,
    ):
        run = RunFactory(job__enabled=True)
        reference_code = str(uuid.uuid4())
        discovered_file = DiscoveredFile.build_unique(
            run,
            reference_code,
            document_type=DocumentType.INVOICE.ident,
            file_format=FileFormat.PDF.ident,
            original_download_url=str(uuid.uuid4()),
            original_filename=f"{reference_code}.json",
            document_properties={},
        )
        discovered_file.save_content(
            SAMPLE_JSON_WITH_EXECUTION_ID, compute_extracted_text_hash=True
        )

        with open(SAMPLE_JSON_WITH_EXECUTION_ID, "rb") as file_contents:
            with tempfile.NamedTemporaryFile(delete=True, suffix=f".json") as temp:
                discovered_file = DiscoveredFile.build_unique(
                    run,
                    reference_code,
                    document_type=DocumentType.INVOICE.ident,
                    file_format=FileFormat.PDF.ident,
                    original_download_url=str(uuid.uuid4()),
                    original_filename=f"{reference_code}.json",
                    document_properties={},
                )
                data = json.loads(file_contents.read())
                data["meta"]["generator"]["execution_id"] = str(uuid.uuid4())
                temp.write(bytes(json.dumps(data), "utf-8"))
                temp.flush()
                with self.assertRaises(IntegrityError):
                    discovered_file.save_content(
                        temp.name, compute_extracted_text_hash=True
                    )

    def test_df__save_content_for_other_files(self):
        run = RunFactory(job__enabled=True)
        reference_code = str(uuid.uuid4())
        discovered_file = DiscoveredFile.build_unique(
            run,
            reference_code,
            document_type=DocumentType.INVOICE.ident,
            file_format=FileFormat.CSV.ident,
            original_download_url=str(uuid.uuid4()),
            original_filename=f"{reference_code}.csv",
            document_properties={},
        )
        with tempfile.NamedTemporaryFile(mode="w", suffix=".csv") as fp:
            fp.writelines(["a,b,c", "x,y,z"])
            discovered_file.save_content(fp.name, compute_extracted_text_hash=True)
        assert discovered_file.content_hash is not None
        assert discovered_file.extracted_text_hash is None

    def test_df__empty_not_allowed_extracted_text_hash(self):
        df = DiscoveredFileFactory(
            content_hash=str(uuid.uuid4()), extracted_text_hash="   "
        )
        with pytest.raises(ValidationError) as exc:
            df.full_clean()
        assert exc.value.message_dict["extracted_text_hash"] == [
            "value is an empty string"
        ]

    def test_df__unique_constraint_content_hash(self):
        content_hash = str(uuid.uuid4())
        DiscoveredFileFactory(content_hash=content_hash)
        with pytest.raises(IntegrityError) as exc:
            DiscoveredFileFactory(content_hash=content_hash)
        assert "duplicate key value violates unique constraint" in exc.value.args[0]

    def test_df__unique_constraint_extracted_text_hash(self):
        extracted_text_hash = str(uuid.uuid4())
        DiscoveredFileFactory(
            extracted_text_hash=extracted_text_hash, content_hash=extracted_text_hash
        )
        with pytest.raises(IntegrityError) as exc:
            DiscoveredFileFactory(
                extracted_text_hash=extracted_text_hash,
                content_hash=extracted_text_hash,
            )
        assert "duplicate key value violates unique constraint" in exc.value.args[0]
