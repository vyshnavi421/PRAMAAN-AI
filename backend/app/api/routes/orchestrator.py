"""
PRAMAAN-AI Full-Application Review Orchestration Endpoints
Enables running and reopening persistent pre-scrutiny runs with coverage audit guarantees.
Enforces role-based permissions and tenant scoping.
"""
from typing import Optional
from fastapi import APIRouter, HTTPException, Path, Query, Depends
from pydantic import BaseModel

from app.models.domain import ApplicationInput
from app.services.review_orchestrator import (
    ReviewOrchestrator,
    ReviewReport,
    CoverageAuditReport,
    global_review_repository,
)
from app.core.auth import get_current_user, require_roles, UserRole, UserContext
from app.core.access import assert_application_access

router = APIRouter(prefix="", tags=["Full-Application Review Orchestrator"])
orchestrator = ReviewOrchestrator(repository=global_review_repository)

class FullReviewRequest(BaseModel):
    # Deprecated: the server always reviews its own stored dossier; any client copy is ignored.
    application_data: Optional[ApplicationInput] = None
    rule_pack_id: str = "rp-aicte-aph-2024-eoa"
    rule_pack_version: str = "1.0.0"

@router.post(
    "/applications/{application_id}/full-review",
    response_model=ReviewReport,
    status_code=201,
    summary="Run Complete Pre-Scrutiny Workflow"
)
def run_full_application_review(
    application_id: str = Path(..., description="Application UUID"),
    request: Optional[FullReviewRequest] = None,
    current_user: UserContext = Depends(require_roles([UserRole.REVIEWER, UserRole.RULES_ADMIN, UserRole.INSTITUTION_USER]))
):
    """
    Executes the full automated pre-scrutiny orchestrator:
    - Snapshots application dossier
    - Checks document processing state
    - Evaluates all applicable rules, duplicate scans, and verification adapters
    - Performs independent Coverage Audit
    - Persists report for reopening
    """
    # Server-authoritative dossier: never trust a client-supplied copy of the application.
    stored_application = assert_application_access(current_user, application_id)
    request = request or FullReviewRequest()

    try:
        report = orchestrator.run_complete_prescrutiny(
            application=stored_application.model_copy(deep=True),
            rule_pack_id=request.rule_pack_id,
            rule_pack_version=request.rule_pack_version
        )
        return report
    except RuntimeError as re:
        # Concurrent run collision / lock failure
        raise HTTPException(status_code=409, detail=str(re))
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Orchestration pipeline failure: {str(exc)}")

@router.get(
    "/applications/{application_id}/full-review/latest",
    response_model=ReviewReport,
    summary="Get latest pre-scrutiny review report for application"
)
def get_latest_review_report(
    application_id: str = Path(..., description="Application UUID"),
    current_user: UserContext = Depends(get_current_user)
):
    """
    Reopens the latest persisted pre-scrutiny report without re-executing checks.
    """
    report = global_review_repository.get_latest_by_application_id(application_id)
    if not report:
        raise HTTPException(
            status_code=404,
            detail=f"No pre-scrutiny review report found for application '{application_id}'."
        )

    assert_application_access(current_user, report.application_id)

    return report

@router.get(
    "/review-runs/{review_id}",
    response_model=ReviewReport,
    summary="Get specific review run report by ID"
)
def get_review_run(
    review_id: str = Path(..., description="Review Run UUID"),
    current_user: UserContext = Depends(get_current_user)
):
    """
    Retrieves an immutable review run by its review ID.
    """
    report = global_review_repository.get_by_id(review_id)
    if not report:
        raise HTTPException(
            status_code=404,
            detail=f"Review report '{review_id}' not found."
        )
    assert_application_access(current_user, report.application_id)
    return report

@router.post(
    "/review-runs/{review_id}/coverage-audit",
    response_model=CoverageAuditReport,
    summary="Re-verify coverage audit independently"
)
def verify_review_coverage(
    review_id: str = Path(..., description="Review Run UUID"),
    current_user: UserContext = Depends(require_roles([UserRole.REVIEWER, UserRole.AUDITOR, UserRole.RULES_ADMIN]))
):
    """
    Independently audits the planned checks against recorded outcomes for a saved review run.
    """
    report = global_review_repository.get_by_id(review_id)
    if not report:
        raise HTTPException(status_code=404, detail=f"Review report '{review_id}' not found.")
    
    # Re-run coverage audit over persisted findings and verifications
    all_findings = report.findings + report.successful_checks + report.not_applicable_checks + report.inconclusive_checks
    audit = orchestrator.auditor.audit(
        planned_checks=report.planned_checks,
        executed_findings=all_findings,
        verifications=report.source_verifications
    )
    return audit


# ---------------------------------------------------------------------------
# Exports: printable scrutiny report + draft deficiency letter
# ---------------------------------------------------------------------------
from fastapi.responses import HTMLResponse, PlainTextResponse
from app.services.report_export import build_scrutiny_report_html, build_deficiency_letter_text
from app.services.audit_service import global_audit_service


@router.get(
    "/applications/{application_id}/scrutiny-report",
    response_class=HTMLResponse,
    summary="Printable pre-scrutiny report (HTML; print to PDF)"
)
def export_scrutiny_report(
    application_id: str = Path(...),
    current_user: UserContext = Depends(get_current_user)
):
    application = assert_application_access(current_user, application_id)
    report = global_review_repository.get_latest_by_application_id(application_id)
    if not report:
        raise HTTPException(status_code=404, detail="Run a full review before exporting a report.")
    name = application.declared_data.get("institution_name", application.institution_id)
    global_audit_service.record_event(
        actor_id=current_user.user_id, event_type="REPORT_EXPORTED",
        details={"review_id": report.review_id, "format": "html"}, application_id=application_id)
    return HTMLResponse(
        build_scrutiny_report_html(report, name),
        headers={"Content-Disposition": f'inline; filename="scrutiny-{application.application_number}.html"'},
    )


@router.get(
    "/applications/{application_id}/deficiency-letter",
    response_class=PlainTextResponse,
    summary="Draft deficiency/clarification letter for officer approval (reviewer only)"
)
def draft_deficiency_letter(
    application_id: str = Path(...),
    current_user: UserContext = Depends(require_roles([UserRole.REVIEWER]))
):
    application = assert_application_access(current_user, application_id)
    report = global_review_repository.get_latest_by_application_id(application_id)
    if not report:
        raise HTTPException(status_code=404, detail="Run a full review before drafting a letter.")
    name = application.declared_data.get("institution_name", application.institution_id)
    global_audit_service.record_event(
        actor_id=current_user.user_id, event_type="DEFICIENCY_LETTER_DRAFTED",
        details={"review_id": report.review_id}, application_id=application_id)
    return PlainTextResponse(build_deficiency_letter_text(report, name, current_user.full_name))
