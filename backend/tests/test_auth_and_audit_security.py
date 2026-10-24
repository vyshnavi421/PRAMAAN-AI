"""
PRAMAAN-AI Automated Security, Authorisation & Audit Test Suite
Verifies:
1. Role-Based Access Control (RBAC) matrix (INSTITUTION_USER, REVIEWER, RULES_ADMIN, AUDITOR)
2. Review actions workflow: confirm finding, request evidence, record manual review
3. Mandatory justification reason for finding dismissal (>= 10 characters)
4. Strict guardrail: Autonomous AI approval/rejection barred
5. Insecure Direct Object Reference (IDOR) prevention on document metadata & content
6. Tenant scoping on application audit trails
7. Cryptographic hash-chain integrity verification (SHA-256)
8. Disposable audit tamper simulation and exact sequence detection
9. Chain restoration to pristine signed state
10. Secure file upload: 25MB limit, magic byte validation, path traversal immunity, extension blacklist
11. Data retention & mathematical limitation statutory disclosures
"""
import io
import pytest
from fastapi.testclient import TestClient

from fastapi import HTTPException
from app.main import app
from app.core.auth import (
    get_current_user,
    UserRole,
    UserContext,
    require_roles,
    create_demo_session,
    get_test_auth_headers,
    global_session_store
)
from app.services.audit_service import global_audit_service
from app.services.application_service import global_application_service

client = TestClient(app)


# ---------------------------------------------------------------------------
# 1. Identity & Role Resolution
# ---------------------------------------------------------------------------

def test_default_unauthenticated_request_raises_401():
    """Unauthenticated access directly raises 401, not defaulting to Scrutiny Officer."""
    with pytest.raises(HTTPException) as exc_info:
        get_current_user(authorization=None)
    assert exc_info.value.status_code == 401

    # Verified session for Scrutiny Officer has correct role
    session = create_demo_session("usr-officer-01")
    assert session.user_id == "usr-officer-01"
    assert session.role == UserRole.REVIEWER
    assert "AICTE Scrutiny Officer" in session.full_name


def test_user_resolution_from_synthetic_directory():
    """Resolves pre-seeded synthetic actors by session creation."""
    inst_user = create_demo_session(user_id="usr-inst-apex")
    assert inst_user.role == UserRole.INSTITUTION_USER
    assert inst_user.institution_id == "inst-apex-01"

    auditor_user = create_demo_session(user_id="usr-auditor-01")
    assert auditor_user.role == UserRole.AUDITOR

    admin_user = create_demo_session(user_id="usr-admin-01")
    assert admin_user.role == UserRole.RULES_ADMIN


def test_user_resolution_from_role_header_and_invalid_role():
    """Custom session with specific role resolves, while missing/invalid session token fails."""
    auditor_session = create_demo_session(user_id="custom-auditor", role=UserRole.AUDITOR)
    assert auditor_session.role == UserRole.AUDITOR

    with pytest.raises(HTTPException) as exc_info:
        get_current_user(authorization="Bearer non-existent-token")
    assert exc_info.value.status_code == 401


# ---------------------------------------------------------------------------
# 2. Review Actions & Server-Side Authorisation
# ---------------------------------------------------------------------------

def test_officer_can_record_valid_review_actions():
    """Scrutiny officer can confirm findings, request evidence, or record manual review."""
    actions = [
        ("CONFIRM_FINDING", "Deficiency confirmed after cross-verifying land records."),
        ("REQUEST_FURTHER_EVIDENCE", "Requesting updated fire safety NOC from municipal authority."),
        ("RECORD_MANUAL_VERIFICATION", "Physical verification completed by regional directorate team.")
    ]
    officer_headers = get_test_auth_headers("usr-officer-01")
    for action_type, reason in actions:
        res = client.post(
            "/api/v1/findings/f-101/review-actions",
            json={
                "action_type": action_type,
                "justification_reason": reason,
                "application_id": "app-case-clean"
            },
            headers=officer_headers
        )
        assert res.status_code == 201
        data = res.json()
        assert data["event_type"] == f"REVIEW_ACTION_{action_type}"
        assert data["details"]["justification"] == reason
        assert data["details"]["is_human_decision"] is True
        assert data["details"]["ai_autonomous_decision"] is False


def test_dismiss_finding_requires_mandatory_justification():
    """Dismissing a finding requires a non-empty reason of at least 10 characters."""
    officer_headers = get_test_auth_headers("usr-officer-01")
    # 1. Valid dismissal (>= 10 chars)
    valid_res = client.post(
        "/api/v1/findings/f-101/review-actions",
        json={
            "action_type": "DISMISS_FINDING",
            "justification_reason": "Waiver granted by AICTE executive committee resolution #44.",
            "application_id": "app-case-clean"
        },
        headers=officer_headers
    )
    assert valid_res.status_code == 201

    # 2. Missing reason (< 10 chars)
    short_res = client.post(
        "/api/v1/findings/f-101/review-actions",
        json={
            "action_type": "DISMISS_FINDING",
            "justification_reason": "ok waive",
            "application_id": "app-case-clean"
        },
        headers=officer_headers
    )
    assert short_res.status_code == 400
    assert "at least 10 characters" in short_res.json()["detail"]

    # 3. Empty reason
    empty_res = client.post(
        "/api/v1/findings/f-101/review-actions",
        json={
            "action_type": "DISMISS_FINDING",
            "justification_reason": "",
            "application_id": "app-case-clean"
        },
        headers=officer_headers
    )
    assert empty_res.status_code == 400
    assert "Mandatory justification reason" in empty_res.json()["detail"]


def test_autonomous_ai_decision_strictly_barred():
    """Strict AICTE guardrail: Any attempt to auto-approve or auto-reject is rejected."""
    officer_headers = get_test_auth_headers("usr-officer-01")
    prohibited_actions = ["AUTO_APPROVE", "AI_DECISION", "AUTONOMOUS_REJECT"]
    for action in prohibited_actions:
        res = client.post(
            "/api/v1/findings/f-101/review-actions",
            json={
                "action_type": action,
                "justification_reason": "Automated pipeline approved the dossier without human scrutiny.",
                "application_id": "app-case-clean"
            },
            headers=officer_headers
        )
        assert res.status_code == 400
        assert "Autonomous AI approval or rejection is strictly barred" in res.json()["detail"]


def test_unauthorised_roles_cannot_record_review_actions():
    """Institution users, Rules Admins, and Auditors cannot record scrutiny decisions (403)."""
    forbidden_users = ["usr-inst-apex", "usr-admin-01", "usr-auditor-01"]
    for uid in forbidden_users:
        res = client.post(
            "/api/v1/findings/f-101/review-actions",
            json={
                "action_type": "CONFIRM_FINDING",
                "justification_reason": "Attempting unauthorised sign-off from non-reviewer account.",
                "application_id": "app-case-clean"
            },
            headers=get_test_auth_headers(uid)
        )
        assert res.status_code == 403
        assert "Forbidden" in res.json()["detail"]


# ---------------------------------------------------------------------------
# 3. Insecure Direct Object Reference (IDOR) & Document Access Control
# ---------------------------------------------------------------------------

def test_institution_user_cannot_access_other_institution_documents():
    """IDOR Protection: Institution User A cannot access Document of Institution B."""
    apex_headers = get_test_auth_headers("usr-inst-apex")
    # Apex user trying to access Greenfield College's document 'doc-exp-fire'
    idor_res = client.get(
        "/api/v1/documents/doc-exp-fire",
        headers=apex_headers
    )
    assert idor_res.status_code == 403
    assert "Forbidden" in idor_res.json()["detail"]
    assert "inst-greenfield-02" in idor_res.json()["detail"]

    # Content stream is also protected against IDOR
    idor_content_res = client.get(
        "/api/v1/documents/doc-exp-fire/content",
        headers=apex_headers
    )
    assert idor_content_res.status_code == 403


def test_institution_user_can_access_own_documents():
    """Institution user can access their own document metadata and protected content."""
    apex_headers = get_test_auth_headers("usr-inst-apex")
    own_res = client.get(
        "/api/v1/documents/doc-clean-affidavit",
        headers=apex_headers
    )
    assert own_res.status_code == 200
    assert own_res.json()["id"] == "doc-clean-affidavit"

    # Protected content stream
    content_res = client.get(
        "/api/v1/documents/doc-clean-affidavit/content",
        headers=apex_headers
    )
    assert content_res.status_code == 200
    assert content_res.headers["content-type"] == "application/pdf"
    assert content_res.headers["x-content-type-options"] == "nosniff"


def test_document_access_records_audit_event():
    """Every read of a protected document appends a DOCUMENT_ACCESSED audit entry."""
    officer_headers = get_test_auth_headers("usr-officer-01")
    client.get(
        "/api/v1/documents/doc-clean-affidavit",
        headers=officer_headers
    )
    events = global_audit_service.get_events(application_id="app-case-clean")
    access_events = [e for e in events if e.event_type == "DOCUMENT_ACCESSED"]
    assert len(access_events) > 0
    latest = access_events[-1]
    assert latest.details["document_id"] == "doc-clean-affidavit"
    assert latest.actor_id == "usr-officer-01"


def test_audit_events_endpoint_enforces_tenant_scoping():
    """Institution user cannot view audit trail for another institution's application."""
    apex_headers = get_test_auth_headers("usr-inst-apex")
    # Apex user requests audit events for Greenfield College
    unauth_res = client.get(
        "/api/v1/applications/app-case-expired/audit-events",
        headers=apex_headers
    )
    assert unauth_res.status_code == 403
    assert "Forbidden" in unauth_res.json()["detail"]

    # Apex user requests own audit trail
    auth_res = client.get(
        "/api/v1/applications/app-case-clean/audit-events",
        headers=apex_headers
    )
    assert auth_res.status_code == 200
    assert isinstance(auth_res.json(), list)


# ---------------------------------------------------------------------------
# 4. Cryptographic Hash-Chain Verification & Tamper Detection
# ---------------------------------------------------------------------------

def test_hash_chain_verification_and_tamper_detection_lifecycle():
    """
    Full cryptographic integrity cycle:
    1. Pristine chain verification passes.
    2. Unauthorised role cannot trigger tamper or verify.
    3. Simulated tamper alters in-memory event.
    4. Chain verification immediately flags exact corrupted sequence.
    5. Chain restore recovers pristine state.
    6. Chain verification passes again.
    """
    auditor_headers = get_test_auth_headers("usr-auditor-01")
    inst_headers = get_test_auth_headers("usr-inst-apex")

    # 1. Pristine chain passes
    init_res = client.post(
        "/api/v1/audit/verify-chain",
        headers=auditor_headers
    )
    assert init_res.status_code == 200
    assert init_res.json()["is_valid"] is True
    assert init_res.json()["corrupted_sequence"] is None

    # 2. Unauthorised role (INSTITUTION_USER) is barred
    unauth_verify = client.post(
        "/api/v1/audit/verify-chain",
        headers=inst_headers
    )
    assert unauth_verify.status_code == 403

    unauth_tamper = client.post(
        "/api/v1/audit/simulate-tamper",
        json={"sequence": 2},
        headers=inst_headers
    )
    assert unauth_tamper.status_code == 403

    # 3. Simulate tamper on sequence #2
    tamper_res = client.post(
        "/api/v1/audit/simulate-tamper",
        json={"sequence": 2},
        headers=auditor_headers
    )
    assert tamper_res.status_code == 200
    assert tamper_res.json()["tampered_sequence"] == 2

    # 4. Chain verification detects corruption at sequence #2
    tampered_verify = client.post(
        "/api/v1/audit/verify-chain",
        headers=auditor_headers
    )
    assert tampered_verify.status_code == 200
    tampered_data = tampered_verify.json()
    assert tampered_data["is_valid"] is False
    assert tampered_data["corrupted_sequence"] == 2
    assert "Hash mismatch at sequence #2" in tampered_data["detail"]

    # 5. Restore chain
    restore_res = client.post(
        "/api/v1/audit/restore-chain",
        headers=auditor_headers
    )
    assert restore_res.status_code == 200
    assert restore_res.json()["restored_events_count"] >= 1

    # 6. Verify again - must be valid
    post_restore = client.post(
        "/api/v1/audit/verify-chain",
        headers=auditor_headers
    )
    assert post_restore.status_code == 200
    assert post_restore.json()["is_valid"] is True


def test_audit_limitation_statement_disclosure():
    """Verifies statutory disclosure regarding mathematical boundaries of hash chaining."""
    res = client.get("/api/v1/audit/limitation-statement")
    assert res.status_code == 200
    body = res.json()
    assert "Statutory Cryptographic Ledger Limitation Notice" in body["title"]
    assert "privileged database superuser" in body["statement"]
    assert "WORM" in body["recommended_production_control"]


# ---------------------------------------------------------------------------
# 5. Secure Upload Validation (Magic Bytes, Size, Traversal Immunity)
# ---------------------------------------------------------------------------

def test_upload_valid_pdf_file():
    """Upload of valid PDF with %PDF- header succeeds with UUID key and sanitised filename."""
    pdf_content = b"%PDF-1.4\n1 0 obj\n<< /Title (Valid Synthetic Doc) >>\nendobj\n%%EOF"
    file_payload = ("test_affidavit.pdf", io.BytesIO(pdf_content), "application/pdf")
    officer_headers = get_test_auth_headers("usr-officer-01")

    res = client.post(
        "/api/v1/documents/upload",
        data={
            "document_type": "AFFIDAVIT_GENERAL",
            "application_id": "app-case-clean"
        },
        files={"file": file_payload},
        headers=officer_headers
    )
    assert res.status_code == 201
    data = res.json()
    assert data["original_filename"] == "test_affidavit.pdf"
    assert data["mime_type"] == "application/pdf"
    assert data["sha256_hash"] is not None
    assert "storage/protected/inst-apex-01/" in data["storage_key"]


def test_upload_sanitizes_path_traversal():
    """Client-provided path traversal sequence in filename is safely stripped."""
    pdf_content = b"%PDF-1.4\n1 0 obj\n<< /Title (Traversal Doc) >>\nendobj\n%%EOF"
    file_payload = ("../../../../windows/system32/cmd_exploit.pdf", io.BytesIO(pdf_content), "application/pdf")
    officer_headers = get_test_auth_headers("usr-officer-01")

    res = client.post(
        "/api/v1/documents/upload",
        data={
            "document_type": "AFFIDAVIT_GENERAL",
            "application_id": "app-case-clean"
        },
        files={"file": file_payload},
        headers=officer_headers
    )
    assert res.status_code == 201
    sanitized = res.json()["original_filename"]
    assert ".." not in sanitized
    assert "/" not in sanitized
    assert "\\" not in sanitized
    assert sanitized == "cmd_exploit.pdf"


def test_upload_rejects_disallowed_extension():
    """Rejects executable and script extensions (.exe, .sh, .svg, .html) even with valid headers."""
    pdf_content = b"%PDF-1.4\nfake executable pretending to be pdf"
    file_payload = ("exploit.exe", io.BytesIO(pdf_content), "application/octet-stream")
    officer_headers = get_test_auth_headers("usr-officer-01")

    res = client.post(
        "/api/v1/documents/upload",
        data={
            "document_type": "AFFIDAVIT_GENERAL",
            "application_id": "app-case-clean"
        },
        files={"file": file_payload},
        headers=officer_headers
    )
    assert res.status_code == 400
    assert "prohibited by file upload policy" in res.json()["detail"]


def test_upload_rejects_spoofed_magic_bytes():
    """Rejects text/script file named as .pdf if magic bytes do not match %PDF, JPG, or PNG."""
    malicious_text = b"echo 'malicious payload pretending to be pdf'"
    file_payload = ("innocent.pdf", io.BytesIO(malicious_text), "application/pdf")
    officer_headers = get_test_auth_headers("usr-officer-01")

    res = client.post(
        "/api/v1/documents/upload",
        data={
            "document_type": "AFFIDAVIT_GENERAL",
            "application_id": "app-case-clean"
        },
        files={"file": file_payload},
        headers=officer_headers
    )
    assert res.status_code == 400
    assert "magic bytes do not match an allowed format" in res.json()["detail"]


def test_upload_rejects_oversized_file():
    """Uploads exceeding 25MB are rejected with HTTP 413 Payload Too Large."""
    large_size = 25 * 1024 * 1024 + 1024
    oversized_bytes = b"%PDF-" + b"0" * (large_size - 5)
    file_payload = ("oversized.pdf", io.BytesIO(oversized_bytes), "application/pdf")
    officer_headers = get_test_auth_headers("usr-officer-01")

    res = client.post(
        "/api/v1/documents/upload",
        data={
            "document_type": "AFFIDAVIT_GENERAL",
            "application_id": "app-case-clean"
        },
        files={"file": file_payload},
        headers=officer_headers
    )
    assert res.status_code == 413
    assert "exceeds 25MB statutory limit" in res.json()["detail"]


def test_upload_enforces_tenant_boundary():
    """Institution User A cannot upload documents to Institution B's application."""
    pdf_content = b"%PDF-1.4\n1 0 obj\n<< >>\nendobj\n%%EOF"
    file_payload = ("uploaded_doc.pdf", io.BytesIO(pdf_content), "application/pdf")
    apex_headers = get_test_auth_headers("usr-inst-apex")

    res = client.post(
        "/api/v1/documents/upload",
        data={
            "document_type": "AFFIDAVIT_GENERAL",
            "application_id": "app-case-expired"  # Belongs to inst-greenfield-02
        },
        files={"file": file_payload},
        headers=apex_headers
    )
    assert res.status_code == 403
    assert "cannot upload documents to another institution" in res.json()["detail"]


def test_retention_policy_endpoint():
    """DPDP Act data retention policy is returned."""
    res = client.get("/api/v1/documents/retention-policy")
    assert res.status_code == 200
    assert "Digital Personal Data Protection (DPDP) Act 2023" in res.json()["framework"]


def test_adapter_toggle_requires_rules_admin_or_reviewer():
    """Administratively toggling adapters requires RULES_ADMIN or REVIEWER role."""
    adapter_id = "SIMULATED_PKI_SIGNATURE_ADAPTER"

    # Institution user is denied (403)
    unauth_res = client.post(
        f"/api/v1/verification/adapters/{adapter_id}/toggle",
        json={"enabled": False},
        headers=get_test_auth_headers("usr-inst-apex")
    )
    assert unauth_res.status_code == 403

    # Rules admin is permitted (200)
    auth_res = client.post(
        f"/api/v1/verification/adapters/{adapter_id}/toggle",
        json={"enabled": True},
        headers=get_test_auth_headers("usr-admin-01")
    )
    assert auth_res.status_code == 200
    assert auth_res.json()["is_enabled"] is True
