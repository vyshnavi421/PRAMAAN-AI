"""
PRAMAAN-AI Canonical Benchmark Fixtures & Ground-Truth Specifications
15 synthetic application bundles covering all AICTE scrutiny conditions, edge cases,
and deliberate false-positive traps.
All data is strictly synthetic and visibly marked DEMO / SIMULATED.
"""
from typing import List, Dict, Any
from datetime import date
import hashlib

from app.models.enums import (
    FindingStatus,
    Severity,
    DocumentType,
    DocumentVerificationStatus,
    ExtractionQuality,
    ApplicationCategory,
)
from app.models.domain import (
    ApplicationInput,
    Document,
    ExtractedField,
    FieldProvenance,
    InstitutionalReferenceRecord,
)
from app.services.duplicate_detector import DuplicateMatchType
from app.benchmark.models import (
    BenchmarkFixture,
    ExpectedField,
    ExpectedFinding,
    ExpectedVerification,
    ExpectedDuplicate,
)


def _sha256(val: str) -> str:
    return hashlib.sha256(val.encode("utf-8")).hexdigest()


def get_canonical_benchmark_fixtures() -> List[BenchmarkFixture]:
    """
    Returns the reproducible 15-bundle evaluation benchmark dataset.
    Fixed version 1.0.0, deterministic synthetic ground truth.
    """
    fixtures: List[BenchmarkFixture] = []

    # -------------------------------------------------------------------------
    # Bundle 01: Clean Compliant Application (All checks pass)
    # -------------------------------------------------------------------------
    app1 = ApplicationInput(
        application_id="bm-01-clean",
        institution_id="inst-apex-01",
        application_number="APP-2026-BM-01",
        academic_year="2026-2027",
        submission_date=date(2026, 4, 10),
        submission_cutoff_date=date(2026, 6, 30),
        category=ApplicationCategory.EXTENSION_OF_APPROVAL,
        declared_data={
            "institution_name": "Apex Institute of Technology",
            "total_intake": 180,
            "builtup_area_sqm": 12500.0,
            "land_area_acres": 7.5,
        },
        documents=[
            Document(
                id="bm-doc-01-affidavit",
                application_id="bm-01-clean",
                document_type=DocumentType.AFFIDAVIT_GENERAL,
                original_filename="affidavit_clean.pdf",
                storage_key="storage/bm-01-clean/affidavit.pdf",
                file_size_bytes=1048576,
                sha256_hash=_sha256("bm-01-clean-affidavit-bytes"),
                page_count=2,
                verification_status=DocumentVerificationStatus.VERIFIED,
                extracted_fields=[
                    ExtractedField(
                        field_key="institution_name",
                        field_value="Apex Institute of Technology",
                        raw_value="Apex Institute of Technology",
                        confidence=0.98,
                        provenance=FieldProvenance(page_number=1, quality_label=ExtractionQuality.HIGH),
                    ),
                    ExtractedField(
                        field_key="total_intake",
                        field_value="180",
                        raw_value="180 seats",
                        confidence=0.97,
                        provenance=FieldProvenance(page_number=1, quality_label=ExtractionQuality.HIGH),
                    ),
                ],
            ),
            Document(
                id="bm-doc-01-fire",
                application_id="bm-01-clean",
                document_type=DocumentType.FIRE_SAFETY_NOC,
                original_filename="fire_clean.pdf",
                storage_key="storage/bm-01-clean/fire.pdf",
                file_size_bytes=1048576,
                sha256_hash=_sha256("bm-01-clean-fire-bytes"),
                page_count=2,
                verification_status=DocumentVerificationStatus.VERIFIED,
                extracted_fields=[
                    ExtractedField(
                        field_key="noc_issue_date",
                        field_value="2026-01-15",
                        raw_value="15/01/2026",
                        confidence=0.96,
                        provenance=FieldProvenance(page_number=1, quality_label=ExtractionQuality.HIGH),
                    ),
                    ExtractedField(
                        field_key="noc_expiry_date",
                        field_value="2027-01-14",
                        raw_value="14/01/2027",
                        confidence=0.97,
                        provenance=FieldProvenance(page_number=1, quality_label=ExtractionQuality.HIGH),
                    ),
                ],
            ),
            Document(
                id="bm-doc-01-architect",
                application_id="bm-01-clean",
                document_type=DocumentType.BUILDING_PLAN_ARCHITECT,
                original_filename="architect_clean.pdf",
                storage_key="storage/bm-01-clean/architect.pdf",
                file_size_bytes=1048576,
                sha256_hash=_sha256("bm-01-clean-architect-bytes"),
                page_count=3,
                verification_status=DocumentVerificationStatus.VERIFIED,
                extracted_fields=[
                    ExtractedField(
                        field_key="builtup_area_sqm",
                        field_value="12500.0",
                        raw_value="12,500 sq.m",
                        confidence=0.96,
                        provenance=FieldProvenance(page_number=2, quality_label=ExtractionQuality.HIGH),
                    ),
                    ExtractedField(
                        field_key="certified_intake_capacity",
                        field_value="180",
                        raw_value="180 student capacity",
                        confidence=0.98,
                        provenance=FieldProvenance(page_number=1, quality_label=ExtractionQuality.HIGH),
                    ),
                ],
            ),
            Document(
                id="bm-doc-01-gov",
                application_id="bm-01-clean",
                document_type=DocumentType.GOVERNING_BODY_RESOLUTION,
                original_filename="gov_clean.pdf",
                storage_key="storage/bm-01-clean/gov.pdf",
                file_size_bytes=1048576,
                sha256_hash=_sha256("bm-01-clean-gov-bytes"),
                page_count=1,
                verification_status=DocumentVerificationStatus.VERIFIED,
                extracted_fields=[
                    ExtractedField(
                        field_key="proposed_intake",
                        field_value="180",
                        raw_value="Resolved that proposed intake for academic year 2026-2027 is 180 seats.",
                        confidence=0.98,
                        provenance=FieldProvenance(page_number=1, quality_label=ExtractionQuality.HIGH),
                    ),
                ],
            ),
        ],
        reference_record=InstitutionalReferenceRecord(
            institution_id="inst-apex-01",
            aicte_permanent_id="1-3324589110",
            legal_name="Apex Institute of Technology",
            academic_year="2025-2026",
            approved_intake=180,
            approved_builtup_area_sqm=12000.0,
            is_synthetic=True,
        ),
    )
    fixtures.append(
        BenchmarkFixture(
            bundle_id="BM-01-CLEAN",
            name="Clean Compliant Application",
            category="CLEAN",
            description="All 4 mandatory documents present, valid dates, consistent intake, compliant area.",
            application=app1,
            ground_truth_fields={
                "bm-doc-01-affidavit": [
                    ExpectedField(field_key="institution_name", expected_value="Apex Institute of Technology"),
                    ExpectedField(field_key="total_intake", expected_value="180"),
                ],
                "bm-doc-01-fire": [
                    ExpectedField(field_key="noc_expiry_date", expected_value="2027-01-14"),
                ],
                "bm-doc-01-architect": [
                    ExpectedField(field_key="builtup_area_sqm", expected_value="12500.0"),
                    ExpectedField(field_key="certified_intake_capacity", expected_value="180"),
                ],
            },
            ground_truth_rules={
                "RULE-APH-DOC-001": ExpectedFinding(rule_id="RULE-APH-DOC-001", expected_status=FindingStatus.COMPLIANT),
                "RULE-APH-FLD-002": ExpectedFinding(rule_id="RULE-APH-FLD-002", expected_status=FindingStatus.COMPLIANT),
                "RULE-APH-EXP-003": ExpectedFinding(rule_id="RULE-APH-EXP-003", expected_status=FindingStatus.COMPLIANT),
                "RULE-DATE-REL-004": ExpectedFinding(rule_id="RULE-DATE-REL-004", expected_status=FindingStatus.COMPLIANT),
                "RULE-CROSS-DOC-005": ExpectedFinding(rule_id="RULE-CROSS-DOC-005", expected_status=FindingStatus.COMPLIANT),
                "RULE-AICTE-HIST-006": ExpectedFinding(rule_id="RULE-AICTE-HIST-006", expected_status=FindingStatus.COMPLIANT),
                "RULE-APH-NAME-009": ExpectedFinding(rule_id="RULE-APH-NAME-009", expected_status=FindingStatus.COMPLIANT),
            },
            ground_truth_verifications={
                "bm-doc-01-fire": ExpectedVerification(
                    document_type=DocumentType.FIRE_SAFETY_NOC,
                    expected_status=DocumentVerificationStatus.VERIFIED
                )
            },
            expected_coverage_complete=True,
            expected_overall_status="COMPLETE_COMPLIANT",
            is_false_positive_trap=False,
        )
    )

    # -------------------------------------------------------------------------
    # Bundle 02: Missing Mandatory Document (RULE-APH-DOC-001 Deficiency)
    # -------------------------------------------------------------------------
    app2 = app1.model_copy(deep=True)
    app2.application_id = "bm-02-missing-doc"
    app2.application_number = "APP-2026-BM-02"
    for d in app2.documents:
        d.id = f"bm-doc-02-{d.document_type.value.lower()}"
        d.sha256_hash = _sha256(f"bm-02-{d.document_type.value}")
    # Omit AFFIDAVIT_GENERAL
    app2.documents = [d for d in app2.documents if d.document_type != DocumentType.AFFIDAVIT_GENERAL]

    fixtures.append(
        BenchmarkFixture(
            bundle_id="BM-02-MISSING-DOC",
            name="Missing Mandatory Document (Affidavit Omitted)",
            category="DEFICIENCY_MISSING",
            description="General affidavit omitted; must trigger RULE-APH-DOC-001 deficiency.",
            application=app2,
            ground_truth_rules={
                "RULE-APH-DOC-001": ExpectedFinding(
                    rule_id="RULE-APH-DOC-001",
                    expected_status=FindingStatus.DEFICIENCY,
                    expected_phrase_in_reason="Missing mandatory document types: AFFIDAVIT_GENERAL"
                ),
            },
            expected_coverage_complete=True,
            expected_overall_status="COMPLETE_WITH_DEFICIENCIES",
            is_false_positive_trap=False,
        )
    )

    # -------------------------------------------------------------------------
    # Bundle 03: Missing Key Field (RULE-APH-FLD-002 Inconclusive)
    # -------------------------------------------------------------------------
    app3 = app1.model_copy(deep=True)
    app3.application_id = "bm-03-missing-field"
    app3.application_number = "APP-2026-BM-03"
    for d in app3.documents:
        d.id = f"bm-doc-03-{d.document_type.value.lower()}"
        d.sha256_hash = _sha256(f"bm-03-{d.document_type.value}")
        if d.document_type == DocumentType.FIRE_SAFETY_NOC:
            # Remove noc_expiry_date
            d.extracted_fields = [f for f in d.extracted_fields if f.field_key != "noc_expiry_date"]

    fixtures.append(
        BenchmarkFixture(
            bundle_id="BM-03-MISSING-FIELD",
            name="Missing Key Field in Fire Certificate",
            category="DEFICIENCY_MISSING",
            description=(
                "Fire NOC document is present but noc_expiry_date was not "
                "extracted; return INCONCLUSIVE and require manual review."
            ),
            application=app3,
            ground_truth_rules={
                "RULE-APH-FLD-002": ExpectedFinding(
                    rule_id="RULE-APH-FLD-002",
                    expected_status=FindingStatus.INCONCLUSIVE,
                    expected_phrase_in_reason="noc_expiry_date"
                ),
            },
            expected_coverage_complete=True,
            expected_overall_status="COMPLETE_COMPLIANT",
            is_false_positive_trap=False,
        )
    )

    # -------------------------------------------------------------------------
    # Bundle 04: Expired Document (RULE-APH-EXP-003 Deficiency & Adapter EXPIRED)
    # -------------------------------------------------------------------------
    app4 = app1.model_copy(deep=True)
    app4.application_id = "bm-04-expired-doc"
    app4.application_number = "APP-2026-BM-04"
    for d in app4.documents:
        d.id = f"bm-doc-04-{d.document_type.value.lower()}"
        d.sha256_hash = _sha256(f"bm-04-{d.document_type.value}")
        if d.document_type == DocumentType.FIRE_SAFETY_NOC:
            d.verification_status = DocumentVerificationStatus.EXPIRED
            for f in d.extracted_fields:
                if f.field_key == "noc_issue_date":
                    f.field_value = "2023-01-01"
                    f.raw_value = "01/01/2023"
                elif f.field_key == "noc_expiry_date":
                    f.field_value = "2023-12-31"
                    f.raw_value = "31/12/2023"

    fixtures.append(
        BenchmarkFixture(
            bundle_id="BM-04-EXPIRED-DOC",
            name="Expired Fire Safety Certificate",
            category="DEFICIENCY_EXPIRED",
            description="Fire NOC expired in 2023 before submission cutoff; triggers RULE-APH-EXP-003 deficiency.",
            application=app4,
            ground_truth_rules={
                "RULE-APH-EXP-003": ExpectedFinding(
                    rule_id="RULE-APH-EXP-003",
                    expected_status=FindingStatus.DEFICIENCY,
                    expected_phrase_in_reason="expired on 2023-12-31"
                ),
                "RULE-DATE-REL-004": ExpectedFinding(
                    rule_id="RULE-DATE-REL-004",
                    expected_status=FindingStatus.COMPLIANT
                ),
            },
            ground_truth_verifications={
                "bm-doc-04-fire_safety_noc": ExpectedVerification(
                    document_type=DocumentType.FIRE_SAFETY_NOC,
                    expected_status=DocumentVerificationStatus.EXPIRED
                )
            },
            expected_coverage_complete=True,
            expected_overall_status="COMPLETE_WITH_DEFICIENCIES",
            is_false_positive_trap=False,
        )
    )

    # -------------------------------------------------------------------------
    # Bundle 05: Conflicting Cross-Document Fields (RULE-CROSS-DOC-005 Deficiency)
    # -------------------------------------------------------------------------
    app5 = app1.model_copy(deep=True)
    app5.application_id = "bm-05-conflicting-fields"
    app5.application_number = "APP-2026-BM-05"
    app5.declared_data["total_intake"] = 180  # Keeps historical check compliant
    for d in app5.documents:
        d.id = f"bm-doc-05-{d.document_type.value.lower()}"
        d.sha256_hash = _sha256(f"bm-05-{d.document_type.value}")
        if d.document_type == DocumentType.BUILDING_PLAN_ARCHITECT:
            for f in d.extracted_fields:
                if f.field_key == "certified_intake_capacity":
                    f.field_value = "180"
        elif d.document_type == DocumentType.GOVERNING_BODY_RESOLUTION:
            for f in d.extracted_fields:
                if f.field_key == "proposed_intake":
                    f.field_value = "240"
                    f.raw_value = "240 seats"

    fixtures.append(
        BenchmarkFixture(
            bundle_id="BM-05-CONFLICTING-FIELDS",
            name="Cross-Document Intake Discrepancy",
            category="ANOMALY_MISMATCH",
            description="Architect certifies 180 seats, resolution specifies 240 seats; triggers RULE-CROSS-DOC-005 deficiency.",
            application=app5,
            ground_truth_rules={
                "RULE-CROSS-DOC-005": ExpectedFinding(
                    rule_id="RULE-CROSS-DOC-005",
                    expected_status=FindingStatus.DEFICIENCY,
                    expected_phrase_in_reason="Cross-document value mismatch"
                ),
                "RULE-AICTE-HIST-006": ExpectedFinding(
                    rule_id="RULE-AICTE-HIST-006",
                    expected_status=FindingStatus.COMPLIANT
                ),
            },
            expected_coverage_complete=True,
            expected_overall_status="COMPLETE_WITH_DEFICIENCIES",
            is_false_positive_trap=False,
        )
    )

    # -------------------------------------------------------------------------
    # Bundle 06: Difference from Prior Baseline (RULE-AICTE-HIST-006 Anomaly)
    # -------------------------------------------------------------------------
    app6 = app1.model_copy(deep=True)
    app6.application_id = "bm-06-historical-diff"
    app6.application_number = "APP-2026-BM-06"
    app6.declared_data["total_intake"] = 240
    for d in app6.documents:
        d.id = f"bm-doc-06-{d.document_type.value.lower()}"
        d.sha256_hash = _sha256(f"bm-06-{d.document_type.value}")
        if d.document_type == DocumentType.BUILDING_PLAN_ARCHITECT:
            for f in d.extracted_fields:
                if f.field_key == "certified_intake_capacity":
                    f.field_value = "240"
        elif d.document_type == DocumentType.GOVERNING_BODY_RESOLUTION:
            for f in d.extracted_fields:
                if f.field_key == "proposed_intake":
                    f.field_value = "240"

    fixtures.append(
        BenchmarkFixture(
            bundle_id="BM-06-HISTORICAL-DIFF",
            name="Unsanctioned Intake Expansion vs AICTE Baseline",
            category="HISTORICAL_CHANGE",
            description="Proposed intake (240) exceeds AICTE approved historical baseline (180) in EoA without sanction order.",
            application=app6,
            ground_truth_rules={
                "RULE-AICTE-HIST-006": ExpectedFinding(
                    rule_id="RULE-AICTE-HIST-006",
                    expected_status=FindingStatus.ANOMALY_SIGNAL,
                    expected_phrase_in_reason="exceeds prior approved AICTE baseline"
                ),
            },
            expected_coverage_complete=True,
            expected_overall_status="COMPLETE_WITH_ANOMALIES",
            is_false_positive_trap=False,
        )
    )

    # -------------------------------------------------------------------------
    # Bundle 07: Exact Duplicate File Reuse Across Institutions
    # -------------------------------------------------------------------------
    app7 = app1.model_copy(deep=True)
    app7.application_id = "bm-07-exact-duplicate"
    app7.institution_id = "inst-somaiya-03"
    app7.application_number = "APP-2026-BM-07"
    app7.declared_data["institution_name"] = "Somaiya College of Engineering"
    for d in app7.documents:
        d.id = f"bm-doc-07-{d.document_type.value.lower()}"
        if d.document_type == DocumentType.AFFIDAVIT_GENERAL:
            # Deliberately identical byte stream to bm-01-clean affidavit
            d.sha256_hash = _sha256("bm-01-clean-affidavit-bytes")
        else:
            d.sha256_hash = _sha256(f"bm-07-{d.document_type.value}")

    fixtures.append(
        BenchmarkFixture(
            bundle_id="BM-07-EXACT-DUPLICATE",
            name="Exact Binary Document Reuse Across Institutions",
            category="DUPLICATE_EXACT",
            description="Identical SHA-256 hash across two institutions; triggers duplicate detection without claiming fraud.",
            application=app7,
            ground_truth_rules={
                "RULE-APH-REUSE-010": ExpectedFinding(
                    rule_id="RULE-APH-REUSE-010",
                    expected_status=FindingStatus.ANOMALY_SIGNAL,
                    expected_phrase_in_reason="Exact file match"
                ),
            },
            ground_truth_duplicates=[
                ExpectedDuplicate(
                    source_document_id="bm-doc-07-affidavit_general",
                    target_application_id="bm-01-clean",
                    expected_match_type=DuplicateMatchType.EXACT_BINARY_MATCH,
                    min_similarity=1.0
                )
            ],
            expected_coverage_complete=True,
            expected_overall_status="COMPLETE_WITH_ANOMALIES",
            is_false_positive_trap=False,
        )
    )

    # -------------------------------------------------------------------------
    # Bundle 08: Approximate Duplicate / Generic Boilerplate Template
    # -------------------------------------------------------------------------
    app8 = app1.model_copy(deep=True)
    app8.application_id = "bm-08-approx-duplicate"
    app8.institution_id = "inst-city-02"
    app8.application_number = "APP-2026-BM-08"
    app8.declared_data["institution_name"] = "City College of Engineering"
    for d in app8.documents:
        d.id = f"bm-doc-08-{d.document_type.value.lower()}"
        d.sha256_hash = _sha256(f"bm-08-{d.document_type.value}")
        if d.document_type == DocumentType.GOVERNING_BODY_RESOLUTION:
            # Text contains high token similarity with bm-01-clean resolution
            d.extracted_fields = [
                ExtractedField(
                    field_key="proposed_intake",
                    field_value="180",
                    raw_value="Resolved that proposed intake for academic year 2026-2027 is 180 seats.",
                    confidence=0.98,
                    provenance=FieldProvenance(page_number=1, quality_label=ExtractionQuality.HIGH)
                )
            ]

    fixtures.append(
        BenchmarkFixture(
            bundle_id="BM-08-APPROX-DUPLICATE",
            name="Approximate Boilerplate Template Recognition",
            category="DUPLICATE_APPROX",
            description="Standard statutory template overlap; recognized as legitimate boilerplate template.",
            application=app8,
            ground_truth_duplicates=[
                ExpectedDuplicate(
                    source_document_id="bm-doc-08-governing_body_resolution",
                    target_application_id="bm-01-clean",
                    expected_match_type=DuplicateMatchType.GENERIC_TEMPLATE,
                    min_similarity=0.70
                )
            ],
            expected_coverage_complete=True,
            expected_overall_status="COMPLETE_COMPLIANT",
            is_false_positive_trap=False,
        )
    )

    # -------------------------------------------------------------------------
    # Bundle 09: Legitimate Name Variation (FALSE-POSITIVE TRAP)
    # -------------------------------------------------------------------------
    app9 = app1.model_copy(deep=True)
    app9.application_id = "bm-09-name-variation"
    app9.application_number = "APP-2026-BM-09"
    for d in app9.documents:
        d.id = f"bm-doc-09-{d.document_type.value.lower()}"
        d.sha256_hash = _sha256(f"bm-09-{d.document_type.value}")
        if d.document_type == DocumentType.AFFIDAVIT_GENERAL:
            for f in d.extracted_fields:
                if f.field_key == "institution_name":
                    f.field_value = "Apex Inst. of Tech."
                    f.raw_value = "Apex Inst. of Tech."

    fixtures.append(
        BenchmarkFixture(
            bundle_id="BM-09-NAME-VARIATION",
            name="Legitimate Name Abbreviation Variation",
            category="LEGITIMATE_VARIATION",
            description="Abbreviation 'Apex Inst. of Tech.' vs declared 'Apex Institute of Technology'. MUST pass without false alarm.",
            application=app9,
            ground_truth_rules={
                "RULE-APH-NAME-009": ExpectedFinding(
                    rule_id="RULE-APH-NAME-009",
                    expected_status=FindingStatus.COMPLIANT,
                    expected_phrase_in_reason="Legitimate abbreviation/token match"
                ),
            },
            expected_coverage_complete=True,
            expected_overall_status="COMPLETE_COMPLIANT",
            is_false_positive_trap=True,
            trap_explanation="Naive string matching fails this as a discrepancy. Fuzzy matcher must recognize abbreviation and pass."
        )
    )

    # -------------------------------------------------------------------------
    # Bundle 10: Poor Scan and OCR Uncertainty (Confidence < 0.65 threshold)
    # -------------------------------------------------------------------------
    app10 = app1.model_copy(deep=True)
    app10.application_id = "bm-10-poor-scan"
    app10.application_number = "APP-2026-BM-10"
    for d in app10.documents:
        d.id = f"bm-doc-10-{d.document_type.value.lower()}"
        d.sha256_hash = _sha256(f"bm-10-{d.document_type.value}")
        if d.document_type == DocumentType.FIRE_SAFETY_NOC:
            for f in d.extracted_fields:
                f.confidence = 0.42
                f.provenance.quality_label = ExtractionQuality.LOW_CONFIDENCE

    fixtures.append(
        BenchmarkFixture(
            bundle_id="BM-10-POOR-SCAN",
            name="Degraded Scan & OCR Uncertainty",
            category="LOW_OCR_QUALITY",
            description="Fire NOC OCR confidence 0.42 < 0.65. System must abstain and route to manual review.",
            application=app10,
            ground_truth_rules={
                "RULE-APH-FLD-002": ExpectedFinding(
                    rule_id="RULE-APH-FLD-002",
                    expected_status=FindingStatus.INCONCLUSIVE,
                    expected_phrase_in_reason="uncertain (confidence: 0.42"
                ),
            },
            expected_coverage_complete=True,
            expected_overall_status="COMPLETE_COMPLIANT",
            is_false_positive_trap=False,
        )
    )

    # -------------------------------------------------------------------------
    # Bundle 11: Invalid/Missing Reference Data (First-Time Applicant)
    # -------------------------------------------------------------------------
    app11 = app1.model_copy(deep=True)
    app11.application_id = "bm-11-missing-ref"
    app11.application_number = "APP-2026-BM-11"
    app11.category = ApplicationCategory.NEW_INSTITUTION
    app11.reference_record = None  # No prior AICTE record exists
    for d in app11.documents:
        d.id = f"bm-doc-11-{d.document_type.value.lower()}"
        d.sha256_hash = _sha256(f"bm-11-{d.document_type.value}")
    # Add LAND_CONVERSION_ORDER so category check RULE-CAT-SPEC-007 passes
    app11.documents.append(
        Document(
            id="bm-doc-11-land-conversion",
            application_id="bm-11-missing-ref",
            document_type=DocumentType.LAND_CONVERSION_ORDER,
            original_filename="land_conversion_order.pdf",
            storage_key="storage/bm-11-missing-ref/land_conv.pdf",
            file_size_bytes=1048576,
            sha256_hash=_sha256("bm-11-land-conv"),
            page_count=2,
            verification_status=DocumentVerificationStatus.VERIFIED,
            extracted_fields=[
                ExtractedField(
                    field_key="land_area_acres",
                    field_value="7.5",
                    raw_value="7.5 acres",
                    confidence=0.98,
                    provenance=FieldProvenance(page_number=1, quality_label=ExtractionQuality.HIGH)
                )
            ]
        )
    )

    fixtures.append(
        BenchmarkFixture(
            bundle_id="BM-11-MISSING-REF",
            name="First-Time Applicant Without Prior Historical Baseline",
            category="MISSING_REFERENCE",
            description="New institution application with no prior reference record; RULE-AICTE-HIST-006 abstains with NOT_APPLICABLE.",
            application=app11,
            ground_truth_rules={
                "RULE-AICTE-HIST-006": ExpectedFinding(
                    rule_id="RULE-AICTE-HIST-006",
                    expected_status=FindingStatus.NOT_APPLICABLE,
                    expected_phrase_in_reason="not applicable to application category"
                ),
                "RULE-CAT-SPEC-007": ExpectedFinding(
                    rule_id="RULE-CAT-SPEC-007",
                    expected_status=FindingStatus.COMPLIANT
                ),
            },
            expected_coverage_complete=True,
            expected_overall_status="COMPLETE_COMPLIANT",
            is_false_positive_trap=False,
        )
    )

    # -------------------------------------------------------------------------
    # Bundle 12: Source Gateway Timeout / Unavailable (503 Simulation)
    # -------------------------------------------------------------------------
    app12 = app1.model_copy(deep=True)
    app12.application_id = "bm-12-source-timeout"
    app12.application_number = "APP-2026-BM-12"
    for d in app12.documents:
        d.id = f"bm-doc-12-{d.document_type.value.lower()}"
        d.sha256_hash = _sha256(f"bm-12-{d.document_type.value}")
        if d.document_type == DocumentType.FIRE_SAFETY_NOC:
            d.verification_status = DocumentVerificationStatus.SOURCE_UNAVAILABLE

    fixtures.append(
        BenchmarkFixture(
            bundle_id="BM-12-SOURCE-TIMEOUT",
            name="Issuing Authority Gateway Timeout (503)",
            category="SOURCE_UNAVAILABLE",
            description="External registry outage; adapter records SOURCE_UNAVAILABLE without failing compliance.",
            application=app12,
            ground_truth_verifications={
                "bm-doc-12-fire_safety_noc": ExpectedVerification(
                    document_type=DocumentType.FIRE_SAFETY_NOC,
                    expected_status=DocumentVerificationStatus.SOURCE_UNAVAILABLE
                )
            },
            expected_coverage_complete=True,
            expected_overall_status="COMPLETE_COMPLIANT",
            is_false_positive_trap=False,
        )
    )

    # -------------------------------------------------------------------------
    # Bundle 13: Non-Applicable Rule Evaluation
    # -------------------------------------------------------------------------
    app13 = app1.model_copy(deep=True)
    app13.application_id = "bm-13-non-applicable"
    app13.application_number = "APP-2026-BM-13"
    app13.category = ApplicationCategory.EXTENSION_OF_APPROVAL
    for d in app13.documents:
        d.id = f"bm-doc-13-{d.document_type.value.lower()}"
        d.sha256_hash = _sha256(f"bm-13-{d.document_type.value}")

    fixtures.append(
        BenchmarkFixture(
            bundle_id="BM-13-NON-APPLICABLE",
            name="Category-Specific Rule Inapplicability",
            category="NON_APPLICABLE_RULE",
            description="RULE-CAT-SPEC-007 is applicable only to NEW_INSTITUTION; must evaluate cleanly as NOT_APPLICABLE.",
            application=app13,
            ground_truth_rules={
                "RULE-CAT-SPEC-007": ExpectedFinding(
                    rule_id="RULE-CAT-SPEC-007",
                    expected_status=FindingStatus.NOT_APPLICABLE,
                    expected_phrase_in_reason="not applicable to application category"
                ),
            },
            expected_coverage_complete=True,
            expected_overall_status="COMPLETE_COMPLIANT",
            is_false_positive_trap=False,
        )
    )

    # -------------------------------------------------------------------------
    # Bundle 14: Deliberately Omitted Check (Coverage Guarantee Verification)
    # -------------------------------------------------------------------------
    app14 = app1.model_copy(deep=True)
    app14.application_id = "bm-14-omitted-check"
    app14.application_number = "APP-2026-BM-14"
    for d in app14.documents:
        d.id = f"bm-doc-14-{d.document_type.value.lower()}"
        d.sha256_hash = _sha256(f"bm-14-{d.document_type.value}")

    fixtures.append(
        BenchmarkFixture(
            bundle_id="BM-14-OMITTED-CHECK",
            name="Deliberately Omitted Check Result (Coverage Auditor Trap)",
            category="OMITTED_CHECK_FAILURE",
            description="RULE-APH-EXP-003 is omitted from execution; CoverageAuditor must catch omission and force INCOMPLETE status.",
            application=app14,
            injection_flags={"force_omit_check_id": "RULE-APH-EXP-003"},
            expected_coverage_complete=False,
            expected_overall_status="INCOMPLETE",
            is_false_positive_trap=False,
        )
    )

    # -------------------------------------------------------------------------
    # Bundle 15: Synthetic Altered-Document Indicator (Test Artifact)
    # -------------------------------------------------------------------------
    app15 = app1.model_copy(deep=True)
    app15.application_id = "bm-15-altered-artifact"
    app15.application_number = "APP-2026-BM-15"
    for d in app15.documents:
        d.id = f"bm-doc-15-{d.document_type.value.lower()}"
        d.sha256_hash = _sha256(f"bm-15-{d.document_type.value}")
        if d.document_type == DocumentType.FIRE_SAFETY_NOC:
            d.original_filename = "fire_safety_noc_SYNTHETIC_TEST_ARTIFACT_ALTERED.pdf"
            d.extracted_fields.append(
                ExtractedField(
                    field_key="test_artifact_marker",
                    field_value="DEMO_ALTERED_DOCUMENT_INDICATOR",
                    raw_value="[DEMO_TEST_ARTIFACT: Tampered Seal Simulation]",
                    confidence=0.99,
                    provenance=FieldProvenance(page_number=1, quality_label=ExtractionQuality.HIGH)
                )
            )

    fixtures.append(
        BenchmarkFixture(
            bundle_id="BM-15-ALTERED-ARTIFACT",
            name="Synthetic Altered-Document Indicator (Test Artifact)",
            category="ALTERED_DOCUMENT_ARTIFACT",
            description="File labeled visibly as synthetic test artifact; routes for manual review as advisory signal.",
            application=app15,
            expected_coverage_complete=True,
            expected_overall_status="COMPLETE_COMPLIANT",
            is_false_positive_trap=False,
        )
    )

    return fixtures
