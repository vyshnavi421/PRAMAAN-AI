"""
PRAMAAN-AI Validation API Routes
Provides endpoints for executing and retrieving deterministic validation runs.
Enforces server-validated session authentication and least privilege.
"""
from typing import List, Optional
from fastapi import APIRouter, HTTPException, Query, Path, Depends
from pydantic import BaseModel

from app.models.domain import ApplicationInput
from app.models.validation import ValidationRun
from app.services.validation_engine import ValidationEngine, validation_repository
from app.core.auth import get_current_user, require_roles, UserRole, UserContext
from app.core.access import assert_application_access

router = APIRouter(prefix="", tags=["Validation Engine"])
engine = ValidationEngine(repository=validation_repository)

class ValidationRunRequest(BaseModel):
    # Deprecated: server always validates its own stored dossier; any client copy is ignored.
    application_data: Optional[ApplicationInput] = None
    rule_pack_id: str = "rp-aicte-aph-2024-eoa"
    rule_pack_version: str = "1.0.0"

@router.post(
    "/applications/{application_id}/validation-runs",
    response_model=ValidationRun,
    status_code=201,
    summary="Execute deterministic validation run"
)
def create_validation_run(
    application_id: str = Path(..., description="Application UUID"),
    request: Optional[ValidationRunRequest] = None,
    current_user: UserContext = Depends(require_roles([UserRole.REVIEWER, UserRole.RULES_ADMIN, UserRole.INSTITUTION_USER]))
):
    """
    Executes versioned regulatory validation rules against the application dossier.
    Returns an immutable ValidationRun with evidence-linked findings.
    """
    stored_application = assert_application_access(current_user, application_id)
    request = request or ValidationRunRequest()

    run = engine.run_validation(
        application=stored_application.model_copy(deep=True),
        rule_pack_id=request.rule_pack_id,
        rule_pack_version=request.rule_pack_version
    )
    return run

@router.get(
    "/applications/{application_id}/validation-runs",
    response_model=List[ValidationRun],
    summary="List historical validation runs for an application"
)
def list_validation_runs(
    application_id: str = Path(..., description="Application UUID"),
    current_user: UserContext = Depends(get_current_user)
):
    """
    Returns all preserved validation runs for this application in chronological order.
    """
    assert_application_access(current_user, application_id)
    runs = validation_repository.get_by_application_id(application_id)
    return runs

@router.get(
    "/validation-runs/{run_id}",
    response_model=ValidationRun,
    summary="Get single validation run by ID"
)
def get_validation_run(
    run_id: str = Path(..., description="Validation Run UUID"),
    current_user: UserContext = Depends(get_current_user)
):
    """
    Retrieves an exact historical validation run and its immutable findings.
    """
    run = validation_repository.get_by_id(run_id)
    if not run:
        raise HTTPException(status_code=404, detail=f"Validation run '{run_id}' not found.")
    assert_application_access(current_user, run.application_id)
    return run
