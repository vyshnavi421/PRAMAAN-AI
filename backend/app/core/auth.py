"""
PRAMAAN-AI Server-Side Role-Based Access Control (RBAC) & Authorization Subsystem
Enforces least-privilege permissions across:
- INSTITUTION_USER: Can only view and submit their own institution's dossier and documents.
- REVIEWER: Scrutiny officer. Can review all applications, confirm/dismiss findings, and record progress.
- RULES_ADMIN: Rules administrator. Can toggle and test regulatory rule packs.
- AUDITOR: Vigilance auditor. Read-only across dossiers; verifies cryptographic audit chains.

Enforces security in backend endpoint dependencies with server-validated demo sessions.
Arbitrary spoofed headers and unauthenticated reviewer fallbacks are strictly prohibited.
"""
from typing import List, Optional, Callable, Dict
from enum import Enum
from datetime import datetime, timezone, timedelta
import secrets
from fastapi import Header, HTTPException, Depends
from app.core.config import settings
from pydantic import BaseModel, Field


class UserRole(str, Enum):
    INSTITUTION_USER = "INSTITUTION_USER"
    REVIEWER = "REVIEWER"
    RULES_ADMIN = "RULES_ADMIN"
    AUDITOR = "AUDITOR"


class UserContext(BaseModel):
    user_id: str
    role: UserRole
    institution_id: Optional[str] = None
    full_name: str


class UserSession(BaseModel):
    session_token: str
    user_id: str
    role: UserRole
    institution_id: Optional[str] = None
    full_name: str
    created_at: datetime
    expires_at: Optional[datetime] = None


# Pre-configured synthetic user directory for SIH26261 demonstrations & tests
SYNTHETIC_USERS: Dict[str, UserContext] = {
    "usr-officer-01": UserContext(
        user_id="usr-officer-01",
        role=UserRole.REVIEWER,
        full_name="Dr. V. K. Sharma (AICTE Scrutiny Officer)"
    ),
    "usr-inst-apex": UserContext(
        user_id="usr-inst-apex",
        role=UserRole.INSTITUTION_USER,
        institution_id="inst-apex-01",
        full_name="Registrar, Apex Institute of Technology"
    ),
    "usr-inst-city": UserContext(
        user_id="usr-inst-city",
        role=UserRole.INSTITUTION_USER,
        institution_id="inst-city-02",
        full_name="Principal, City College of Engineering"
    ),
    "usr-admin-01": UserContext(
        user_id="usr-admin-01",
        role=UserRole.RULES_ADMIN,
        full_name="AICTE Regulatory Policy Administrator"
    ),
    "usr-auditor-01": UserContext(
        user_id="usr-auditor-01",
        role=UserRole.AUDITOR,
        full_name="Chief Vigilance Officer & Quality Auditor"
    ),
}


class SessionStore:
    """
    In-memory server-side session registry managing authenticated demo sessions.
    Validates session tokens and enforces expiration.

    Security contract: sessions are ONLY created for user_ids pre-registered in
    SYNTHETIC_USERS. The role and institution are taken EXCLUSIVELY from the
    server-side registry; callers cannot override them via the public login endpoint.
    """
    def __init__(self, ttl_hours: int = 24):
        self._sessions: Dict[str, UserSession] = {}
        self.ttl = timedelta(hours=ttl_hours)

    def login(self, user_id: str) -> UserSession:
        """
        Public login method used by the /auth/session API endpoint.
        Accepts ONLY user_ids pre-registered in SYNTHETIC_USERS.
        Role and institution are assigned exclusively from the server registry.
        Raises ValueError for any unknown user_id.
        """
        if not user_id or user_id not in SYNTHETIC_USERS:
            raise ValueError(f"Unknown user_id: '{user_id}'. Only pre-configured demo accounts may authenticate.")

        base_user = SYNTHETIC_USERS[user_id]
        now = datetime.now(timezone.utc)
        token = f"demo_sess_{secrets.token_hex(16)}"

        session = UserSession(
            session_token=token,
            user_id=base_user.user_id,
            role=base_user.role,
            institution_id=base_user.institution_id,
            full_name=base_user.full_name,
            created_at=now,
            expires_at=now + self.ttl,
        )
        self._sessions[token] = session
        return session

    def _create_internal_session(
        self,
        user_id: str,
        role: Optional[UserRole] = None,
        institution_id: Optional[str] = None,
        full_name: Optional[str] = None,
    ) -> UserSession:
        """
        Internal helper for test bootstrapping only. Never exposed via any API endpoint.
        Always resolves from SYNTHETIC_USERS first; role/institution may be overridden
        only by server-side test code (not by any client request).
        """
        now = datetime.now(timezone.utc)
        token = f"demo_sess_{secrets.token_hex(16)}"

        if user_id in SYNTHETIC_USERS:
            base_user = SYNTHETIC_USERS[user_id]
            user_role = role if role is not None else base_user.role
            user_inst = institution_id if institution_id is not None else base_user.institution_id
            name = full_name or base_user.full_name
        else:
            # Internal sessions for unknown ids are permitted ONLY in tests (no API path reaches here)
            user_role = role or UserRole.REVIEWER
            user_inst = institution_id
            name = full_name or f"Demo User ({user_id})"

        session = UserSession(
            session_token=token,
            user_id=user_id,
            role=user_role,
            institution_id=user_inst,
            full_name=name,
            created_at=now,
            expires_at=now + self.ttl,
        )
        self._sessions[token] = session
        return session

    def get_session(self, token: str) -> Optional[UserSession]:
        session = self._sessions.get(token)
        if not session:
            return None
        now = datetime.now(timezone.utc)
        if session.expires_at and session.expires_at < now:
            del self._sessions[token]
            return None
        return session

    def delete_session(self, token: str) -> bool:
        if token in self._sessions:
            del self._sessions[token]
            return True
        return False

    def clear(self):
        self._sessions.clear()


global_session_store = SessionStore()


def create_demo_session(
    user_id: str = "usr-officer-01",
    role: Optional[UserRole] = None,
    institution_id: Optional[str] = None,
) -> UserSession:
    """
    Server-side helper to provision a validated session for tests and bootstrapping.
    Uses the internal session creator — NOT the public login endpoint.
    Not reachable via any API route.
    """
    return global_session_store._create_internal_session(
        user_id=user_id, role=role, institution_id=institution_id
    )


def get_test_auth_headers(
    user_id: str = "usr-officer-01",
    role: Optional[UserRole] = None,
    institution_id: Optional[str] = None,
) -> Dict[str, str]:
    """Helper for unit and integration tests to acquire authenticated headers."""
    session = create_demo_session(user_id=user_id, role=role, institution_id=institution_id)
    return {"Authorization": f"Bearer {session.session_token}"}


def get_current_user(
    authorization: Optional[str] = Header(None, alias="Authorization", description="Bearer session_token"),
    x_session_token: Optional[str] = Header(None, alias="X-Session-Token", description="Session token header"),
) -> UserContext:
    """
    Extracts and validates user identity from a server-managed session.
    Strictly raises HTTP 401 if missing, invalid, or expired.
    Unauthenticated fallback to REVIEWER is eliminated.
    """
    token: Optional[str] = None
    if authorization:
        parts = authorization.split()
        if len(parts) == 2 and parts[0].lower() == "bearer":
            token = parts[1]
        elif len(parts) == 1:
            token = parts[0]
    elif x_session_token:
        token = x_session_token

    if not token:
        raise HTTPException(
            status_code=401,
            detail="Authentication required. Please provide a valid session token via Authorization: Bearer <token> or X-Session-Token."
        )

    session = global_session_store.get_session(token)
    if not session:
        raise HTTPException(
            status_code=401,
            detail="Invalid or expired session. Please authenticate via /api/v1/auth/session."
        )

    if not settings.IS_DEMO_MODE:
        raise HTTPException(
            status_code=403,
            detail=(
                "Demo authentication is disabled. "
                "Configure a production identity provider."
            ),
        )

    return UserContext(
        user_id=session.user_id,
        role=session.role,
        institution_id=session.institution_id,
        full_name=session.full_name
    )


def require_roles(allowed_roles: List[UserRole]) -> Callable:
    """
    FastAPI dependency factory enforcing server-side role check.
    Raises 403 Forbidden if current user lacks required role.
    """
    def role_checker(current_user: UserContext = Depends(get_current_user)) -> UserContext:
        if current_user.role not in allowed_roles:
            role_names = [r.value for r in allowed_roles]
            raise HTTPException(
                status_code=403,
                detail=(
                    f"Forbidden: Action requires role in {role_names}. "
                    f"Current user '{current_user.user_id}' has role '{current_user.role.value}'."
                )
            )
        return current_user
    return role_checker
