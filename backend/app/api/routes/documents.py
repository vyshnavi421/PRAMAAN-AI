
"""
PRAMAAN-AI Protected Documents & Secure Ingestion API Routes

Security controls:
1. Institution-level document access authorization.
2. Upload size limit of 25 MB.
3. Allowed extensions: PDF, JPEG, PNG.
4. Magic-byte validation and extension/MIME consistency.
5. Filename sanitization and internal UUID storage keys.
6. SHA-256 integrity calculation.
7. Audit events for document access and uploads.
8. Document-type content validation before storage.
"""

from typing import Optional
import os
import re
import uuid
import hashlib

from fastapi import (
    APIRouter,
    HTTPException,
    Path,
    Depends,
    UploadFile,
    File,
    Form,
    Response,
)

from app.models.enums import (
    DocumentType,
    DocumentVerificationStatus,
)
from app.models.domain import Document, ApplicationInput
from app.core.auth import (
    get_current_user,
    require_roles,
    UserRole,
    UserContext,
)
from app.services.application_service import global_application_service
from app.services.audit_service import global_audit_service
from app.services.document_storage import global_document_storage
from app.services.document_extractor import (
    global_document_extractor,
    DocumentTypeMismatchError,
)


router = APIRouter(
    prefix="",
    tags=["Protected Documents & Secure Upload"],
)


# Upload policy
MAX_UPLOAD_SIZE_BYTES = 25 * 1024 * 1024

ALLOWED_EXTENSIONS = {
    ".pdf",
    ".jpg",
    ".jpeg",
    ".png",
}

ALLOWED_MAGIC_SIGNATURES = {
    b"%PDF-": ("application/pdf", {".pdf"}),
    b"\xff\xd8\xff": ("image/jpeg", {".jpg", ".jpeg"}),
    b"\x89PNG\r\n\x1a\n": ("image/png", {".png"}),
}

WRITE_ROLES = [
    UserRole.INSTITUTION_USER,
    UserRole.REVIEWER,
]


def sanitize_filename(filename: str) -> str:
    """Remove directory components and unsafe filename characters."""

    normalized = filename.replace("\\", "/")
    clean = os.path.basename(normalized)
    clean = re.sub(r"[^A-Za-z0-9_.-]", "_", clean)
    clean = re.sub(r"\.{2,}", "_", clean)
    clean = clean.strip("._")

    return clean or f"document_{uuid.uuid4().hex[:8]}.pdf"


def verify_document_ownership(
    current_user: UserContext,
    document_id: str,
) -> tuple[ApplicationInput, Document]:
    """Find a document and enforce institution-level access restrictions."""

    found = global_application_service.find_document(document_id)

    if not found:
        raise HTTPException(
            status_code=404,
            detail=f"Document '{document_id}' not found.",
        )

    app, doc = found

    if current_user.role == UserRole.INSTITUTION_USER:
        if (
            current_user.institution_id
            and app.institution_id != current_user.institution_id
        ):
            raise HTTPException(
                status_code=403,
                detail="Forbidden: You are not authorized to access this document.",
            )

    return app, doc


@router.get(
    "/documents/retention-policy",
    summary="Statutory data retention and disposal specifications",
)
def get_retention_policy():
    """Return the prototype's data retention policy."""

    return {
        "framework": "Digital Personal Data Protection (DPDP) Act 2023 & AICTE Guidelines",
        "demo_mode": True,
        "policy": (
            "In this prototype demonstration, synthetic dossiers are retained "
            "in protected storage for evaluation. Production retention and "
            "disposal must follow applicable legal and institutional requirements."
        ),
        "threat_model_reference": "docs/THREAT_MODEL.md Section 4",
    }


@router.get(
    "/documents/{document_id}",
    response_model=Document,
    summary="Get protected document metadata",
)
def get_document(
    document_id: str = Path(..., description="Document UUID"),
    current_user: UserContext = Depends(get_current_user),
):
    """Return document metadata and record the access event."""

    app, doc = verify_document_ownership(current_user, document_id)

    global_audit_service.record_event(
        actor_id=current_user.user_id,
        event_type="DOCUMENT_ACCESSED",
        details={
            "document_id": doc.id,
            "filename": doc.original_filename,
            "document_type": doc.document_type.value,
            "actor_role": current_user.role.value,
            "institution_id": app.institution_id,
        },
        application_id=app.application_id,
    )

    global_application_service.persist()

    return doc


@router.get(
    "/documents/{document_id}/content",
    summary="Get protected document binary content",
)
def get_document_content(
    document_id: str = Path(..., description="Document UUID"),
    current_user: UserContext = Depends(get_current_user),
):
    """Return document bytes after checking authorization."""

    _, doc = verify_document_ownership(current_user, document_id)

    content_bytes = global_document_storage.get_document_bytes(
        doc.storage_key,
        doc.id,
    )

    if not content_bytes:
        raise HTTPException(
            status_code=404,
            detail=f"Protected document bytes for '{document_id}' not found.",
        )

    return Response(
        content=content_bytes,
        media_type=doc.mime_type or "application/octet-stream",
        headers={
            "Content-Disposition": f'inline; filename="{doc.original_filename}"',
            "X-Content-Type-Options": "nosniff",
        },
    )


@router.post(
    "/documents/upload",
    response_model=Document,
    status_code=201,
    summary="Secure document upload with file validation",
)
async def upload_document(
    file: UploadFile = File(
        ...,
        description="PDF, JPEG, or PNG file up to 25 MB",
    ),
    document_type: str = Form(..., description="DocumentType enum string"),
    application_id: str = Form(..., description="Application UUID"),
    current_user: UserContext = Depends(require_roles(WRITE_ROLES)),
):
    """
    Validate the upload before storage:
    - Allow only PDF, JPEG, and PNG extensions.
    - Match the extension against the detected file signature.
    - Reject files larger than 25 MB.
    - Check readable document contents against the selected type.
    - Store using an internal UUID and calculate SHA-256.
    """

    # 1. Verify that the application exists.
    app = global_application_service.get_application(application_id)

    if not app:
        raise HTTPException(
            status_code=404,
            detail=f"Application '{application_id}' not found.",
        )

    # 2. Enforce institution-level upload authorization.
    if current_user.role == UserRole.INSTITUTION_USER:
        if (
            current_user.institution_id
            and app.institution_id != current_user.institution_id
        ):
            raise HTTPException(
                status_code=403,
                detail="Forbidden: You cannot upload to another institution's dossier.",
            )

    # 3. Sanitize the filename and check the extension.
    raw_filename = file.filename or ""
    clean_filename = sanitize_filename(raw_filename)
    ext = os.path.splitext(clean_filename)[1].lower()

    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=(
                f"Unsupported file extension '{ext}'. "
                "Only PDF, JPG, JPEG, and PNG files are allowed."
            ),
        )

    # 4. Read no more than one byte beyond the size limit.
    content = await file.read(MAX_UPLOAD_SIZE_BYTES + 1)

    if len(content) > MAX_UPLOAD_SIZE_BYTES:
        raise HTTPException(
            status_code=413,
            detail="File exceeds the maximum allowed size of 25 MB.",
        )

    if not content:
        raise HTTPException(
            status_code=400,
            detail="The uploaded file is empty.",
        )

    # 5. Check the file signature against the extension.
    detected_mime = None

    for magic_prefix, (mime, valid_extensions) in ALLOWED_MAGIC_SIGNATURES.items():
        if content.startswith(magic_prefix):
            if ext not in valid_extensions:
                raise HTTPException(
                    status_code=400,
                    detail=(
                        f"The file extension '{ext}' does not match "
                        f"the detected format '{mime}'."
                    ),
                )

            detected_mime = mime
            break

    if detected_mime is None:
        raise HTTPException(
            status_code=400,
            detail=(
                "Invalid file content. Only PDF, JPEG, and PNG "
                "file signatures are accepted."
            ),
        )

    # 6. Validate the selected document type.
    try:
        doc_type_enum = DocumentType(document_type)
    except ValueError as exc:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid DocumentType '{document_type}'.",
        ) from exc

    # 7. Validate actual contents BEFORE storing the upload.
    #
    # The current document extractor performs text extraction/OCR and raises
    # DocumentTypeMismatchError when readable content does not match the
    # selected document type.
    #
    # This extractor currently processes PDFs. Do not pass JPEG/PNG bytes
    # into the PDF parser: route image uploads for manual review unless your
    # extractor has a dedicated image OCR path.
    if detected_mime == "application/pdf":
        try:
            extracted_fields, initial_status, note = (
                global_document_extractor.extract_document(
                    content_bytes=content,
                    doc_type=doc_type_enum,
                    original_filename=clean_filename,
                )
            )
        except DocumentTypeMismatchError as exc:
            raise HTTPException(
                status_code=400,
                detail=str(exc),
            ) from exc
        except Exception as exc:
            raise HTTPException(
                status_code=400,
                detail=(
                    "The PDF could not be validated. Please upload a valid "
                    "PDF document or submit it for manual review."
                ),
            ) from exc
    else:
        # The supplied extractor uses pypdf and is PDF-only. Avoid trying to
        # parse an image as a PDF. Images need a separate image OCR validator.
        extracted_fields = []
        initial_status = DocumentVerificationStatus.MANUAL_REVIEW_REQUIRED
        note = (
            "Image uploaded successfully, but document-type validation "
            "requires an image OCR pipeline; manual review is required."
        )

    # 8. Prepare identifiers and the integrity hash only after validation.
    doc_uuid = str(uuid.uuid4())
    sha256_hash = hashlib.sha256(content).hexdigest()

    logical_storage_key = (
        f"storage/protected/{app.institution_id}/{doc_uuid}.bin"
    )

    new_doc: Optional[Document] = None
    storage_written = False

    # 9. Store bytes, persist metadata, and audit the upload.
    try:
        global_document_storage.store_document(
            app.institution_id,
            doc_uuid,
            content,
        )
        storage_written = True

        new_doc = Document(
            id=doc_uuid,
            application_id=application_id,
            document_type=doc_type_enum,
            original_filename=clean_filename,
            storage_key=logical_storage_key,
            file_size_bytes=len(content),
            mime_type=detected_mime,
            sha256_hash=sha256_hash,
            verification_status=initial_status,
            extracted_fields=extracted_fields,
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
                "extraction_note": note,
            },
            application_id=application_id,
        )

    except Exception:
        if new_doc is not None and new_doc in app.documents:
            app.documents.remove(new_doc)

            try:
                global_application_service.persist()
            except Exception:
                pass

        if storage_written:
            try:
                global_document_storage.delete_document(
                    app.institution_id,
                    doc_uuid,
                )
            except Exception:
                pass

        raise

    return new_doc


@router.post(
    "/documents/{document_id}/extract",
    response_model=Document,
    summary="Trigger document extraction/OCR pipeline",
)
def extract_document_fields(
    document_id: str = Path(..., description="Document UUID"),
    current_user: UserContext = Depends(require_roles(WRITE_ROLES)),
):
    """Re-extract fields from a stored document."""

    app, doc = verify_document_ownership(current_user, document_id)

    if global_document_storage.is_demo_seed_key(doc.storage_key):
        raise HTTPException(
            status_code=409,
            detail=(
                "Seeded demo documents have no stored binary; "
                "extraction is unavailable."
            ),
        )

    content_bytes = global_document_storage.get_document_bytes(
        doc.storage_key,
        doc.id,
    )

    if not content_bytes:
        raise HTTPException(
            status_code=404,
            detail=f"Protected document bytes for '{document_id}' not found.",
        )

    try:
        extracted, rec_status, note = (
            global_document_extractor.extract_document(
                content_bytes=content_bytes,
                doc_type=doc.document_type,
                original_filename=doc.original_filename,
            )
        )
    except DocumentTypeMismatchError as exc:
        raise HTTPException(
            status_code=400,
            detail=str(exc),
        ) from exc
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail="Extraction failed; the document was left unchanged.",
        ) from exc

    if extracted:
        doc.extracted_fields = extracted

        if rec_status == DocumentVerificationStatus.MANUAL_REVIEW_REQUIRED:
            doc.verification_status = rec_status

        global_application_service.persist()

    elif not doc.extracted_fields:
        if rec_status == DocumentVerificationStatus.MANUAL_REVIEW_REQUIRED:
            doc.verification_status = rec_status
            global_application_service.persist()
    else:
        note = (
            "Re-extraction produced no fields; existing fields preserved. "
            f"({note})"
        )

    global_audit_service.record_event(
        actor_id=current_user.user_id,
        event_type="DOCUMENT_EXTRACTION_COMPLETED",
        details={
            "document_id": doc.id,
            "fields_extracted": len(doc.extracted_fields),
            "document_type": doc.document_type.value,
            "status": doc.verification_status.value,
            "note": note,
        },
        application_id=app.application_id,
    )

    return doc
