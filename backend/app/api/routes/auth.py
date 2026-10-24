"""
PRAMAAN-AI Session Management & Authentication Routes

Provides endpoints for:
- Initializing demo sessions (/auth/session)
- Inspecting the current session (/auth/me)
- Terminating sessions (/auth/session DELETE)
- Discovering synthetic demo personas (/auth/demo-users)

Demo authentication is available only when IS_DEMO_MODE is enabled.
This demo login is not a substitute for production identity verification.
"""

from typing import List, Optional

from fastapi import APIRouter, HTTPException, Depends, Header
from pydantic import BaseModel

from app.core.auth import (
    global_session_store,
    get_current_user,
    UserRole,
    UserContext,
    SYNTHETIC_USERS,
)
from app.core.config import settings


router = APIRouter(
    prefix="/auth",
    tags=["Authentication & Sessions"],
)


class CreateSessionRequest(BaseModel):
    user_id: str


class UserProfileResponse(BaseModel):
    user_id: str
    role: UserRole
    institution_id: Optional[str] = None
    full_name: str


class SessionResponse(BaseModel):
    session_token: str
    user: UserProfileResponse
    expires_at: Optional[str] = None


def require_demo_mode() -> None:
    """Reject demo-only operations when demo mode is disabled."""
    if not settings.IS_DEMO_MODE:
        raise HTTPException(
            status_code=403,
            detail=(
                "Demo authentication is disabled. "
                "Configure a production identity provider."
            ),
        )


@router.post(
    "/session",
    response_model=SessionResponse,
    summary="Create server-validated demo session",
)
def create_session(request: CreateSessionRequest):
    """
    Creates a session for a configured synthetic demo persona.

    The role and institution are assigned by the server-side registry.
    Client-supplied privilege claims are not used.

    IMPORTANT: A known user_id alone does not prove real-world identity.
    """
    require_demo_mode()

    try:
        session = global_session_store.login(
            user_id=request.user_id
        )
    except ValueError:
        raise HTTPException(
            status_code=401,
            detail=(
                "Unknown user_id. Only pre-configured demo "
                "accounts may authenticate."
            ),
        )

    return SessionResponse(
        session_token=session.session_token,
        user=UserProfileResponse(
            user_id=session.user_id,
            role=session.role,
            institution_id=session.institution_id,
            full_name=session.full_name,
        ),
        expires_at=(
            session.expires_at.isoformat()
            if session.expires_at
            else None
        ),
    )


@router.get(
    "/me",
    response_model=UserProfileResponse,
    summary="Get current authenticated user profile",
)
def get_me(
    current_user: UserContext = Depends(get_current_user),
):
    """Return the profile associated with a validated session."""
    return UserProfileResponse(
        user_id=current_user.user_id,
        role=current_user.role,
        institution_id=current_user.institution_id,
        full_name=current_user.full_name,
    )


@router.delete(
    "/session",
    summary="Terminate session",
)
def delete_session(
    authorization: Optional[str] = Header(
        None,
        alias="Authorization",
    ),
    x_session_token: Optional[str] = Header(
        None,
        alias="X-Session-Token",
    ),
):
    """
    Invalidate a supplied session token.

    Repeated logout requests remain safe and idempotent.
    """
    token = None

    if authorization:
        parts = authorization.split()

        if (
            len(parts) == 2
            and parts[0].lower() == "bearer"
        ):
            token = parts[1]
        elif len(parts) == 1:
            token = parts[0]

    if not token and x_session_token:
        token = x_session_token.strip() or None

    if token:
        global_session_store.delete_session(token)

    return {
        "status": "SESSION_TERMINATED",
        "detail": "Session termination request processed.",
    }


@router.get(
    "/demo-users",
    response_model=List[UserProfileResponse],
    summary="List synthetic demo user personas",
)
def list_demo_users():
    """List configured synthetic personas when demo mode is enabled."""
    require_demo_mode()

    return [
        UserProfileResponse(
            user_id=user.user_id,
            role=user.role,
            institution_id=user.institution_id,
            full_name=user.full_name,
        )
        for user in SYNTHETIC_USERS.values()
    ]