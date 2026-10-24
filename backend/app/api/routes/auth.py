"""
PRAMAAN-AI Session Management & Authentication Routes
Provides endpoints for:
- Initializing demo sessions (/auth/session)
- Inspecting current session (/auth/me)
- Terminating session (/auth/session DELETE)
- Discovering pre-configured synthetic demo user profiles (/auth/demo-users)
"""
from typing import List, Optional, Dict, Any
from fastapi import APIRouter, HTTPException, Depends, Header
from pydantic import BaseModel

from app.core.auth import (
    global_session_store,
    get_current_user,
    UserRole,
    UserContext,
    SYNTHETIC_USERS,
)

router = APIRouter(prefix="/auth", tags=["Authentication & Sessions"])


class CreateSessionRequest(BaseModel):
    user_id: str  # Must match a pre-configured SYNTHETIC_USERS entry


class UserProfileResponse(BaseModel):
    user_id: str
    role: UserRole
    institution_id: Optional[str] = None
    full_name: str


class SessionResponse(BaseModel):
    session_token: str
    user: UserProfileResponse
    expires_at: Optional[str] = None


@router.post("/session", response_model=SessionResponse, summary="Create server-validated demo session")
def create_session(request: CreateSessionRequest):
    """
    Authenticates a demo actor by user_id against the server-side SYNTHETIC_USERS registry.
    The role and institution are assigned exclusively by the server; any client-supplied
    role or privilege claim is ignored.
    Returns a session token to be included as 'Authorization: Bearer <session_token>'.
    """
    try:
        session = global_session_store.login(user_id=request.user_id)
    except ValueError:
        raise HTTPException(
            status_code=401,
            detail="Unknown user_id. Only pre-configured demo accounts may authenticate."
        )
    return SessionResponse(
        session_token=session.session_token,
        user=UserProfileResponse(
            user_id=session.user_id,
            role=session.role,
            institution_id=session.institution_id,
            full_name=session.full_name
        ),
        expires_at=session.expires_at.isoformat() if session.expires_at else None
    )


@router.get("/me", response_model=UserProfileResponse, summary="Get current authenticated user profile")
def get_me(current_user: UserContext = Depends(get_current_user)):
    """
    Returns authenticated user profile parsed from the server-validated session.
    """
    return UserProfileResponse(
        user_id=current_user.user_id,
        role=current_user.role,
        institution_id=current_user.institution_id,
        full_name=current_user.full_name
    )


@router.delete("/session", summary="Terminate authenticated session")
def delete_session(
    authorization: Optional[str] = Header(None, alias="Authorization"),
    x_session_token: Optional[str] = Header(None, alias="X-Session-Token")
):
    """
    Terminates the active session token.
    """
    token = None
    if authorization:
        parts = authorization.split()
        if len(parts) == 2 and parts[0].lower() == "bearer":
            token = parts[1]
        elif len(parts) == 1:
            token = parts[0]
    elif x_session_token:
        token = x_session_token

    if token:
        global_session_store.delete_session(token)

    return {"status": "SESSION_TERMINATED", "detail": "Session successfully invalidated."}


@router.get("/demo-users", response_model=List[UserProfileResponse], summary="List synthetic demo user personas")
def list_demo_users():
    """
    Lists the available synthetic personas for easy 1-click persona switching during demonstration.
    """
    return [
        UserProfileResponse(
            user_id=u.user_id,
            role=u.role,
            institution_id=u.institution_id,
            full_name=u.full_name
        )
        for u in SYNTHETIC_USERS.values()
    ]
