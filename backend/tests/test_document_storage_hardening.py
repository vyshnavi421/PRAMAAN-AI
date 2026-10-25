"""
Regression tests for upload/storage hardening (audit findings F1-F4):
F1 - missing real uploads are never replaced with fabricated bytes (seeded demo docs keep their placeholder)
F2 - extraction cannot overwrite existing fields on failure; seeded docs refused; success is persisted
F3 - only INSTITUTION_USER (owner) and REVIEWER may upload / extract
F4 - document_type validated before any write; failed uploads leave no file and no metadata
"""
import glob
import io
import os

import pytest
from fastapi.testclient import TestClient

from app.core.auth import UserRole, get_test_auth_headers
from app.main import app
from app.models.enums import DocumentVerificationStatus, DocumentType
from app.models.domain import ExtractedField, FieldProvenance
from app.services.application_service import ApplicationService, global_application_service as app_svc
from app.services.audit_service import global_audit_service
from app.services.document_extractor import global_document_extractor
from app.services.document_storage import DocumentStorageService, global_document_storage

client = TestClient(app)
client_no_raise = TestClient(app, raise_server_exceptions=False)

INSTITUTION = "inst-hardening-01"


def make_pdf(text: str) -> bytes:
    stream = f"BT /F1 12 Tf 50 750 Td ({text}) Tj ET"
    return (
        "%PDF-1.4\n1 0 obj\n<< /Type /Catalog /Pages 2 0 R >>\nendobj\n"
        "2 0 obj\n<< /Type /Pages /Kids [3 0 R] /Count 1 >>\nendobj\n"
        "3 0 obj\n<< /Type /Page /Parent 2 0 R /MediaBox [0 0 595 842] /Contents 4 0 R "
        "/Resources << /Font << /F1 5 0 R >> >> >>\nendobj\n"
        f"4 0 obj\n<< /Length {len(stream)} >>\nstream\n{stream}\nendstream\nendobj\n"
        "5 0 obj\n<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>\nendobj\n"
        "trailer\n<< /Size 6 /Root 1 0 R >>\nstartxref\n0\n%%EOF"
    ).encode("latin-1")


NOC_PDF = make_pdf("STATE FIRE AND RESCUE SERVICES CERTIFICATE No: FS-2026-9999 Valid Until: 2029-12-31")


def test_extracted_expiry_bbox_focuses_on_date_substring():
    """A claim embedded in a longer PDF text chunk gets a focused normalized box."""
    fields, status, note = global_document_extractor.extract_document(
        content_bytes=make_pdf("Issuing Authority: Fire Service Valid until: 2024-01-14"),
        doc_type=DocumentType.FIRE_SAFETY_NOC,
        original_filename="fire_safety_noc.pdf",
    )
    expiry = next(field for field in fields if field.field_key == "noc_expiry_date")
    bbox = expiry.provenance.bounding_box
    assert status == DocumentVerificationStatus.VERIFICATION_PENDING, note
    assert bbox is not None and len(bbox) == 4
    assert 0 <= bbox[0] < bbox[2] <= 1
    assert 0 <= bbox[1] < bbox[3] <= 1
    # The expected date token should occupy only a small piece of the containing text line.
    assert bbox[2] - bbox[0] < 0.2
    assert bbox[0] > 0.1



@pytest.mark.parametrize("document_type", list(DocumentType))
def test_extractor_handles_every_public_document_type(document_type):
    """All exposed DocumentType values should extract a supported field or honestly abstain."""
    fields, status, note = global_document_extractor.extract_document(
        content_bytes=make_pdf(
            "Institution: Test Institute Valid Until: 2029-12-31 "
            "Land Area: 50 acres Built-up Area: 2000 sqm"
        ),
        doc_type=document_type,
        original_filename=f"{document_type.value.lower()}.pdf",
    )
    assert status in {
        DocumentVerificationStatus.VERIFICATION_PENDING,
        DocumentVerificationStatus.MANUAL_REVIEW_REQUIRED,
    }, note
    if not fields:
        assert status == DocumentVerificationStatus.MANUAL_REVIEW_REQUIRED, note



@pytest.mark.parametrize("document_type", list(DocumentType))
def test_extractor_supports_every_declared_document_type(document_type):
    """Every public upload type must route through extraction without enum-attribute errors."""
    fields, status, note = global_document_extractor.extract_document(
        content_bytes=make_pdf(
            "Institution: Test Institute Valid Until: 2029-12-31 "
            "Land Area: 50 acres Built-up Area: 2000 sqm"
        ),
        doc_type=document_type,
        original_filename=f"{document_type.value.lower()}.pdf",
    )
    assert fields, f"{document_type.value} should at least retain an auditable generic claim: {note}"
    assert status in {
        DocumentVerificationStatus.VERIFICATION_PENDING,
        DocumentVerificationStatus.MANUAL_REVIEW_REQUIRED,
    }



@pytest.fixture(autouse=True)
def isolated_storage(tmp_path, monkeypatch):
    """Point protected storage at a temp dir so tests never touch the real storage folder."""
    root = tmp_path / "protected"
    root.mkdir()
    monkeypatch.setattr(global_document_storage, "root_dir", str(root))
    monkeypatch.setattr(global_document_storage, "_memory_cache", {})
    return root


@pytest.fixture
def dossier():
    """A fresh, empty application owned by INSTITUTION; removed afterwards so seeded state is untouched."""
    res = client.post(
        "/api/v1/applications",
        json={"institution_name": "Hardening Test Institute", "institution_id": INSTITUTION},
        headers=get_test_auth_headers("usr-officer-01"),
    )
    assert res.status_code == 201, res.text
    app_id = res.json()["application_id"]
    yield app_id
    app_svc._applications.pop(app_id, None)
    app_svc._workflow.pop(app_id, None)


def headers_for(role_user: str):
    if role_user == "inst-owner":
        return get_test_auth_headers("usr-inst-hard", role=UserRole.INSTITUTION_USER, institution_id=INSTITUTION)
    return get_test_auth_headers(role_user)


def upload(app_id, headers, data=NOC_PDF, doc_type="FIRE_SAFETY_NOC", name="noc.pdf", c=client):
    return c.post(
        "/api/v1/documents/upload",
        data={"document_type": doc_type, "application_id": app_id},
        files={"file": (name, io.BytesIO(data), "application/pdf")},
        headers=headers,
    )


def stored_files(root):
    return glob.glob(os.path.join(str(root), "**", "*"), recursive=True) and [
        f for f in glob.glob(os.path.join(str(root), "**", "*"), recursive=True) if os.path.isfile(f)
    ]


# ───────────────────────── F1: no fabricated bytes ─────────────────────────

def test_f1_real_upload_bytes_survive_storage_restart_with_custom_root(tmp_path):
    root = str(tmp_path / "custom_root")
    first = DocumentStorageService(root_dir=root)
    first.store_document("inst-x", "doc-1", NOC_PDF)
    restarted = DocumentStorageService(root_dir=root)  # empty cache == process restart
    assert restarted.get_document_bytes("storage/protected/inst-x/doc-1.bin", "doc-1") == NOC_PDF


def test_f1_missing_real_upload_returns_none_not_fake_pdf(tmp_path):
    svc = DocumentStorageService(root_dir=str(tmp_path / "r"))
    assert svc.get_document_bytes("storage/protected/inst-x/never-stored.bin", "never-stored") is None


def test_f1_protected_key_cannot_escape_storage_root(tmp_path):
    outside = tmp_path / "secret.bin"
    outside.write_bytes(b"%PDF-secret")
    svc = DocumentStorageService(root_dir=str(tmp_path / "r"))
    assert svc.get_document_bytes("storage/protected/../secret.bin", "x") is None


def test_f1_content_endpoint_404_when_real_file_is_gone(dossier, isolated_storage):
    doc = upload(dossier, headers_for("usr-officer-01")).json()
    for f in stored_files(isolated_storage):
        os.unlink(f)
    global_document_storage._memory_cache.clear()
    res = client.get(f"/api/v1/documents/{doc['id']}/content", headers=headers_for("usr-officer-01"))
    assert res.status_code == 404


def test_f1_seeded_demo_document_content_is_still_served():
    res = client.get("/api/v1/documents/doc-clean-fire/content", headers=headers_for("usr-officer-01"))
    assert res.status_code == 200
    assert res.content.startswith(b"%PDF-")


@pytest.mark.parametrize("key", [
    "storage/unknown-app/doc.pdf",                 # unknown application id
    "storage/app-case-clean/../../etc/passwd.pdf", # traversal / wrong depth
    "storage/app-case-clean/doc.exe",              # wrong extension
    "storage/app-case-clean/sub/doc.pdf",          # wrong depth
    "other/app-case-clean/doc.pdf",                # wrong prefix
    "random.pdf", "", "storage/protected/inst-x/missing.bin",
])
def test_f1_unknown_or_malformed_non_protected_keys_never_get_synthetic_bytes(tmp_path, key):
    svc = DocumentStorageService(root_dir=str(tmp_path / "r"))
    assert svc.get_document_bytes(key, "no-such-doc") is None
    assert DocumentStorageService.is_demo_seed_key(key) is False


def test_f1_every_seeded_document_key_is_recognised_and_served(tmp_path):
    seeded = [d for a in app_svc._applications.values() if a.application_id in ApplicationService._SEEDED_IDS
              for d in a.documents if not d.storage_key.startswith("storage/protected/")]
    assert seeded
    svc = DocumentStorageService(root_dir=str(tmp_path / "storage"))
    for d in seeded:
        assert DocumentStorageService.is_demo_seed_key(d.storage_key), d.storage_key
        assert svc.get_document_bytes(d.storage_key, d.id).startswith(b"%PDF-")


# ───────────────────────── F2: extraction safety ─────────────────────────

def test_f2_extract_on_seeded_demo_document_is_refused_and_leaves_it_untouched():
    _, doc = app_svc.find_document("doc-clean-fire")
    before = (doc.verification_status, [f.id for f in doc.extracted_fields])
    res = client.post("/api/v1/documents/doc-clean-fire/extract", headers=headers_for("usr-officer-01"))
    assert res.status_code == 409
    assert before == (doc.verification_status, [f.id for f in doc.extracted_fields])
    assert len(doc.extracted_fields) > 0


def test_f2_extract_404_when_real_bytes_missing_and_fields_kept(dossier, isolated_storage):
    doc = upload(dossier, headers_for("usr-officer-01")).json()
    _, stored = app_svc.find_document(doc["id"])
    n_fields = len(stored.extracted_fields)
    for f in stored_files(isolated_storage):
        os.unlink(f)
    global_document_storage._memory_cache.clear()
    res = client.post(f"/api/v1/documents/{doc['id']}/extract", headers=headers_for("usr-officer-01"))
    assert res.status_code == 404
    assert len(stored.extracted_fields) == n_fields


def test_f2_empty_reextraction_preserves_existing_fields_and_status(dossier, monkeypatch):
    doc = upload(dossier, headers_for("usr-officer-01")).json()
    _, stored = app_svc.find_document(doc["id"])
    assert stored.extracted_fields, "precondition: upload should have extracted fields"
    before_ids = [f.id for f in stored.extracted_fields]
    before_status = stored.verification_status
    monkeypatch.setattr(
        global_document_extractor, "extract_document",
        lambda **kw: ([], DocumentVerificationStatus.MANUAL_REVIEW_REQUIRED, "forced inconclusive"),
    )
    res = client.post(f"/api/v1/documents/{doc['id']}/extract", headers=headers_for("usr-officer-01"))
    assert res.status_code == 200
    assert [f.id for f in stored.extracted_fields] == before_ids
    assert stored.verification_status == before_status


def test_f2_extractor_exception_leaves_document_unchanged(dossier, monkeypatch):
    doc = upload(dossier, headers_for("usr-officer-01")).json()
    _, stored = app_svc.find_document(doc["id"])
    before_ids = [f.id for f in stored.extracted_fields]

    def boom(**kw):
        raise RuntimeError("parser exploded")

    monkeypatch.setattr(global_document_extractor, "extract_document", boom)
    res = client_no_raise.post(f"/api/v1/documents/{doc['id']}/extract", headers=headers_for("usr-officer-01"))
    assert res.status_code == 500
    assert [f.id for f in stored.extracted_fields] == before_ids


def test_f2_successful_extraction_is_persisted(dossier, tmp_path, monkeypatch):
    data_dir = tmp_path / "data"
    data_dir.mkdir()
    monkeypatch.setattr(app_svc, "_path", str(data_dir / "applications.json"))
    doc = upload(dossier, headers_for("usr-officer-01")).json()

    new_field = ExtractedField(
        field_key="noc_expiry_date", field_value="2031-01-01", raw_value="2031-01-01", confidence=0.9,
        provenance=FieldProvenance(page_number=1),
    )
    monkeypatch.setattr(
        global_document_extractor, "extract_document",
        lambda **kw: ([new_field], DocumentVerificationStatus.VERIFICATION_PENDING, "ok"),
    )
    res = client.post(f"/api/v1/documents/{doc['id']}/extract", headers=headers_for("usr-officer-01"))
    assert res.status_code == 200

    reloaded = ApplicationService(data_dir=str(data_dir))  # simulates a restart
    persisted_doc = [d for d in reloaded.get_application(dossier).documents if d.id == doc["id"]][0]
    assert persisted_doc.get_field("noc_expiry_date").field_value == "2031-01-01"


# ───────────────────────── F3: role enforcement ─────────────────────────

@pytest.mark.parametrize("user", ["usr-auditor-01", "usr-admin-01"])
def test_f3_read_only_roles_cannot_upload_or_extract(dossier, isolated_storage, user):
    res = upload(dossier, headers_for(user))
    assert res.status_code == 403
    assert stored_files(isolated_storage) == []
    assert app_svc.get_application(dossier).documents == []

    real = upload(dossier, headers_for("usr-officer-01")).json()
    ext = client.post(f"/api/v1/documents/{real['id']}/extract", headers=headers_for(user))
    assert ext.status_code == 403


@pytest.mark.parametrize("user", ["usr-officer-01", "inst-owner"])
def test_f3_reviewer_and_owning_institution_can_upload_and_extract(dossier, user):
    res = upload(dossier, headers_for(user))
    assert res.status_code == 201
    assert client.post(f"/api/v1/documents/{res.json()['id']}/extract", headers=headers_for(user)).status_code == 200


def test_f3_other_institution_is_still_forbidden(dossier):
    res = upload(dossier, get_test_auth_headers("usr-inst-city"))
    assert res.status_code == 403
    real = upload(dossier, headers_for("usr-officer-01")).json()
    assert client.post(f"/api/v1/documents/{real['id']}/extract", headers=get_test_auth_headers("usr-inst-city")).status_code == 403


def test_f3_unauthenticated_upload_still_401(dossier):
    res = client.post(
        "/api/v1/documents/upload",
        data={"document_type": "FIRE_SAFETY_NOC", "application_id": dossier},
        files={"file": ("a.pdf", io.BytesIO(NOC_PDF), "application/pdf")},
    )
    assert res.status_code == 401


# ───────────────────────── F4: validate first, roll back on failure ─────────────────────────

def test_f4_invalid_document_type_writes_nothing(dossier, isolated_storage):
    res = upload(dossier, headers_for("usr-officer-01"), doc_type="NOT_A_TYPE")
    assert res.status_code == 400
    assert stored_files(isolated_storage) == []
    assert app_svc.get_application(dossier).documents == []


def test_f4_persist_failure_rolls_back_file_and_metadata(dossier, isolated_storage, monkeypatch):
    calls = {"n": 0}
    real_persist = app_svc.persist

    def flaky_persist():
        calls["n"] += 1
        if calls["n"] == 1:
            raise OSError("disk full")
        real_persist()

    monkeypatch.setattr(app_svc, "persist", flaky_persist)
    res = upload(dossier, headers_for("usr-officer-01"), c=client_no_raise)
    assert res.status_code == 500
    assert stored_files(isolated_storage) == []
    assert app_svc.get_application(dossier).documents == []


def test_f4_audit_failure_rolls_back_file_and_metadata(dossier, isolated_storage, monkeypatch):
    def boom(*a, **kw):
        raise RuntimeError("audit down")

    monkeypatch.setattr(global_audit_service, "record_event", boom)
    res = upload(dossier, headers_for("usr-officer-01"), c=client_no_raise)
    assert res.status_code == 500
    assert stored_files(isolated_storage) == []
    assert app_svc.get_application(dossier).documents == []


def test_f4_extractor_failure_during_upload_leaves_no_file(dossier, isolated_storage, monkeypatch):
    def boom(**kw):
        raise RuntimeError("parser exploded")

    monkeypatch.setattr(global_document_extractor, "extract_document", boom)
    res = upload(dossier, headers_for("usr-officer-01"), c=client_no_raise)
    assert res.status_code == 500
    assert stored_files(isolated_storage) == []
    assert app_svc.get_application(dossier).documents == []


def test_f4_successful_upload_still_stores_exactly_one_file(dossier, isolated_storage):
    res = upload(dossier, headers_for("usr-officer-01"))
    assert res.status_code == 201
    assert len(stored_files(isolated_storage)) == 1
    assert client.get(f"/api/v1/documents/{res.json()['id']}/content", headers=headers_for("usr-officer-01")).content == NOC_PDF
