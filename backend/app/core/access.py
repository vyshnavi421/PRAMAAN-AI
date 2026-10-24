"""
PRAMAAN-AI centralised tenant-access guard.

Every route that reads or writes data belonging to an application must call
``assert_application_access`` so tenant isolation is enforced server-side in one place.
"""
from fastapi import HTTPException

from app.core.auth import UserContext, UserRole
from app.models.domain import ApplicationInput
from app.services.application_service import global_application_service


def load_application_or_404(application_id: str) -> ApplicationInput:
    app = global_application_service.get_application(application_id)
    if not app:
        raise HTTPException(status_code=404, detail=f"Application '{application_id}' not found.")
    return app


def assert_application_access(user: UserContext, application_id: str) -> ApplicationInput:
    """Return the server-held dossier, or raise 404/403 if the caller may not see it."""
    app = load_application_or_404(application_id)
    if user.role == UserRole.INSTITUTION_USER and app.institution_id != user.institution_id:
        raise HTTPException(
            status_code=403,
            detail="Forbidden: this application belongs to a different institution.",
        )
    return app
