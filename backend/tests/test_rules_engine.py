"""
Comprehensive Test Suite for PRAMAAN-AI Deterministic Rules Engine
Covers pass, fail, boundary dates, invalid dates, missing inputs, category applicability,
conflicting fields, legitimate name variation, missing reference record, repeatable replay,
and API contracts.
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
from app.models.validation import Finding
from app.rules.catalog import (
    RequiredDocumentMissingRule,
    RequiredFieldAbsentOrUncertainRule,
    DocumentExpiryValidityRule,
    InvalidDateRelationshipRule,
    CrossDocumentMismatchRule,
    ReferenceRecordDifferenceRule,
    CategorySpecificRule,
    EvidenceAvailabilityGuardRule,
    InstitutionalNameConsistencyRule,
    get_default_rules,
)
from app.services.validation_engine import ValidationEngine, ValidationRunRepository
from app.main import app
from app.core.auth import get_test_auth_headers

client = TestClient(app)
auth_headers = get_test_auth_headers("usr-officer-01")

# Helper fixtures
def make_field(key: str, value: str, confidence: float = 0.95, quality: ExtractionQuality = ExtractionQuality.HIGH) -> ExtractedField:
    return ExtractedField(
        field_key=key,
        field_value=value,
        raw_value=value,
        confidence=confidence,
        provenance=FieldProvenance(
            page_number=1,
            bounding_box=[0.1, 0.2, 0.3, 0.4],
            quality_label=quality
        )
    )

def make_doc(doc_type: DocumentType, fields=None, verification_status=DocumentVerificationStatus.VERIFICATION_PENDING) -> Document:
    return Document(
        application_id="app-test-1",
        document_type=doc_type,
        original_filename=f"{doc_type.value.lower()}.pdf",
        storage_key=f"storage/{doc_type.value.lower()}.bin",
        sha256_hash="e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
        verification_status=verification_status,
        extracted_fields=fields or []
    )

def make_application(docs=None, ref_record=None, declared=None, category=ApplicationCategory.EXTENSION_OF_APPROVAL) -> ApplicationInput:
    return ApplicationInput(
        application_id="app-test-1",
        institution_id="inst-test-1",
        application_number="APP-2026-EOA-001",
        submission_date=date(2026, 5, 1),
        submission_cutoff_date=date(2026, 6, 30),
        category=category,
        declared_data=declared or {"total_intake": 180},
        documents=docs or [],
        reference_record=ref_record
    )


# ==============================================================================
# 1. Required Document Missing Rule Tests
# ==============================================================================
def test_required_document_missing_fail():
    rule = RequiredDocumentMissingRule()
    # Missing FIRE_SAFETY_NOC and BUILDING_PLAN_ARCHITECT
    app_input = make_application(docs=[make_doc(DocumentType.AFFIDAVIT_GENERAL)])
    finding = rule.evaluate(app_input)

    assert finding.status == FindingStatus.DEFICIENCY
    assert finding.severity == Severity.DEFICIENCY
    assert "BUILDING_PLAN_ARCHITECT" in finding.reason
    assert "FIRE_SAFETY_NOC" in finding.reason
    assert "AICTE Approval Process Handbook" in finding.clause_citation
    assert not finding.is_demo

def test_required_document_missing_pass():
    rule = RequiredDocumentMissingRule()
    docs = [
        make_doc(DocumentType.AFFIDAVIT_GENERAL),
        make_doc(DocumentType.FIRE_SAFETY_NOC),
        make_doc(DocumentType.BUILDING_PLAN_ARCHITECT),
    ]
    app_input = make_application(docs=docs)
    finding = rule.evaluate(app_input)

    assert finding.status == FindingStatus.COMPLIANT


# ==============================================================================
# 2. Required Field Absent or Extraction Uncertain Tests
# ==============================================================================
def test_required_field_absent_fail():
    rule = RequiredFieldAbsentOrUncertainRule()
    doc = make_doc(DocumentType.FIRE_SAFETY_NOC, fields=[])
    app_input = make_application(docs=[doc])
    finding = rule.evaluate(app_input)

    assert finding.status == FindingStatus.INCONCLUSIVE
    assert "noc_expiry_date" in finding.reason

def test_required_field_uncertain_quality_abstains():
    rule = RequiredFieldAbsentOrUncertainRule()
    # Low confidence (0.45) and LOW_CONFIDENCE quality
    field = make_field("noc_expiry_date", "2026-12-31", confidence=0.45, quality=ExtractionQuality.LOW_CONFIDENCE)
    doc = make_doc(DocumentType.FIRE_SAFETY_NOC, fields=[field])
    app_input = make_application(docs=[doc])
    finding = rule.evaluate(app_input)

    # Engine must abstain from false pass
    assert finding.status == FindingStatus.INCONCLUSIVE
    assert "uncertain" in finding.reason.lower()
    assert "manual visual verification" in finding.recommended_action.lower()

def test_required_field_present_pass():
    rule = RequiredFieldAbsentOrUncertainRule()
    field = make_field("noc_expiry_date", "2026-12-31", confidence=0.98, quality=ExtractionQuality.HIGH)
    doc = make_doc(DocumentType.FIRE_SAFETY_NOC, fields=[field])
    app_input = make_application(docs=[doc])
    finding = rule.evaluate(app_input)

    assert finding.status == FindingStatus.COMPLIANT


# ==============================================================================
# 3. Expiry / Validity Boundary Date Tests
# ==============================================================================
def test_expiry_validity_expired_fail():
    rule = DocumentExpiryValidityRule()
    # Expired on 2024-01-14 (cutoff is 2026-06-30)
    field = make_field("noc_expiry_date", "2024-01-14")
    doc = make_doc(DocumentType.FIRE_SAFETY_NOC, fields=[field])
    app_input = make_application(docs=[doc])
    finding = rule.evaluate(app_input)

    assert finding.status == FindingStatus.DEFICIENCY
    assert "expired" in finding.reason.lower()
    # Confirms document verification status was set to expired
    assert doc.verification_status == DocumentVerificationStatus.EXPIRED

def test_expiry_validity_boundary_date_exact_cutoff_pass():
    rule = DocumentExpiryValidityRule()
    # Exactly matches cutoff date 2026-06-30
    field = make_field("noc_expiry_date", "2026-06-30")
    doc = make_doc(DocumentType.FIRE_SAFETY_NOC, fields=[field])
    app_input = make_application(docs=[doc])
    finding = rule.evaluate(app_input)

    assert finding.status == FindingStatus.COMPLIANT
    assert "meets cutoff" in finding.reason.lower()

def test_expiry_validity_future_date_pass():
    rule = DocumentExpiryValidityRule()
    field = make_field("noc_expiry_date", "2027-12-31")
    doc = make_doc(DocumentType.FIRE_SAFETY_NOC, fields=[field])
    app_input = make_application(docs=[doc])
    finding = rule.evaluate(app_input)

    assert finding.status == FindingStatus.COMPLIANT


# ==============================================================================
# 4. Invalid Date Relationship Tests
# ==============================================================================
def test_invalid_date_relationship_issue_after_expiry():
    rule = InvalidDateRelationshipRule()
    fields = [
        make_field("noc_issue_date", "2026-05-01"),
        make_field("noc_expiry_date", "2025-05-01"),  # Expiry before issue!
    ]
    doc = make_doc(DocumentType.FIRE_SAFETY_NOC, fields=fields)
    app_input = make_application(docs=[doc])
    finding = rule.evaluate(app_input)

    assert finding.status == FindingStatus.ANOMALY_SIGNAL
    assert "chronological anomaly" in finding.reason.lower()
    assert finding.is_demo

def test_invalid_date_relationship_future_issue_date():
    rule = InvalidDateRelationshipRule()
    # Submission date is 2026-05-01; issue date is 2026-10-01 (in the future!)
    fields = [
        make_field("noc_issue_date", "2026-10-01"),
        make_field("noc_expiry_date", "2027-10-01"),
    ]
    doc = make_doc(DocumentType.FIRE_SAFETY_NOC, fields=fields)
    app_input = make_application(docs=[doc])
    finding = rule.evaluate(app_input)

    assert finding.status == FindingStatus.ANOMALY_SIGNAL
    assert "future issue date" in finding.reason.lower()

def test_invalid_date_relationship_valid_pass():
    rule = InvalidDateRelationshipRule()
    fields = [
        make_field("noc_issue_date", "2026-01-15"),
        make_field("noc_expiry_date", "2027-01-14"),
    ]
    doc = make_doc(DocumentType.FIRE_SAFETY_NOC, fields=fields)
    app_input = make_application(docs=[doc])
    finding = rule.evaluate(app_input)

    assert finding.status == FindingStatus.COMPLIANT


# ==============================================================================
# 5. Cross-Document Value Mismatch Tests
# ==============================================================================
def test_cross_document_mismatch_conflicting_fields():
    rule = CrossDocumentMismatchRule()
    doc_arch = make_doc(
        DocumentType.BUILDING_PLAN_ARCHITECT,
        fields=[make_field("certified_intake_capacity", "180")]
    )
    doc_gov = make_doc(
        DocumentType.GOVERNING_BODY_RESOLUTION,
        fields=[make_field("proposed_intake", "240")]
    )
    app_input = make_application(docs=[doc_arch, doc_gov])
    finding = rule.evaluate(app_input)

    assert finding.status == FindingStatus.DEFICIENCY
    assert "mismatch" in finding.reason.lower()
    assert len(finding.evidence) == 2
    assert finding.evidence[0].extracted_value == "180"
    assert finding.evidence[1].extracted_value == "240"

def test_cross_document_consistent_pass():
    rule = CrossDocumentMismatchRule()
    doc_arch = make_doc(
        DocumentType.BUILDING_PLAN_ARCHITECT,
        fields=[make_field("certified_intake_capacity", "240")]
    )
    doc_gov = make_doc(
        DocumentType.GOVERNING_BODY_RESOLUTION,
        fields=[make_field("proposed_intake", "240")]
    )
    app_input = make_application(docs=[doc_arch, doc_gov])
    finding = rule.evaluate(app_input)

    assert finding.status == FindingStatus.COMPLIANT


# ==============================================================================
# 6. Reference Record Difference Tests (AICTE Historical Baseline)
# ==============================================================================
def test_reference_record_intake_increase_anomaly():
    rule = ReferenceRecordDifferenceRule()
    ref = InstitutionalReferenceRecord(
        institution_id="inst-test-1",
        aicte_permanent_id="1-3324589110",
        legal_name="Apex Institute of Technology",
        academic_year="2025-2026",
        approved_intake=180,
        approved_builtup_area_sqm=12000.0
    )
    # Current EoA claims 240 seats (exceeding 180)
    app_input = make_application(ref_record=ref, declared={"total_intake": 240})
    finding = rule.evaluate(app_input)

    assert finding.status == FindingStatus.ANOMALY_SIGNAL
    assert "exceeds prior approved aicte baseline" in finding.reason.lower()

def test_reference_record_consistent_pass():
    rule = ReferenceRecordDifferenceRule()
    ref = InstitutionalReferenceRecord(
        institution_id="inst-test-1",
        aicte_permanent_id="1-3324589110",
        legal_name="Apex Institute of Technology",
        academic_year="2025-2026",
        approved_intake=180,
        approved_builtup_area_sqm=12000.0
    )
    app_input = make_application(ref_record=ref, declared={"total_intake": 180})
    finding = rule.evaluate(app_input)

    assert finding.status == FindingStatus.COMPLIANT

def test_reference_record_missing_input_abstains():
    rule = ReferenceRecordDifferenceRule()
    # reference_record is None
    app_input = make_application(ref_record=None, declared={"total_intake": 180})
    finding = rule.evaluate(app_input)

    assert finding.status == FindingStatus.INCONCLUSIVE
    assert "unavailable" in finding.reason.lower()


# ==============================================================================
# 7. Category Applicability Tests
# ==============================================================================
def test_category_applicability_not_applicable_for_eoa():
    rule = CategorySpecificRule()
    # Rule only applies to NEW_INSTITUTION; test with EXTENSION_OF_APPROVAL
    app_input = make_application(category=ApplicationCategory.EXTENSION_OF_APPROVAL)
    finding = rule.evaluate(app_input)

    assert finding.status == FindingStatus.NOT_APPLICABLE
    assert "not applicable" in finding.reason.lower()

def test_category_applicability_applied_for_new_institution():
    rule = CategorySpecificRule()
    app_input = make_application(category=ApplicationCategory.NEW_INSTITUTION, docs=[])
    finding = rule.evaluate(app_input)

    # For NEW_INSTITUTION, rule is active and missing land conversion order is a deficiency
    assert finding.status == FindingStatus.DEFICIENCY
    assert "Land Conversion Order" in finding.reason


# ==============================================================================
# 8. Evidence Availability Guardrail Tests
# ==============================================================================
def test_evidence_availability_guard_source_unavailable():
    rule = EvidenceAvailabilityGuardRule()
    # Simulate a document where the external issuer returned HTTP 503 / timeout
    doc = make_doc(
        DocumentType.FIRE_SAFETY_NOC,
        verification_status=DocumentVerificationStatus.SOURCE_UNAVAILABLE
    )
    app_input = make_application(docs=[doc])
    finding = rule.evaluate(app_input)

    assert finding.status == FindingStatus.INCONCLUSIVE
    assert "source was unavailable" in finding.reason.lower()
    assert "not a compliance failure" in finding.reason.lower()


# ==============================================================================
# 9. Fuzzy Institutional Name Normalization Tests
# ==============================================================================
def test_fuzzy_name_exact_match():
    rule = InstitutionalNameConsistencyRule()
    ref = InstitutionalReferenceRecord(
        institution_id="inst-test-1",
        aicte_permanent_id="1-3324589110",
        legal_name="Apex Institute of Technology",
        academic_year="2025-2026",
        approved_intake=180,
        approved_builtup_area_sqm=12000.0
    )
    doc = make_doc(
        DocumentType.AFFIDAVIT_GENERAL,
        fields=[make_field("institution_name", "Apex Institute of Technology")]
    )
    app_input = make_application(docs=[doc], ref_record=ref)
    finding = rule.evaluate(app_input)

    assert finding.status == FindingStatus.COMPLIANT
    assert "matches aicte master record verbatim" in finding.reason.lower()

def test_fuzzy_name_legitimate_abbreviation_variation():
    rule = InstitutionalNameConsistencyRule()
    ref = InstitutionalReferenceRecord(
        institution_id="inst-test-1",
        aicte_permanent_id="1-3324589110",
        legal_name="Apex Institute of Technology",
        academic_year="2025-2026",
        approved_intake=180,
        approved_builtup_area_sqm=12000.0
    )
    # Document has benign abbreviation: "Apex Inst. of Tech."
    doc = make_doc(
        DocumentType.AFFIDAVIT_GENERAL,
        fields=[make_field("institution_name", "Apex Inst. of Tech.")]
    )
    app_input = make_application(docs=[doc], ref_record=ref)
    finding = rule.evaluate(app_input)

    # Must NOT fail as fraud/deficiency; recognized as legitimate variation
    assert finding.status == FindingStatus.COMPLIANT
    assert "legitimate abbreviation/spelling variation detected" in finding.reason.lower()

def test_fuzzy_name_substantive_mismatch():
    rule = InstitutionalNameConsistencyRule()
    ref = InstitutionalReferenceRecord(
        institution_id="inst-test-1",
        aicte_permanent_id="1-3324589110",
        legal_name="Apex Institute of Technology",
        academic_year="2025-2026",
        approved_intake=180,
        approved_builtup_area_sqm=12000.0
    )
    # Completely different institution
    doc = make_doc(
        DocumentType.AFFIDAVIT_GENERAL,
        fields=[make_field("institution_name", "Bharati Vidyapeeth College of Engineering")]
    )
    app_input = make_application(docs=[doc], ref_record=ref)
    finding = rule.evaluate(app_input)

    assert finding.status == FindingStatus.DEFICIENCY
    assert "substantive institutional name mismatch" in finding.reason.lower()


# ==============================================================================
# 10. Repeatable Replay & Run Immutability Tests
# ==============================================================================
def test_repeatable_replay_same_input_and_version():
    repo = ValidationRunRepository()
    engine = ValidationEngine(repository=repo)

    docs = [
        make_doc(DocumentType.AFFIDAVIT_GENERAL, fields=[make_field("institution_name", "Apex Institute of Technology")]),
        make_doc(DocumentType.FIRE_SAFETY_NOC, fields=[
            make_field("noc_issue_date", "2026-01-15"),
            make_field("noc_expiry_date", "2027-01-14"),
        ]),
        make_doc(DocumentType.BUILDING_PLAN_ARCHITECT, fields=[make_field("certified_intake_capacity", "180")]),
        make_doc(DocumentType.GOVERNING_BODY_RESOLUTION, fields=[make_field("proposed_intake", "180")]),
    ]
    ref = InstitutionalReferenceRecord(
        institution_id="inst-test-1",
        aicte_permanent_id="1-3324589110",
        legal_name="Apex Institute of Technology",
        academic_year="2025-2026",
        approved_intake=180,
        approved_builtup_area_sqm=12000.0
    )
    app_input = make_application(docs=docs, ref_record=ref, declared={"total_intake": 180})

    run1 = engine.run_validation(app_input, rule_pack_version="1.0.0")
    run2 = engine.run_validation(app_input, rule_pack_version="1.0.0")

    # Hashes must be identical
    assert run1.input_snapshot_hash == run2.input_snapshot_hash
    # Findings count and outcomes must be bit-for-bit identical
    assert len(run1.findings) == len(run2.findings)
    assert run1.overall_result == run2.overall_result
    assert run1.findings_summary == run2.findings_summary
    for f1, f2 in zip(run1.findings, run2.findings):
        assert f1.rule_id == f2.rule_id
        assert f1.status == f2.status
        assert f1.reason == f2.reason

    # Old runs must be preserved
    app_runs = repo.get_by_application_id("app-test-1")
    assert len(app_runs) == 2
    assert app_runs[0].id == run1.id
    assert app_runs[1].id == run2.id


# ==============================================================================
# 11. API Endpoint Contract Tests
# ==============================================================================
def test_health_endpoints():
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["is_demo_mode"] is True
    assert "DEMO DATA" in data["banner"]

    ready = client.get("/health/ready")
    assert ready.status_code == 200
    assert ready.json()["status"] == "ready"

def test_api_create_validation_run():
    docs = [
        make_doc(DocumentType.AFFIDAVIT_GENERAL, fields=[make_field("institution_name", "Apex Institute of Technology")]),
        make_doc(DocumentType.FIRE_SAFETY_NOC, fields=[
            make_field("noc_issue_date", "2026-01-15"),
            make_field("noc_expiry_date", "2024-01-14"),  # Expired!
        ]),
        make_doc(DocumentType.BUILDING_PLAN_ARCHITECT, fields=[make_field("certified_intake_capacity", "180")]),
    ]
    app_input = make_application(docs=docs)

    # The server validates its own stored dossier, never a client-supplied copy.
    from app.services.application_service import global_application_service
    app_input.application_id = "app-test-1"
    global_application_service.save_application(app_input)
    payload = {
        "rule_pack_id": "rp-aicte-aph-2024-eoa",
        "rule_pack_version": "1.0.0"
    }

    res = client.post("/api/v1/applications/app-test-1/validation-runs", json=payload, headers=auth_headers)
    assert res.status_code == 201
    run_data = res.json()

    assert run_data["application_id"] == "app-test-1"
    assert run_data["overall_result"] == "DEFICIENCIES_DETECTED"
    assert run_data["findings_summary"]["deficiency"] >= 1

    # Check GET historical runs
    get_res = client.get("/api/v1/applications/app-test-1/validation-runs", headers=auth_headers)
    assert get_res.status_code == 200
    assert len(get_res.json()) >= 1
