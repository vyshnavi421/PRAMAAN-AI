"""
Comprehensive Test Suite for PRAMAAN-AI Full-Application Review Orchestrator & Coverage Auditor
Covers:
- Clean application pre-scrutiny (100% complete)
- Missing document pre-scrutiny
- Expired document pre-scrutiny
- Cross-document mismatch
- Poor scan / extraction uncertainty
- Unavailable issuer (503 / timeout guardrail)
- Non-applicable category check
- Engine exception handling
- Deliberately omitted check detection (Coverage Auditor guarantee)
- Concurrent execution lock / duplicate run rejection
- Reopening saved reports without rerunning
- REST API contracts
"""
import pytest
from datetime import date
from fastapi.testclient import TestClient

from app.models.enums import (
    FindingStatus,
    Severity,
    ApplicationCategory,
    DocumentType,
    ExtractionQuality,
    DocumentVerificationStatus,
)
from app.models.domain import (
    ApplicationInput,
    Document,
    ExtractedField,
    FieldProvenance,
    InstitutionalReferenceRecord,
)
from app.services.review_orchestrator import (
    ReviewOrchestrator,
    CoverageAuditor,
    ReviewRunRepository,
)
from app.services.duplicate_detector import DuplicateDetector, DuplicateIndex
from app.main import app
from app.core.auth import get_test_auth_headers

client = TestClient(app)
auth_headers = get_test_auth_headers("usr-officer-01")

# Helper fixtures
def make_field(key: str, value: str, confidence: float = 0.98, quality: ExtractionQuality = ExtractionQuality.HIGH) -> ExtractedField:
    return ExtractedField(
        field_key=key,
        field_value=value,
        raw_value=value,
        confidence=confidence,
        provenance=FieldProvenance(page_number=1, bounding_box=[0.1, 0.2, 0.3, 0.4], quality_label=quality)
    )

def make_doc(doc_type: DocumentType, fields=None, verification_status=DocumentVerificationStatus.VERIFICATION_PENDING, sha256: str = None, app_id: str = "app-orch-1") -> Document:
    computed_hash = sha256 or f"hash-{app_id}-{doc_type.value.lower()}"
    return Document(
        id=f"doc-{app_id}-{doc_type.value.lower()}",
        application_id=app_id,
        document_type=doc_type,
        original_filename=f"{doc_type.value.lower()}.pdf",
        storage_key=f"storage/{doc_type.value.lower()}.bin",
        sha256_hash=computed_hash,
        verification_status=verification_status,
        extracted_fields=fields or []
    )

def make_full_application(docs=None, ref_record=None, declared=None, category=ApplicationCategory.EXTENSION_OF_APPROVAL, app_id="app-orch-1") -> ApplicationInput:
    return ApplicationInput(
        application_id=app_id,
        institution_id=f"inst-{app_id}",
        application_number=f"APP-2026-EOA-{app_id[-4:]}",
        submission_date=date(2026, 5, 1),
        submission_cutoff_date=date(2026, 6, 30),
        category=category,
        declared_data=declared or {"total_intake": 180},
        documents=docs or [],
        reference_record=ref_record
    )

def make_clean_docs(app_id="app-orch-1"):
    return [
        make_doc(DocumentType.AFFIDAVIT_GENERAL, fields=[make_field("institution_name", "Apex Institute of Technology")], app_id=app_id),
        make_doc(DocumentType.FIRE_SAFETY_NOC, fields=[
            make_field("noc_issue_date", "2026-01-15"),
            make_field("noc_expiry_date", "2027-01-14"),
        ], app_id=app_id),
        make_doc(DocumentType.BUILDING_PLAN_ARCHITECT, fields=[make_field("certified_intake_capacity", "180")], app_id=app_id),
        make_doc(DocumentType.GOVERNING_BODY_RESOLUTION, fields=[make_field("proposed_intake", "180")], app_id=app_id),
    ]

def make_clean_ref():
    return InstitutionalReferenceRecord(
        institution_id="inst-test-1",
        aicte_permanent_id="1-3324589110",
        legal_name="Apex Institute of Technology",
        academic_year="2025-2026",
        approved_intake=180,
        approved_builtup_area_sqm=12000.0
    )


# ==============================================================================
# 1. Clean Application Pre-Scrutiny Workflow
# ==============================================================================
def test_clean_application_full_review():
    repo = ReviewRunRepository()
    orch = ReviewOrchestrator(repository=repo)
    app_input = make_full_application(docs=make_clean_docs(), ref_record=make_clean_ref())

    report = orch.run_complete_prescrutiny(app_input)

    # Coverage Guarantee
    assert report.coverage_audit.is_complete is True
    assert report.coverage_audit.audit_verdict == "COMPLETE"
    assert len(report.coverage_audit.missing_checks) == 0
    assert report.coverage_audit.coverage_percentage == 100.0
    assert report.review_status == "COMPLETE_COMPLIANT"

    # Outcome Categorization
    assert len(report.findings) == 0 # 0 Deficiencies or Anomalies
    assert len(report.successful_checks) >= 6
    assert len(report.not_applicable_checks) >= 1 # CategorySpecificRule not applicable for EoA
    assert len(report.source_verifications) >= 2 # Fire NOC + Architect Building Plan


# ==============================================================================
# 2. Missing Mandatory Document Pre-Scrutiny
# ==============================================================================
def test_missing_document_full_review():
    repo = ReviewRunRepository()
    orch = ReviewOrchestrator(repository=repo)
    # Only upload affidavit, missing Fire NOC and Building Plan
    docs = [make_doc(DocumentType.AFFIDAVIT_GENERAL, fields=[make_field("institution_name", "Apex Institute of Technology")])]
    app_input = make_full_application(docs=docs, ref_record=make_clean_ref())

    report = orch.run_complete_prescrutiny(app_input)

    # Coverage is complete because missing document check ran to terminal DEFICIENCY outcome
    assert report.coverage_audit.is_complete is True
    assert report.review_status == "COMPLETE_WITH_DEFICIENCIES"
    assert any(f.rule_id == "RULE-APH-DOC-001" and f.status == FindingStatus.DEFICIENCY for f in report.findings)
    assert len(report.unresolved_tasks) > 0


# ==============================================================================
# 3. Expired Document Pre-Scrutiny & Source Verification
# ==============================================================================
def test_expired_document_full_review():
    repo = ReviewRunRepository()
    orch = ReviewOrchestrator(repository=repo)
    docs = [
        make_doc(DocumentType.AFFIDAVIT_GENERAL, fields=[make_field("institution_name", "Apex Institute of Technology")]),
        make_doc(DocumentType.FIRE_SAFETY_NOC, fields=[
            make_field("noc_issue_date", "2023-01-15"),
            make_field("noc_expiry_date", "2024-01-14"), # Expired prior to 2026-06-30 cutoff
        ]),
        make_doc(DocumentType.BUILDING_PLAN_ARCHITECT, fields=[make_field("certified_intake_capacity", "180")]),
        make_doc(DocumentType.GOVERNING_BODY_RESOLUTION, fields=[make_field("proposed_intake", "180")]),
    ]
    app_input = make_full_application(docs=docs, ref_record=make_clean_ref())

    report = orch.run_complete_prescrutiny(app_input)

    assert report.coverage_audit.is_complete is True
    assert report.review_status == "COMPLETE_WITH_DEFICIENCIES"
    expired_findings = [f for f in report.findings if f.rule_id == "RULE-APH-EXP-003"]
    assert len(expired_findings) == 1
    assert expired_findings[0].status == FindingStatus.DEFICIENCY


# ==============================================================================
# 4. Cross-Document Mismatch
# ==============================================================================
def test_cross_document_mismatch_full_review():
    repo = ReviewRunRepository()
    orch = ReviewOrchestrator(repository=repo)
    docs = [
        make_doc(DocumentType.AFFIDAVIT_GENERAL, fields=[make_field("institution_name", "Apex Institute of Technology")]),
        make_doc(DocumentType.FIRE_SAFETY_NOC, fields=[
            make_field("noc_issue_date", "2026-01-15"),
            make_field("noc_expiry_date", "2027-01-14"),
        ]),
        make_doc(DocumentType.BUILDING_PLAN_ARCHITECT, fields=[make_field("certified_intake_capacity", "180")]),
        make_doc(DocumentType.GOVERNING_BODY_RESOLUTION, fields=[make_field("proposed_intake", "240")]), # Mismatch 180 vs 240
    ]
    app_input = make_full_application(docs=docs, ref_record=make_clean_ref())

    report = orch.run_complete_prescrutiny(app_input)

    assert report.coverage_audit.is_complete is True
    assert report.review_status == "COMPLETE_WITH_DEFICIENCIES"
    mismatch_findings = [f for f in report.findings if f.rule_id == "RULE-CROSS-DOC-005"]
    assert len(mismatch_findings) == 1
    assert mismatch_findings[0].status == FindingStatus.DEFICIENCY


# ==============================================================================
# 5. Poor Scan / Low Extraction Quality (Abstains Gracefully)
# ==============================================================================
def test_poor_scan_uncertain_extraction_full_review():
    repo = ReviewRunRepository()
    orch = ReviewOrchestrator(repository=repo)
    docs = [
        make_doc(DocumentType.AFFIDAVIT_GENERAL, fields=[make_field("institution_name", "Apex Institute of Technology")]),
        make_doc(DocumentType.FIRE_SAFETY_NOC, fields=[
            make_field("noc_expiry_date", "2027-01-14", confidence=0.45, quality=ExtractionQuality.LOW_CONFIDENCE),
        ]),
        make_doc(DocumentType.BUILDING_PLAN_ARCHITECT, fields=[make_field("certified_intake_capacity", "180")]),
        make_doc(DocumentType.GOVERNING_BODY_RESOLUTION, fields=[make_field("proposed_intake", "180")]),
    ]
    app_input = make_full_application(docs=docs, ref_record=make_clean_ref())

    report = orch.run_complete_prescrutiny(app_input)

    assert report.coverage_audit.is_complete is True
    # Field check abstains as INCONCLUSIVE rather than generating false pass
    inconclusive = [f for f in report.inconclusive_checks if f.rule_id == "RULE-APH-FLD-002"]
    assert len(inconclusive) == 1
    assert "uncertain" in inconclusive[0].reason.lower()


# ==============================================================================
# 6. Issuer Unavailable (503 / Timeout Guardrail)
# ==============================================================================
def test_issuer_unavailable_guardrail_full_review():
    repo = ReviewRunRepository()
    orch = ReviewOrchestrator(repository=repo)
    docs = [
        make_doc(DocumentType.AFFIDAVIT_GENERAL, fields=[make_field("institution_name", "Apex Institute of Technology")]),
        make_doc(
            DocumentType.FIRE_SAFETY_NOC,
            fields=[
                make_field("noc_issue_date", "2026-01-15"),
                make_field("noc_expiry_date", "2027-01-14"),
            ],
            verification_status=DocumentVerificationStatus.SOURCE_UNAVAILABLE
        ),
        make_doc(DocumentType.BUILDING_PLAN_ARCHITECT, fields=[make_field("certified_intake_capacity", "180")]),
        make_doc(DocumentType.GOVERNING_BODY_RESOLUTION, fields=[make_field("proposed_intake", "180")]),
    ]
    app_input = make_full_application(docs=docs, ref_record=make_clean_ref())

    report = orch.run_complete_prescrutiny(app_input)

    assert report.coverage_audit.is_complete is True
    # Guardrail confirms source unavailable does NOT fail compliance
    guard_findings = [f for f in report.inconclusive_checks if f.rule_id == "RULE-INP-UNAVAIL-008"]
    assert len(guard_findings) == 1
    assert "not a compliance failure" in guard_findings[0].reason.lower()


# ==============================================================================
# 7. Non-Applicable Category Rule Check
# ==============================================================================
def test_non_applicable_rule_recorded_with_reason():
    repo = ReviewRunRepository()
    orch = ReviewOrchestrator(repository=repo)
    app_input = make_full_application(docs=make_clean_docs(), ref_record=make_clean_ref(), category=ApplicationCategory.EXTENSION_OF_APPROVAL)

    report = orch.run_complete_prescrutiny(app_input)

    # RULE-CAT-SPEC-007 is applicable only to NEW_INSTITUTION
    na = [f for f in report.not_applicable_checks if f.rule_id == "RULE-CAT-SPEC-007"]
    assert len(na) == 1
    assert na[0].status == FindingStatus.NOT_APPLICABLE
    assert "not applicable to application category 'EXTENSION_OF_APPROVAL'" in na[0].reason


# ==============================================================================
# 8. Negative Coverage Test: Coverage Auditor Catches Omitted Check
# ==============================================================================
def test_coverage_auditor_catches_deliberate_omission():
    repo = ReviewRunRepository()
    orch = ReviewOrchestrator(repository=repo)
    app_input = make_full_application(docs=make_clean_docs(), ref_record=make_clean_ref(), app_id="app-omit-1")

    # Deliberately omit RULE-APH-EXP-003 from execution
    report = orch.run_complete_prescrutiny(app_input, force_omit_check_id="RULE-APH-EXP-003")

    # The Coverage Auditor must REFUSE to declare the review complete!
    assert report.coverage_audit.is_complete is False
    assert report.coverage_audit.audit_verdict == "INCOMPLETE"
    assert "RULE-APH-EXP-003" in report.coverage_audit.missing_checks
    assert report.review_status == "INCOMPLETE"
    assert report.coverage_audit.coverage_percentage < 100.0


# ==============================================================================
# 9. Concurrent Execution Lock / Duplicate Run Prevention
# ==============================================================================
def test_concurrent_run_lock_prevention():
    repo = ReviewRunRepository()
    orch = ReviewOrchestrator(repository=repo)
    app_input = make_full_application(docs=make_clean_docs(app_id="app-lock-test"), ref_record=make_clean_ref(), app_id="app-lock-test")

    # Manually hold lock on app-lock-test
    assert repo.acquire_lock("app-lock-test") is True

    # Attempting to run pre-scrutiny while lock is held must raise RuntimeError
    with pytest.raises(RuntimeError, match="Concurrent review rejected"):
        orch.run_complete_prescrutiny(app_input)

    # Release lock
    repo.release_lock("app-lock-test")
    # Now it succeeds
    report = orch.run_complete_prescrutiny(app_input)
    assert report.review_status == "COMPLETE_COMPLIANT"


# ==============================================================================
# 10. Reopen Saved Report Without Re-running
# ==============================================================================
def test_reopen_saved_report_persistence():
    repo = ReviewRunRepository()
    orch = ReviewOrchestrator(repository=repo)
    app_input = make_full_application(docs=make_clean_docs(app_id="app-persist-1"), ref_record=make_clean_ref(), app_id="app-persist-1")

    # Execute run
    created_report = orch.run_complete_prescrutiny(app_input)
    review_id = created_report.review_id

    # Retrieve by review_id
    reopened = repo.get_by_id(review_id)
    assert reopened is not None
    assert reopened.review_id == review_id
    assert reopened.input_snapshot_hash == created_report.input_snapshot_hash
    assert reopened.review_status == created_report.review_status
    assert len(reopened.findings) == len(created_report.findings)

    # Retrieve latest by application_id
    latest = repo.get_latest_by_application_id("app-persist-1")
    assert latest is not None
    assert latest.review_id == review_id


# ==============================================================================
# 11. REST API Contract Endpoints
# ==============================================================================
def test_api_full_review_orchestrator_flow():
    app_input = make_full_application(docs=make_clean_docs(app_id="app-api-flow"), ref_record=make_clean_ref(), app_id="app-api-flow")

    # The server reviews its own stored dossier, never a client-supplied copy.
    from app.services.application_service import global_application_service
    global_application_service.save_application(app_input)
    payload = {
        "rule_pack_id": "rp-aicte-aph-2024-eoa",
        "rule_pack_version": "1.0.0"
    }

    # 1. POST full review
    res = client.post("/api/v1/applications/app-api-flow/full-review", json=payload, headers=auth_headers)
    assert res.status_code == 201
    report = res.json()
    assert report["review_status"] == "COMPLETE_COMPLIANT"
    assert report["coverage_audit"]["is_complete"] is True
    review_id = report["review_id"]

    # 2. GET latest full review for application
    latest_res = client.get("/api/v1/applications/app-api-flow/full-review/latest", headers=auth_headers)
    assert latest_res.status_code == 200
    assert latest_res.json()["review_id"] == review_id

    # 3. GET specific review run by ID
    run_res = client.get(f"/api/v1/review-runs/{review_id}", headers=auth_headers)
    assert run_res.status_code == 200
    assert run_res.json()["review_id"] == review_id

    # 4. POST independent coverage audit verification
    audit_res = client.post(f"/api/v1/review-runs/{review_id}/coverage-audit", headers=auth_headers)
    assert audit_res.status_code == 200
    audit_data = audit_res.json()
    assert audit_data["is_complete"] is True
    assert audit_data["audit_verdict"] == "COMPLETE"


# ==============================================================================
# 12. Cross-Application Document Reuse Detection Test
# ==============================================================================
def test_cross_application_reuse_detection():
    custom_index = DuplicateIndex()
    detector = DuplicateDetector(index=custom_index)
    orch = ReviewOrchestrator(duplicate_detector=detector)

    # 1. Run for Application A
    shared_hash = "shared-certificate-sha256-abc123xyz"
    doc_a = make_doc(DocumentType.LAND_USE_CERTIFICATE, sha256=shared_hash, app_id="app-college-a")
    app_a = make_full_application(docs=[doc_a], ref_record=make_clean_ref(), app_id="app-college-a")
    report_a = orch.run_complete_prescrutiny(app_a)

    # In Application A, file is registered; no duplicate yet
    reuse_a = [f for f in report_a.findings if f.rule_id == "RULE-APH-REUSE-010"]
    assert len(reuse_a) == 0

    # 2. Run for Application B with the SAME document hash
    doc_b = make_doc(DocumentType.LAND_USE_CERTIFICATE, sha256=shared_hash, app_id="app-college-b")
    app_b = make_full_application(docs=[doc_b], ref_record=make_clean_ref(), app_id="app-college-b")
    report_b = orch.run_complete_prescrutiny(app_b)

    # Application B must detect the reuse from Application A
    reuse_b = [f for f in report_b.findings if f.rule_id == "RULE-APH-REUSE-010"]
    assert len(reuse_b) == 1
    assert reuse_b[0].status == FindingStatus.ANOMALY_SIGNAL
    assert "app-college-a" in reuse_b[0].reason
    assert "NOT proof of misconduct" in reuse_b[0].reason
