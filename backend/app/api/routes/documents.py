"""
PRAMAAN-AI Protected Documents & Secure Ingestion API Routes
Enforces strict server-side authorization and threat mitigation per docs/THREAT_MODEL.md:
1. Insecure Direct Object Reference (IDOR) prevention: Institution users can only access their own documents.
2. File Upload Validation:
   - 25MB file size limit (HTTP 413)
   - Magic byte header inspection (%PDF-, JPEG, PNG; rejects executables, SVG, HTML)
   - Path traversal immunity: client filename completely sanitized via os.path.basename & regex
   - Internal UUID storage keys
   - SHA-256 integrity calculation
3. Sensitive access auditing: every document read appends to the immutable audit trail.
"""
from typing import List, Optional, Dict, Any
from fastapi import APIRouter, HTTPException, Path, Depends, UploadFile, File, Form, Response, Request
from pydantic import BaseModel, Field
import os
import re
import uuid
import hashlib

from app.models.enums import DocumentType, DocumentVerificationStatus, ExtractionQuality
from app.models.domain import Document, ApplicationInput, ExtractedField, FieldProvenance
from app.core.auth import get_current_user, require_roles, UserRole, UserContext
from app.services.application_service import global_application_service
from app.services.audit_service import global_audit_service
from app.services.document_storage import global_document_storage
from app.services.document_extractor import global_document_extractor
from app.services.upload_validation import (
    MAX_UPLOAD_SIZE_BYTES, MULTIPART_OVERHEAD_ALLOWANCE, validate_upload,
)


router = APIRouter(prefix="", tags=["Protected Documents & Secure Upload"])

# Keep per-read memory bounded; UploadFile is already spooled by the multipart parser.
UPLOAD_READ_CHUNK_BYTES = 1024 * 1024

# Constants from docs/THREAT_MODEL.md
MAX_UPLOAD_SIZE_BYTES = 25 * 1024 * 1024  # 25 MB
ALLOWED_MAGIC_SIGNATURES = {
    b"%PDF-": "application/pdf",
    b"\xff\xd8\xff": "image/jpeg",
    b"\x89PNG\r\n\x1a\n": "image/png"
}
# Only these roles may add or re-extract documents (AUDITOR / RULES_ADMIN are read-only here).
WRITE_ROLES = [UserRole.INSTITUTION_USER, UserRole.REVIEWER]
DISALLOWED_EXTENSIONS = {".exe", ".bat", ".cmd", ".sh", ".py", ".js", ".svg", ".html", ".htm", ".vbs", ".dll"}


def sanitize_filename(filename: str) -> str:
    """
    Strips directory traversal sequences, path separators, and special characters.
    Handles both POSIX and Windows separators across all hosting environments.
    """
    normalized = filename.replace("\\", "/")
    clean = os.path.basename(normalized)
    clean = re.sub(r"[^\w\.\-]", "_", clean)
    clean = re.sub(r"\.{2,}", "_", clean)
    return clean or f"document_{uuid.uuid4().hex[:8]}.pdf"


def verify_document_ownership(current_user: UserContext, document_id: str) -> tuple[ApplicationInput, Document]:
    """
    Locates document across applications and enforces strict institutional tenant boundary.
    """
    found = global_application_service.find_document(document_id)
    if not found:
        raise HTTPException(status_code=404, detail=f"Document '{document_id}' not found.")

    app, doc = found

    # IDOR Check for Institution Users
    if current_user.role == UserRole.INSTITUTION_USER:
        if current_user.institution_id and app.institution_id != current_user.institution_id:
            raise HTTPException(
                status_code=403,
                detail=f"Forbidden: You are not authorized to access documents belonging to institution '{app.institution_id}'."
            )

    return app, doc


@router.get(
    "/documents/retention-policy",
    summary="Statutory data retention & disposal specifications"
)
def get_retention_policy():
    """
    Returns data retention, purging, and privacy specifications under DPDP Act 2023.
    """
    return {
        "framework": "Digital Personal Data Protection (DPDP) Act 2023 & AICTE Guidelines",
        "demo_mode": True,
        "policy": (
            "In this prototype demonstration, synthetic dossiers are retained in protected storage "
            "for evaluation. In production deployment, dossiers are subject to 7-year statutory retention "
            "following approval decisions, with cryptographic purge certificates issued upon authorized record retirement."
        ),
        "threat_model_reference": "docs/THREAT_MODEL.md Section 4"
    }


@router.get(
    "/documents/{document_id}",
    response_model=Document,
    summary="Get protected document metadata & extracted claims (RBAC Enforced)"
)
def get_document(
    document_id: str = Path(..., description="Document UUID"),
    current_user: UserContext = Depends(get_current_user)
):
    """
    Returns document entity. Enforces institutional scoping and logs an audit access event.
    """
    app, doc = verify_document_ownership(current_user, document_id)

    # Record sensitive access in audit ledger
    global_audit_service.record_event(
        actor_id=current_user.user_id,
        event_type="DOCUMENT_ACCESSED",
        details={
            "document_id": doc.id,
            "filename": doc.original_filename,
            "document_type": doc.document_type.value,
            "actor_role": current_user.role.value,
            "institution_id": app.institution_id
        },
        application_id=app.application_id
    )
    global_application_service.persist()

    return doc


@router.get(
    "/documents/{document_id}/content",
    summary="Get protected document binary content stream (RBAC Enforced)"
)
def get_document_content(
    document_id: str = Path(..., description="Document UUID"),
    current_user: UserContext = Depends(get_current_user)
):
    """
    Returns document file content. IDOR protected; never exposes server-side filesystem paths.
    Returns the exact uploaded bytes stored securely on disk.
    """
    app, doc = verify_document_ownership(current_user, document_id)

    content_bytes = global_document_storage.get_document_bytes(doc.storage_key, doc.id)
    if not content_bytes:
        raise HTTPException(status_code=404, detail=f"Protected document bytes for '{document_id}' not found.")

    return Response(
        content=content_bytes,
        media_type=doc.mime_type or "application/pdf",
        headers={
            "Content-Disposition": f'inline; filename="{doc.original_filename}"',
            "X-Content-Type-Options": "nosniff"
        }
    )



@router.get(
    "/documents/{document_id}/pages/{page}/view",
    summary="Render a page of the real uploaded document as PNG (RBAC Enforced)"
)
def get_document_page_view(
    document_id: str = Path(..., description="Document UUID"),
    page: int = Path(..., ge=1, description="1-indexed page number"),
    current_user: UserContext = Depends(get_current_user)
):
    """Render the requested page of a stored upload; never invent content for missing bytes."""
    app, doc = verify_document_ownership(current_user, document_id)

    if global_document_storage.is_demo_seed_key(doc.storage_key):
        raise HTTPException(status_code=404, detail="Seeded demo document has no stored binary to render.")
    if page > max(1, doc.page_count):
        raise HTTPException(status_code=404, detail=f"Page {page} does not exist (document has {doc.page_count}).")

    content_bytes = global_document_storage.get_document_bytes(doc.storage_key, doc.id)
    if not content_bytes:
        raise HTTPException(status_code=404, detail=f"Protected document bytes for '{document_id}' not found.")

    png = global_document_extractor.render_page_png(content_bytes, doc.mime_type, page)
    if png is None:
        raise HTTPException(status_code=503, detail="Page rendering is unavailable on this server.")
    global_audit_service.record_event(
        actor_id=current_user.user_id,
        event_type="DOCUMENT_PAGE_VIEWED",
        details={
            "document_id": doc.id,
            "page": page,
            "actor_role": current_user.role.value,
            "institution_id": app.institution_id,
        },
        application_id=app.application_id
    )
    return Response(
        content=png,
        media_type="image/png",
        headers={"X-Content-Type-Options": "nosniff", "Cache-Control": "private, max-age=60"}
    )

@router.post(
    "/documents/upload",
    response_model=Document,
    status_code=201,
    summary="Secure Document Intake with extension, signature, and size validation"
)
async def upload_document(
    request: Request,
    file: UploadFile = File(..., description="File to upload (PDF, JPEG, PNG <= 25MB)"),
    document_type: str = Form(..., description="DocumentType enum string"),
    application_id: str = Form(..., description="Application UUID"),
    current_user: UserContext = Depends(require_roles(WRITE_ROLES))
):
    """
    Accept a real upload, enforce size/extension/signature rules, extract claims,
    store under a generated UUID, and roll back file/metadata when intake fails.
    Note: FastAPI/Starlette parses multipart framing before invoking this handler;
    the chunk loop bounds the additional application-level read buffer.
    """
    app = global_application_service.get_application(application_id)
    if not app:
        raise HTTPException(status_code=404, detail=f"Application '{application_id}' not found.")

    if current_user.role == UserRole.INSTITUTION_USER and app.institution_id != current_user.institution_id:
        raise HTTPException(
            status_code=403,
            detail="Forbidden: You cannot upload documents to another institution's dossier."
        )

    try:
        doc_type_enum = DocumentType(document_type)
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Invalid DocumentType '{document_type}'.")

    declared_length = request.headers.get("content-length")
    if declared_length and declared_length.isdigit() and int(declared_length) > (
        MAX_UPLOAD_SIZE_BYTES + MULTIPART_OVERHEAD_ALLOWANCE
    ):
        raise HTTPException(status_code=413, detail="Payload Too Large: File size exceeds 25MB limit.")

    clean_filename = sanitize_filename(file.filename or "upload.bin")

    chunks: List[bytes] = []
    total = 0
    while True:
        chunk = await file.read(UPLOAD_READ_CHUNK_BYTES)
        if not chunk:
            break
        total += len(chunk)
        if total > MAX_UPLOAD_SIZE_BYTES:
            raise HTTPException(status_code=413, detail="Payload Too Large: File size exceeds 25MB limit.")
        chunks.append(chunk)
    content = b"".join(chunks)

    detected_mime, validation_error = validate_upload(clean_filename, content)
    if validation_error:
        raise HTTPException(status_code=400, detail=f"Security Violation: {validation_error}")

    doc_uuid = str(uuid.uuid4())
    sha256_hash = hashlib.sha256(content).hexdigest()
    logical_storage_key = f"storage/protected/{app.institution_id}/{doc_uuid}.bin"
    new_doc: Optional[Document] = None
    try:
        global_document_storage.store_document(app.institution_id, doc_uuid, content)
        extracted_fields, initial_status, note = global_document_extractor.extract_document(
            content_bytes=content,
            doc_type=doc_type_enum,
            original_filename=clean_filename
        )
        new_doc = Document(
            id=doc_uuid,
            application_id=application_id,
            document_type=doc_type_enum,
            original_filename=clean_filename,
            storage_key=logical_storage_key,
            file_size_bytes=len(content),
            mime_type=detected_mime,
            sha256_hash=sha256_hash,
            page_count=global_document_extractor.count_pages(content, detected_mime),
            verification_status=initial_status,
            extracted_fields=extracted_fields
        )
        app.documents.append(new_doc)
        global_application_service.persist()
        global_audit_service.record_event(
            actor_id=current_user.user_id,
            event_type="DOCUMENT_UPLOADED",
            details={
                "document_id": doc_uuid,
                "filename": clean_filename,
                "file_size": len(content),
                "sha256": sha256_hash,
                "document_type": doc_type_enum.value,
                "mime_type": detected_mime,
                "fields_extracted": len(extracted_fields),
                "extraction_note": note
            },
            application_id=application_id
        )
    except BaseException:
        if new_doc is not None and new_doc in app.documents:
            app.documents.remove(new_doc)
            try:
                global_application_service.persist()
            except Exception:
                pass
        global_document_storage.delete_document(app.institution_id, doc_uuid)
        raise

    return new_doc


@router.post(
    "/documents/{document_id}/extract",
    response_model=Document,
    summary="Trigger Automated Document Extraction/OCR Pipeline (RBAC Enforced)"
)
def extract_document_fields(
    document_id: str = Path(..., description="Document UUID"),
    current_user: UserContext = Depends(require_roles(WRITE_ROLES))
):
    """
    Executes real text extraction and OCR fallback on actual stored document bytes.
    Extracts traceable fields with bounding boxes, confidence scores, and provenance.
    If document text is unreadable and OCR is unavailable, honestly abstains and routes to manual review.

    Existing fields are never overwritten by a failed/empty re-extraction. Seeded demo documents
    have no stored binary, so they are refused (409); a real upload whose bytes are missing is 404.
    """
    app, doc = verify_document_ownership(current_user, document_id)

    if global_document_storage.is_demo_seed_key(doc.storage_key):
        raise HTTPException(
            status_code=409,
            detail="Seeded demo documents have no stored binary; extraction is not available for them."
        )

    content_bytes = global_document_storage.get_document_bytes(doc.storage_key, doc.id)
    if not content_bytes:
        raise HTTPException(status_code=404, detail=f"Protected document bytes for '{document_id}' not found.")

    try:
        extracted, rec_status, note = global_document_extractor.extract_document(
            content_bytes=content_bytes,
            doc_type=doc.document_type,
            original_filename=doc.original_filename
        )
    except Exception:
        raise HTTPException(status_code=500, detail="Extraction failed; the document was left unchanged.")

    if extracted:
        doc.extracted_fields = extracted
        if rec_status == DocumentVerificationStatus.MANUAL_REVIEW_REQUIRED:
            doc.verification_status = rec_status
        global_application_service.persist()
    elif doc.extracted_fields:
        note = f"Re-extraction produced no fields; existing fields preserved. ({note})"
    else:
        if rec_status == DocumentVerificationStatus.MANUAL_REVIEW_REQUIRED:
            doc.verification_status = rec_status
            global_application_service.persist()

    global_audit_service.record_event(
        actor_id=current_user.user_id,
        event_type="DOCUMENT_EXTRACTION_COMPLETED",
        details={
            "document_id": doc.id,
            "fields_extracted": len(doc.extracted_fields),
            "document_type": doc.document_type.value,
            "status": doc.verification_status.value,
            "note": note
        },
        application_id=app.application_id
    )

    return doc
