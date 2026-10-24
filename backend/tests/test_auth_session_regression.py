"""
Regression tests for Issue 4: Server-Validated Demo Sessions & RBAC Hardening
Verifies:
1. Rejection of unauthenticated requests (no silent default to Scrutiny Officer).
2. Rejection of spoofed headers without a server-validated session token.
3. Creation and validation of server-managed demo sessions.
4. Role enforcement across all protected endpoints with session tokens.
5. Session termination (logout).
"""
import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.core.auth import global_session_store, UserRole

client = TestClient(app)


def test_unauthenticated_request_rejected_with_401():
    """Unauthenticated access to protected routes must return 401, not default to REVIEWER."""
    # Applications
    res_apps = client.get("/api/v1/applications")
    assert res_apps.status_code == 401, f"Expected 401, got {res_apps.status_code}: {res_apps.text}"

    # Documents upload
    res_upload = client.post("/api/v1/documents/upload")
    assert res_upload.status_code == 401, f"Expected 401, got {res_upload.status_code}: {res_upload.text}"

    # Findings review
    res_review = client.post(
        "/api/v1/findings/f-101/review-actions",
        json={"action_type": "CONFIRM_FINDING", "justification_reason": "Testing", "application_id": "app-case-clean"}
    )
    assert res_review.status_code == 401, f"Expected 401, got {res_review.status_code}: {res_review.text}"

    # Full review orchestrator
    res_orch = client.post(
        "/api/v1/applications/app-case-clean/full-review",
        json={"application_data": {}, "rule_pack_id": "rp-aicte-aph-2024-eoa", "rule_pack_version": "1.0.0"}
    )
    assert res_orch.status_code == 401, f"Expected 401, got {res_orch.status_code}: {res_orch.text}"


def test_spoofed_headers_without_session_are_rejected_with_401():
    """Sending X-User-Role or X-User-Id without a valid session token must be rejected."""
    res = client.get(
        "/api/v1/applications",
        headers={"X-User-Role": "REVIEWER", "X-User-Id": "usr-officer-01"}
    )
    assert res.status_code == 401, f"Expected 401 for spoofed headers, got {res.status_code}"


def test_create_and_validate_demo_session():
    """Session creation endpoint yields a server-validated token that authenticates requests."""
    # 1. Login as Scrutiny Officer
    login_res = client.post("/api/v1/auth/session", json={"user_id": "usr-officer-01"})
    assert login_res.status_code == 200
    login_data = login_res.json()
    token = login_data["session_token"]
    assert token.startswith("demo_sess_") or len(token) > 20
    assert login_data["user"]["role"] == "REVIEWER"

    # 2. Check /api/v1/auth/me with Bearer token
    me_res = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert me_res.status_code == 200
    assert me_res.json()["user_id"] == "usr-officer-01"

    # 3. Access protected applications list with Bearer token
    apps_res = client.get("/api/v1/applications", headers={"Authorization": f"Bearer {token}"})
    assert apps_res.status_code == 200
    assert len(apps_res.json()) > 0


def test_role_enforcement_with_session_token():
    """Institution user cannot trigger reviewer actions, even with a valid session."""
    # Login as Institution User
    login_res = client.post("/api/v1/auth/session", json={"user_id": "usr-inst-apex"})
    assert login_res.status_code == 200
    token = login_res.json()["session_token"]

    # Try reviewer endpoint -> 403 Forbidden
    res = client.post(
        "/api/v1/findings/f-101/review-actions",
        json={"action_type": "CONFIRM_FINDING", "justification_reason": "Institution attempting officer action", "application_id": "app-case-clean"},
        headers={"Authorization": f"Bearer {token}"}
    )
    assert res.status_code == 403, f"Expected 403 Forbidden, got {res.status_code}"


def test_logout_invalidates_session():
    """Terminating session with DELETE /api/v1/auth/session invalidates subsequent calls."""
    login_res = client.post("/api/v1/auth/session", json={"user_id": "usr-auditor-01"})
    token = login_res.json()["session_token"]

    # Authenticated call succeeds
    me_res = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert me_res.status_code == 200

    # Logout
    logout_res = client.delete("/api/v1/auth/session", headers={"Authorization": f"Bearer {token}"})
    assert logout_res.status_code == 200

    # Subsequent call fails with 401
    me_after = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert me_after.status_code == 401
