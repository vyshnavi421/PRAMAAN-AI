"""
Tests for Application Queue, Dossiers, Overview Metrics, and Audit Chain Verification
"""
import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.services.application_service import global_application_service
from app.services.audit_service import global_audit_service
from app.core.auth import get_test_auth_headers

client = TestClient(app)
auth_headers = get_test_auth_headers("usr-officer-01")

def test_list_applications_endpoint():
    res = client.get("/api/v1/applications", headers=auth_headers)
    assert res.status_code == 200
    apps = res.json()
    assert len(apps) >= 7
    # Verify synthetic tag present
    assert all(a.get("is_synthetic") is True for a in apps)
    
    # Test category filter
    res_eoa = client.get("/api/v1/applications?category=EXTENSION_OF_APPROVAL", headers=auth_headers)
    assert res_eoa.status_code == 200
    assert all(a["category"] == "EXTENSION_OF_APPROVAL" for a in res_eoa.json())

    # Test search filter
    res_search = client.get("/api/v1/applications?search=Apex", headers=auth_headers)
    assert res_search.status_code == 200
    assert any("Apex" in a["institution_name"] for a in res_search.json())

def test_get_application_dossier():
    res = client.get("/api/v1/applications/app-case-clean", headers=auth_headers)
    assert res.status_code == 200
    data = res.json()
    assert data["application_id"] == "app-case-clean"
    assert data["application_number"] == "APP-2026-EOA-101"
    assert len(data["documents"]) == 4

def test_get_nonexistent_application():
    res = client.get("/api/v1/applications/nonexistent-id", headers=auth_headers)
    assert res.status_code == 404

def test_get_overview_metrics():
    res = client.get("/api/v1/overview/metrics", headers=auth_headers)
    assert res.status_code == 200
    metrics = res.json()
    assert metrics["total_applications"] >= 7
    assert metrics["is_demo_mode"] is True
    assert "DEMO DATA" in metrics["demo_banner"]

def test_audit_verify_chain_and_record_action():
    # Verify chain initially intact
    res = client.post("/api/v1/audit/verify-chain", headers=auth_headers)
    assert res.status_code == 200
    result = res.json()
    assert result["is_valid"] is True
    assert result["events_evaluated"] >= 2

    # Record scrutiny action
    action_payload = {
        "action_type": "CONFIRM_DEFICIENCY",
        "justification_reason": "Fire Safety NOC expired. Issued formal 7-day cure notice.",
        "actor_id": "usr-officer-01",
        "application_id": "app-case-expired"
    }
    res_action = client.post("/api/v1/findings/find-test-01/review-actions", json=action_payload, headers=auth_headers)
    assert res_action.status_code == 201
    event = res_action.json()
    assert event["event_type"] == "REVIEW_ACTION_CONFIRM_DEFICIENCY"

    # Verify chain again after append
    res_verify = client.post("/api/v1/audit/verify-chain", headers=auth_headers)
    assert res_verify.status_code == 200
    assert res_verify.json()["is_valid"] is True
    assert res_verify.json()["events_evaluated"] > result["events_evaluated"]
