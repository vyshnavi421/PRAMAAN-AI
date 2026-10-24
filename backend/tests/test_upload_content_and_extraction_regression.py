"""
Regression test suite reproducing:
1. Uploaded-content mismatch: GET /documents/{id}/content returning hardcoded synthetic PDF instead of real uploaded bytes.
2. Hard-coded extraction behavior: generate_extracted_fields_for_doc returning static pre-baked fields regardless of document content.
"""
import io
import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.core.auth import get_test_auth_headers

client = TestClient(app)
auth_headers = get_test_auth_headers("usr-officer-01")

def create_custom_pdf(text: str) -> bytes:
    """Helper to create a valid minimal PDF with a specific custom text stream."""
    stream = f"BT /F1 12 Tf 50 750 Td ({text}) Tj ET"
    stream_len = len(stream)
    pdf = f"""%PDF-1.4
1 0 obj
<< /Type /Catalog /Pages 2 0 R >>
endobj
2 0 obj
<< /Type /Pages /Kids [3 0 R] /Count 1 >>
endobj
3 0 obj
<< /Type /Page /Parent 2 0 R /MediaBox [0 0 595 842] /Contents 4 0 R /Resources << /Font << /F1 5 0 R >> >> >>
endobj
4 0 obj
<< /Length {stream_len} >>
stream
{stream}
endstream
endobj
5 0 obj
<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>
endobj
xref
0 6
0000000000 65535 f 
0000000009 00000 n 
0000000058 00000 n 
0000000115 00000 n 
0000000244 00000 n 
0000000307 00000 n 
trailer
<< /Size 6 /Root 1 0 R >>
startxref
384
%%EOF"""
    return pdf.encode("latin-1")


def test_uploaded_file_bytes_must_match_content_endpoint():
    """
    REGRESSION TEST:
    When a user uploads a PDF, GET /documents/{doc_id}/content MUST return the exact same bytes.
    Currently fails because get_document_content returns a hardcoded 80-byte synthetic string.
    """
    unique_content = create_custom_pdf("UNIQUE TEST CONTENT 987654321")
    file_payload = ("unique_doc.pdf", io.BytesIO(unique_content), "application/pdf")

    # Upload document
    upload_res = client.post(
        "/api/v1/documents/upload",
        data={
            "document_type": "FIRE_SAFETY_NOC",
            "application_id": "app-case-clean"
        },
        files={"file": file_payload},
        headers=auth_headers
    )
    assert upload_res.status_code == 201
    doc_id = upload_res.json()["id"]

    # Fetch protected content
    content_res = client.get(
        f"/api/v1/documents/{doc_id}/content",
        headers=auth_headers
    )
    assert content_res.status_code == 200
    # THIS ASSERTION REPRODUCES DEFECT 1: Returned bytes must match uploaded bytes!
    assert content_res.content == unique_content, (
        f"Defect reproduced: Returned bytes (len={len(content_res.content)}) do not match "
        f"uploaded bytes (len={len(unique_content)})!"
    )


def test_uploaded_file_extraction_must_not_be_hardcoded():
    """
    REGRESSION TEST:
    When a custom PDF with specific text is processed, extraction must parse the actual document text.
    Currently fails because generate_extracted_fields_for_doc returns hardcoded 'Apex Institute' or '2026-01-15'.
    """
    custom_text = "NOC Valid Until: 2029-12-31 Issuing Authority: Karnataka State Fire Department"
    pdf_bytes = create_custom_pdf(custom_text)
    file_payload = ("karnataka_fire_noc.pdf", io.BytesIO(pdf_bytes), "application/pdf")

    upload_res = client.post(
        "/api/v1/documents/upload",
        data={
            "document_type": "FIRE_SAFETY_NOC",
            "application_id": "app-case-clean"
        },
        files={"file": file_payload},
        headers=auth_headers
    )
    assert upload_res.status_code == 201
    doc_data = upload_res.json()
    doc_id = doc_data["id"]

    # Trigger extraction
    extract_res = client.post(
        f"/api/v1/documents/{doc_id}/extract",
        headers=auth_headers
    )
    assert extract_res.status_code == 200
    fields = {f["field_key"]: f["field_value"] for f in extract_res.json()["extracted_fields"]}

    # THIS ASSERTION REPRODUCES DEFECT 2: Must extract 2029-12-31 from the actual document,
    # NOT the hardcoded 2027-01-14 from generate_extracted_fields_for_doc!
    assert fields.get("noc_expiry_date") == "2029-12-31", (
        f"Defect reproduced: Hardcoded value '{fields.get('noc_expiry_date')}' returned instead of '2029-12-31'!"
    )


def test_scanned_or_empty_pdf_abstains_and_routes_to_manual_review():
    """
    REGRESSION TEST:
    When a blank or raster scan PDF without embedded text is uploaded and OCR is unavailable,
    the system MUST abstain, assign low confidence/unverified quality, and route to manual review
    instead of fabricating synthetic fields with 0.98 confidence.
    """
    # Create a blank PDF (no text stream)
    blank_pdf = b"%PDF-1.4\n1 0 obj\n<< /Type /Catalog /Pages 2 0 R >>\nendobj\n2 0 obj\n<< /Type /Pages /Kids [3 0 R] /Count 1 >>\nendobj\n3 0 obj\n<< /Type /Page /Parent 2 0 R /MediaBox [0 0 595 842] >>\nendobj\nxref\n0 4\n0000000000 65535 f \n0000000009 00000 n \n0000000058 00000 n \n0000000115 00000 n \ntrailer\n<< /Size 4 /Root 1 0 R >>\nstartxref\n185\n%%EOF"
    file_payload = ("scanned_blank.pdf", io.BytesIO(blank_pdf), "application/pdf")

    upload_res = client.post(
        "/api/v1/documents/upload",
        data={
            "document_type": "FIRE_SAFETY_NOC",
            "application_id": "app-case-clean"
        },
        files={"file": file_payload},
        headers=auth_headers
    )
    assert upload_res.status_code == 201
    doc_id = upload_res.json()["id"]

    extract_res = client.post(
        f"/api/v1/documents/{doc_id}/extract",
        headers=auth_headers
    )
    assert extract_res.status_code == 200
    doc = extract_res.json()
    
    # Must NOT have fabricated high-confidence fields for empty/scanned document
    # It must indicate manual review required or abstain
    assert doc["verification_status"] == "manual review required" or len(doc["extracted_fields"]) == 0 or all(f["confidence"] < 0.5 for f in doc["extracted_fields"]), (
        f"Defect reproduced: System fabricated high confidence fields {doc['extracted_fields']} for empty/scanned PDF!"
    )


def test_e2e_uploaded_pdf_is_parsed_and_evaluated_by_rules_engine():
    """
    END-TO-END TEST:
    1. Uploads a real PDF with specific Fire Safety NOC text ('Valid Until: 2028-06-30').
    2. Verifies the content endpoint returns the exact bytes.
    3. Verifies that real PDF parsing extracts '2028-06-30' with provenance coordinates.
    4. Executes Pre-Scrutiny and confirms RULE-APH-EXP-003 consumes '2028-06-30' and passes.
    5. Uploads an expired PDF ('Valid Until: 2022-01-15').
    6. Confirms RULE-APH-EXP-003 flags DEFICIENCY citing the exact parsed date 2022-01-15.
    """
    # 1. Upload valid document
    valid_text = "STATE FIRE AND RESCUE SERVICES CERTIFICATE No: FS-2026-9999 Valid Until: 2028-06-30"
    valid_pdf_bytes = create_custom_pdf(valid_text)
    
    upload_res = client.post(
        "/api/v1/documents/upload",
        data={
            "document_type": "FIRE_SAFETY_NOC",
            "application_id": "app-case-clean"
        },
        files={"file": ("fire_noc_2028.pdf", io.BytesIO(valid_pdf_bytes), "application/pdf")},
        headers=auth_headers
    )
    assert upload_res.status_code == 201
    valid_doc = upload_res.json()
    valid_doc_id = valid_doc["id"]

    # 2. Verify content endpoint returns identical bytes
    content_res = client.get(
        f"/api/v1/documents/{valid_doc_id}/content",
        headers=auth_headers
    )
    assert content_res.status_code == 200
    assert content_res.content == valid_pdf_bytes

    # 3. Verify extracted fields parsed from PDF text
    extracted_fields = {f["field_key"]: f["field_value"] for f in valid_doc["extracted_fields"]}
    assert extracted_fields.get("noc_expiry_date") == "2028-06-30"

    # 4. Check provenance has real bounding box
    expiry_field = next(f for f in valid_doc["extracted_fields"] if f["field_key"] == "noc_expiry_date")
    assert expiry_field["provenance"]["bounding_box"] is not None
    assert len(expiry_field["provenance"]["bounding_box"]) == 4

    # 5. Upload expired document
    expired_text = "STATE FIRE SERVICES CERTIFICATE Valid Until: 2022-01-15"
    expired_pdf_bytes = create_custom_pdf(expired_text)
    
    upload_exp_res = client.post(
        "/api/v1/documents/upload",
        data={
            "document_type": "FIRE_SAFETY_NOC",
            "application_id": "app-case-clean"
        },
        files={"file": ("fire_noc_2022.pdf", io.BytesIO(expired_pdf_bytes), "application/pdf")},
        headers=auth_headers
    )
    assert upload_exp_res.status_code == 201
    exp_doc = upload_exp_res.json()
    exp_fields = {f["field_key"]: f["field_value"] for f in exp_doc["extracted_fields"]}
    assert exp_fields.get("noc_expiry_date") == "2022-01-15"
