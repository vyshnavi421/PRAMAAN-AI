"""
Comprehensive Automated Test Suite for PRAMAAN-AI Duplicates & Change-Aware Historical Review
Covers all mandated requirements:
1. Exact file reuse: SHA-256 hash collision of original bytes.
2. Approximate similarity: text shingle similarity on similar but distinct documents.
3. Repeated generic template: boilerplate affidavit template shared across institutions.
4. Altered synthetic NOC: altered dates/numbers detected as approximate similarity.
5. Change in intake: intake increase (+33.3%) recognized as expansion request, never as fraud.
6. Legitimate name change & normalisation: abbreviations (Inst. vs Institute, Rd vs Road).
7. Absent previous record: first-time application dossier handled gracefully without error.
8. Mismatches across different documents: cross-document discrepancy handling.
9. Side-by-side review payload and REST API endpoints.
"""
import pytest
from datetime import date
from fastapi.testclient import TestClient

from app.main import app
from app.core.auth import get_test_auth_headers

auth_headers = get_test_auth_headers("usr-officer-01")
from app.models.enums import DocumentType, ApplicationCategory, ExtractionQuality, DocumentVerificationStatus
from app.models.domain import ApplicationInput, Document, ExtractedField, FieldProvenance
from app.services.duplicate_detector import (
    DuplicateDetector,
    DuplicateIndex,
    DuplicateMatchType,
    DuplicateMatchMethod,
    compute_shingle_similarity,
)
from app.services.historical_service import (
    HistoricalComparisonEngine,
    HistoricalSnapshotRepository,
    HistoricalApplicationSnapshot,
    ChangeType,
    normalize_text,
    compute_token_similarity,
)


client = TestClient(app)


def make_test_doc(doc_id: str, app_id: str, doc_type: DocumentType, filename: str, sha256: str, text: str = "") -> Document:
    return Document(
        id=doc_id,
        application_id=app_id,
        document_type=doc_type,
        original_filename=filename,
        storage_key=f"storage/{app_id}/{filename}",
        sha256_hash=sha256,
        verification_status=DocumentVerificationStatus.VERIFIED,
        extracted_fields=[
            ExtractedField(
                field_key="document_text",
                field_value=text or filename,
                raw_value=text or filename,
                confidence=0.98,
                provenance=FieldProvenance(page_number=1, quality_label=ExtractionQuality.HIGH)
            )
        ]
    )


# ---------------------------------------------------------------------------
# Unit Tests: Duplicates & Similarity Detection
# ---------------------------------------------------------------------------

def test_exact_binary_duplicate_detection():
    index = DuplicateIndex()
    detector = DuplicateDetector(index)

    # Document 1 in Application A
    doc_a = make_test_doc("doc-a-arch", "app-101", DocumentType.BUILDING_PLAN_ARCHITECT, "arch_plan.pdf", "hash-exact-binary-999")
    app_a = ApplicationInput(
        application_id="app-101",
        institution_id="inst-alpha",
        application_number="APP-2026-EOA-101",
        submission_date=date(2026, 4, 1),
        submission_cutoff_date=date(2026, 6, 30),
        documents=[doc_a]
    )
    detector.scan_document(app_a, doc_a)

    # Document 2 in Application B with identical SHA-256 hash
    doc_b = make_test_doc("doc-b-arch", "app-202", DocumentType.BUILDING_PLAN_ARCHITECT, "arch_plan_copy.pdf", "hash-exact-binary-999")
    app_b = ApplicationInput(
        application_id="app-202",
        institution_id="inst-beta",
        application_number="APP-2026-NEW-202",
        submission_date=date(2026, 4, 5),
        submission_cutoff_date=date(2026, 6, 30),
        documents=[doc_b]
    )
    matches = detector.scan_document(app_b, doc_b)

    assert len(matches) == 1
    match = matches[0]
    assert match.match_type == DuplicateMatchType.EXACT_BINARY_MATCH
    assert match.method == DuplicateMatchMethod.SHA256_BYTE_HASH
    assert match.similarity_score == 1.0
    assert "NOT_FRAUD" in match.legitimacy_assessment
    assert match.source_doc.document_id == "doc-b-arch"
    assert match.target_doc.document_id == "doc-a-arch"


def test_similar_but_distinct_document():
    index = DuplicateIndex()
    detector = DuplicateDetector(index)

    text_original = "State Fire Service Clearance Certificate. Inspected building premises at Sector 4. Fire extinguishers and exits functional."
    text_modified = "State Fire Service Clearance Certificate. Inspected building premises at Sector 4. Fire extinguishers, alarms and exits functional."

    doc_1 = make_test_doc("doc-1", "app-1", DocumentType.FIRE_SAFETY_NOC, "fire_noc_v1.pdf", "hash-unique-111", text_original)
    app_1 = ApplicationInput(application_id="app-1", institution_id="inst-1", application_number="APP-1", submission_date=date(2026, 4, 1), submission_cutoff_date=date(2026, 6, 30), documents=[doc_1])
    detector.scan_document(app_1, doc_1)

    doc_2 = make_test_doc("doc-2", "app-2", DocumentType.FIRE_SAFETY_NOC, "fire_noc_v2.pdf", "hash-unique-222", text_modified)
    app_2 = ApplicationInput(application_id="app-2", institution_id="inst-2", application_number="APP-2", submission_date=date(2026, 4, 2), submission_cutoff_date=date(2026, 6, 30), documents=[doc_2])
    matches = detector.scan_document(app_2, doc_2, similarity_threshold=0.75)

    assert len(matches) == 1
    match = matches[0]
    assert match.match_type == DuplicateMatchType.APPROXIMATE_SIMILARITY
    assert match.method == DuplicateMatchMethod.TEXT_SHINGLE_SIMILARITY
    assert match.similarity_score >= 0.75


def test_repeated_generic_template():
    index = DuplicateIndex()
    detector = DuplicateDetector(index)

    # Standard AICTE Affidavit Format A boilerplate with differing deponent details
    boilerplate_a = "Affidavit under AICTE Act. I, Chairman of Apex Society, swear that the college is free from encumbrance and follows all AICTE APH norms."
    boilerplate_b = "Affidavit under AICTE Act. I, Chairman of Sunrise Trust, swear that the college is free from encumbrance and follows all AICTE APH norms."

    doc_a = make_test_doc("doc-aff-a", "app-a", DocumentType.AFFIDAVIT_GENERAL, "affidavit_apex.pdf", "hash-aff-a", boilerplate_a)
    app_a = ApplicationInput(application_id="app-a", institution_id="inst-a", application_number="APP-A", submission_date=date(2026, 4, 1), submission_cutoff_date=date(2026, 6, 30), documents=[doc_a])
    detector.scan_document(app_a, doc_a)

    doc_b = make_test_doc("doc-aff-b", "app-b", DocumentType.AFFIDAVIT_GENERAL, "affidavit_sunrise.pdf", "hash-aff-b", boilerplate_b)
    app_b = ApplicationInput(application_id="app-b", institution_id="inst-b", application_number="APP-B", submission_date=date(2026, 4, 2), submission_cutoff_date=date(2026, 6, 30), documents=[doc_b])
    matches = detector.scan_document(app_b, doc_b, similarity_threshold=0.80)

    assert len(matches) == 1
    match = matches[0]
    # Standard format recognized as generic template boilerplate
    assert match.match_type == DuplicateMatchType.GENERIC_TEMPLATE
    assert match.method == DuplicateMatchMethod.BOILERPLATE_TEMPLATE_MATCH


def test_altered_synthetic_noc():
    index = DuplicateIndex()
    detector = DuplicateDetector(index)

    # Altered validity date and registration number on identical clearance letter
    noc_orig = "Karnataka Fire Safety Clearance NOC-FS-2023-8891. Valid until 14/01/2024. Clear for educational occupancy."
    noc_altered = "Karnataka Fire Safety Clearance NOC-FS-2023-8891. Valid until 14/01/2027. Clear for educational occupancy."

    doc_orig = make_test_doc("doc-noc-1", "app-orig", DocumentType.FIRE_SAFETY_NOC, "fire_noc_2023.pdf", "hash-orig-noc", noc_orig)
    app_orig = ApplicationInput(application_id="app-orig", institution_id="inst-orig", application_number="APP-ORIG", submission_date=date(2026, 4, 1), submission_cutoff_date=date(2026, 6, 30), documents=[doc_orig])
    detector.scan_document(app_orig, doc_orig)

    doc_alt = make_test_doc("doc-noc-2", "app-alt", DocumentType.FIRE_SAFETY_NOC, "fire_noc_altered.pdf", "hash-altered-noc", noc_altered)
    app_alt = ApplicationInput(application_id="app-alt", institution_id="inst-alt", application_number="APP-ALT", submission_date=date(2026, 4, 2), submission_cutoff_date=date(2026, 6, 30), documents=[doc_alt])
    matches = detector.scan_document(app_alt, doc_alt, similarity_threshold=0.85)

    assert len(matches) == 1
    match = matches[0]
    assert match.match_type == DuplicateMatchType.APPROXIMATE_SIMILARITY
    assert match.similarity_score >= 0.85


# ---------------------------------------------------------------------------
# Unit Tests: Change-Aware Review, Normalisation & Missing Records
# ---------------------------------------------------------------------------

def test_change_in_intake():
    repo = HistoricalSnapshotRepository()
    engine = HistoricalComparisonEngine(repo)

    # Bharat Polytechnic baseline had 120 intake; currently requesting 180 seats (+50%)
    app_input = ApplicationInput(
        application_id="app-case-hist",
        institution_id="inst-bharat-04",
        application_number="APP-2026-EOA-104",
        academic_year="2026-2027",
        submission_date=date(2026, 4, 10),
        submission_cutoff_date=date(2026, 6, 30),
        category=ApplicationCategory.EXTENSION_OF_APPROVAL,
        declared_data={
            "institution_name": "Bharat Polytechnic College",
            "address": "Kalyan Bypass Road, Raigad",
            "total_intake": 180,  # +60 seats (+50%)
            "builtup_area_sqm": 8500.0,
            "land_area_acres": 5.0,
            "head_of_institution": "Prof. V. K. Patil",
        }
    )

    report = engine.compare_application(app_input)
    assert report.is_first_time_application is False
    assert report.baseline_academic_year == "2025-2026"

    intake_delta = next(d for d in report.deltas if d.field_key == "total_intake")
    assert intake_delta.change_type == ChangeType.INCREASE_REQUESTED
    assert intake_delta.previous_value == 120
    assert intake_delta.current_value == 180
    assert intake_delta.variance_pct == 50.0
    # Crucial statutory guardrail: Must NEVER be classified as an automatic compliance violation or fraud!
    assert intake_delta.is_compliance_violation is False
    assert intake_delta.related_rule_id == "RULE-AICTE-HIST-006"


def test_legitimate_name_change_and_normalisation():
    repo = HistoricalSnapshotRepository()
    engine = HistoricalComparisonEngine(repo)

    # 1. Normalised abbreviations: "Apex Inst. of Tech." vs "Apex Institute of Technology", "Rd" vs "Road"
    app_norm = ApplicationInput(
        application_id="app-norm-test",
        institution_id="inst-apex-01",
        application_number="APP-2026-EOA-101",
        academic_year="2026-2027",
        submission_date=date(2026, 4, 10),
        submission_cutoff_date=date(2026, 6, 30),
        declared_data={
            "institution_name": "Apex Inst. of Tech.",  # Normalised match
            "address": "Plot No. 12, Tech Zone, Electronic City, Rd, Bangalore", # Normalised match
            "total_intake": 180,
            "builtup_area_sqm": 12000.0,
            "land_area_acres": 7.5,
            "head_of_institution": "Dr. S. Ramanujan",
        }
    )

    report_norm = engine.compare_application(app_norm)
    name_delta = next(d for d in report_norm.deltas if d.field_key == "institution_name")
    assert name_delta.change_type == ChangeType.NORMALIZED_MATCH
    assert name_delta.is_compliance_violation is False

    addr_delta = next(d for d in report_norm.deltas if d.field_key == "address")
    assert addr_delta.change_type == ChangeType.NORMALIZED_MATCH
    assert addr_delta.is_compliance_violation is False

    # 2. Legitimate Name Change: "Apex Institute of Technology and Research" (Borderline Review)
    app_rename = ApplicationInput(
        application_id="app-rename-test",
        institution_id="inst-apex-01",
        application_number="APP-2026-EOA-101",
        academic_year="2026-2027",
        submission_date=date(2026, 4, 10),
        submission_cutoff_date=date(2026, 6, 30),
        declared_data={
            "institution_name": "Apex Institute of Technology & Advanced Research",
            "total_intake": 180,
        }
    )
    report_rename = engine.compare_application(app_rename)
    rename_delta = next(d for d in report_rename.deltas if d.field_key == "institution_name")
    assert rename_delta.change_type == ChangeType.BORDERLINE_REVIEW
    assert rename_delta.requires_manual_scrutiny is True
    assert rename_delta.is_compliance_violation is False


def test_absent_previous_record_first_time_application():
    repo = HistoricalSnapshotRepository()
    engine = HistoricalComparisonEngine(repo)

    # First-time institution with zero prior annual records in registry
    app_first_time = ApplicationInput(
        application_id="app-brand-new",
        institution_id="inst-new-establishment-999",
        application_number="APP-2026-NEW-999",
        academic_year="2026-2027",
        submission_date=date(2026, 4, 15),
        submission_cutoff_date=date(2026, 6, 30),
        category=ApplicationCategory.NEW_INSTITUTION,
        declared_data={
            "institution_name": "Zenith Institute of Emerging Technology",
            "address": "Survey 99, Knowledge City, Hyderabad",
            "total_intake": 300,
        }
    )

    report = engine.compare_application(app_first_time)
    assert report.is_first_time_application is True
    assert report.baseline_academic_year is None
    assert len(report.deltas) == 1
    assert report.deltas[0].change_type == ChangeType.FIRST_TIME_APPLICATION
    assert report.deltas[0].is_compliance_violation is False
    assert "First-Time Institutional Filing" in report.deltas[0].delta_description


def test_mismatches_across_different_documents():
    # Comparing dissimilar document types produces near-zero similarity
    text_fire = "Fire Safety NOC No. 2026-99 valid up to 2027."
    text_land = "Revenue Department Land Conversion Order for Survey 44/1 extent 7.5 acres."

    sim = compute_shingle_similarity(text_fire, text_land, k=3)
    assert sim < 0.20 # Dissimilar documents do not false-alarm


# ---------------------------------------------------------------------------
# API Route Integration Tests
# ---------------------------------------------------------------------------

def test_api_duplicate_scan_and_side_by_side():
    # 1. Trigger duplicate scan on app-case-reuse (which collides with app-case-clean on architect certificate)
    res_scan = client.get("/api/v1/duplicates/scan/app-case-reuse", headers=auth_headers)
    assert res_scan.status_code == 200
    matches = res_scan.json()
    assert len(matches) >= 1
    match = matches[0]
    match_id = match["id"]
    assert match["match_type"] == "EXACT_BINARY_MATCH"

    # 2. Fetch side-by-side comparison payload
    res_side = client.get(f"/api/v1/duplicates/matches/{match_id}/side-by-side", headers=auth_headers)
    assert res_side.status_code == 200
    side_data = res_side.json()
    assert "source_panel" in side_data
    assert "target_panel" in side_data
    assert "CONFIRM_SHARED_SPONSORING_TRUST" in side_data["reviewer_options"]
    assert "NOT_FRAUD" in side_data["legitimacy_assessment"]

    # 3. Post authorized reviewer resolution
    res_verdict = client.post(
        f"/api/v1/duplicates/matches/{match_id}/verdict",
        json={
            "verdict": "CONFIRM_SHARED_SPONSORING_TRUST",
            "notes": "Both colleges operate on contiguous land parcel owned by Vidya Educational Trust.",
            "actor_id": "usr-scrutiny-officer"
        },
        headers=auth_headers
    )
    assert res_verdict.status_code == 200
    assert res_verdict.json()["verdict"] == "CONFIRM_SHARED_SPONSORING_TRUST"


def test_api_historical_comparison():
    # Fetch historical comparison report for Apex Institute
    res = client.get("/api/v1/applications/app-case-clean/historical-comparison", headers=auth_headers)
    assert res.status_code == 200
    report = res.json()
    assert report["institution_id"] == "inst-apex-01"
    assert report["baseline_academic_year"] == "2025-2026"
    assert len(report["deltas"]) >= 3
    # Check that legal name and intake were evaluated
    keys = [d["field_key"] for d in report["deltas"]]
    assert "institution_name" in keys
    assert "total_intake" in keys


def test_api_snapshots_list():
    res = client.get("/api/v1/historical/snapshots/inst-apex-01", headers=auth_headers)
    assert res.status_code == 200
    snaps = res.json()
    assert len(snaps) >= 1
    assert snaps[0]["academic_year"] == "2025-2026"
    assert snaps[0]["parameters"]["total_intake"] == 180
