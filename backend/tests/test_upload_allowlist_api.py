"""Route-level tests for upload validation and manual-review abstention."""
import io

import pytest
from fastapi.testclient import TestClient
from PIL import Image

from app.main import app
from app.services.application_service import global_application_service as app_svc
from tests.test_document_storage_hardening import (
    dossier, isolated_storage, make_pdf, stored_files, upload,
)
from app.core.auth import get_test_auth_headers

client = TestClient(app)
REVIEWER = lambda: get_test_auth_headers("usr-officer-01")  # noqa: E731


def make_png() -> bytes:
    output = io.BytesIO()
    Image.new("RGB", (2, 2), color=(240, 240, 240)).save(output, format="PNG")
    return output.getvalue()


@pytest.mark.parametrize("name,data", [
    ("noc.txt", b"%PDF-1.4\nnot really a full PDF"),
    ("noc", b"%PDF-1.4\nno extension"),
    ("noc.png", b"%PDF-1.4\nwrong extension"),
    ("noc.pdf", make_png()),
])
def test_bad_extension_or_mismatch_is_rejected_and_nothing_is_stored(
    dossier, isolated_storage, name, data
):
    before = len(app_svc.get_application(dossier).documents)
    res = upload(dossier, REVIEWER(), data=data, name=name)
    assert res.status_code == 400
    assert len(app_svc.get_application(dossier).documents) == before
    assert stored_files(isolated_storage) == []


def test_oversized_upload_is_rejected_and_not_stored(dossier, isolated_storage):
    big = b"%PDF-1.4\n" + b"0" * (26 * 1024 * 1024)
    res = upload(dossier, REVIEWER(), data=big, name="big.pdf")
    assert res.status_code == 413
    assert stored_files(isolated_storage) == []


def test_png_upload_is_stored_with_png_mime_and_requires_review(dossier):
    res = upload(dossier, REVIEWER(), data=make_png(), name="scan.png")
    assert res.status_code == 201, res.text
    body = res.json()
    assert body["mime_type"] == "image/png"
    assert body["verification_status"] == "manual review required"


def test_readable_pdf_without_recognisable_fields_abstains_instead_of_inventing_a_claim(dossier):
    res = upload(
        dossier, REVIEWER(),
        data=make_pdf("Hello world nothing useful here at all"),
        name="random.pdf",
    )
    assert res.status_code == 201, res.text
    body = res.json()
    assert body["extracted_fields"] == []
    assert body["verification_status"] == "manual review required"
