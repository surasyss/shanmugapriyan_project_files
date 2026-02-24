import uuid

import pytest
from spices.documents import DocumentType

from apps.adapters.file_actions import *
from tests.apps.jobconfig.factories import FileDiscoveryActionFactory
from tests.apps.runs.factories import DiscoveredFileFactory


@pytest.mark.parametrize(
    "document_type",
    [
        DocumentType.INVOICE,
    ],
)
def test_factory__no_discovery_action_defined(document_type):
    discovered_file = DiscoveredFileFactory.create(
        document_type=document_type.ident, content_hash=str(uuid.uuid4())
    )

    action = factory(discovered_file)
    assert isinstance(action, DoNothingAction)
    assert action.discovered_file is discovered_file


@pytest.mark.parametrize(
    "document_type, action_type, action_cls",
    [
        (DocumentType.INVOICE, FileDiscoveryActionType.NONE, DoNothingAction),
        (
            DocumentType.INVOICE,
            FileDiscoveryActionType.PIQ_STANDARD_UPLOAD,
            InvoiceStandardPIQUploadAction,
        ),
        (
            DocumentType.INVOICE,
            FileDiscoveryActionType.PIQ_EDI_UPLOAD,
            InvoiceEDIPIQUploadAction,
        ),
        (
            DocumentType.PAYMENT,
            FileDiscoveryActionType.PAYMENTS_EDI_UPLOAD,
            PaymentUploadEDIAction,
        ),
    ],
)
def test_factory__discovery_action_defined__valid(
    document_type, action_type, action_cls
):
    discovery_action = FileDiscoveryActionFactory.create(
        document_type=document_type.ident, action_type=action_type.ident
    )
    discovered_file = DiscoveredFileFactory.create(
        document_type=document_type.ident,
        run__job=discovery_action.job,
        content_hash=str(uuid.uuid4()),
    )

    action = factory(discovered_file)
    assert isinstance(action, action_cls)
    assert action.discovered_file is discovered_file


def test_factory__discovery_action_defined__not_registered():
    discovery_action = FileDiscoveryActionFactory.create(action_type="hello")
    discovered_file = DiscoveredFileFactory.create(
        document_type=DocumentType.INVOICE.ident,
        run__job=discovery_action.job,
        content_hash=str(uuid.uuid4()),
    )

    with pytest.raises(KeyError):
        factory(discovered_file)
