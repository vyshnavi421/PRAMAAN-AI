"""
PRAMAAN-AI Seeded Synthetic Application Repository & Overview Metrics Service
Maintains the canonical synthetic application bundles for SIH26261 demonstrations.
All bundles are strictly synthetic and visibly labeled DEMO / SIMULATED.
"""
from typing import List, Optional, Dict, Any
from datetime import date
import os
import uuid

from app.core.config import settings
from app.core.persistence import ensure_dir, read_json, write_json_atomic

from app.models.domain import (
    ApplicationInput,
    Document,
    ExtractedField,
    FieldProvenance,
    InstitutionalReferenceRecord,
)
from app.models.enums import (
    DocumentType,
    DocumentVerificationStatus,
    ExtractionQuality,
    ApplicationCategory,
)


class ApplicationService:
    _SEEDED_IDS = frozenset({"app-case-clean", "app-case-expired", "app-case-intake-mismatch",
                             "app-case-historical", "app-case-fuzzy-name", "app-case-source-outage", "app-case-reuse"})

    def __init__(self, data_dir: Optional[str] = None):
        self._applications: Dict[str, ApplicationInput] = {}
        self._workflow: Dict[str, str] = {}
        self._path: Optional[str] = None
        self._seed_applications()
        data_dir = ensure_dir(data_dir)
        if data_dir:
            self._path = os.path.join(data_dir, "applications.json")
            stored = read_json(self._path, default={}) or {}
            for app_id, raw in stored.get("applications", {}).items():
                self._applications[app_id] = ApplicationInput(**raw)
            self._workflow.update(stored.get("workflow", {}))

    def _flush(self) -> None:
        if not self._path:
            return
        write_json_atomic(self._path, {
            "applications": {k: v.model_dump(mode="json") for k, v in self._applications.items()},
            "workflow": self._workflow,
        })

    def save_application(self, application: ApplicationInput) -> ApplicationInput:
        """Insert or replace a dossier and persist it (if persistence is enabled)."""
        self._applications[application.application_id] = application
        self._flush()
        return application

    def persist(self) -> None:
        """Flush in-place mutations (e.g. extraction results) to disk."""
        self._flush()

    def set_workflow_status(self, application_id: str, status: str) -> None:
        self._workflow[application_id] = status
        self._flush()

    def get_workflow_status(self, application_id: str) -> str:
        return self._workflow.get(application_id, "UNDER_SCRUTINY")

    def _seed_applications(self):
        """
        Seeds 7 canonical synthetic benchmark bundles.
        """
        # Bundle 1: Clean Compliant Application
        app1 = ApplicationInput(
            application_id="app-case-clean",
            institution_id="inst-apex-01",
            application_number="APP-2026-EOA-101",
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
                    id="doc-clean-affidavit",
                    application_id="app-case-clean",
                    document_type=DocumentType.AFFIDAVIT_GENERAL,
                    original_filename="affidavit_format_a100.pdf",
                    storage_key="storage/app-case-clean/affidavit.pdf",
                    file_size_bytes=1048576,
                    sha256_hash="a1b2c3d4e5f60718293a4b5c6d7e8f901234567890abcdef1234567890abcdef",
                    page_count=2,
                    verification_status=DocumentVerificationStatus.VERIFIED,
                    extracted_fields=[
                        ExtractedField(
                            field_key="institution_name",
                            field_value="Apex Institute of Technology",
                            raw_value="Apex Institute of Technology",
                            confidence=0.99,
                            provenance=FieldProvenance(
                                page_number=1,
                                bounding_box=[0.15, 0.20, 0.70, 0.25],
                                surrounding_snippet="Affidavit of Apex Institute of Technology",
                                quality_label=ExtractionQuality.HIGH,
                            ),
                        )
                    ],
                ),
                Document(
                    id="doc-clean-fire",
                    application_id="app-case-clean",
                    document_type=DocumentType.FIRE_SAFETY_NOC,
                    original_filename="fire_safety_noc_valid.pdf",
                    storage_key="storage/app-case-clean/fire_noc.pdf",
                    file_size_bytes=2097152,
                    sha256_hash="b2c3d4e5f6a10718293a4b5c6d7e8f901234567890abcdef1234567890abcdef",
                    page_count=2,
                    verification_status=DocumentVerificationStatus.VERIFIED,
                    extracted_fields=[
                        ExtractedField(
                            field_key="noc_issue_date",
                            field_value="2026-01-15",
                            raw_value="15/01/2026",
                            confidence=0.97,
                            provenance=FieldProvenance(
                                page_number=1,
                                bounding_box=[0.12, 0.45, 0.35, 0.48],
                                surrounding_snippet="Issued on 15/01/2026",
                                quality_label=ExtractionQuality.HIGH,
                            ),
                        ),
                        ExtractedField(
                            field_key="noc_expiry_date",
                            field_value="2027-01-14",
                            raw_value="14/01/2027",
                            confidence=0.98,
                            provenance=FieldProvenance(
                                page_number=1,
                                bounding_box=[0.12, 0.52, 0.35, 0.55],
                                surrounding_snippet="Valid up to: 14/01/2027",
                                quality_label=ExtractionQuality.HIGH,
                            ),
                        ),
                    ],
                ),
                Document(
                    id="doc-clean-arch",
                    application_id="app-case-clean",
                    document_type=DocumentType.BUILDING_PLAN_ARCHITECT,
                    original_filename="architect_certificate.pdf",
                    storage_key="storage/app-case-clean/arch.pdf",
                    file_size_bytes=4194304,
                    sha256_hash="c3d4e5f6a1b20718293a4b5c6d7e8f901234567890abcdef1234567890abcdef",
                    page_count=3,
                    verification_status=DocumentVerificationStatus.VERIFIED,
                    extracted_fields=[
                        ExtractedField(
                            field_key="certified_intake_capacity",
                            field_value="180",
                            raw_value="180",
                            confidence=0.96,
                            provenance=FieldProvenance(page_number=1, quality_label=ExtractionQuality.HIGH),
                        ),
                        ExtractedField(
                            field_key="builtup_area_sqm",
                            field_value="12500.0",
                            raw_value="12,500 sq.m",
                            confidence=0.96,
                            provenance=FieldProvenance(page_number=2, quality_label=ExtractionQuality.HIGH),
                        ),
                    ],
                ),
                Document(
                    id="doc-clean-gov",
                    application_id="app-case-clean",
                    document_type=DocumentType.GOVERNING_BODY_RESOLUTION,
                    original_filename="governing_body_resolution.pdf",
                    storage_key="storage/app-case-clean/gov.pdf",
                    file_size_bytes=1048576,
                    sha256_hash="d4e5f6a1b2c30718293a4b5c6d7e8f901234567890abcdef1234567890abcdef",
                    page_count=1,
                    verification_status=DocumentVerificationStatus.VERIFIED,
                    extracted_fields=[
                        ExtractedField(
                            field_key="proposed_intake",
                            field_value="180",
                            raw_value="180 seats",
                            confidence=0.98,
                            provenance=FieldProvenance(page_number=1, quality_label=ExtractionQuality.HIGH),
                        )
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

        # Bundle 2: Expired Fire Safety NOC (Deficiency)
        app2 = ApplicationInput(
            application_id="app-case-expired",
            institution_id="inst-greenfield-02",
            application_number="APP-2026-EOA-102",
            academic_year="2026-2027",
            submission_date=date(2026, 4, 12),
            submission_cutoff_date=date(2026, 6, 30),
            category=ApplicationCategory.EXTENSION_OF_APPROVAL,
            declared_data={
                "institution_name": "Greenfield College of Engineering",
                "total_intake": 180,
                "builtup_area_sqm": 11000.0,
            },
            documents=[
                Document(
                    id="doc-exp-affidavit",
                    application_id="app-case-expired",
                    document_type=DocumentType.AFFIDAVIT_GENERAL,
                    original_filename="affidavit.pdf",
                    storage_key="storage/app-case-expired/affidavit.pdf",
                    file_size_bytes=1048576,
                    sha256_hash="e1f2a3b4c5d60718293a4b5c6d7e8f901234567890abcdef1234567890abcdef",
                    page_count=2,
                    verification_status=DocumentVerificationStatus.VERIFIED,
                    extracted_fields=[
                        ExtractedField(
                            field_key="institution_name",
                            field_value="Greenfield College of Engineering",
                            raw_value="Greenfield College of Engineering",
                            confidence=0.98,
                            provenance=FieldProvenance(page_number=1, quality_label=ExtractionQuality.HIGH),
                        )
                    ],
                ),
                Document(
                    id="doc-exp-fire",
                    application_id="app-case-expired",
                    document_type=DocumentType.FIRE_SAFETY_NOC,
                    original_filename="fire_safety_noc_2023.pdf",
                    storage_key="storage/app-case-expired/fire.pdf",
                    file_size_bytes=2097152,
                    sha256_hash="f2a3b4c5d6e10718293a4b5c6d7e8f901234567890abcdef1234567890abcdef",
                    page_count=2,
                    verification_status=DocumentVerificationStatus.EXPIRED,
                    extracted_fields=[
                        ExtractedField(
                            field_key="noc_issue_date",
                            field_value="2023-01-15",
                            raw_value="15/01/2023",
                            confidence=0.96,
                            provenance=FieldProvenance(
                                page_number=1,
                                bounding_box=[0.12, 0.45, 0.35, 0.48],
                                surrounding_snippet="Issued on 15/01/2023",
                                quality_label=ExtractionQuality.HIGH,
                            ),
                        ),
                        ExtractedField(
                            field_key="noc_expiry_date",
                            field_value="2024-01-14",
                            raw_value="14/01/2024",
                            confidence=0.965,
                            provenance=FieldProvenance(
                                page_number=1,
                                bounding_box=[0.12, 0.52, 0.32, 0.55],
                                surrounding_snippet="Valid up to: 14/01/2024",
                                quality_label=ExtractionQuality.HIGH,
                            ),
                        ),
                    ],
                ),
                Document(
                    id="doc-exp-arch",
                    application_id="app-case-expired",
                    document_type=DocumentType.BUILDING_PLAN_ARCHITECT,
                    original_filename="architect_certificate.pdf",
                    storage_key="storage/app-case-expired/arch.pdf",
                    file_size_bytes=3145728,
                    sha256_hash="a3b4c5d6e1f20718293a4b5c6d7e8f901234567890abcdef1234567890abcdef",
                    page_count=2,
                    verification_status=DocumentVerificationStatus.VERIFIED,
                    extracted_fields=[
                        ExtractedField(
                            field_key="certified_intake_capacity",
                            field_value="180",
                            raw_value="180",
                            confidence=0.95,
                            provenance=FieldProvenance(page_number=1, quality_label=ExtractionQuality.HIGH),
                        )
                    ],
                ),
                Document(
                    id="doc-exp-gov",
                    application_id="app-case-expired",
                    document_type=DocumentType.GOVERNING_BODY_RESOLUTION,
                    original_filename="governing_body_resolution.pdf",
                    storage_key="storage/app-case-expired/gov.pdf",
                    file_size_bytes=1048576,
                    sha256_hash="b4c5d6e1f2a30718293a4b5c6d7e8f901234567890abcdef1234567890abcdef",
                    page_count=1,
                    verification_status=DocumentVerificationStatus.VERIFIED,
                    extracted_fields=[
                        ExtractedField(
                            field_key="proposed_intake",
                            field_value="180",
                            raw_value="180",
                            confidence=0.97,
                            provenance=FieldProvenance(page_number=1, quality_label=ExtractionQuality.HIGH),
                        )
                    ],
                ),
            ],
            reference_record=InstitutionalReferenceRecord(
                institution_id="inst-greenfield-02",
                aicte_permanent_id="1-4458921134",
                legal_name="Greenfield College of Engineering",
                academic_year="2025-2026",
                approved_intake=180,
                approved_builtup_area_sqm=11000.0,
                is_synthetic=True,
            ),
        )

        # Bundle 3: Cross-Document Intake Mismatch (Anomaly/Defect)
        app3 = ApplicationInput(
            application_id="app-case-intake-mismatch",
            institution_id="inst-sunrise-03",
            application_number="APP-2026-EOA-103",
            academic_year="2026-2027",
            submission_date=date(2026, 4, 15),
            submission_cutoff_date=date(2026, 6, 30),
            category=ApplicationCategory.EXTENSION_OF_APPROVAL,
            declared_data={
                "institution_name": "Sunrise Institute of Technology",
                "total_intake": 240,
            },
            documents=[
                Document(
                    id="doc-mis-affidavit",
                    application_id="app-case-intake-mismatch",
                    document_type=DocumentType.AFFIDAVIT_GENERAL,
                    original_filename="affidavit.pdf",
                    storage_key="storage/app-case-intake-mismatch/affidavit.pdf",
                    sha256_hash="c5d6e1f2a3b40718293a4b5c6d7e8f901234567890abcdef1234567890abcdef",
                    extracted_fields=[
                        ExtractedField(
                            field_key="institution_name",
                            field_value="Sunrise Institute of Technology",
                            raw_value="Sunrise Institute of Technology",
                            confidence=0.98,
                            provenance=FieldProvenance(page_number=1, quality_label=ExtractionQuality.HIGH),
                        )
                    ],
                ),
                Document(
                    id="doc-mis-fire",
                    application_id="app-case-intake-mismatch",
                    document_type=DocumentType.FIRE_SAFETY_NOC,
                    original_filename="fire_safety_noc.pdf",
                    storage_key="storage/app-case-intake-mismatch/fire.pdf",
                    sha256_hash="d6e1f2a3b4c50718293a4b5c6d7e8f901234567890abcdef1234567890abcdef",
                    extracted_fields=[
                        ExtractedField(
                            field_key="noc_issue_date",
                            field_value="2026-01-10",
                            raw_value="10/01/2026",
                            confidence=0.96,
                            provenance=FieldProvenance(page_number=1, quality_label=ExtractionQuality.HIGH),
                        ),
                        ExtractedField(
                            field_key="noc_expiry_date",
                            field_value="2027-01-09",
                            raw_value="09/01/2027",
                            confidence=0.98,
                            provenance=FieldProvenance(page_number=1, quality_label=ExtractionQuality.HIGH),
                        ),
                    ],
                ),
                Document(
                    id="doc-mis-arch",
                    application_id="app-case-intake-mismatch",
                    document_type=DocumentType.BUILDING_PLAN_ARCHITECT,
                    original_filename="architect_certificate.pdf",
                    storage_key="storage/app-case-intake-mismatch/arch.pdf",
                    sha256_hash="e1f2a3b4c5d60718293a4b5c6d7e8f901234567890abcdef1234567890abcdef",
                    extracted_fields=[
                        ExtractedField(
                            field_key="certified_intake_capacity",
                            field_value="180",
                            raw_value="180",
                            confidence=0.95,
                            provenance=FieldProvenance(page_number=1, quality_label=ExtractionQuality.HIGH),
                        )
                    ],
                ),
                Document(
                    id="doc-mis-gov",
                    application_id="app-case-intake-mismatch",
                    document_type=DocumentType.GOVERNING_BODY_RESOLUTION,
                    original_filename="governing_body_resolution.pdf",
                    storage_key="storage/app-case-intake-mismatch/gov.pdf",
                    sha256_hash="f2a3b4c5d6e10718293a4b5c6d7e8f901234567890abcdef1234567890abcdef",
                    extracted_fields=[
                        ExtractedField(
                            field_key="proposed_intake",
                            field_value="240",
                            raw_value="240",
                            confidence=0.97,
                            provenance=FieldProvenance(page_number=1, quality_label=ExtractionQuality.HIGH),
                        )
                    ],
                ),
            ],
            reference_record=InstitutionalReferenceRecord(
                institution_id="inst-sunrise-03",
                aicte_permanent_id="1-5567812239",
                legal_name="Sunrise Institute of Technology",
                academic_year="2025-2026",
                approved_intake=180,
                approved_builtup_area_sqm=10000.0,
                is_synthetic=True,
            ),
        )

        # Bundle 4: Unsanctioned Intake Increase vs AICTE Baseline (Historical Anomaly)
        app4 = ApplicationInput(
            application_id="app-case-historical",
            institution_id="inst-bharat-04",
            application_number="APP-2026-EOA-104",
            academic_year="2026-2027",
            submission_date=date(2026, 4, 18),
            submission_cutoff_date=date(2026, 6, 30),
            category=ApplicationCategory.EXTENSION_OF_APPROVAL,
            declared_data={
                "institution_name": "Bharat Polytechnic",
                "total_intake": 240,
            },
            documents=[
                Document(
                    id="doc-hist-affidavit",
                    application_id="app-case-historical",
                    document_type=DocumentType.AFFIDAVIT_GENERAL,
                    original_filename="affidavit.pdf",
                    storage_key="storage/app-case-historical/affidavit.pdf",
                    sha256_hash="a4b5c6d7e1f20718293a4b5c6d7e8f901234567890abcdef1234567890abcdef",
                    extracted_fields=[
                        ExtractedField(
                            field_key="institution_name",
                            field_value="Bharat Polytechnic",
                            raw_value="Bharat Polytechnic",
                            confidence=0.98,
                            provenance=FieldProvenance(page_number=1, quality_label=ExtractionQuality.HIGH),
                        )
                    ],
                ),
                Document(
                    id="doc-hist-fire",
                    application_id="app-case-historical",
                    document_type=DocumentType.FIRE_SAFETY_NOC,
                    original_filename="fire_safety_noc.pdf",
                    storage_key="storage/app-case-historical/fire.pdf",
                    sha256_hash="b5c6d7e1f2a30718293a4b5c6d7e8f901234567890abcdef1234567890abcdef",
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
                            confidence=0.98,
                            provenance=FieldProvenance(page_number=1, quality_label=ExtractionQuality.HIGH),
                        ),
                    ],
                ),
                Document(
                    id="doc-hist-arch",
                    application_id="app-case-historical",
                    document_type=DocumentType.BUILDING_PLAN_ARCHITECT,
                    original_filename="architect_certificate.pdf",
                    storage_key="storage/app-case-historical/arch.pdf",
                    sha256_hash="c6d7e1f2a3b40718293a4b5c6d7e8f901234567890abcdef1234567890abcdef",
                    extracted_fields=[
                        ExtractedField(
                            field_key="certified_intake_capacity",
                            field_value="240",
                            raw_value="240",
                            confidence=0.95,
                            provenance=FieldProvenance(page_number=1, quality_label=ExtractionQuality.HIGH),
                        )
                    ],
                ),
                Document(
                    id="doc-hist-gov",
                    application_id="app-case-historical",
                    document_type=DocumentType.GOVERNING_BODY_RESOLUTION,
                    original_filename="governing_body_resolution.pdf",
                    storage_key="storage/app-case-historical/gov.pdf",
                    sha256_hash="d7e1f2a3b4c50718293a4b5c6d7e8f901234567890abcdef1234567890abcdef",
                    extracted_fields=[
                        ExtractedField(
                            field_key="proposed_intake",
                            field_value="240",
                            raw_value="240",
                            confidence=0.97,
                            provenance=FieldProvenance(page_number=1, quality_label=ExtractionQuality.HIGH),
                        )
                    ],
                ),
            ],
            reference_record=InstitutionalReferenceRecord(
                institution_id="inst-bharat-04",
                aicte_permanent_id="1-6678912345",
                legal_name="Bharat Polytechnic",
                academic_year="2025-2026",
                approved_intake=180,
                approved_builtup_area_sqm=9500.0,
                is_synthetic=True,
            ),
        )

        # Bundle 5: Legitimate Abbreviation Variation
        app5 = ApplicationInput(
            application_id="app-case-fuzzy-name",
            institution_id="inst-xavier-05",
            application_number="APP-2026-EOA-105",
            academic_year="2026-2027",
            submission_date=date(2026, 4, 20),
            submission_cutoff_date=date(2026, 6, 30),
            category=ApplicationCategory.EXTENSION_OF_APPROVAL,
            declared_data={
                "institution_name": "St. Xavier Tech. Campus",
                "total_intake": 180,
            },
            documents=[
                Document(
                    id="doc-fuz-affidavit",
                    application_id="app-case-fuzzy-name",
                    document_type=DocumentType.AFFIDAVIT_GENERAL,
                    original_filename="affidavit.pdf",
                    storage_key="storage/app-case-fuzzy-name/affidavit.pdf",
                    sha256_hash="e2f3a4b5c6d70718293a4b5c6d7e8f901234567890abcdef1234567890abcdef",
                    extracted_fields=[
                        ExtractedField(
                            field_key="institution_name",
                            field_value="St. Xavier Technical Campus",
                            raw_value="St. Xavier Technical Campus",
                            confidence=0.98,
                            provenance=FieldProvenance(page_number=1, quality_label=ExtractionQuality.HIGH),
                        )
                    ],
                ),
                Document(
                    id="doc-fuz-fire",
                    application_id="app-case-fuzzy-name",
                    document_type=DocumentType.FIRE_SAFETY_NOC,
                    original_filename="fire_safety_noc.pdf",
                    storage_key="storage/app-case-fuzzy-name/fire.pdf",
                    sha256_hash="f3a4b5c6d7e20718293a4b5c6d7e8f901234567890abcdef1234567890abcdef",
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
                            confidence=0.98,
                            provenance=FieldProvenance(page_number=1, quality_label=ExtractionQuality.HIGH),
                        ),
                    ],
                ),
                Document(
                    id="doc-fuz-arch",
                    application_id="app-case-fuzzy-name",
                    document_type=DocumentType.BUILDING_PLAN_ARCHITECT,
                    original_filename="architect_certificate.pdf",
                    storage_key="storage/app-case-fuzzy-name/arch.pdf",
                    sha256_hash="a5b6c7d8e2f30718293a4b5c6d7e8f901234567890abcdef1234567890abcdef",
                    extracted_fields=[
                        ExtractedField(
                            field_key="certified_intake_capacity",
                            field_value="180",
                            raw_value="180",
                            confidence=0.95,
                            provenance=FieldProvenance(page_number=1, quality_label=ExtractionQuality.HIGH),
                        )
                    ],
                ),
                Document(
                    id="doc-fuz-gov",
                    application_id="app-case-fuzzy-name",
                    document_type=DocumentType.GOVERNING_BODY_RESOLUTION,
                    original_filename="governing_body_resolution.pdf",
                    storage_key="storage/app-case-fuzzy-name/gov.pdf",
                    sha256_hash="b6c7d8e2f3a40718293a4b5c6d7e8f901234567890abcdef1234567890abcdef",
                    extracted_fields=[
                        ExtractedField(
                            field_key="proposed_intake",
                            field_value="180",
                            raw_value="180",
                            confidence=0.97,
                            provenance=FieldProvenance(page_number=1, quality_label=ExtractionQuality.HIGH),
                        )
                    ],
                ),
            ],
            reference_record=InstitutionalReferenceRecord(
                institution_id="inst-xavier-05",
                aicte_permanent_id="1-7789012346",
                legal_name="St. Xavier Technical Campus",
                academic_year="2025-2026",
                approved_intake=180,
                approved_builtup_area_sqm=12500.0,
                is_synthetic=True,
            ),
        )

        # Bundle 6: External Issuer Server Down (Source Unavailable)
        app6 = ApplicationInput(
            application_id="app-case-source-outage",
            institution_id="inst-national-06",
            application_number="APP-2026-EOA-106",
            academic_year="2026-2027",
            submission_date=date(2026, 4, 22),
            submission_cutoff_date=date(2026, 6, 30),
            category=ApplicationCategory.EXTENSION_OF_APPROVAL,
            declared_data={
                "institution_name": "National Institute of Science",
                "total_intake": 180,
            },
            documents=[
                Document(
                    id="doc-out-affidavit",
                    application_id="app-case-source-outage",
                    document_type=DocumentType.AFFIDAVIT_GENERAL,
                    original_filename="affidavit.pdf",
                    storage_key="storage/app-case-source-outage/affidavit.pdf",
                    sha256_hash="c7d8e2f3a4b50718293a4b5c6d7e8f901234567890abcdef1234567890abcdef",
                    extracted_fields=[
                        ExtractedField(
                            field_key="institution_name",
                            field_value="National Institute of Science",
                            raw_value="National Institute of Science",
                            confidence=0.98,
                            provenance=FieldProvenance(page_number=1, quality_label=ExtractionQuality.HIGH),
                        )
                    ],
                ),
                Document(
                    id="doc-out-fire",
                    application_id="app-case-source-outage",
                    document_type=DocumentType.FIRE_SAFETY_NOC,
                    original_filename="fire_safety_noc.pdf",
                    storage_key="storage/app-case-source-outage/fire.pdf",
                    sha256_hash="d8e2f3a4b5c60718293a4b5c6d7e8f901234567890abcdef1234567890abcdef",
                    verification_status=DocumentVerificationStatus.SOURCE_UNAVAILABLE,
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
                            confidence=0.98,
                            provenance=FieldProvenance(page_number=1, quality_label=ExtractionQuality.HIGH),
                        ),
                    ],
                ),
                Document(
                    id="doc-out-arch",
                    application_id="app-case-source-outage",
                    document_type=DocumentType.BUILDING_PLAN_ARCHITECT,
                    original_filename="architect_certificate.pdf",
                    storage_key="storage/app-case-source-outage/arch.pdf",
                    sha256_hash="e3f4a5b6c7d80718293a4b5c6d7e8f901234567890abcdef1234567890abcdef",
                    extracted_fields=[
                        ExtractedField(
                            field_key="certified_intake_capacity",
                            field_value="180",
                            raw_value="180",
                            confidence=0.95,
                            provenance=FieldProvenance(page_number=1, quality_label=ExtractionQuality.HIGH),
                        )
                    ],
                ),
                Document(
                    id="doc-out-gov",
                    application_id="app-case-source-outage",
                    document_type=DocumentType.GOVERNING_BODY_RESOLUTION,
                    original_filename="governing_body_resolution.pdf",
                    storage_key="storage/app-case-source-outage/gov.pdf",
                    sha256_hash="f4a5b6c7d8e30718293a4b5c6d7e8f901234567890abcdef1234567890abcdef",
                    extracted_fields=[
                        ExtractedField(
                            field_key="proposed_intake",
                            field_value="180",
                            raw_value="180",
                            confidence=0.97,
                            provenance=FieldProvenance(page_number=1, quality_label=ExtractionQuality.HIGH),
                        )
                    ],
                ),
            ],
            reference_record=InstitutionalReferenceRecord(
                institution_id="inst-national-06",
                aicte_permanent_id="1-8890123457",
                legal_name="National Institute of Science",
                academic_year="2025-2026",
                approved_intake=180,
                approved_builtup_area_sqm=13000.0,
                is_synthetic=True,
            ),
        )

        # Bundle 7: Cross-Application Document Reuse Signal
        # Shares the same architect hash as app1: c3d4e5f6a1b20718293a4b5c6d7e8f901234567890abcdef1234567890abcdef
        app7 = ApplicationInput(
            application_id="app-case-reuse",
            institution_id="inst-vidya-07",
            application_number="APP-2026-NEW-107",
            academic_year="2026-2027",
            submission_date=date(2026, 4, 25),
            submission_cutoff_date=date(2026, 6, 30),
            category=ApplicationCategory.NEW_INSTITUTION,
            declared_data={
                "institution_name": "Vidya Academy of Technology",
                "total_intake": 120,
            },
            documents=[
                Document(
                    id="doc-reuse-affidavit",
                    application_id="app-case-reuse",
                    document_type=DocumentType.AFFIDAVIT_GENERAL,
                    original_filename="affidavit.pdf",
                    storage_key="storage/app-case-reuse/affidavit.pdf",
                    sha256_hash="1122334455660718293a4b5c6d7e8f901234567890abcdef1234567890abcdef",
                    extracted_fields=[
                        ExtractedField(
                            field_key="institution_name",
                            field_value="Vidya Academy of Technology",
                            raw_value="Vidya Academy of Technology",
                            confidence=0.98,
                            provenance=FieldProvenance(page_number=1, quality_label=ExtractionQuality.HIGH),
                        )
                    ],
                ),
                Document(
                    id="doc-reuse-arch",
                    application_id="app-case-reuse",
                    document_type=DocumentType.BUILDING_PLAN_ARCHITECT,
                    original_filename="architect_certificate.pdf",
                    storage_key="storage/app-case-reuse/arch.pdf",
                    sha256_hash="c3d4e5f6a1b20718293a4b5c6d7e8f901234567890abcdef1234567890abcdef",
                    extracted_fields=[
                        ExtractedField(
                            field_key="certified_intake_capacity",
                            field_value="120",
                            raw_value="120",
                            confidence=0.95,
                            provenance=FieldProvenance(page_number=1, quality_label=ExtractionQuality.HIGH),
                        )
                    ],
                ),
            ],
            reference_record=None,
        )

        for app in [app1, app2, app3, app4, app5, app6, app7]:
            self._applications[app.application_id] = app

    def list_applications(
        self,
        category: Optional[str] = None,
        search_query: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """
        Lists summary information for all applications in the reviewer queue.
        """
        results = []
        for app in self._applications.values():
            if category and app.category.value != category:
                continue

            inst_name = app.declared_data.get("institution_name", "Unknown Institution")
            if search_query:
                q = search_query.lower()
                if (
                    q not in app.application_number.lower()
                    and q not in inst_name.lower()
                    and q not in app.institution_id.lower()
                ):
                    continue

            # Determine quick summary tags based on documents
            has_expired = any(
                d.verification_status == DocumentVerificationStatus.EXPIRED for d in app.documents
            )
            has_source_unavail = any(
                d.verification_status == DocumentVerificationStatus.SOURCE_UNAVAILABLE for d in app.documents
            )
            is_reuse_candidate = app.application_id == "app-case-reuse"

            status_tag = "ALL_CLEAR" if app.application_id in self._SEEDED_IDS else "NOT_YET_REVIEWED"
            if has_expired:
                status_tag = "DEFICIENCY_EXPIRED"
            elif is_reuse_candidate:
                status_tag = "ANOMALY_REUSE"
            elif has_source_unavail:
                status_tag = "SOURCE_UNAVAILABLE"
            elif app.application_id == "app-case-intake-mismatch":
                status_tag = "ANOMALY_MISMATCH"
            elif app.application_id == "app-case-historical":
                status_tag = "ANOMALY_INTAKE"

            results.append({
                "application_id": app.application_id,
                "application_number": app.application_number,
                "institution_id": app.institution_id,
                "institution_name": inst_name,
                "category": app.category.value,
                "academic_year": app.academic_year,
                "submission_date": str(app.submission_date),
                "submission_cutoff_date": str(app.submission_cutoff_date),
                "document_count": len(app.documents),
                "status_tag": status_tag,
                "workflow_status": self.get_workflow_status(app.application_id),
                "is_synthetic": True,
            })
        return results

    def get_application(self, application_id: str) -> Optional[ApplicationInput]:
        return self._applications.get(application_id)

    def find_document(self, document_id: str) -> Optional[tuple[ApplicationInput, Document]]:
        """
        Locates a document by ID across all seeded applications.
        """
        for app in self._applications.values():
            for doc in app.documents:
                if doc.id == document_id:
                    return app, doc
        return None

    def update_document_status(self, document_id: str, new_status: DocumentVerificationStatus) -> bool:
        """
        Updates the verification status of a specific document entity.
        """
        found = self.find_document(document_id)
        if found:
            _, doc = found
            doc.verification_status = new_status
            self._flush()
            return True
        return False

    def get_overview_metrics(self) -> Dict[str, Any]:
        """
        Computes real metrics from seeded synthetic database and review runs.
        """
        total = len(self._applications)
        categories = {}
        for app in self._applications.values():
            cat = app.category.value
            categories[cat] = categories.get(cat, 0) + 1

        return {
            "total_applications": total,
            "categories": categories,
            "academic_cycle": "2026-2027",
            "active_rule_pack": "rp-aicte-aph-2024-eoa v1.0.0",
            "is_demo_mode": True,
            "demo_banner": "DEMO DATA — NOT CONNECTED TO LIVE AICTE SYSTEMS (SIH26261 PROTOTYPE)",
        }


# Global application service instance
global_application_service = ApplicationService(data_dir=settings.DATA_DIR or None)
