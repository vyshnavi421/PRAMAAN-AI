"""
PRAMAAN-AI Duplicates & Historical Comparison API Routes
Provides endpoints for cross-application file reuse detection, approximate text similarity,
side-by-side document comparison, and change-aware review against historical baseline snapshots.
Enforces server-validated session authentication and least privilege RBAC.
"""
from typing import List, Optional, Dict, Any
from datetime import datetime, timezone
from fastapi import APIRouter, HTTPException, Path, Body, Depends
from pydantic import BaseModel, Field

from app.services.duplicate_detector import (
    global_duplicate_detector,
    global_duplicate_index,
    DuplicateMatchRecord,
)
from app.services.historical_service import (
    global_historical_engine,
    global_historical_repo,
    HistoricalComparisonReport,
    HistoricalApplicationSnapshot,
)
from app.services.application_service import global_application_service
from app.services.audit_service import global_audit_service
from app.core.auth import get_current_user, require_roles, UserRole, UserContext


router = APIRouter(prefix="", tags=["Duplicates & Historical Comparison"])


class ReviewerVerdictRequest(BaseModel):
    verdict: str = Field(..., description="Reviewer decision, e.g. CONFIRM_SHARED_SPONSORING_TRUST")
    notes: Optional[str] = Field(None, description="Reviewer justification notes")
    actor_id: Optional[str] = Field(None, description="Reviewer ID (optional, defaults to session user)")


@router.get(
    "/duplicates/scan/{application_id}",
    response_model=List[DuplicateMatchRecord],
    summary="Scan application documents for cross-application binary reuse or approximate similarity"
)
def scan_application_duplicates(
    application_id: str = Path(..., description="Application UUID to scan"),
    current_user: UserContext = Depends(get_current_user)
):
    """
    Executes cross-application duplicate and text similarity scan.
    Identifies exact binary collisions, high text overlap, and generic boilerplate templates.
    """
    app = global_application_service.get_application(application_id)
    if not app:
        raise HTTPException(status_code=404, detail=f"Application '{application_id}' not found.")

    if current_user.role == UserRole.INSTITUTION_USER and app.institution_id != current_user.institution_id:
        raise HTTPException(
            status_code=403,
            detail=f"Forbidden: Institution '{current_user.institution_id}' cannot scan '{app.institution_id}'."
        )

    # Ensure all seeded applications are registered in index
    all_apps = list(global_application_service._applications.values())
    global_duplicate_detector.seed_from_application_service(all_apps)

    matches: List[DuplicateMatchRecord] = []
    for doc in app.documents:
        m = global_duplicate_detector.scan_document(app, doc)
        matches.extend(m)

    return matches


@router.get(
    "/duplicates/matches",
    response_model=List[DuplicateMatchRecord],
    summary="List all recorded duplicate and similarity match records"
)
def list_duplicate_matches(
    current_user: UserContext = Depends(require_roles([UserRole.REVIEWER, UserRole.AUDITOR, UserRole.RULES_ADMIN]))
):
    """
    Returns all detected duplicate and similarity matches across the repository.
    """
    all_apps = list(global_application_service._applications.values())
    global_duplicate_detector.seed_from_application_service(all_apps)

    # If no matches detected yet, perform an initial cross-scan
    if not global_duplicate_index.list_matches():
        for app in all_apps:
            for doc in app.documents:
                global_duplicate_detector.scan_document(app, doc)

    return global_duplicate_index.list_matches()


@router.get(
    "/duplicates/matches/{match_id}/side-by-side",
    summary="Get detailed side-by-side document comparison payload"
)
def get_duplicate_side_by_side(
    match_id: str = Path(..., description="Duplicate match UUID"),
    current_user: UserContext = Depends(require_roles([UserRole.REVIEWER, UserRole.AUDITOR, UserRole.RULES_ADMIN]))
):
    """
    Returns side-by-side panels with source document, target document, hashes, snippets, and reviewer actions.
    """
    comp = global_duplicate_detector.get_side_by_side_comparison(match_id)
    if not comp:
        # Fallback check if index needs re-indexing
        all_apps = list(global_application_service._applications.values())
        global_duplicate_detector.seed_from_application_service(all_apps)
        for app in all_apps:
            for doc in app.documents:
                global_duplicate_detector.scan_document(app, doc)
        comp = global_duplicate_detector.get_side_by_side_comparison(match_id)

    if not comp:
        raise HTTPException(status_code=404, detail=f"Duplicate match '{match_id}' not found.")
    return comp


@router.post(
    "/duplicates/matches/{match_id}/verdict",
    summary="Record reviewer resolution for detected document reuse"
)
def record_duplicate_verdict(
    match_id: str = Path(..., description="Duplicate match UUID"),
    payload: ReviewerVerdictRequest = Body(...),
    current_user: UserContext = Depends(require_roles([UserRole.REVIEWER]))
):
    """
    Records an authorized reviewer resolution for a duplicate or similarity signal.
    Appends an immutable audit event to prevent false fraud escalation.
    """
    match = global_duplicate_index.get_match(match_id)
    if not match:
        raise HTTPException(status_code=404, detail=f"Duplicate match '{match_id}' not found.")

    match.reviewer_verdict = payload.verdict
    match.reviewer_notes = payload.notes

    actor = current_user.user_id

    # Record in audit trail
    global_audit_service.record_event(
        actor_id=actor,
        event_type="DUPLICATE_REUSE_RESOLVED",
        details={
            "match_id": match_id,
            "match_type": match.match_type.value,
            "verdict": payload.verdict,
            "notes": payload.notes,
            "source_doc_id": match.source_doc.document_id,
            "target_doc_id": match.target_doc.document_id,
            "explanation": "Reviewer determined legitimate shared trust or template usage."
        },
        application_id=match.source_doc.application_id
    )

    return {
        "status": "success",
        "match_id": match_id,
        "verdict": payload.verdict,
        "recorded_at": datetime.now(timezone.utc).isoformat()
    }


@router.get(
    "/applications/{application_id}/historical-comparison",
    response_model=HistoricalComparisonReport,
    summary="Perform change-aware comparison of current application vs previous baseline snapshot"
)
def get_historical_comparison(
    application_id: str = Path(..., description="Application UUID"),
    current_user: UserContext = Depends(get_current_user)
):
    """
    Compares current submission against previous approved institutional baseline.
    Normalises names/addresses, routes borderline variations, tracks intake expansion,
    and safeguards against false fraud verdicts.
    """
    app = global_application_service.get_application(application_id)
    if not app:
        raise HTTPException(status_code=404, detail=f"Application '{application_id}' not found.")

    if current_user.role == UserRole.INSTITUTION_USER and app.institution_id != current_user.institution_id:
        raise HTTPException(
            status_code=403,
            detail=f"Forbidden: Institution '{current_user.institution_id}' cannot view history for '{app.institution_id}'."
        )

    report = global_historical_engine.compare_application(app)
    return report


@router.get(
    "/historical/snapshots/{institution_id}",
    response_model=List[HistoricalApplicationSnapshot],
    summary="List historical approved snapshots for an institution"
)
def list_institution_snapshots(
    institution_id: str = Path(..., description="Institution ID, e.g. inst-apex-01"),
    current_user: UserContext = Depends(get_current_user)
):
    """
    Returns previous annual snapshots with approved parameters and documents.
    """
    if current_user.role == UserRole.INSTITUTION_USER and institution_id != current_user.institution_id:
        raise HTTPException(
            status_code=403,
            detail=f"Forbidden: Institution '{current_user.institution_id}' cannot view snapshots for '{institution_id}'."
        )

    return global_historical_repo.list_snapshots_for_institution(institution_id)
