"""
Comprehensive Automated Test Suite for PRAMAAN-AI Statutory Verification Subsystem
Validates:
1. The 6 exact statutory document-verification labels:
   - verified
   - mismatch detected
   - expired
   - verification pending
   - source unavailable
   - manual review required
2. The 3 verification methods:
   - DIGITAL_SIGNATURE (PKCS#7, X.509 chain, digest integrity)
   - QR_CODE (2D symbol decoding, HMAC token check)
   - ISSUER_REGISTRY (Simulated statutory government portal lookup)
3. Honest uncertainty guardrails:
   - Timeouts & unreachable sources produce 'source unavailable' with zero applicant penalty.
   - Bounded retries (cap at 3) without infinite loops.
   - Malformed responses route to manual review.
   - Disabled adapters yield safe source unavailable status.
4. Response hashing (SHA-256) and audit ledger chaining.
5. Strict separation of verification status from rule findings and workflow status.
6. REST API routes and payloads.
"""
import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.core.auth import get_test_auth_headers

auth_headers = get_test_auth_headers("usr-officer-01")
from app.models.enums import (
    DocumentVerificationStatus,
    DocumentType,
    VerificationMethod,
    FindingStatus,
    ApplicationWorkflowStatus,
)
from app.adapters.base import VerificationAttemptRecord
from app.adapters.verification import (
    SimulatedIssuerRegistryAdapter,
    SimulatedDigitalSignatureAdapter,
    SimulatedQRCodeAdapter,
    adapter_registry,
    FIXTURE_DEFINITIONS,
)
from app.services.verification_service import VerificationService, global_verification_service
from app.services.application_service import global_application_service
from app.services.audit_service import global_audit_service


client = TestClient(app)


# ---------------------------------------------------------------------------
# Unit Tests: Adapter Implementations & Six Statutory Statuses
# ---------------------------------------------------------------------------

def test_six_statutory_statuses_in_registry_adapter():
    adapter = SimulatedIssuerRegistryAdapter()
    
    # 1. verified
    res_verified = adapter.verify("doc-01", DocumentType.FIRE_SAFETY_NOC, "FIX-VERIFIED")
    assert res_verified.status == DocumentVerificationStatus.VERIFIED
    assert res_verified.response_hash is not None
    assert "registry lookup validates the recorded clearance" in res_verified.scope_limitations.lower()

    # 2. mismatch detected
    res_mismatch = adapter.verify("doc-02", DocumentType.LAND_USE_CERTIFICATE, "FIX-MISMATCH")
    assert res_mismatch.status == DocumentVerificationStatus.MISMATCH_DETECTED
    assert res_mismatch.response_payload["claims_match"] is False

    # 3. expired
    res_expired = adapter.verify("doc-03", DocumentType.FIRE_SAFETY_NOC, "FIX-EXPIRED")
    assert res_expired.status == DocumentVerificationStatus.EXPIRED
    assert "valid_until" in res_expired.response_payload

    # 4. verification pending
    res_pending = adapter.verify("doc-04", DocumentType.BUILDING_PLAN_ARCHITECT, "FIX-PENDING")
    assert res_pending.status == DocumentVerificationStatus.VERIFICATION_PENDING
    assert res_pending.response_payload["status"] == "PROCESSING"

    # 5. source unavailable
    res_unavail = adapter.verify("doc-05", DocumentType.FIRE_SAFETY_NOC, "FIX-SOURCE-UNAVAIL")
    assert res_unavail.status == DocumentVerificationStatus.SOURCE_UNAVAILABLE
    assert res_unavail.response_payload["status_code"] == 504

    # 6. manual review required
    res_manual = adapter.verify("doc-06", DocumentType.LAND_USE_CERTIFICATE, "FIX-MANUAL-REVIEW")
    assert res_manual.status == DocumentVerificationStatus.MANUAL_REVIEW_REQUIRED


def test_digital_signature_adapter_scope_and_states():
    adapter = SimulatedDigitalSignatureAdapter()
    assert adapter.supported_methods == [VerificationMethod.DIGITAL_SIGNATURE]

    # Valid signature
    res_valid = adapter.verify("doc-sig-1", DocumentType.AFFIDAVIT_GENERAL, "SIG-VALID")
    assert res_valid.status == DocumentVerificationStatus.VERIFIED
    assert res_valid.response_payload["signature_valid"] is True
    assert "does not establish that every factual claim made inside the document is true" in res_valid.scope_limitations.lower()

    # Tampered / byte mismatch
    res_tamper = adapter.verify("doc-sig-2", DocumentType.AFFIDAVIT_GENERAL, "SIG-MISMATCH-TAMPER")
    assert res_tamper.status == DocumentVerificationStatus.MISMATCH_DETECTED
    assert res_tamper.response_payload["error"] == "DOCUMENT_DIGEST_MISMATCH"

    # Expired signing certificate
    res_expired = adapter.verify("doc-sig-3", DocumentType.AFFIDAVIT_GENERAL, "SIG-EXPIRED")
    assert res_expired.status == DocumentVerificationStatus.EXPIRED

    # OCSP timeout -> source unavailable
    res_ocsp = adapter.verify("doc-sig-4", DocumentType.AFFIDAVIT_GENERAL, "SIG-TIMEOUT")
    assert res_ocsp.status == DocumentVerificationStatus.SOURCE_UNAVAILABLE
    assert res_ocsp.response_payload["error"] == "OCSP_RESPONDER_TIMEOUT"

    # Untrusted root CA -> manual review required
    res_untrusted = adapter.verify("doc-sig-5", DocumentType.AFFIDAVIT_GENERAL, "SIG-MANUAL-UNTRUSTED")
    assert res_untrusted.status == DocumentVerificationStatus.MANUAL_REVIEW_REQUIRED


def test_qr_code_adapter_scope_and_states():
    adapter = SimulatedQRCodeAdapter()
    assert adapter.supported_methods == [VerificationMethod.QR_CODE]

    # Valid decoded QR
    res_valid = adapter.verify("doc-qr-1", DocumentType.AICTE_PREVIOUS_EOA, "QR-VALID")
    assert res_valid.status == DocumentVerificationStatus.VERIFIED
    assert res_valid.response_payload["qr_decoded"] is True
    assert "does not prove institutional authenticity unless backed by a cryptographically signed payload" in res_valid.scope_limitations.lower()

    # Mismatch between QR payload and declared text
    res_mismatch = adapter.verify("doc-qr-2", DocumentType.AICTE_PREVIOUS_EOA, "QR-MISMATCH")
    assert res_mismatch.status == DocumentVerificationStatus.MISMATCH_DETECTED

    # Expired token in QR
    res_expired = adapter.verify("doc-qr-3", DocumentType.AICTE_PREVIOUS_EOA, "QR-EXPIRED")
    assert res_expired.status == DocumentVerificationStatus.EXPIRED

    # Corrupt / damaged matrix -> manual review
    res_unreadable = adapter.verify("doc-qr-4", DocumentType.AICTE_PREVIOUS_EOA, "QR-MANUAL-DAMAGE")
    assert res_unreadable.status == DocumentVerificationStatus.MANUAL_REVIEW_REQUIRED


def test_malformed_response_handling():
    adapter = SimulatedIssuerRegistryAdapter()
    # Malformed response fixture
    res = adapter.verify("doc-err-1", DocumentType.FIRE_SAFETY_NOC, "ERR-MALFORMED")
    assert res.status == DocumentVerificationStatus.MANUAL_REVIEW_REQUIRED
    assert res.response_payload["error"] == "CORRUPT_PAYLOAD_STRUCTURE"


# ---------------------------------------------------------------------------
# Service-Level Tests: Bounded Retries, Tasks, Hash Computation & Audit
# ---------------------------------------------------------------------------

def test_service_bounded_retries_on_timeout():
    service = VerificationService()
    
    # Requesting 10 retries should be bounded to MAX_PERMITTED_RETRIES (3)
    attempt = service.verify_document(
        document_id="doc-clean-fire",
        adapter_id="SIMULATED_ISSUER_REGISTRY_ADAPTER",
        reference_id="ERR-TIMEOUT",
        max_retries=10,
        simulate_retry=True
    )
    
    # Must remain SOURCE_UNAVAILABLE and cap retries at 3
    assert attempt.status == DocumentVerificationStatus.SOURCE_UNAVAILABLE
    assert attempt.retry_count == 2 # 0-indexed count reaching attempt 3
    assert attempt.retry_outcome == "RETRY_CAP_REACHED"
    assert "ZERO penalty levied against applicant" in attempt.manual_review_task
    assert attempt.response_hash is not None


def test_service_disabled_adapter_honest_uncertainty():
    service = VerificationService()
    adapter = adapter_registry.get("SIMULATED_ISSUER_REGISTRY_ADAPTER")
    assert adapter is not None
    
    try:
        # Disable adapter
        adapter.set_enabled(False)
        
        attempt = service.verify_document(
            document_id="doc-clean-fire",
            adapter_id="SIMULATED_ISSUER_REGISTRY_ADAPTER",
            reference_id="FIX-VERIFIED"
        )
        
        assert attempt.status == DocumentVerificationStatus.SOURCE_UNAVAILABLE
        assert attempt.retry_outcome == "ADAPTER_UNAVAILABLE"
        assert "Manual authority verification required" in attempt.manual_review_task
    finally:
        adapter.set_enabled(True)


def test_service_manual_review_task_generation():
    service = VerificationService()

    # Mismatch detected generates mismatch task
    att_mismatch = service.verify_document(
        document_id="doc-clean-fire",
        reference_id="FIX-MISMATCH"
    )
    assert att_mismatch.status == DocumentVerificationStatus.MISMATCH_DETECTED
    assert "statutory clarification notice" in att_mismatch.manual_review_task

    # Verified state has no pending manual review task
    att_verified = service.verify_document(
        document_id="doc-clean-fire",
        reference_id="FIX-VERIFIED"
    )
    assert att_verified.status == DocumentVerificationStatus.VERIFIED
    assert att_verified.manual_review_task is None


def test_response_hash_computation_tamper_detection():
    service = VerificationService()
    attempt = service.verify_document(
        document_id="doc-clean-fire",
        reference_id="FIX-VERIFIED"
    )
    original_hash = attempt.response_hash
    assert original_hash is not None

    # Recomputing on identical payload gives exact same hash
    recomputed = attempt.compute_response_hash()
    assert recomputed == original_hash

    # Tampering with payload changes the hash
    attempt.response_payload["status_code"] = 404
    tampered_hash = attempt.compute_response_hash()
    assert tampered_hash != original_hash


def test_audit_ledger_event_dispatch():
    initial_event_count = len(global_audit_service._events)
    
    global_verification_service.verify_document(
        document_id="doc-clean-fire",
        reference_id="FIX-EXPIRED",
        actor_id="usr-test-auditor"
    )
    
    new_event_count = len(global_audit_service._events)
    assert new_event_count == initial_event_count + 1
    
    latest_event = global_audit_service._events[-1]
    assert latest_event.event_type == "DOCUMENT_VERIFICATION_ATTEMPTED"
    assert latest_event.actor_id == "usr-test-auditor"
    assert latest_event.details["statutory_status"] == "expired"
    
    # Audit hash chain must verify valid
    chain_check = global_audit_service.verify_chain()
    assert chain_check.is_valid is True


def test_strict_status_taxonomy_separation():
    # Verify that DocumentVerificationStatus is separate from FindingStatus and ApplicationWorkflowStatus
    assert DocumentVerificationStatus.EXPIRED.value == "expired"
    assert FindingStatus.DEFICIENCY.value == "DEFICIENCY"
    assert ApplicationWorkflowStatus.UNDER_SCRUTINY.value == "UNDER_SCRUTINY"

    # DocumentVerificationStatus values must never equal FindingStatus values
    for d_status in DocumentVerificationStatus:
        for f_status in FindingStatus:
            assert d_status.value != f_status.value


# ---------------------------------------------------------------------------
# API Route Integration Tests
# ---------------------------------------------------------------------------

def test_api_list_adapters():
    res = client.get("/api/v1/verification/adapters", headers=auth_headers)
    assert res.status_code == 200
    data = res.json()
    assert data["is_demo_mode"] is True
    assert len(data["adapters"]) >= 3
    adapter_ids = [a["adapter_id"] for a in data["adapters"]]
    assert "SIMULATED_ISSUER_REGISTRY_ADAPTER" in adapter_ids
    assert "SIMULATED_PKI_SIGNATURE_ADAPTER" in adapter_ids
    assert "SIMULATED_2D_QR_ADAPTER" in adapter_ids


def test_api_get_fixtures():
    res = client.get("/api/v1/verification/fixtures", headers=auth_headers)
    assert res.status_code == 200
    fixtures = res.json()
    assert "FIX-VERIFIED" in fixtures
    assert "FIX-MISMATCH" in fixtures
    assert "FIX-EXPIRED" in fixtures
    assert "FIX-PENDING" in fixtures
    assert "FIX-SOURCE-UNAVAIL" in fixtures
    assert "FIX-MANUAL-REVIEW" in fixtures
    assert "ERR-TIMEOUT" in fixtures
    assert "ERR-MALFORMED" in fixtures
    assert fixtures["FIX-EXPIRED"]["expected_status"] == "expired"


def test_api_verify_document_post_and_get():
    # Execute verification via POST
    payload = {
        "adapter_id": "SIMULATED_ISSUER_REGISTRY_ADAPTER",
        "method": "ISSUER_REGISTRY",
        "reference_id": "FIX-VERIFIED",
        "max_retries": 3,
        "actor_id": "usr-api-officer"
    }
    post_res = client.post("/api/v1/documents/doc-clean-fire/verify", json=payload, headers=auth_headers)
    assert post_res.status_code == 200
    res_json = post_res.json()
    attempt_id = res_json["id"]
    assert res_json["status"] == "verified"
    assert res_json["response_hash"] is not None

    # Fetch attempts history for document
    history_res = client.get("/api/v1/documents/doc-clean-fire/verification-attempts", headers=auth_headers)
    assert history_res.status_code == 200
    attempts = history_res.json()
    assert any(a["id"] == attempt_id for a in attempts)

    # Fetch single attempt by ID
    single_res = client.get(f"/api/v1/verification/attempts/{attempt_id}", headers=auth_headers)
    assert single_res.status_code == 200
    assert single_res.json()["id"] == attempt_id


def test_api_adapter_toggle():
    adapter_id = "SIMULATED_PKI_SIGNATURE_ADAPTER"
    
    # Toggle off
    toggle_off = client.post(
        f"/api/v1/verification/adapters/{adapter_id}/toggle",
        json={"enabled": False},
        headers=auth_headers
    )
    assert toggle_off.status_code == 200
    assert toggle_off.json()["is_enabled"] is False

    # Verify document with disabled adapter produces source unavailable
    verify_res = client.post(
        "/api/v1/documents/doc-clean-fire/verify",
        json={
            "adapter_id": adapter_id,
            "method": "DIGITAL_SIGNATURE",
            "reference_id": "SIG-VALID"
        },
        headers=auth_headers
    )
    assert verify_res.status_code == 200
    assert verify_res.json()["status"] == "source unavailable"

    # Toggle back on
    toggle_on = client.post(
        f"/api/v1/verification/adapters/{adapter_id}/toggle",
        json={"enabled": True},
        headers=auth_headers
    )
    assert toggle_on.status_code == 200
    assert toggle_on.json()["is_enabled"] is True
