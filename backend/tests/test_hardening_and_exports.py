"""
Regression tests for: server-authoritative dossiers, tenant isolation on reads of review/validation/
verification data, application creation, persistence of uploads/status, audit service independence,
and the scrutiny-report / deficiency-letter exports.
"""
import tempfile
import shutil
import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.core.auth import get_test_auth_headers
from app.services.audit_service import AuditService
from app.services.application_service import ApplicationService
from app.models.domain import ApplicationInput

client = TestClient(app)
OFFICER = get_test_auth_headers("usr-officer-01")
APEX = get_test_auth_headers("usr-inst-apex")
CITY = get_test_auth_headers("usr-inst-city")
AUDITOR = get_test_auth_headers("usr-auditor-01")


def _run_review(app_id="app-case-clean", headers=OFFICER):
    return client.post(f"/api/v1/applications/{app_id}/full-review", headers=headers)


def test_full_review_ignores_forged_client_dossier():
    """A client-supplied dossier must never replace the server's stored one."""
    stored = client.get("/api/v1/applications/app-case-expired", headers=OFFICER).json()
    forged = dict(stored)
    forged["documents"] = []
    forged["declared_data"] = {"institution_name": "Forged"}
    res = client.post("/api/v1/applications/app-case-expired/full-review",
                      headers=OFFICER, json={"application_data": forged})
    assert res.status_code == 201
    assert res.json()["summary"]["deficiencies"] >= 1, "Expired NOC deficiency must still be found"


def test_full_review_unknown_application_is_404():
    assert _run_review("app-does-not-exist").status_code == 404


def test_institution_cannot_read_other_tenants_review_or_validation():
    review = _run_review("app-case-clean").json()  # belongs to inst-apex-01
    rid, aid = review["review_id"], "app-case-clean"
    for url in (f"/api/v1/review-runs/{rid}",
                f"/api/v1/applications/{aid}/full-review/latest",
                f"/api/v1/applications/{aid}/validation-runs",
                f"/api/v1/applications/{aid}/scrutiny-report"):
        assert client.get(url, headers=CITY).status_code == 403, url
        assert client.get(url, headers=APEX).status_code == 200, url


def test_institution_cannot_run_review_on_other_tenant():
    assert _run_review("app-case-clean", CITY).status_code == 403


def test_institution_cannot_use_verification_reads_on_other_tenant():
    doc_id = client.get("/api/v1/applications/app-case-clean", headers=OFFICER).json()["documents"][0]["id"]
    assert client.get(f"/api/v1/documents/{doc_id}/verification-attempts", headers=CITY).status_code == 403
    r = client.post(f"/api/v1/documents/{doc_id}/verify", headers=CITY, json={
        "adapter_id": "issuer-registry", "method": "ISSUER_REGISTRY", "reference_id": "X"})
    assert r.status_code == 403


def test_create_application_uses_session_identity_not_body():
    res = client.post("/api/v1/applications", headers=CITY, json={
        "institution_name": "City College of Engineering",
        "institution_id": "inst-apex-01",  # spoof attempt: must be ignored
    })
    assert res.status_code == 201
    body = res.json()
    assert body["institution_id"] == "inst-city-02"
    assert client.get(f"/api/v1/applications/{body['application_id']}", headers=APEX).status_code == 403
    listed = client.get("/api/v1/applications", headers=CITY).json()
    assert any(a["application_id"] == body["application_id"] and a["status_tag"] == "NOT_YET_REVIEWED"
               and a["workflow_status"] == "DRAFT" for a in listed)


def test_auditor_cannot_create_application():
    r = client.post("/api/v1/applications", headers=AUDITOR, json={"institution_name": "Whoever Institute"})
    assert r.status_code == 403


def test_reviewer_must_name_institution():
    r = client.post("/api/v1/applications", headers=OFFICER, json={"institution_name": "Some Institute"})
    assert r.status_code == 422


def test_audit_service_instances_are_independent_and_tamper_safe():
    a, b = AuditService(), AuditService()
    a.simulate_tamper()
    assert a.verify_chain().is_valid is False
    assert b.verify_chain().is_valid is True
    a.restore_chain()
    assert a.verify_chain().is_valid is True


def test_persistence_roundtrip_for_status_and_documents():
    tmp = tempfile.mkdtemp(prefix="pramaan_hard_")
    try:
        s1 = ApplicationService(data_dir=tmp)
        s1.set_workflow_status("app-case-clean", "CLARIFICATION_REQUESTED")
        s2 = ApplicationService(data_dir=tmp)
        assert s2.get_workflow_status("app-case-clean") == "CLARIFICATION_REQUESTED"
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def test_audit_ledger_survives_restart_and_stays_valid():
    tmp = tempfile.mkdtemp(prefix="pramaan_audit_")
    try:
        a1 = AuditService(data_dir=tmp)
        a1.record_event("usr-officer-01", "X", {"k": 1}, application_id="app-x")
        a2 = AuditService(data_dir=tmp)
        assert a2.verify_chain().is_valid and len(a2.get_events()) == len(a1.get_events())
        a2.record_event("usr-officer-01", "Y", {}, application_id="app-x")
        assert AuditService(data_dir=tmp).verify_chain().is_valid
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def test_scrutiny_report_export_and_html_escaping():
    _run_review("app-case-expired")
    r = client.get("/api/v1/applications/app-case-expired/scrutiny-report", headers=OFFICER)
    assert r.status_code == 200 and "DEMO / SIMULATED" in r.text and "RULE-APH-EXP-003" in r.text
    from app.services.report_export import _e
    assert "<script>" not in _e("<script>alert(1)</script>")


def test_scrutiny_report_requires_prior_review():
    res = client.post("/api/v1/applications", headers=OFFICER,
                      json={"institution_name": "Fresh Institute", "institution_id": "inst-fresh-09"})
    aid = res.json()["application_id"]
    assert client.get(f"/api/v1/applications/{aid}/scrutiny-report", headers=OFFICER).status_code == 404


def test_deficiency_letter_is_reviewer_only_and_marked_draft():
    _run_review("app-case-expired")
    url = "/api/v1/applications/app-case-expired/deficiency-letter"
    assert client.get(url, headers=APEX).status_code == 403
    assert client.get(url, headers=AUDITOR).status_code == 403
    r = client.get(url, headers=OFFICER)
    assert r.status_code == 200
    assert "DRAFT — NOT ISSUED" in r.text and "not a finding of misconduct" in r.text
