import tempfile
import uuid
from unittest import mock

import pytest
from spices.documents import DocumentType
from spices.services import ContextualError

from apps import error_codes
from apps.adapters.framework import download
from apps.runs.models import DiscoveredFile, FileFormat
from tests.apps.runs.factories import RunFactory


def _build_discovered_file(discovered_file=None):
    if not discovered_file:
        discovered_file = DiscoveredFile()
    discovered_file.document_type = DocumentType.INVOICE.ident
    discovered_file.file_format = FileFormat.CSV.ident
    discovered_file.original_download_url = str(uuid.uuid4())
    discovered_file.original_filename = str(uuid.uuid4())
    discovered_file.document_properties = {}
    return discovered_file


def test_ddf__empty_piq_container_id():
    df = _build_discovered_file()
    df.id = df.pk = str(uuid.uuid4())
    downloader = mock.Mock()
    assert download.download_discovered_file(df, downloader) is None


def test_ddf__already_saved():
    df = _build_discovered_file()
    df.id = df.pk = df.piq_container_id = str(uuid.uuid4())
    downloader = mock.Mock()

    with pytest.raises(ContextualError) as exc:
        download.download_discovered_file(df, downloader)
        assert exc.value.code == error_codes.ErrorCode.PE_INVALID_DISCOVERED_FILE


def test_ddf__success():
    df = _build_discovered_file()
    df.run = RunFactory.create()
    downloader = mock.Mock()

    with tempfile.NamedTemporaryFile(suffix=".csv", delete=False) as fp:
        with open(fp.name, "w") as tmpfile:
            tmpfile.write(f"something-{fp.name}")
        downloader.download.return_value = fp.name
        download.download_discovered_file(df, downloader)
        assert df.local_filepath == fp.name

    downloader.download.assert_called_once()
    assert df.id in df.original_file.name
