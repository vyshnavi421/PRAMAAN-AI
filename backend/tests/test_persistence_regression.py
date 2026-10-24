"""
Regression test suite for Issue 6: Persistent Storage for Applications, Review Runs, and Audit Events
Verifies:
1. Applications survive service restart (persisted on disk).
2. Review reports and coverage audits survive repository restart.
3. Audit ledger events and hash chain continuity survive service restart.
"""
import pytest
import tempfile
import os
import shutil
from datetime import date
from pydantic import BaseModel

from app.models.domain import ApplicationInput, Document, ExtractedField, FieldProvenance
from app.models.enums import DocumentType, DocumentVerificationStatus, ApplicationCategory, ExtractionQuality
from app.services.application_service import ApplicationService
from app.services.review_orchestrator import ReviewRunRepository, ReviewReport, CoverageAuditReport
from app.services.audit_service import AuditService


@pytest.fixture
def temp_storage_dir():
    temp_dir = tempfile.mkdtemp(prefix="pramaan_persist_test_")
    yield temp_dir
    shutil.rmtree(temp_dir, ignore_errors=True)



def test_applications_persist_across_restarts(temp_storage_dir):
    """Applications saved to disk must reload accurately upon service restart."""
    # 1. Instantiate service with temp directory
    app_service_1 = ApplicationService(data_dir=temp_storage_dir)
    
    # 2. Add custom application
    custom_app = ApplicationInput(
        application_id="app-persist-custom",
        institution_id="inst-persist-01",
        application_number="APP-2026-PERSIST-999",
        academic_year="2026-2027",
        submission_date=date(2026, 4, 1),
        submission_cutoff_date=date(2026, 6, 30),
        category=ApplicationCategory.NEW_INSTITUTION,
        declared_data={"institution_name": "Persistent Institute of Technology", "total_intake": 240},
        documents=[
            Document(
                id="doc-persist-1",
                application_id="app-persist-custom",
                document_type=DocumentType.AFFIDAVIT_GENERAL,
                original_filename="affidavit.pdf",
                storage_key="storage/protected/inst-persist-01/affidavit.bin",
                file_size_bytes=1024,
                sha256_hash="abcdef1234567890",
                page_count=1,
                verification_status=DocumentVerificationStatus.VERIFIED,
                extracted_fields=[]
            )
        ]
    )
    app_service_1.save_application(custom_app)

    # 3. Instantiate NEW service pointing to same directory (simulating restart)
    app_service_2 = ApplicationService(data_dir=temp_storage_dir)
    reloaded = app_service_2.get_application("app-persist-custom")

    assert reloaded is not None, "Application failed to persist across service re-instantiation!"
    assert reloaded.application_number == "APP-2026-PERSIST-999"
    assert reloaded.declared_data["institution_name"] == "Persistent Institute of Technology"
    assert len(reloaded.documents) == 1
    assert reloaded.documents[0].id == "doc-persist-1"


def test_review_runs_persist_across_restarts(temp_storage_dir):
    """Review reports and coverage audits must persist and reopen across restarts."""
    repo_1 = ReviewRunRepository(data_dir=temp_storage_dir)

    report = ReviewReport(
        review_id="rev-persist-12345",
        application_id="app-persist-custom",
        application_number="APP-2026-PERSIST-999",
        academic_year="2026-2027",
        category="NEW_INSTITUTION",
        rule_pack_id="rp-aicte-aph-2024-eoa",
        rule_pack_version="1.0.0",
        input_snapshot_hash="a" * 64,
        review_status="COMPLETE",
        coverage_audit=CoverageAuditReport(
            is_complete=True,
            audit_verdict="COMPLETE",
            total_planned=2,
            total_accounted=2,
            coverage_percentage=100.0,
        ),
    )
    repo_1.save(report)

    # Re-instantiate repository
    repo_2 = ReviewRunRepository(data_dir=temp_storage_dir)
    reloaded_report = repo_2.get_by_id("rev-persist-12345")

    assert reloaded_report is not None, "Review report failed to persist across repository restart!"
    assert reloaded_report.review_status == "COMPLETE"
    assert reloaded_report.coverage_audit.is_complete is True
    assert repo_2.get_latest_by_application_id("app-persist-custom").review_id == "rev-persist-12345"



def test_audit_events_persist_and_maintain_chain_across_restarts(temp_storage_dir):
    """Audit ledger entries and hash-chain continuity must survive service restart."""
    audit_1 = AuditService(data_dir=temp_storage_dir)

    evt1 = audit_1.record_event(
        actor_id="usr-officer-01",
        event_type="REVIEW_STARTED",
        details={"case": "app-persist-custom"},
        application_id="app-persist-custom"
    )

    # Re-instantiate audit service
    audit_2 = AuditService(data_dir=temp_storage_dir)
    events = audit_2.get_events("app-persist-custom")

    assert len(events) >= 1
    assert events[-1].event_hash == evt1.event_hash
    assert events[-1].sequence == evt1.sequence

    # Verification of cryptographic chain must pass
    chain_result = audit_2.verify_chain()
    assert chain_result.is_valid is True, f"Hash chain corrupted on reload: {chain_result.detail}"
