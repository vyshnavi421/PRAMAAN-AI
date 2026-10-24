# PRAMAAN-AI: REST API Contracts & Endpoint Specification

**Document Status:** Approved Architecture Baseline (Planning Only)  
**Version:** 1.0.0  
**Format:** OpenAPI 3.1 Compatible JSON/REST  
**Base URL:** `/api/v1`  
**Authentication:** Bearer Token (JWT / Session Cookie)  

---

## 1. Global Standards & Error Envelope

All API endpoints follow predictable HTTP status codes and return standardized error envelopes adhering to RFC 7807 (Problem Details).

### Standard Error Schema
```json
{
  "type": "https://pramaan-ai.aicte.gov.in/errors/VALIDATION_ERROR",
  "title": "Invalid Document Upload",
  "status": 400,
  "detail": "Uploaded file mime-type application/x-msdownload is not allowed.",
  "instance": "/api/v1/applications/4f7e2a9b-1234-4567-89ab-cdef01234567/documents",
  "timestamp": "2026-10-23T10:15:30.000Z",
  "errors": [
    {
      "field": "file",
      "code": "INVALID_MIME_TYPE",
      "message": "Only PDF, PNG, and JPEG files under 25MB are permitted."
    }
  ]
}
```

---

## 2. Role-Based Access Control (RBAC) Matrix

| Endpoint | Method | Allowed Roles | Audit Logged |
|---|---|---|:---:|
| `/health`, `/health/ready` | GET | Anonymous / All | No |
| `/applications` | GET | `institution_user` (scoped), `reviewer`, `auditor` | No |
| `/applications` | POST | `institution_user` | Yes |
| `/applications/{id}` | GET | `institution_user` (owner), `reviewer`, `auditor` | Yes |
| `/applications/{id}/documents` | POST | `institution_user` (owner), `reviewer` | Yes |
| `/documents/{id}` | GET | `institution_user` (owner), `reviewer`, `auditor` | No |
| `/documents/{id}/pages/{page}/view` | GET | `institution_user` (owner), `reviewer`, `auditor` | No |
| `/applications/{id}/validation-runs` | POST | `institution_user` (owner), `reviewer` | Yes |
| `/applications/{id}/validation-runs` | GET | `institution_user` (owner), `reviewer`, `auditor` | No |
| `/findings/{id}` | GET | `institution_user` (owner), `reviewer`, `auditor` | No |
| `/findings/{id}/review-actions` | POST | `reviewer` | Yes |
| `/applications/{id}/evidence-graph` | GET | `institution_user` (owner), `reviewer`, `auditor` | No |
| `/documents/{id}/verification-attempts`| POST | `reviewer` | Yes |
| `/applications/{id}/duplicates` | GET | `reviewer`, `auditor` | No |
| `/applications/{id}/compare-previous` | POST | `reviewer`, `auditor` | Yes |
| `/rule-packs` | GET | `reviewer`, `rules_admin`, `auditor` | No |
| `/rule-packs/{id}/test` | POST | `rules_admin` | Yes |
| `/rule-packs/{id}/activate` | POST | `rules_admin` | Yes |
| `/applications/{id}/audit-events` | GET | `auditor`, `reviewer` | Yes |
| `/audit/verify-chain` | POST | `auditor`, `rules_admin` | Yes |

---

## 3. Core API Endpoints

### 3.1 Health & Readiness
#### `GET /health`
- **Description:** Liveness probe.
- **Response 200 OK:**
```json
{
  "status": "healthy",
  "version": "1.0.0",
  "environment": "development",
  "is_demo_mode": true
}
```

#### `GET /health/ready`
- **Description:** Readiness probe checking database connectivity and document storage mounts without leaking credentials or local filesystem paths.
- **Response 200 OK:**
```json
{
  "status": "ready",
  "database": "connected",
  "storage": "writable"
}
```

---

### 3.2 Applications & Dossiers

#### `POST /applications`
- **Description:** Create a new synthetic application dossier.
- **Request Body:**
```json
{
  "institution_id": "9b1deb4d-3b7d-4bad-9bdd-2b0d7b3dcb6d",
  "academic_year": "2026-2027",
  "category": "EXTENSION_OF_APPROVAL",
  "declared_data": {
    "total_intake": 240,
    "faculty_count": 16,
    "builtup_area_sqm": 12500.0,
    "land_area_acres": 7.5
  }
}
```
- **Response 201 Created:**
```json
{
  "id": "e2a4b6c8-1111-2222-3333-444455556666",
  "application_number": "APP-2026-EOA-108",
  "institution_id": "9b1deb4d-3b7d-4bad-9bdd-2b0d7b3dcb6d",
  "academic_year": "2026-2027",
  "category": "EXTENSION_OF_APPROVAL",
  "workflow_status": "DRAFT",
  "is_synthetic": true,
  "created_at": "2026-10-23T11:00:00.000Z"
}
```

---

### 3.3 Secure Document Intake & Extraction

#### `POST /applications/{application_id}/documents`
- **Description:** Secure intake of PDF/Image documents.
- **Request:** `multipart/form-data`
  - `file`: Binary file (PDF, PNG, JPG, max 25MB)
  - `document_type`: `FIRE_SAFETY_NOC`
- **Response 202 Accepted:**
```json
{
  "id": "d1e2f3a4-5555-6666-7777-888899990000",
  "application_id": "e2a4b6c8-1111-2222-3333-444455556666",
  "document_type": "FIRE_SAFETY_NOC",
  "original_filename": "fire_safety_noc_2026.pdf",
  "file_size_bytes": 1048576,
  "mime_type": "application/pdf",
  "sha256_hash": "a1b2c3d4e5f60718293a4b5c6d7e8f901234567890abcdef1234567890abcdef",
  "page_count": 2,
  "verification_status": "verification pending",
  "processing_status": "PROCESSED",
  "created_at": "2026-10-23T11:05:00.000Z"
}
```

#### `GET /documents/{document_id}/extracted-fields`
- **Description:** Returns extracted factual claims with bounding-box provenance.
- **Response 200 OK:**
```json
{
  "document_id": "d1e2f3a4-5555-6666-7777-888899990000",
  "fields": [
    {
      "field_key": "noc_issue_date",
      "field_value": "2023-01-15",
      "raw_value": "15th January, 2023",
      "data_type": "DATE",
      "confidence": 0.982,
      "extraction_method": "PDF_TEXT_STREAM",
      "provenance": {
        "page_number": 1,
        "bounding_box": [0.12, 0.45, 0.35, 0.48],
        "surrounding_snippet": "Issued on this 15th January, 2023 by the State Fire Service",
        "quality_label": "HIGH"
      }
    },
    {
      "field_key": "noc_expiry_date",
      "field_value": "2024-01-14",
      "raw_value": "14/01/2024",
      "data_type": "DATE",
      "confidence": 0.965,
      "extraction_method": "PDF_TEXT_STREAM",
      "provenance": {
        "page_number": 1,
        "bounding_box": [0.12, 0.52, 0.32, 0.55],
        "surrounding_snippet": "Valid up to: 14/01/2024",
        "quality_label": "HIGH"
      }
    }
  ]
}
```

---

### 3.4 Validation Runs & Evidence Findings

#### `POST /applications/{application_id}/validation-runs`
- **Description:** Execute deterministic rule engine against application claims and documents.
- **Response 201 Created:**
```json
{
  "id": "v7e8f9a0-1234-5678-90ab-cdef12345678",
  "application_id": "e2a4b6c8-1111-2222-3333-444455556666",
  "rule_pack_id": "r1a2b3c4-9999-8888-7777-666655554444",
  "rule_pack_version": "v1.2.0",
  "executed_at": "2026-10-23T11:10:00.000Z",
  "overall_result": "DEFICIENCIES_DETECTED",
  "findings_count": {
    "compliant": 5,
    "deficiency": 1,
    "anomaly_signal": 0,
    "inconclusive": 0
  },
  "findings": [
    {
      "id": "f1a2b3c4-1111-2222-3333-444455556666",
      "rule_code": "RULE-APH-002",
      "rule_title": "Document Expiry & Validity Check",
      "clause_citation": "AICTE APH 2024-27 Clause 4.2(b)",
      "status": "DEFICIENCY",
      "reason": "Fire Safety NOC expired on 2024-01-14, which precedes the 2026-2027 academic submission cutoff.",
      "recommended_action": "Request current valid Fire Safety Certificate from institution.",
      "evidence": [
        {
          "document_id": "d1e2f3a4-5555-6666-7777-888899990000",
          "field_key": "noc_expiry_date",
          "extracted_value": "2024-01-14",
          "page_number": 1,
          "bounding_box": [0.12, 0.52, 0.32, 0.55]
        }
      ]
    }
  ]
}
```

---

### 3.5 Evidence Graph

#### `GET /applications/{application_id}/evidence-graph`
- **Description:** Retrieve nodes and edges representing the complete provenance graph for Cytoscape.js rendering.
- **Response 200 OK:**
```json
{
  "application_id": "e2a4b6c8-1111-2222-3333-444455556666",
  "nodes": [
    {
      "id": "app_node",
      "type": "Application",
      "label": "Application APP-2026-EOA-108",
      "data": { "status": "UNDER_SCRUTINY" }
    },
    {
      "id": "doc_fire_noc",
      "type": "Document",
      "label": "Fire Safety NOC",
      "data": { "verification_status": "expired" }
    },
    {
      "id": "claim_expiry",
      "type": "Claim",
      "label": "NOC Expiry: 2024-01-14",
      "data": { "confidence": 0.965, "page": 1 }
    },
    {
      "id": "rule_aph_002",
      "type": "Rule",
      "label": "RULE-APH-002 (Validity Check)",
      "data": { "version": "v1.2.0" }
    },
    {
      "id": "finding_deficiency_1",
      "type": "Finding",
      "label": "DEFICIENCY: Expired Fire NOC",
      "data": { "severity": "DEFICIENCY" }
    }
  ],
  "edges": [
    {
      "id": "e1",
      "source": "app_node",
      "target": "doc_fire_noc",
      "label": "CONTAINS_DOCUMENT"
    },
    {
      "id": "e2",
      "source": "doc_fire_noc",
      "target": "claim_expiry",
      "label": "EXTRACTED_FROM"
    },
    {
      "id": "e3",
      "source": "claim_expiry",
      "target": "rule_aph_002",
      "label": "EVALUATED_AGAINST"
    },
    {
      "id": "e4",
      "source": "rule_aph_002",
      "target": "finding_deficiency_1",
      "label": "PRODUCED_FINDING"
    }
  ]
}
```

---

### 3.6 Verification Ladder (External Issuer Adapters)

#### `POST /documents/{document_id}/verification-attempts`
- **Description:** Execute simulated/authorized issuer check returning exactly one of the 6 official states.
- **Request Body:**
```json
{
  "adapter_name": "SIMULATED_STATE_FIRE_SERVICE_ADAPTER",
  "request_reference": "NOC-FS-2023-8891"
}
```
- **Response 200 OK:**
```json
{
  "id": "att-9988-7766-5544-33221100aabb",
  "document_id": "d1e2f3a4-5555-6666-7777-888899990000",
  "adapter_name": "SIMULATED_STATE_FIRE_SERVICE_ADAPTER",
  "is_simulated": true,
  "request_reference": "NOC-FS-2023-8891",
  "status": "expired",
  "response_payload": {
    "issuer": "State Fire & Emergency Services",
    "issued_to": "Apex Institute of Technology",
    "valid_until": "2024-01-14",
    "renewal_applied": false,
    "simulation_note": "DEMO DATA: Simulated response reflecting expired status"
  },
  "attempted_at": "2026-10-23T11:15:00.000Z"
}
```

---

### 3.7 Scrutiny Actions & Hash-Chained Audit

#### `POST /findings/{finding_id}/review-actions`
- **Description:** Officer records a scrutiny decision.
- **Request Body:**
```json
{
  "action_type": "CONFIRM_DEFICIENCY",
  "justification_reason": "Verified that Fire NOC is expired and no renewal receipt was uploaded. Issued compliance defect notice."
}
```
- **Response 201 Created:**
```json
{
  "id": "act-1122-3344-5566-77889900aabb",
  "finding_id": "f1a2b3c4-1111-2222-3333-444455556666",
  "action_type": "CONFIRM_DEFICIENCY",
  "actor_id": "usr-officer-01",
  "action_timestamp": "2026-10-23T11:20:00.000Z"
}
```

#### `POST /audit/verify-chain`
- **Description:** Recomputes cryptographic hash chain over all `audit_events` to prove ledger integrity.
- **Response 200 OK (Chain Intact):**
```json
{
  "is_valid": true,
  "events_evaluated": 142,
  "genesis_hash": "0000000000000000000000000000000000000000000000000000000000000000",
  "latest_hash": "b5a93c7d6e8f1a2b3c4d5e6f7a8b9c0d1e2f3a4b5c6d7e8f9a0b1c2d3e4f5a6b",
  "corrupted_event_id": null
}
```
- **Response 200 OK (Tampering Detected):**
```json
{
  "is_valid": false,
  "events_evaluated": 142,
  "corrupted_event_id": "evt-7788-9900-aabb-ccddeeff0011",
  "corrupted_sequence_number": 47,
  "expected_hash": "e1f2a3b4c5d6...",
  "computed_hash": "8899aabbccdd...",
  "detail": "Cryptographic hash mismatch at sequence 47. Database row altered outside authorized application workflow."
}
```
