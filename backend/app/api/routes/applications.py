"""
PRAMAAN-AI Applications & Scrutiny Queue API Routes
Provides endpoints for retrieving applications, dossiers, and overview metrics.
Enforces authentication and tenant isolation for applicant institutions.
"""
from typing import List, Optional, Dict, Any
from datetime import date
import re
import uuid
from fastapi import APIRouter, HTTPException, Query, Path, Depends
from pydantic import BaseModel, Field

from app.models.domain import ApplicationInput
from app.services.application_service import global_application_service
from app.core.auth import get_current_user, require_roles, UserContext, UserRole
from app.models.enums import ApplicationCategory
from app.services.audit_service import global_audit_service

router = APIRouter(prefix="", tags=["Applications & Queue"])

@router.get(
    "/applications",
    response_model=List[Dict[str, Any]],
    summary="List applications in reviewer scrutiny queue"
)
def list_applications(
    category: Optional[str] = Query(None, description="Filter by ApplicationCategory"),
    search: Optional[str] = Query(None, description="Search query by number, name or ID"),
    current_user: UserContext = Depends(get_current_user)
):
    """
    Returns application queue summaries with quick status tags.
    If current user is an INSTITUTION_USER, results are scoped strictly to their own institution.
    """
    apps = global_application_service.list_applications(category=category, search_query=search)
    if current_user.role == UserRole.INSTITUTION_USER:
        apps = [a for a in apps if a.get("institution_id") == current_user.institution_id]
    return apps

@router.get(
    "/applications/{application_id}",
    response_model=ApplicationInput,
    summary="Get single application dossier by ID"
)
def get_application(
    application_id: str = Path(..., description="Application UUID"),
    current_user: UserContext = Depends(get_current_user)
):
    """
    Returns full application dossier with declared data and documents.
    Enforces tenant scoping: institution users cannot view other institutions' applications.
    """
    app = global_application_service.get_application(application_id)
    if not app:
        raise HTTPException(
            status_code=404,
            detail=f"Application '{application_id}' not found."
        )

    if current_user.role == UserRole.INSTITUTION_USER and app.institution_id != current_user.institution_id:
        raise HTTPException(
            status_code=403,
            detail=f"Forbidden: Institution '{current_user.institution_id}' cannot access application belonging to '{app.institution_id}'."
        )

    return app

@router.get(
    "/overview/metrics",
    summary="Get aggregated scrutiny command centre metrics"
)
def get_overview_metrics(
    current_user: UserContext = Depends(get_current_user)
):
    """
    Returns real metrics computed from backend applications and active rule pack.
    """
    return global_application_service.get_overview_metrics()


class CreateApplicationRequest(BaseModel):
    institution_name: str = Field(..., min_length=3, max_length=200)
    institution_id: Optional[str] = Field(None, description="Ignored for institution users; taken from the session.")
    category: ApplicationCategory = ApplicationCategory.EXTENSION_OF_APPROVAL
    academic_year: str = Field("2026-2027", pattern=r"^\d{4}-\d{4}$")
    application_ref: Optional[str] = Field(None, max_length=64)
    total_intake: Optional[int] = Field(None, ge=0, le=100000)
    builtup_area_sqm: Optional[float] = Field(None, ge=0)
    land_area_acres: Optional[float] = Field(None, ge=0)


@router.post("/applications/", response_model=ApplicationInput, status_code=201, include_in_schema=False)
@router.post(
    "/applications",
    response_model=ApplicationInput,
    status_code=201,
    summary="Create a new (empty) application dossier"
)
def create_application(
    payload: CreateApplicationRequest,
    current_user: UserContext = Depends(require_roles([UserRole.INSTITUTION_USER, UserRole.REVIEWER]))
):
    """
    Institution users open a dossier for their OWN institution (identity comes from the session,
    never from the request body). Reviewers may open one on behalf of a named institution.
    Documents are then uploaded via /documents/upload.
    """
    if current_user.role == UserRole.INSTITUTION_USER:
        institution_id = current_user.institution_id
    else:
        institution_id = payload.institution_id
        if not institution_id:
            raise HTTPException(status_code=422, detail="institution_id is required when a reviewer creates a dossier.")
    if not re.fullmatch(r"[a-z0-9][a-z0-9\-]{2,63}", institution_id or ""):
        raise HTTPException(status_code=422, detail="institution_id must be lowercase letters, digits or hyphens.")

    seq = len(global_application_service.list_applications()) + 101
    app_id = f"app-{uuid.uuid4().hex[:12]}"
    application = ApplicationInput(
        application_id=app_id,
        institution_id=institution_id,
        application_number=payload.application_ref or f"APP-{payload.academic_year[:4]}-{payload.category.value[:3]}-{seq}",
        academic_year=payload.academic_year,
        submission_date=date.today(),
        submission_cutoff_date=date(int(payload.academic_year[:4]), 6, 30),
        category=payload.category,
        declared_data={
            k: v for k, v in {
                "institution_name": payload.institution_name.strip(),
                "total_intake": payload.total_intake,
                "builtup_area_sqm": payload.builtup_area_sqm,
                "land_area_acres": payload.land_area_acres,
            }.items() if v is not None
        },
        documents=[],
    )
    global_application_service.save_application(application)
    global_application_service.set_workflow_status(app_id, "DRAFT")
    global_audit_service.record_event(
        actor_id=current_user.user_id,
        event_type="APPLICATION_CREATED",
        details={"application_number": application.application_number, "institution_id": institution_id},
        application_id=app_id,
    )
    return application
