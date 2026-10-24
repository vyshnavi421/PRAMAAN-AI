"""
PRAMAAN-AI Initial Rule Catalog
Implements the 8 foundational deterministic rules for the MVP.
Every rule cites either an authoritative AICTE Approval Process Handbook (APH) clause
or carries an explicit [DEMO_RULE] label.
"""
from typing import List, Optional
from datetime import date, datetime

from app.models.enums import (
    FindingStatus,
    Severity,
    RuleState,
    ApplicationCategory,
    DocumentType,
    ExtractionQuality,
    DocumentVerificationStatus,
)
from app.models.domain import ApplicationInput, Document, ExtractedField
from app.models.validation import Finding, FindingEvidence
from app.rules.base import BaseRule, RuleMetadata
from app.rules.fuzzy import compare_names

# ==============================================================================
# 1. Required Document Missing Rule
# ==============================================================================
class RequiredDocumentMissingRule(BaseRule):
    """
    Checks that all mandatory documents for an Extension of Approval (EoA) application are present.
    """
    def __init__(self, version: str = "1.0.0"):
        meta = RuleMetadata(
            rule_id="RULE-APH-DOC-001",
            rule_version=version,
            name="Mandatory Document Completeness Check",
            explanation=(
                "Verifies that all mandatory supporting documents prescribed by the AICTE APH "
                "for Extension of Approval are uploaded."
            ),
            applicable_categories=[
                ApplicationCategory.EXTENSION_OF_APPROVAL,
                ApplicationCategory.INCREASE_IN_INTAKE,
                ApplicationCategory.NEW_COURSE,
            ],
            effective_from=date(2024, 4, 1),
            effective_to=date(2027, 3, 31),
            required_document_types=[
                DocumentType.AFFIDAVIT_GENERAL,
                DocumentType.FIRE_SAFETY_NOC,
                DocumentType.BUILDING_PLAN_ARCHITECT,
            ],
            severity=Severity.DEFICIENCY,
            severity_rationale="Statutory requirement; incomplete dossiers cannot proceed to approval.",
            evidence_requirements=["List of uploaded document types"],
            reviewer_next_action="Issue deficiency memo requesting missing documents before scrutiny deadline.",
            source_citation="AICTE Approval Process Handbook (APH) 2024-2027, Chapter II, Clause 2.3 & Appendix 16",
            is_demo=False,
            state=RuleState.ACTIVE,
        )
        super().__init__(meta)

    def _evaluate_logic(self, application: ApplicationInput) -> Finding:
        uploaded_types = {doc.document_type for doc in application.documents}
        required_types = set(self.meta.required_document_types)
        missing = required_types - uploaded_types

        if missing:
            missing_names = sorted([t.value for t in missing])
            return Finding(
                rule_id=self.meta.rule_id,
                rule_version=self.meta.rule_version,
                rule_name=self.meta.name,
                clause_citation=self.meta.source_citation,
                is_demo=self.meta.is_demo,
                status=FindingStatus.DEFICIENCY,
                severity=self.meta.severity,
                reason=f"Mandatory document(s) missing from application dossier: {', '.join(missing_names)}.",
                recommended_action=self.meta.reviewer_next_action,
                evidence=[
                    FindingEvidence(
                        comparison_value=", ".join(missing_names),
                        comparison_source="Prescribed AICTE APH Appendix 16 Checklist"
                    )
                ]
            )

        return Finding(
            rule_id=self.meta.rule_id,
            rule_version=self.meta.rule_version,
            rule_name=self.meta.name,
            clause_citation=self.meta.source_citation,
            is_demo=self.meta.is_demo,
            status=FindingStatus.COMPLIANT,
            severity=Severity.OBSERVATION,
            reason="All mandatory supporting documents are present in the application dossier.",
            recommended_action="Proceed with document content scrutiny.",
            evidence=[
                FindingEvidence(
                    extracted_value=", ".join(sorted([t.value for t in uploaded_types])),
                    comparison_source="Application Document Inventory"
                )
            ]
        )


# ==============================================================================
# 2. Required Field Absent or Extraction Uncertain
# ==============================================================================
class RequiredFieldAbsentOrUncertainRule(BaseRule):
    """
    Verifies that a mandatory field is present on a document and meets quality confidence criteria.
    If absent or low confidence, abstains from a false pass and flags for review.
    """
    def __init__(self, version: str = "1.0.0"):
        meta = RuleMetadata(
            rule_id="RULE-APH-FLD-002",
            rule_version=version,
            name="Required Field Presence & OCR Quality Check",
            explanation=(
                "Validates that required certificate attributes (e.g. Fire NOC expiry date) "
                "were extracted with acceptable confidence and uncorrupted quality."
            ),
            applicable_categories=[
                ApplicationCategory.EXTENSION_OF_APPROVAL,
                ApplicationCategory.INCREASE_IN_INTAKE,
            ],
            effective_from=date(2024, 4, 1),
            effective_to=date(2027, 3, 31),
            required_document_types=[DocumentType.FIRE_SAFETY_NOC],
            required_field_keys=["noc_expiry_date"],
            severity=Severity.DEFICIENCY,
            severity_rationale="Absence or unreliability of critical compliance dates prevents validation.",
            evidence_requirements=["ExtractedField 'noc_expiry_date' on FIRE_SAFETY_NOC"],
            reviewer_next_action="Perform manual visual inspection of the certificate scan.",
            source_citation="AICTE Approval Process Handbook (APH) 2024-2027, Clause 4.2 & Appendix 16",
            is_demo=False,
            state=RuleState.ACTIVE,
        )
        super().__init__(meta)

    def _evaluate_logic(self, application: ApplicationInput) -> Finding:
        doc = application.get_document_by_type(DocumentType.FIRE_SAFETY_NOC)
        if not doc:
            return Finding(
                rule_id=self.meta.rule_id,
                rule_version=self.meta.rule_version,
                rule_name=self.meta.name,
                clause_citation=self.meta.source_citation,
                is_demo=self.meta.is_demo,
                status=FindingStatus.INCONCLUSIVE,
                severity=self.meta.severity,
                reason="Cannot evaluate required field: Fire Safety NOC document is not uploaded.",
                recommended_action="Upload Fire Safety NOC first.",
                evidence=[]
            )

        field = doc.get_field("noc_expiry_date")
        if not field or not field.field_value.strip():
            return Finding(
                rule_id=self.meta.rule_id,
                rule_version=self.meta.rule_version,
                rule_name=self.meta.name,
                clause_citation=self.meta.source_citation,
                is_demo=self.meta.is_demo,
                status=FindingStatus.DEFICIENCY,
                severity=self.meta.severity,
                reason="Required field 'noc_expiry_date' was not found in the Fire Safety NOC document.",
                recommended_action=self.meta.reviewer_next_action,
                evidence=[
                    FindingEvidence(
                        document_id=doc.id,
                        document_type=doc.document_type.value,
                        field_key="noc_expiry_date"
                    )
                ]
            )

        # Check extraction quality / confidence
        if field.confidence < 0.65 or field.provenance.quality_label in [
            ExtractionQuality.LOW_CONFIDENCE,
            ExtractionQuality.UNREADABLE
        ]:
            return Finding(
                rule_id=self.meta.rule_id,
                rule_version=self.meta.rule_version,
                rule_name=self.meta.name,
                clause_citation=self.meta.source_citation,
                is_demo=self.meta.is_demo,
                status=FindingStatus.INCONCLUSIVE,
                severity=Severity.ANOMALY_SIGNAL,
                reason=(
                    f"Extraction of 'noc_expiry_date' is uncertain (confidence: {field.confidence:.2f}, "
                    f"quality: {field.provenance.quality_label.value}). System abstains from automated pass."
                ),
                recommended_action="Manual visual verification required to confirm date on scan.",
                evidence=[
                    FindingEvidence(
                        document_id=doc.id,
                        document_type=doc.document_type.value,
                        field_key="noc_expiry_date",
                        extracted_value=field.raw_value,
                        page_number=field.provenance.page_number,
                        bounding_box=field.provenance.bounding_box
                    )
                ]
            )

        return Finding(
            rule_id=self.meta.rule_id,
            rule_version=self.meta.rule_version,
            rule_name=self.meta.name,
            clause_citation=self.meta.source_citation,
            is_demo=self.meta.is_demo,
            status=FindingStatus.COMPLIANT,
            severity=Severity.OBSERVATION,
            reason=f"Required field 'noc_expiry_date' successfully extracted with high confidence ({field.confidence:.2f}).",
            recommended_action="Proceed with validity date evaluation.",
            evidence=[
                FindingEvidence(
                    document_id=doc.id,
                    document_type=doc.document_type.value,
                    field_key="noc_expiry_date",
                    extracted_value=field.field_value,
                    page_number=field.provenance.page_number,
                    bounding_box=field.provenance.bounding_box
                )
            ]
        )


# ==============================================================================
# 3. Expiry / Validity Check with Configured Policy & Boundary Dates
# ==============================================================================
class DocumentExpiryValidityRule(BaseRule):
    """
    Validates certificate expiration against application submission cutoff date.
    Exact boundary test: expiry on the cutoff date is COMPLIANT.
    """
    def __init__(self, version: str = "1.0.0"):
        meta = RuleMetadata(
            rule_id="RULE-APH-EXP-003",
            rule_version=version,
            name="Certificate Expiry & Submission Cutoff Check",
            explanation=(
                "Validates that the Fire Safety NOC has not expired prior to the regulatory "
                "submission cutoff date for the academic year."
            ),
            applicable_categories=[
                ApplicationCategory.EXTENSION_OF_APPROVAL,
                ApplicationCategory.INCREASE_IN_INTAKE,
                ApplicationCategory.NEW_COURSE,
            ],
            effective_from=date(2024, 4, 1),
            effective_to=date(2027, 3, 31),
            required_document_types=[DocumentType.FIRE_SAFETY_NOC],
            required_field_keys=["noc_expiry_date"],
            severity=Severity.DEFICIENCY,
            severity_rationale="Operating an institution with an expired fire certificate violates safety norms.",
            evidence_requirements=["noc_expiry_date", "submission_cutoff_date"],
            reviewer_next_action="Require applicant to submit current renewed Fire NOC or renewal application receipt.",
            source_citation="AICTE Approval Process Handbook (APH) 2024-2027, Clause 4.2(b)",
            is_demo=False,
            state=RuleState.ACTIVE,
        )
        super().__init__(meta)

    def _evaluate_logic(self, application: ApplicationInput) -> Finding:
        doc = application.get_document_by_type(DocumentType.FIRE_SAFETY_NOC)
        if not doc:
            return Finding(
                rule_id=self.meta.rule_id,
                rule_version=self.meta.rule_version,
                rule_name=self.meta.name,
                clause_citation=self.meta.source_citation,
                is_demo=self.meta.is_demo,
                status=FindingStatus.INCONCLUSIVE,
                severity=self.meta.severity,
                reason="Cannot evaluate validity: Fire Safety NOC document is not uploaded.",
                recommended_action="Upload Fire Safety NOC.",
                evidence=[]
            )

        field = doc.get_field("noc_expiry_date")
        if not field:
            return Finding(
                rule_id=self.meta.rule_id,
                rule_version=self.meta.rule_version,
                rule_name=self.meta.name,
                clause_citation=self.meta.source_citation,
                is_demo=self.meta.is_demo,
                status=FindingStatus.INCONCLUSIVE,
                severity=self.meta.severity,
                reason="Field 'noc_expiry_date' missing from document; cannot verify validity.",
                recommended_action="Check extraction or re-enter expiry date.",
                evidence=[]
            )

        try:
            expiry_date = datetime.strptime(field.field_value, "%Y-%m-%d").date()
        except ValueError:
            return Finding(
                rule_id=self.meta.rule_id,
                rule_version=self.meta.rule_version,
                rule_name=self.meta.name,
                clause_citation=self.meta.source_citation,
                is_demo=self.meta.is_demo,
                status=FindingStatus.INCONCLUSIVE,
                severity=self.meta.severity,
                reason=f"Date format invalid or unparseable: '{field.field_value}'. Expected YYYY-MM-DD.",
                recommended_action="Verify date format manually.",
                evidence=[
                    FindingEvidence(
                        document_id=doc.id,
                        document_type=doc.document_type.value,
                        field_key="noc_expiry_date",
                        extracted_value=field.raw_value
                    )
                ]
            )

        cutoff = application.submission_cutoff_date
        evidence = [
            FindingEvidence(
                document_id=doc.id,
                document_type=doc.document_type.value,
                field_key="noc_expiry_date",
                extracted_value=str(expiry_date),
                page_number=field.provenance.page_number,
                bounding_box=field.provenance.bounding_box,
                comparison_value=str(cutoff),
                comparison_source="Application Academic Cutoff Date"
            )
        ]

        if expiry_date < cutoff:
            # Update document status explicitly
            doc.verification_status = DocumentVerificationStatus.EXPIRED
            return Finding(
                rule_id=self.meta.rule_id,
                rule_version=self.meta.rule_version,
                rule_name=self.meta.name,
                clause_citation=self.meta.source_citation,
                is_demo=self.meta.is_demo,
                status=FindingStatus.DEFICIENCY,
                severity=self.meta.severity,
                reason=f"Fire Safety NOC expired on {expiry_date}, which is prior to cutoff date {cutoff}.",
                recommended_action=self.meta.reviewer_next_action,
                evidence=evidence
            )

        # Boundary date: expiry_date >= cutoff is compliant
        return Finding(
            rule_id=self.meta.rule_id,
            rule_version=self.meta.rule_version,
            rule_name=self.meta.name,
            clause_citation=self.meta.source_citation,
            is_demo=self.meta.is_demo,
            status=FindingStatus.COMPLIANT,
            severity=Severity.OBSERVATION,
            reason=f"Fire Safety NOC is valid through {expiry_date} (meets cutoff {cutoff}).",
            recommended_action="No action required.",
            evidence=evidence
        )


# ==============================================================================
# 4. Invalid Date Relationship Check
# ==============================================================================
class InvalidDateRelationshipRule(BaseRule):
    """
    Temporal sanity check: issue_date must be <= expiry_date and <= submission_date.
    """
    def __init__(self, version: str = "1.0.0"):
        meta = RuleMetadata(
            rule_id="RULE-DATE-REL-004",
            rule_version=version,
            name="Certificate Date Relationship Consistency",
            explanation=(
                "Validates chronological consistency: issue date must precede or equal expiry date, "
                "and issue date cannot be in the future relative to submission date."
            ),
            applicable_categories=[
                ApplicationCategory.EXTENSION_OF_APPROVAL,
                ApplicationCategory.INCREASE_IN_INTAKE,
                ApplicationCategory.NEW_COURSE,
            ],
            effective_from=date(2024, 4, 1),
            effective_to=date(2027, 3, 31),
            required_document_types=[DocumentType.FIRE_SAFETY_NOC],
            required_field_keys=["noc_issue_date", "noc_expiry_date"],
            severity=Severity.ANOMALY_SIGNAL,
            severity_rationale="Anomalous date chronology is a strong indicator of scan alteration or clerical error.",
            evidence_requirements=["noc_issue_date", "noc_expiry_date", "application.submission_date"],
            reviewer_next_action="Inspect original document for date transposition or typographical error.",
            source_citation="[DEMO_RULE] PRAMAAN-AI Temporal Consistency Norms v1.0",
            is_demo=True,
            state=RuleState.ACTIVE,
        )
        super().__init__(meta)

    def _evaluate_logic(self, application: ApplicationInput) -> Finding:
        doc = application.get_document_by_type(DocumentType.FIRE_SAFETY_NOC)
        if not doc:
            return Finding(
                rule_id=self.meta.rule_id,
                rule_version=self.meta.rule_version,
                rule_name=self.meta.name,
                clause_citation=self.meta.source_citation,
                is_demo=self.meta.is_demo,
                status=FindingStatus.INCONCLUSIVE,
                severity=self.meta.severity,
                reason="Cannot check date relationship: Fire Safety NOC not found.",
                recommended_action="Upload Fire Safety NOC.",
                evidence=[]
            )

        issue_field = doc.get_field("noc_issue_date")
        expiry_field = doc.get_field("noc_expiry_date")

        if not issue_field or not expiry_field:
            return Finding(
                rule_id=self.meta.rule_id,
                rule_version=self.meta.rule_version,
                rule_name=self.meta.name,
                clause_citation=self.meta.source_citation,
                is_demo=self.meta.is_demo,
                status=FindingStatus.INCONCLUSIVE,
                severity=self.meta.severity,
                reason="Both 'noc_issue_date' and 'noc_expiry_date' are required to verify date relationship.",
                recommended_action="Extract missing dates.",
                evidence=[]
            )

        try:
            issue_date = datetime.strptime(issue_field.field_value, "%Y-%m-%d").date()
            expiry_date = datetime.strptime(expiry_field.field_value, "%Y-%m-%d").date()
        except ValueError:
            return Finding(
                rule_id=self.meta.rule_id,
                rule_version=self.meta.rule_version,
                rule_name=self.meta.name,
                clause_citation=self.meta.source_citation,
                is_demo=self.meta.is_demo,
                status=FindingStatus.INCONCLUSIVE,
                severity=self.meta.severity,
                reason="One or both dates could not be parsed into YYYY-MM-DD.",
                recommended_action="Verify raw date strings.",
                evidence=[]
            )

        evidence = [
            FindingEvidence(
                document_id=doc.id,
                field_key="noc_issue_date",
                extracted_value=str(issue_date),
                page_number=issue_field.provenance.page_number
            ),
            FindingEvidence(
                document_id=doc.id,
                field_key="noc_expiry_date",
                extracted_value=str(expiry_date),
                page_number=expiry_field.provenance.page_number
            )
        ]

        if issue_date > expiry_date:
            return Finding(
                rule_id=self.meta.rule_id,
                rule_version=self.meta.rule_version,
                rule_name=self.meta.name,
                clause_citation=self.meta.source_citation,
                is_demo=self.meta.is_demo,
                status=FindingStatus.ANOMALY_SIGNAL,
                severity=self.meta.severity,
                reason=f"Chronological anomaly: Issue date ({issue_date}) is after expiry date ({expiry_date}).",
                recommended_action=self.meta.reviewer_next_action,
                evidence=evidence
            )

        if issue_date > application.submission_date:
            return Finding(
                rule_id=self.meta.rule_id,
                rule_version=self.meta.rule_version,
                rule_name=self.meta.name,
                clause_citation=self.meta.source_citation,
                is_demo=self.meta.is_demo,
                status=FindingStatus.ANOMALY_SIGNAL,
                severity=self.meta.severity,
                reason=(
                    f"Future issue date anomaly: Issue date ({issue_date}) is after application "
                    f"submission date ({application.submission_date})."
                ),
                recommended_action=self.meta.reviewer_next_action,
                evidence=evidence
            )

        return Finding(
            rule_id=self.meta.rule_id,
            rule_version=self.meta.rule_version,
            rule_name=self.meta.name,
            clause_citation=self.meta.source_citation,
            is_demo=self.meta.is_demo,
            status=FindingStatus.COMPLIANT,
            severity=Severity.OBSERVATION,
            reason=f"Date relationship is chronologically consistent (Issued: {issue_date}, Expires: {expiry_date}).",
            recommended_action="No action required.",
            evidence=evidence
        )


# ==============================================================================
# 5. Cross-Document Value Mismatch Check
# ==============================================================================
class CrossDocumentMismatchRule(BaseRule):
    """
    Compares declared intake across Building Plan (Architect Certificate) and Governing Body Resolution.
    """
    def __init__(self, version: str = "1.0.0"):
        meta = RuleMetadata(
            rule_id="RULE-CROSS-DOC-005",
            rule_version=version,
            name="Cross-Document Intake Consistency Check",
            explanation=(
                "Validates that the intake capacity certified by the registered Architect "
                "matches the proposed intake approved in the Governing Body Resolution."
            ),
            applicable_categories=[
                ApplicationCategory.EXTENSION_OF_APPROVAL,
                ApplicationCategory.INCREASE_IN_INTAKE,
            ],
            effective_from=date(2024, 4, 1),
            effective_to=date(2027, 3, 31),
            required_document_types=[
                DocumentType.BUILDING_PLAN_ARCHITECT,
                DocumentType.GOVERNING_BODY_RESOLUTION,
            ],
            required_field_keys=["certified_intake_capacity", "proposed_intake"],
            severity=Severity.DEFICIENCY,
            severity_rationale="Inconsistent capacity claims indicate unaligned governance approvals or space deficits.",
            evidence_requirements=["Architect Certificate intake", "Governing Body Resolution intake"],
            reviewer_next_action="Reconcile contradictory capacity figures with applicant.",
            source_citation="AICTE Approval Process Handbook (APH) 2024-2027, Clause 3.1 & Table 4.1",
            is_demo=False,
            state=RuleState.ACTIVE,
        )
        super().__init__(meta)

    def _evaluate_logic(self, application: ApplicationInput) -> Finding:
        doc_arch = application.get_document_by_type(DocumentType.BUILDING_PLAN_ARCHITECT)
        doc_gov = application.get_document_by_type(DocumentType.GOVERNING_BODY_RESOLUTION)

        if not doc_arch or not doc_gov:
            missing_docs = []
            if not doc_arch:
                missing_docs.append(DocumentType.BUILDING_PLAN_ARCHITECT.value)
            if not doc_gov:
                missing_docs.append(DocumentType.GOVERNING_BODY_RESOLUTION.value)
            return Finding(
                rule_id=self.meta.rule_id,
                rule_version=self.meta.rule_version,
                rule_name=self.meta.name,
                clause_citation=self.meta.source_citation,
                is_demo=self.meta.is_demo,
                status=FindingStatus.INCONCLUSIVE,
                severity=self.meta.severity,
                reason=f"Cannot execute cross-document check: Missing document(s): {', '.join(missing_docs)}.",
                recommended_action="Upload missing documents.",
                evidence=[]
            )

        f_arch = doc_arch.get_field("certified_intake_capacity")
        f_gov = doc_gov.get_field("proposed_intake")

        if not f_arch or not f_gov:
            missing_fields = []
            if not f_arch:
                missing_fields.append("certified_intake_capacity (on Building Plan)")
            if not f_gov:
                missing_fields.append("proposed_intake (on Governing Body Resolution)")
            return Finding(
                rule_id=self.meta.rule_id,
                rule_version=self.meta.rule_version,
                rule_name=self.meta.name,
                clause_citation=self.meta.source_citation,
                is_demo=self.meta.is_demo,
                status=FindingStatus.INCONCLUSIVE,
                severity=self.meta.severity,
                reason=f"Required fields missing for cross-document comparison: {', '.join(missing_fields)}.",
                recommended_action="Ensure both certificates have legible intake capacity figures.",
                evidence=[]
            )

        evidence = [
            FindingEvidence(
                document_id=doc_arch.id,
                document_type=doc_arch.document_type.value,
                field_key="certified_intake_capacity",
                extracted_value=f_arch.field_value,
                page_number=f_arch.provenance.page_number,
                bounding_box=f_arch.provenance.bounding_box,
                comparison_source="Architect Building Plan Certificate"
            ),
            FindingEvidence(
                document_id=doc_gov.id,
                document_type=doc_gov.document_type.value,
                field_key="proposed_intake",
                extracted_value=f_gov.field_value,
                page_number=f_gov.provenance.page_number,
                bounding_box=f_gov.provenance.bounding_box,
                comparison_source="Governing Body Resolution"
            )
        ]

        if f_arch.field_value.strip() != f_gov.field_value.strip():
            return Finding(
                rule_id=self.meta.rule_id,
                rule_version=self.meta.rule_version,
                rule_name=self.meta.name,
                clause_citation=self.meta.source_citation,
                is_demo=self.meta.is_demo,
                status=FindingStatus.DEFICIENCY,
                severity=self.meta.severity,
                reason=(
                    f"Cross-document value mismatch: Building Plan certifies intake of "
                    f"'{f_arch.field_value}', but Governing Body Resolution specifies '{f_gov.field_value}'."
                ),
                recommended_action=self.meta.reviewer_next_action,
                evidence=evidence
            )

        return Finding(
            rule_id=self.meta.rule_id,
            rule_version=self.meta.rule_version,
            rule_name=self.meta.name,
            clause_citation=self.meta.source_citation,
            is_demo=self.meta.is_demo,
            status=FindingStatus.COMPLIANT,
            severity=Severity.OBSERVATION,
            reason=f"Cross-document intake figures are consistent ({f_arch.field_value} seats).",
            recommended_action="No action required.",
            evidence=evidence
        )


# ==============================================================================
# 6. Difference from Authorised Reference Record (Historical Baseline)
# ==============================================================================
class ReferenceRecordDifferenceRule(BaseRule):
    """
    Compares current application declared intake against the prior approved AICTE baseline record.
    In an Extension of Approval, declared intake cannot exceed prior approved intake without an increase sanction.
    """
    def __init__(self, version: str = "1.0.0"):
        meta = RuleMetadata(
            rule_id="RULE-AICTE-HIST-006",
            rule_version=version,
            name="Consistency with Prior Approved AICTE Baseline",
            explanation=(
                "Validates that declared student intake in an Extension of Approval request does not "
                "unilaterally exceed the approved intake recorded in the prior year's AICTE approval order."
            ),
            applicable_categories=[ApplicationCategory.EXTENSION_OF_APPROVAL],
            effective_from=date(2024, 4, 1),
            effective_to=date(2027, 3, 31),
            required_field_keys=["total_intake"],
            severity=Severity.ANOMALY_SIGNAL,
            severity_rationale="Intake increases require a dedicated approval category and fee payment.",
            evidence_requirements=["Application declared total_intake", "AICTE Prior Approved Baseline Intake"],
            reviewer_next_action="Verify whether institution submitted a separate Increase in Intake request.",
            source_citation="AICTE Approval Process Handbook (APH) 2024-2027, Clause 3.1 & AICTE Historical Records",
            is_demo=False,
            state=RuleState.ACTIVE,
        )
        super().__init__(meta)

    def _evaluate_logic(self, application: ApplicationInput) -> Finding:
        if not application.reference_record:
            return Finding(
                rule_id=self.meta.rule_id,
                rule_version=self.meta.rule_version,
                rule_name=self.meta.name,
                clause_citation=self.meta.source_citation,
                is_demo=self.meta.is_demo,
                status=FindingStatus.INCONCLUSIVE,
                severity=self.meta.severity,
                reason="Historical AICTE baseline reference record for prior academic year is unavailable.",
                recommended_action="Retrieve prior year approval order from AICTE archives.",
                evidence=[]
            )

        declared_intake = application.declared_data.get("total_intake")
        if declared_intake is None:
            return Finding(
                rule_id=self.meta.rule_id,
                rule_version=self.meta.rule_version,
                rule_name=self.meta.name,
                clause_citation=self.meta.source_citation,
                is_demo=self.meta.is_demo,
                status=FindingStatus.INCONCLUSIVE,
                severity=self.meta.severity,
                reason="Field 'total_intake' was not declared in the application form.",
                recommended_action="Ensure total intake is declared in application.",
                evidence=[]
            )

        try:
            declared_val = int(declared_intake)
        except (ValueError, TypeError):
            return Finding(
                rule_id=self.meta.rule_id,
                rule_version=self.meta.rule_version,
                rule_name=self.meta.name,
                clause_citation=self.meta.source_citation,
                is_demo=self.meta.is_demo,
                status=FindingStatus.INCONCLUSIVE,
                severity=self.meta.severity,
                reason=f"Declared intake '{declared_intake}' is not a valid integer.",
                recommended_action="Correct declared intake format.",
                evidence=[]
            )

        prior_approved = application.reference_record.approved_intake
        evidence = [
            FindingEvidence(
                field_key="total_intake",
                extracted_value=str(declared_val),
                comparison_value=str(prior_approved),
                comparison_source=(
                    f"AICTE Historical Master Store (AY {application.reference_record.academic_year})"
                )
            )
        ]

        if declared_val > prior_approved:
            return Finding(
                rule_id=self.meta.rule_id,
                rule_version=self.meta.rule_version,
                rule_name=self.meta.name,
                clause_citation=self.meta.source_citation,
                is_demo=self.meta.is_demo,
                status=FindingStatus.ANOMALY_SIGNAL,
                severity=self.meta.severity,
                reason=(
                    f"Declared intake ({declared_val}) exceeds prior approved AICTE baseline "
                    f"({prior_approved}) in an Extension of Approval application."
                ),
                recommended_action=self.meta.reviewer_next_action,
                evidence=evidence
            )

        return Finding(
            rule_id=self.meta.rule_id,
            rule_version=self.meta.rule_version,
            rule_name=self.meta.name,
            clause_citation=self.meta.source_citation,
            is_demo=self.meta.is_demo,
            status=FindingStatus.COMPLIANT,
            severity=Severity.OBSERVATION,
            reason=(
                f"Declared intake ({declared_val}) is consistent with prior approved baseline "
                f"({prior_approved} seats)."
            ),
            recommended_action="No action required.",
            evidence=evidence
        )


# ==============================================================================
# 7. Category Specific Applicability Check
# ==============================================================================
class CategorySpecificRule(BaseRule):
    """
    Illustrates category applicability: applies ONLY to NEW_INSTITUTION applications
    requiring a Land Conversion Order. For EoA applications, it cleanly evaluates to NOT_APPLICABLE.
    """
    def __init__(self, version: str = "1.0.0"):
        meta = RuleMetadata(
            rule_id="RULE-CAT-SPEC-007",
            rule_version=version,
            name="New Institution Land Conversion Order Check",
            explanation="Requires non-agricultural land conversion order for all new establishment applications.",
            applicable_categories=[ApplicationCategory.NEW_INSTITUTION],
            effective_from=date(2024, 4, 1),
            effective_to=date(2027, 3, 31),
            required_document_types=[DocumentType.LAND_CONVERSION_ORDER],
            severity=Severity.DEFICIENCY,
            severity_rationale="Statutory requirement for establishing new technical campuses.",
            evidence_requirements=["Land Conversion Order from District Collectorate"],
            reviewer_next_action="Require land conversion certificate.",
            source_citation="AICTE Approval Process Handbook (APH) 2024-2027, Chapter I, Clause 1.4",
            is_demo=False,
            state=RuleState.ACTIVE,
        )
        super().__init__(meta)

    def _evaluate_logic(self, application: ApplicationInput) -> Finding:
        doc = application.get_document_by_type(DocumentType.LAND_CONVERSION_ORDER)
        if not doc:
            return Finding(
                rule_id=self.meta.rule_id,
                rule_version=self.meta.rule_version,
                rule_name=self.meta.name,
                clause_citation=self.meta.source_citation,
                is_demo=self.meta.is_demo,
                status=FindingStatus.DEFICIENCY,
                severity=self.meta.severity,
                reason="Mandatory Land Conversion Order missing for New Institution application.",
                recommended_action=self.meta.reviewer_next_action,
                evidence=[]
            )

        return Finding(
            rule_id=self.meta.rule_id,
            rule_version=self.meta.rule_version,
            rule_name=self.meta.name,
            clause_citation=self.meta.source_citation,
            is_demo=self.meta.is_demo,
            status=FindingStatus.COMPLIANT,
            severity=Severity.OBSERVATION,
            reason="Land Conversion Order is present in dossier.",
            recommended_action="No action required.",
            evidence=[
                FindingEvidence(
                    document_id=doc.id,
                    document_type=doc.document_type.value
                )
            ]
        )


# ==============================================================================
# 8. Evidence Availability Guardrail Rule
# ==============================================================================
class EvidenceAvailabilityGuardRule(BaseRule):
    """
    Enforces the rule that an automated check CANNOT produce a pass or fail
    if essential comparison evidence is missing or external source is offline.
    """
    def __init__(self, version: str = "1.0.0"):
        meta = RuleMetadata(
            rule_id="RULE-INP-UNAVAIL-008",
            rule_version=version,
            name="External Verification Evidence Guardrail Check",
            explanation=(
                "Guarantees that when external issuing authority evidence or institutional reference "
                "data is unreachable, the engine abstains and reports INCONCLUSIVE rather than failing the applicant."
            ),
            applicable_categories=[
                ApplicationCategory.EXTENSION_OF_APPROVAL,
                ApplicationCategory.INCREASE_IN_INTAKE,
                ApplicationCategory.NEW_COURSE,
                ApplicationCategory.NEW_INSTITUTION,
                ApplicationCategory.CLOSURE,
            ],
            effective_from=date(2024, 4, 1),
            effective_to=date(2027, 3, 31),
            severity=Severity.OBSERVATION,
            severity_rationale="Integrity guardrail ensuring technical unavailability does not harm applicant.",
            evidence_requirements=["Issuing Authority Verification Attempt Record"],
            reviewer_next_action="Check issuer network status or route to manual confirmation queue.",
            source_citation="[DEMO_RULE] PRAMAAN-AI Guardrail on Evidence Completeness",
            is_demo=True,
            state=RuleState.ACTIVE,
        )
        super().__init__(meta)

    def _evaluate_logic(self, application: ApplicationInput) -> Finding:
        # Check if any document has an unavailable or missing verification
        unavailable_docs = []
        for doc in application.documents:
            if doc.verification_status == DocumentVerificationStatus.SOURCE_UNAVAILABLE:
                unavailable_docs.append(doc)

        if unavailable_docs:
            doc_names = [f"{d.document_type.value} ({d.original_filename})" for d in unavailable_docs]
            return Finding(
                rule_id=self.meta.rule_id,
                rule_version=self.meta.rule_version,
                rule_name=self.meta.name,
                clause_citation=self.meta.source_citation,
                is_demo=self.meta.is_demo,
                status=FindingStatus.INCONCLUSIVE,
                severity=Severity.OBSERVATION,
                reason=(
                    f"Automated verification could not run because issuer source was unavailable for: "
                    f"{', '.join(doc_names)}. This is NOT a compliance failure."
                ),
                recommended_action="System scheduled retry; manual verification review available.",
                evidence=[
                    FindingEvidence(
                        document_id=d.id,
                        document_type=d.document_type.value,
                        comparison_source="External Issuer Adapter (HTTP 503 / Timeout)"
                    )
                    for d in unavailable_docs
                ]
            )

        return Finding(
            rule_id=self.meta.rule_id,
            rule_version=self.meta.rule_version,
            rule_name=self.meta.name,
            clause_citation=self.meta.source_citation,
            is_demo=self.meta.is_demo,
            status=FindingStatus.COMPLIANT,
            severity=Severity.OBSERVATION,
            reason="All external verification records and input evidence are available.",
            recommended_action="No action required.",
            evidence=[]
        )


# ==============================================================================
# 9. Institutional Legal Name Consistency (Fuzzy Comparison)
# ==============================================================================
class InstitutionalNameConsistencyRule(BaseRule):
    """
    Validates institutional name consistency using fuzzy normalization.
    Distinguishes legitimate variations (abbreviations) from substantive mismatches.
    """
    def __init__(self, version: str = "1.0.0"):
        meta = RuleMetadata(
            rule_id="RULE-APH-NAME-009",
            rule_version=version,
            name="Institutional Name Cross-Consistency & Fuzzy Match",
            explanation=(
                "Compares the institutional name extracted from legal documents against the "
                "registered AICTE master record using token-based fuzzy matching."
            ),
            applicable_categories=[
                ApplicationCategory.EXTENSION_OF_APPROVAL,
                ApplicationCategory.INCREASE_IN_INTAKE,
                ApplicationCategory.NEW_COURSE,
            ],
            effective_from=date(2024, 4, 1),
            effective_to=date(2027, 3, 31),
            required_document_types=[DocumentType.AFFIDAVIT_GENERAL],
            required_field_keys=["institution_name"],
            severity=Severity.ANOMALY_SIGNAL,
            severity_rationale="Name discrepancies may indicate outdated deeds or misattributed documents.",
            evidence_requirements=["Extracted institution_name on Affidavit", "AICTE Master Record Legal Name"],
            reviewer_next_action="Review name variation; confirm legal name continuity.",
            source_citation="AICTE Approval Process Handbook (APH) 2024-2027, Appendix 16 & Clause 2.4",
            is_demo=False,
            state=RuleState.ACTIVE,
        )
        super().__init__(meta)

    def _evaluate_logic(self, application: ApplicationInput) -> Finding:
        if not application.reference_record:
            return Finding(
                rule_id=self.meta.rule_id,
                rule_version=self.meta.rule_version,
                rule_name=self.meta.name,
                clause_citation=self.meta.source_citation,
                is_demo=self.meta.is_demo,
                status=FindingStatus.INCONCLUSIVE,
                severity=self.meta.severity,
                reason="Cannot check name consistency: Master AICTE reference record is unavailable.",
                recommended_action="Retrieve AICTE master registration record.",
                evidence=[]
            )

        doc = application.get_document_by_type(DocumentType.AFFIDAVIT_GENERAL)
        if not doc:
            return Finding(
                rule_id=self.meta.rule_id,
                rule_version=self.meta.rule_version,
                rule_name=self.meta.name,
                clause_citation=self.meta.source_citation,
                is_demo=self.meta.is_demo,
                status=FindingStatus.INCONCLUSIVE,
                severity=self.meta.severity,
                reason="Affidavit document missing; cannot compare institutional name.",
                recommended_action="Upload General Affidavit.",
                evidence=[]
            )

        field = doc.get_field("institution_name")
        if not field:
            return Finding(
                rule_id=self.meta.rule_id,
                rule_version=self.meta.rule_version,
                rule_name=self.meta.name,
                clause_citation=self.meta.source_citation,
                is_demo=self.meta.is_demo,
                status=FindingStatus.INCONCLUSIVE,
                severity=self.meta.severity,
                reason="Field 'institution_name' not extracted from Affidavit.",
                recommended_action="Extract institution name.",
                evidence=[]
            )

        extracted_name = field.field_value
        master_name = application.reference_record.legal_name
        ratio, classification = compare_names(extracted_name, master_name)

        evidence = [
            FindingEvidence(
                document_id=doc.id,
                document_type=doc.document_type.value,
                field_key="institution_name",
                extracted_value=extracted_name,
                page_number=field.provenance.page_number,
                bounding_box=field.provenance.bounding_box,
                comparison_value=master_name,
                comparison_source="AICTE Master Record"
            )
        ]

        if classification == "EXACT_MATCH":
            return Finding(
                rule_id=self.meta.rule_id,
                rule_version=self.meta.rule_version,
                rule_name=self.meta.name,
                clause_citation=self.meta.source_citation,
                is_demo=self.meta.is_demo,
                status=FindingStatus.COMPLIANT,
                severity=Severity.OBSERVATION,
                reason=f"Institutional name matches AICTE master record verbatim: '{extracted_name}'.",
                recommended_action="No action required.",
                evidence=evidence
            )
        elif classification == "LEGITIMATE_VARIATION":
            # Legitimate spelling or abbreviation variation (ratio >= 0.85) -> Compliant with informative observation
            return Finding(
                rule_id=self.meta.rule_id,
                rule_version=self.meta.rule_version,
                rule_name=self.meta.name,
                clause_citation=self.meta.source_citation,
                is_demo=self.meta.is_demo,
                status=FindingStatus.COMPLIANT,
                severity=Severity.OBSERVATION,
                reason=(
                    f"Legitimate abbreviation/spelling variation detected (similarity {ratio*100:.1f}%): "
                    f"Document '{extracted_name}' vs AICTE Master '{master_name}'. Recognized as equivalent."
                ),
                recommended_action="No action required; system normalized standard abbreviation.",
                evidence=evidence
            )
        elif classification == "POTENTIAL_VARIATION":
            # Potential variation (0.70 to 0.84) -> ANOMALY_SIGNAL for human review, NOT an automatic fraud or failure
            return Finding(
                rule_id=self.meta.rule_id,
                rule_version=self.meta.rule_version,
                rule_name=self.meta.name,
                clause_citation=self.meta.source_citation,
                is_demo=self.meta.is_demo,
                status=FindingStatus.ANOMALY_SIGNAL,
                severity=self.meta.severity,
                reason=(
                    f"Minor name variation detected (similarity {ratio*100:.1f}%): "
                    f"Document states '{extracted_name}' while AICTE master states '{master_name}'. "
                    f"Requires human officer confirmation."
                ),
                recommended_action="Confirm that the certificate refers to the same applicant institution.",
                evidence=evidence
            )
        else:
            # Significant mismatch (< 0.70)
            return Finding(
                rule_id=self.meta.rule_id,
                rule_version=self.meta.rule_version,
                rule_name=self.meta.name,
                clause_citation=self.meta.source_citation,
                is_demo=self.meta.is_demo,
                status=FindingStatus.DEFICIENCY,
                severity=Severity.DEFICIENCY,
                reason=(
                    f"Substantive institutional name mismatch (similarity {ratio*100:.1f}%): "
                    f"Document states '{extracted_name}', but registered AICTE master record is '{master_name}'."
                ),
                recommended_action="Verify if the document belongs to a different institution.",
                evidence=evidence
            )


def get_default_rules(pack_version: str = "1.0.0") -> List[BaseRule]:
    """
    Returns the complete set of initial MVP rules.
    """
    return [
        RequiredDocumentMissingRule(version=pack_version),
        RequiredFieldAbsentOrUncertainRule(version=pack_version),
        DocumentExpiryValidityRule(version=pack_version),
        InvalidDateRelationshipRule(version=pack_version),
        CrossDocumentMismatchRule(version=pack_version),
        ReferenceRecordDifferenceRule(version=pack_version),
        CategorySpecificRule(version=pack_version),
        EvidenceAvailabilityGuardRule(version=pack_version),
        InstitutionalNameConsistencyRule(version=pack_version),
    ]
