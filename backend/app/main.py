"""
PRAMAAN-AI Main FastAPI Application Entrypoint
Provides health probes, demo banners, and API route dispatch.
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.api.routes.auth import router as auth_router
from app.api.routes.validation import router as validation_router
from app.api.routes.orchestrator import router as orchestrator_router
from app.api.routes.applications import router as applications_router
from app.api.routes.audit import router as audit_router
from app.api.routes.verification import router as verification_router
from app.api.routes.duplicates_and_comparison import router as comparison_router
from app.api.routes.documents import router as documents_router

app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    description="Evidence-First Validation Copilot for AICTE Approvals (SIH26261 Prototype)",
    openapi_url=f"{settings.API_V1_PREFIX}/openapi.json",
    docs_url=f"{settings.API_V1_PREFIX}/docs",
    redoc_url=f"{settings.API_V1_PREFIX}/redoc"
)

# CORS: explicit origin allowlist — wildcard + credentials is rejected by browsers and is insecure.
# Override ALLOWED_ORIGINS in the environment for non-local deployments.
_allowed_origins = [
    "http://localhost:3000",
    "http://localhost:5173",
    "http://localhost:8000",
    "http://127.0.0.1:8000",
    "http://127.0.0.1:3000",
]
app.add_middleware(
    CORSMiddleware,
    allow_origins=_allowed_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "X-Session-Token"],
)

@app.get("/health", tags=["Health & Probes"])
def liveness_probe():
    """
    Standard liveness probe showing product status and clear DEMO label.
    """
    return {
        "status": "healthy",
        "service": settings.PROJECT_NAME,
        "version": settings.VERSION,
        "is_demo_mode": settings.IS_DEMO_MODE,
        "banner": settings.DEMO_BANNER_TEXT
    }

@app.get("/health/ready", tags=["Health & Probes"])
def readiness_probe():
    """
    Readiness probe verifying engine and storage readiness without exposing internal paths.
    """
    return {
        "status": "ready",
        "validation_engine": "operational",
        "is_demo_mode": settings.IS_DEMO_MODE
    }

# Mount API v1 routes
app.include_router(auth_router, prefix=settings.API_V1_PREFIX)
app.include_router(validation_router, prefix=settings.API_V1_PREFIX)
app.include_router(orchestrator_router, prefix=settings.API_V1_PREFIX)
app.include_router(applications_router, prefix=settings.API_V1_PREFIX)
app.include_router(audit_router, prefix=settings.API_V1_PREFIX)
app.include_router(verification_router, prefix=settings.API_V1_PREFIX)
app.include_router(comparison_router, prefix=settings.API_V1_PREFIX)
app.include_router(documents_router, prefix=settings.API_V1_PREFIX)


# Mount interactive static frontend at root
import os
from fastapi.staticfiles import StaticFiles

static_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "static")
if os.path.exists(static_dir):
    app.mount("/", StaticFiles(directory=static_dir, html=True), name="static")
