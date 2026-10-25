"""
Pure, dependency-free upload validation for PRAMAAN-AI document intake.

The client file picker is not trusted:
- Explicit extension allowlist (.pdf, .jpg, .jpeg, .png)
- File signature must identify an allowed type
- The filename extension and detected MIME type must agree
"""
import os
from typing import Optional, Tuple

MAX_UPLOAD_SIZE_BYTES = 25 * 1024 * 1024  # 25 MiB
# Multipart boundaries/headers add overhead beyond the uploaded file bytes.
MULTIPART_OVERHEAD_ALLOWANCE = 64 * 1024

ALLOWED_EXTENSIONS = {
    ".pdf": "application/pdf",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".png": "image/png",
}

MAGIC_SIGNATURES = (
    (b"%PDF-", "application/pdf"),
    (b"\xff\xd8\xff", "image/jpeg"),
    (b"\x89PNG\r\n\x1a\n", "image/png"),
)


def detect_mime(content: bytes) -> Optional[str]:
    """Return the MIME type identified by the file signature, or None if unrecognised."""
    for prefix, mime in MAGIC_SIGNATURES:
        if content.startswith(prefix):
            return mime
    return None


def validate_upload(clean_filename: str, content: bytes) -> Tuple[Optional[str], Optional[str]]:
    """Return (detected MIME, error message); an accepted file has no error message."""
    if not content:
        return None, "Uploaded file is empty."
    ext = os.path.splitext(clean_filename)[1].lower()
    if ext not in ALLOWED_EXTENSIONS:
        return None, f"Extension '{ext}' is prohibited by file upload policy. Allowed extensions: .pdf, .jpg, .jpeg, .png."
    detected = detect_mime(content)
    if detected is None:
        return None, "File magic bytes do not match an allowed format (PDF, JPEG, PNG)."
    if ALLOWED_EXTENSIONS[ext] != detected:
        return None, (
            f"File extension '{ext}' does not match the detected content type ({detected}); upload rejected."
        )
    return detected, None
