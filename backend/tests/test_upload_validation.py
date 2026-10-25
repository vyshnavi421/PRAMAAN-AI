"""Pure unit tests for the server-side document upload allowlist."""
import pytest

from app.services.upload_validation import ALLOWED_EXTENSIONS, detect_mime, validate_upload

PDF = b"%PDF-1.4\n%synthetic\n"
JPEG = b"\xff\xd8\xff\xe0" + b"\x00" * 16
PNG = b"\x89PNG\r\n\x1a\n" + b"\x00" * 16


def test_allowlist_is_exactly_the_four_supported_extensions():
    assert set(ALLOWED_EXTENSIONS) == {".pdf", ".jpg", ".jpeg", ".png"}


@pytest.mark.parametrize("name,content,mime", [
    ("a.pdf", PDF, "application/pdf"),
    ("a.PDF", PDF, "application/pdf"),
    ("a.jpg", JPEG, "image/jpeg"),
    ("a.jpeg", JPEG, "image/jpeg"),
    ("a.png", PNG, "image/png"),
])
def test_valid_signatures_and_extensions_are_accepted(name, content, mime):
    assert validate_upload(name, content) == (mime, None)


@pytest.mark.parametrize("name,content", [
    ("a.txt", PDF),
    ("noextension", PDF),
    ("a.exe", PDF),
    ("a.svg", b"<svg></svg>"),
    ("a.html", b"<html></html>"),
    ("a.pdf.exe", PDF),
    ("a.png", PDF),
    ("a.pdf", PNG),
    ("a.jpg", PNG),
    ("a.pdf", b"not a real pdf"),
    ("a.pdf", b""),
])
def test_invalid_extensions_signatures_and_empty_files_are_rejected(name, content):
    mime, error = validate_upload(name, content)
    assert mime is None and error


def test_detect_mime_from_signature():
    assert detect_mime(PDF) == "application/pdf"
    assert detect_mime(JPEG) == "image/jpeg"
    assert detect_mime(PNG) == "image/png"
    assert detect_mime(b"MZ\x90\x00") is None
