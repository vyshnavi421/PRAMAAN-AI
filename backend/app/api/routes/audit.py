"""
PRAMAAN-AI Scrutiny Action & Tamper-Evident Audit Ledger API Routes
Provides endpoints for recording formal officer scrutiny actions,
verifying cryptographic hash chain integrity, testing tamper detection on disposable events,
and declaring the mathematical boundaries of hash chaining.
"""
from typing import List, Optional, Dict, Any
from fastapi import APIRouter, HTTPException, Query, Path, Depends, Body
from pydantic import BaseModel, Field

from app.core.auth import get_current_user, require_roles, UserRole, UserContext
from app.services.audit_service import (
    global_audit_service,
    AuditEvent,
    AuditChainVerificationResult,
)

router = APIRouter(prefix="", tags=["Audit & Review Actions"])


class ReviewActionRequest(BaseModel):
    action_type: str = Field(
        ...,
        description="CONFIRM_FINDING, DISMISS_FINDING, REQUEST_FURTHER_EVIDENCE, RECORD_MANUAL_VERIFICATION"
    )
    justification_reason: Optional[str] = Field(None, description="Officer justification remarks")
    actor_id: Optional[str] = Field(None, description="Reviewer user ID (overridden by auth context if present)")
    application_id: Optional[str] = None


class TamperSimulationRequest(BaseModel):
    sequence: Optional[int] = Field(None, description="Specific event sequence number to tamper (defaults to midpoint)")


@router.post(
    "/findings/{finding_id}/review-actions",
    response_model=AuditEvent,
    status_code=201,
    summary="Record formal scrutiny action on a finding (Requires REVIEWER role)"
)
def record_review_action(
    finding_id: str = Path(..., description="Finding UUID"),
    request: ReviewActionRequest = Body(...),
    current_user: UserContext = Depends(require_roles([UserRole.REVIEWER]))
):
    """
    Appends an authorized reviewer decision into the immutable cryptographic audit chain.
    Mandates a non-empty justification reason (>= 10 characters) when dismissing a finding.
    Strict Guardrail: Autonomous AI approval or rejection is strictly barred.
    """
    norm_action = request.action_type.strip().upper()

    # Guardrail: Ban autonomous AI approval/rejection
    if "AUTO_APPROVE" in norm_action or "AI_DECISION" in norm_action or "AUTONOMOUS" in norm_action:
        raise HTTPException(
            status_code=400,
            detail="Autonomous AI approval or rejection is strictly barred by AICTE statutory guardrails."
        )

    # Mandatory dismissal justification check
    if "DISMISS" in norm_action:
        reason = (request.justification_reason or "").strip()
        if not reason or len(reason) < 10:
            raise HTTPException(
                status_code=400,
                detail="Mandatory justification reason (at least 10 characters) is required to dismiss a finding."
            )

    effective_actor = current_user.user_id if current_user else (request.actor_id or "usr-officer-01")

    event = global_audit_service.record_event(
        actor_id=effective_actor,
        event_type=f"REVIEW_ACTION_{norm_action}",
        details={
            "action_type": norm_action,
            "justification": request.justification_reason or "Action recorded by scrutiny officer.",
            "finding_id": finding_id,
            "actor_role": current_user.role.value if current_user else UserRole.REVIEWER.value,
            "is_human_decision": True,
            "ai_autonomous_decision": False
        },
        application_id=request.application_id,
        finding_id=finding_id
    )
    return event


@router.get(
    "/applications/{application_id}/audit-events",
    response_model=List[AuditEvent],
    summary="Get cryptographic audit events for an application"
)
def get_audit_events(
    application_id: str = Path(..., description="Application UUID"),
    current_user: UserContext = Depends(get_current_user)
):
    """
    Returns audit trail entries associated with this application.
    Enforces institution scoping for applicant users.
    """
    if current_user.role == UserRole.INSTITUTION_USER:
        if current_user.institution_id:
            from app.services.application_service import global_application_service
            app = global_application_service.get_application(application_id)
            if app and app.institution_id != current_user.institution_id:
                raise HTTPException(
                    status_code=403,
                    detail="Forbidden: You are not authorized to view audit events for another institution."
                )

    return global_audit_service.get_events(application_id=application_id)


@router.post(
    "/audit/verify-chain",
    response_model=AuditChainVerificationResult,
    summary="Verify cryptographic hash chain integrity (Requires REVIEWER or AUDITOR)"
)
def verify_hash_chain(
    current_user: UserContext = Depends(require_roles([UserRole.AUDITOR, UserRole.REVIEWER]))
):
    """
    Recomputes SHA-256 hash chain from genesis to head; detects any unauthorized row modification.
    """
    return global_audit_service.verify_chain()


@router.post(
    "/audit/simulate-tamper",
    summary="Simulate unauthorized tampering on a disposable audit block (Auditor Test)"
)
def simulate_audit_tamper(
    payload: TamperSimulationRequest = Body(default_factory=TamperSimulationRequest),
    current_user: UserContext = Depends(require_roles([UserRole.AUDITOR, UserRole.REVIEWER]))
):
    """
    Deliberately alters an in-memory audit event to test tamper-detection capabilities.
    """
    try:
        return global_audit_service.simulate_tamper(payload.sequence)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post(
    "/audit/restore-chain",
    summary="Restore audit chain to original valid state (Auditor Test)"
)
def restore_audit_chain(
    current_user: UserContext = Depends(require_roles([UserRole.AUDITOR, UserRole.REVIEWER]))
):
    """
    Restores tampered events to their original signed state.
    """
    return global_audit_service.restore_chain()


@router.get(
    "/audit/limitation-statement",
    summary="Statutory disclosure on the mathematical boundaries of hash chaining"
)
def get_audit_limitation_statement():
    """
    Explains what hash chaining establishes and its limit against privileged database administrators.
    """
    return {
        "title": "Statutory Cryptographic Ledger Limitation Notice",
        "statement": global_audit_service.get_limitation_statement(),
        "threat_model_reference": "docs/THREAT_MODEL.md Section 3",
        "recommended_production_control": "HSM-signed periodic checkpoints published to Write-Once-Read-Many (WORM) storage."
    }
