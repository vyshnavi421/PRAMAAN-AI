"""
Privilege Escalation Regression Tests — SIH26261 / PRAMAAN-AI
==============================================================
These tests FIRST reproduce the known vulnerability (they will FAIL on the current
insecure code), then verify the fixed behaviour after the patch is applied.

Attack vectors reproduced:
  A. Arbitrary user_id not in SYNTHETIC_USERS can obtain a session.
  B. Client can supply role=RULES_ADMIN in the request body and receive that role.
  C. A forged / random token is accepted by protected endpoints.
  D. Unauthenticated requests reach protected routes.
  E. A normal user can access a RULES_ADMIN-only endpoint after fix.
  F. An institution user can access another institution's records.
  G. Valid configured accounts receive only their server-assigned role.
"""
import pytest
import hashlib
from fastapi.testclient import TestClient

from app.main import app
from app.core.auth import get_test_auth_headers, UserRole

client = TestClient(app, raise_server_exceptions=False)


# ---------------------------------------------------------------------------
# A. Arbitrary user_id — must be REJECTED after fix
# ---------------------------------------------------------------------------
class TestArbitraryUserIdRejected:
    def test_unknown_user_id_returns_401(self):
        """An unknown user_id not in SYNTHETIC_USERS must not create a session."""
        resp = client.post(
            "/api/v1/auth/session",
            json={"user_id": "attacker-99999"}
        )
        assert resp.status_code == 401, (
            f"VULNERABILITY: unknown user_id created a session → {resp.status_code} {resp.text}"
        )

    def test_empty_user_id_returns_401(self):
        resp = client.post("/api/v1/auth/session", json={"user_id": ""})
        assert resp.status_code == 401, (
            f"Empty user_id must be rejected → {resp.status_code} {resp.text}"
        )

    def test_sql_injection_attempt_returns_401(self):
        resp = client.post(
            "/api/v1/auth/session",
            json={"user_id": "' OR '1'='1"}
        )
        assert resp.status_code == 401, (
            f"SQL injection-style user_id must be rejected → {resp.status_code} {resp.text}"
        )


# ---------------------------------------------------------------------------
# B. Client-supplied role escalation — must be REJECTED after fix
# ---------------------------------------------------------------------------
class TestClientRoleEscalationRejected:
    def test_client_cannot_request_rules_admin_role(self):
        """Supplying role=RULES_ADMIN in request must be ignored/rejected."""
        resp = client.post(
            "/api/v1/auth/session",
            json={"user_id": "usr-inst-apex", "role": "RULES_ADMIN"}
        )
        # Either rejected (401/422) OR the returned role must NOT be RULES_ADMIN
        if resp.status_code == 200:
            data = resp.json()
            assigned_role = data.get("user", {}).get("role")
            assert assigned_role != "RULES_ADMIN", (
                f"VULNERABILITY: client supplied role=RULES_ADMIN and received it → {data}"
            )

    def test_client_cannot_request_reviewer_role_for_institution_user(self):
        """Institution user cannot elevate to REVIEWER by supplying role in body."""
        resp = client.post(
            "/api/v1/auth/session",
            json={"user_id": "usr-inst-apex", "role": "REVIEWER"}
        )
        if resp.status_code == 200:
            data = resp.json()
            assigned_role = data.get("user", {}).get("role")
            assert assigned_role == "INSTITUTION_USER", (
                f"VULNERABILITY: usr-inst-apex was elevated to {assigned_role} via role field"
            )

    def test_client_cannot_elevate_unknown_user_to_auditor(self):
        """An attacker cannot create a privileged AUDITOR account for an arbitrary identity."""
        resp = client.post(
            "/api/v1/auth/session",
            json={"user_id": "custom-auditor", "role": "AUDITOR"}
        )
        assert resp.status_code == 401, (
            f"VULNERABILITY: unknown user with role=AUDITOR was accepted → {resp.status_code} {resp.text}"
        )

    def test_institution_id_override_rejected(self):
        """Client must not be able to re-assign institution_id to access a different institution."""
        resp = client.post(
            "/api/v1/auth/session",
            json={"user_id": "usr-inst-apex", "institution_id": "inst-city-02"}
        )
        if resp.status_code == 200:
            data = resp.json()
            assigned_inst = data.get("user", {}).get("institution_id")
            assert assigned_inst != "inst-city-02", (
                f"VULNERABILITY: client overrode institution_id to inst-city-02 → {data}"
            )


# ---------------------------------------------------------------------------
# C. Forged / random token rejected
# ---------------------------------------------------------------------------
class TestForgedTokenRejected:
    def test_random_token_returns_401(self):
        resp = client.get(
            "/api/v1/auth/me",
            headers={"Authorization": "Bearer totally_forged_token_xyz"}
        )
        assert resp.status_code == 401, (
            f"Forged token must return 401 → {resp.status_code}"
        )

    def test_empty_bearer_returns_401(self):
        resp = client.get(
            "/api/v1/auth/me",
            headers={"Authorization": "Bearer "}
        )
        assert resp.status_code == 401, (
            f"Empty Bearer must return 401 → {resp.status_code}"
        )

    def test_malformed_auth_header_returns_401(self):
        resp = client.get(
            "/api/v1/auth/me",
            headers={"Authorization": "NotBearer sometoken"}
        )
        assert resp.status_code == 401, (
            f"Malformed auth header must return 401 → {resp.status_code}"
        )


# ---------------------------------------------------------------------------
# D. Unauthenticated requests reach protected routes
# ---------------------------------------------------------------------------
class TestUnauthenticatedRejected:
    def test_applications_list_requires_auth(self):
        resp = client.get("/api/v1/applications")
        assert resp.status_code == 401, (
            f"Applications list must require auth → {resp.status_code}"
        )

    def test_orchestrator_requires_auth(self):
        resp = client.get(
            "/api/v1/applications/app-test/full-review/latest"
        )
        assert resp.status_code in (401, 404), (
            f"Orchestrator must require auth → {resp.status_code}"
        )

    def test_documents_requires_auth(self):
        resp = client.get("/api/v1/documents/doc-test/content")
        assert resp.status_code in (401, 404), (
            f"Document content must require auth → {resp.status_code}"
        )

    def test_audit_chain_requires_auth(self):
        resp = client.post("/api/v1/audit/verify-chain", json={})
        assert resp.status_code == 401, (
            f"Audit verify-chain must require auth → {resp.status_code}"
        )

    def test_duplicates_scan_requires_auth(self):
        resp = client.get("/api/v1/duplicates/scan/app-test")
        assert resp.status_code == 401, (
            f"Duplicates scan must require auth → {resp.status_code}"
        )

    def test_verification_adapters_requires_auth(self):
        resp = client.get("/api/v1/verification/adapters")
        assert resp.status_code == 401, (
            f"Verification adapters must require auth → {resp.status_code}"
        )


# ---------------------------------------------------------------------------
# E. Role boundary — normal user cannot access admin endpoint
# ---------------------------------------------------------------------------
class TestRoleBoundaries:
    def test_institution_user_cannot_trigger_full_review(self):
        """Institution users cannot run scrutiny reviews (reviewer-only action)."""
        headers = get_test_auth_headers("usr-inst-apex")
        resp = client.post(
            "/api/v1/applications/fake-app-id/full-review",
            headers=headers,
            json={}
        )
        assert resp.status_code in (403, 404, 422), (
            f"Institution user must receive 403/404 on full-review → {resp.status_code}"
        )

    def test_auditor_cannot_post_review_action(self):
        """Auditors have read-only access and cannot record review actions."""
        headers = get_test_auth_headers("usr-auditor-01")
        resp = client.post(
            "/api/v1/findings/fake-finding-id/review-actions",
            headers=headers,
            json={"action": "CONFIRM", "reason": "test"}
        )
        assert resp.status_code in (403, 404, 422), (
            f"Auditor must receive 403/404 on review-actions → {resp.status_code}"
        )

    def test_reviewer_can_access_applications(self):
        """Reviewer should successfully access the applications list."""
        headers = get_test_auth_headers("usr-officer-01")
        resp = client.get("/api/v1/applications", headers=headers)
        assert resp.status_code == 200, (
            f"Reviewer should have access to applications → {resp.status_code}"
        )


# ---------------------------------------------------------------------------
# F. Tenant isolation — institution user cannot access other institution
# ---------------------------------------------------------------------------
class TestTenantIsolation:
    def test_inst_apex_cannot_access_city_documents(self):
        """usr-inst-apex must not access inst-city-02 records."""
        headers_apex = get_test_auth_headers("usr-inst-apex")
        headers_city = get_test_auth_headers("usr-inst-city")

        # Create an application as city
        city_app_resp = client.post(
            "/api/v1/applications/",
            headers=headers_city,
            json={
                "institution_name": "City College of Engineering",
                "application_ref": "CITY-ISOLATION-TEST-001",
                "institution_id": "inst-city-02"
            }
        )
        if city_app_resp.status_code != 201:
            pytest.skip("Could not create city application for isolation test")

        city_app_id = city_app_resp.json()["application_id"]

        # apex user should be denied access
        resp = client.get(
            f"/api/v1/applications/{city_app_id}",
            headers=headers_apex
        )
        assert resp.status_code == 403, (
            f"Tenant isolation failure: usr-inst-apex accessed inst-city application → {resp.status_code}"
        )


# ---------------------------------------------------------------------------
# G. Valid configured accounts get correct server-assigned role
# ---------------------------------------------------------------------------
class TestServerAssignedRoles:
    def test_reviewer_gets_reviewer_role(self):
        resp = client.post(
            "/api/v1/auth/session",
            json={"user_id": "usr-officer-01"}
        )
        assert resp.status_code == 200, f"Reviewer login failed → {resp.text}"
        data = resp.json()
        assert data["user"]["role"] == "REVIEWER"
        assert data["user"]["user_id"] == "usr-officer-01"

    def test_rules_admin_gets_rules_admin_role(self):
        resp = client.post(
            "/api/v1/auth/session",
            json={"user_id": "usr-admin-01"}
        )
        assert resp.status_code == 200, f"Admin login failed → {resp.text}"
        assert resp.json()["user"]["role"] == "RULES_ADMIN"

    def test_institution_user_gets_correct_institution(self):
        resp = client.post(
            "/api/v1/auth/session",
            json={"user_id": "usr-inst-apex"}
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["user"]["role"] == "INSTITUTION_USER"
        assert data["user"]["institution_id"] == "inst-apex-01"

    def test_session_token_works_for_me_endpoint(self):
        login_resp = client.post(
            "/api/v1/auth/session",
            json={"user_id": "usr-officer-01"}
        )
        assert login_resp.status_code == 200
        token = login_resp.json()["session_token"]
        me_resp = client.get(
            "/api/v1/auth/me",
            headers={"Authorization": f"Bearer {token}"}
        )
        assert me_resp.status_code == 200
        assert me_resp.json()["user_id"] == "usr-officer-01"

    def test_auditor_gets_auditor_role(self):
        resp = client.post(
            "/api/v1/auth/session",
            json={"user_id": "usr-auditor-01"}
        )
        assert resp.status_code == 200
        assert resp.json()["user"]["role"] == "AUDITOR"
