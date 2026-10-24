"""
PRAMAAN-AI Issuing Authority & Cryptographic Verification Endpoints
Provides routes for executing deterministic external verifications and managing adapters.
All mock and simulated operations are clearly labeled DEMO / SIMULATED.
Enforces server-validated session authentication and role-based permissions.
"""
from typing import List, Optional, Dict, Any
from fastapi import APIRouter, HTTPException, Path, Body, Depends
from pydantic import BaseModel, Field

from app.models.enums import DocumentVerificationStatus, VerificationMethod
from app.adapters.verification import adapter_registry
from app.services.verification_service import (
    global_verification_service,
    VerificationAttemptRecord,
)
from app.core.auth import get_current_user, require_roles, UserRole, UserContext


router = APIRouter(prefix="", tags=["Verification Adapters & Gateways"])


class AdapterToggleRequest(BaseModel):
    enabled: bool = Field(..., description="Target operational state for adapter")


class VerifyDocumentRequest(BaseModel):
    adapter_id: str = Field(..., description="Machine ID of verification adapter")
    method: VerificationMethod = Field(..., description="Verification modality")
    reference_id: str = Field(..., description="Digest, serial number, or portal query ID")
    max_retries: int = Field(3, ge=1, le=5, description="Maximum retry attempts on transient failures")
    simulate_retry: bool = Field(False, description="Simulate transient network failure for testing")
    context: Dict[str, Any] = Field(default_factory=dict, description="Metadata context for adapter")
    actor_id: str = Field("usr-officer-01", description="Reviewer or automated service account ID")


@router.get(
    "/verification/adapters",
    summary="List all registered verification adapters and operational health"
)
def list_adapters(
    current_user: UserContext = Depends(get_current_user)
):
    """
    Returns configured adapters, simulation modes, and availability.
    """
    return {
        "is_demo_mode": True,
        "adapters": adapter_registry.list_adapters()
    }


@router.post(
    "/verification/adapters/{adapter_id}/toggle",
    summary="Administratively toggle adapter operational status (Requires RULES_ADMIN or REVIEWER)"
)
def toggle_adapter(
    adapter_id: str = Path(..., description="Adapter machine ID"),
    payload: AdapterToggleRequest = Body(...),
    current_user: UserContext = Depends(require_roles([UserRole.RULES_ADMIN, UserRole.REVIEWER]))
):
    """
    Enables or disables an adapter to simulate source unavailability and gateway outages.
    """
    adapter = adapter_registry.get(adapter_id)
    if not adapter:
        raise HTTPException(status_code=404, detail=f"Adapter '{adapter_id}' not found.")
    
    if hasattr(adapter, "set_enabled"):
        adapter.set_enabled(payload.enabled)
    
    return {
        "adapter_id": adapter.adapter_id,
        "adapter_name": adapter.adapter_name,
        "is_enabled": adapter.is_enabled,
        "demo_notice": "DEMO / SIMULATED"
    }


@router.get(
    "/verification/fixtures",
    summary="List documented test fixtures and expected statutory states"
)
def get_verification_fixtures(
    current_user: UserContext = Depends(get_current_user)
):
    """
    Returns reproducible fixtures for all 6 statutory states and error edge cases.
    """
    return global_verification_service.get_fixtures()


@router.post(
    "/documents/{document_id}/verify",
    response_model=VerificationAttemptRecord,
    summary="Execute statutory document verification against issuing authority adapter"
)
def verify_document(
    document_id: str = Path(..., description="Document UUID to verify"),
    payload: VerifyDocumentRequest = Body(...),
    current_user: UserContext = Depends(require_roles([UserRole.REVIEWER, UserRole.RULES_ADMIN, UserRole.INSTITUTION_USER]))
):
    """
    Executes a verification attempt returning exactly one of the 6 official statutory states:
    verified, mismatch detected, expired, verification pending, source unavailable, manual review required.
    """
    # Tenant isolation: callers may only verify documents inside their own dossier.
    from app.api.routes.documents import verify_document_ownership
    verify_document_ownership(current_user, document_id)

    attempt = global_verification_service.verify_document(
        document_id=document_id,
        adapter_id=payload.adapter_id,
        method=payload.method,
        reference_id=payload.reference_id,
        max_retries=payload.max_retries,
        simulate_retry=payload.simulate_retry,
        context=payload.context,
        actor_id=current_user.user_id
    )
    return attempt


@router.get(
    "/documents/{document_id}/verification-attempts",
    response_model=List[VerificationAttemptRecord],
    summary="Get chronological verification history for a document"
)
def get_document_verification_attempts(
    document_id: str = Path(..., description="Document UUID"),
    current_user: UserContext = Depends(get_current_user)
):
    """
    Returns timestamped attempts, safe payload hashes, retry counts, and manual review tasks.
    """
    from app.api.routes.documents import verify_document_ownership
    verify_document_ownership(current_user, document_id)
    return global_verification_service.get_attempts_for_document(document_id)


@router.get(
    "/verification/attempts/{attempt_id}",
    response_model=VerificationAttemptRecord,
    summary="Get single verification attempt by ID"
)
def get_verification_attempt(
    attempt_id: str = Path(..., description="Verification attempt UUID"),
    current_user: UserContext = Depends(get_current_user)
):
    """
    Returns verification attempt details including safe response payload and SHA-256 hash.
    """
    attempt = global_verification_service.get_attempt(attempt_id)
    if not attempt:
        raise HTTPException(status_code=404, detail=f"Verification attempt '{attempt_id}' not found.")
    from app.api.routes.documents import verify_document_ownership
    verify_document_ownership(current_user, attempt.document_id)
    return attempt
