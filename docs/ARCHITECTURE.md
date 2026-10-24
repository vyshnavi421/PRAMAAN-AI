# PRAMAAN-AI: System Architecture & Technical Design

**Document Status:** Approved Architecture Baseline (Planning Only)  
**Version:** 1.0.0  
**Stack:** React + TypeScript (Vite, Tailwind, PDF.js, Cytoscape.js) | Python FastAPI (SQLAlchemy, Alembic, Pydantic) | PostgreSQL | Protected Local Storage  

---

## 1. Architectural Philosophy & Style

PRAMAAN-AI is architected as a **modular monolith**. It avoids premature microservices, message brokers, or distributed queues for the SIH prototype while maintaining strict domain boundaries that allow future horizontal extraction into independent services if warranted by scale.

```mermaid
flowchart TB
    subgraph Frontend["Frontend Client (React + TypeScript)"]
        UI_Shell["Application Shell & DEMO Banner"]
        PreflightUI["Institution Pre-flight & Intake UI"]
        ReviewerUI["Officer Review Queue & Case File"]
        ViewerUI["PDF.js Evidence Viewer (Box Overlays)"]
        GraphUI["Evidence Graph (Cytoscape.js)"]
        AuditUI["Audit Trail & Hash-Chain Verifier"]
    end

    subgraph Gateway["FastAPI Application Core"]
        AuthMiddleware["RBAC & Session Middleware"]
        API_Router["REST API Router (/api/v1)"]
    end

    subgraph Modules["Modular Monolith Services"]
        IngestService["Ingestion & Document Storage Service"]
        DocAIService["Doc AI & Text Extraction Service"]
        RuleEngine["Deterministic Rule Engine & Snapshotter"]
        VerifyService["Verification Hub & Issuer Adapters"]
        ReuseService["Deduplication & Reuse Engine"]
        ReviewService["Case Management & Review Service"]
        AuditService["Hash-Chained Audit Service"]
    end

    subgraph Persistence["Storage & Data Layer"]
        DB[(PostgreSQL Relational DB)]
        DocStore[Protected Document File Store]
    end

    subgraph ExternalAdapters["Simulated / Authorised Source Layer"]
        MockIssuer["Simulated Issuer Adapter (6 States)"]
        MockAICTE["Simulated AICTE Portal & Historical Records"]
    end

    Frontend -->|HTTPS REST| Gateway
    Gateway --> Modules
    Modules --> DB
    IngestService --> DocStore
    VerifyService --> ExternalAdapters
```

---

## 2. Module Boundaries & Responsibilities

| Module | Core Responsibility | Internal Dependencies | Output Artifacts |
|---|---|---|---|
| **`ingestion`** | Validates uploaded files (magic MIME check, size/page limits, SHA-256 calculation). Prevents path traversal and writes to protected store. | Storage backend | `Document` record with hash and server-side storage key. |
| **`document_ai`** | Extracts text and layout. Uses embedded PDF text first, falls back to OCR (Tesseract) on scanned pages. Computes bounding boxes and extraction confidence. | `ingestion` | `ExtractedField` with `FieldProvenance` (page index, coordinates, text). |
| **`rule_engine`** | Loads versioned APH rule packs. Executes deterministic validation against application fields and AICTE historical baselines. Generates immutable findings. | `document_ai`, `persistence` | `ValidationRun`, `Finding`, and `FindingEvidence` records. |
| **`verification`** | Implements the Verification Ladder. Coordinates digital signature verification, QR decoding, and external registry lookups via provider-agnostic adapters. | `ingestion`, `external_adapters` | `VerificationAttempt` with one of 6 honest statuses. |
| **`reuse_engine`** | Detects cross-application file reuse using exact SHA-256 and text fingerprinting. Flags potential overlap for review. | `ingestion`, `persistence` | `DocumentDuplicate` records with similarity metrics. |
| **`review`** | Manages officer case files, reviewer decisions (`confirm`, `dismiss`, `rectify`, `inspect`), and updates application workflow status. | `rule_engine`, `verification` | `ReviewAction` audit records and updated case states. |
| **`audit`** | Appends structured security and compliance events to a tamper-evident SHA-256 cryptographic hash chain. Provides audit verification engine. | All modules | Hash-chained `AuditEvent` ledger. |

---

## 3. End-to-End System Workflows & Data Flows

### 3.1 Document Ingestion & Field Extraction Pipeline

```mermaid
sequenceDiagram
    autonumber
    actor User as Institution / Reviewer
    participant API as Ingest Service
    participant Store as Protected Storage
    participant Extractor as Doc AI Worker
    participant DB as PostgreSQL DB

    User->>API: POST /applications/{id}/documents (Multipart File)
    API->>API: Validate Magic Bytes, Size (<25MB), SHA-256
    API->>Store: Save file with safe UUID filename (No public path)
    API->>DB: Insert Document (status="PROCESSING")
    API->>Extractor: Process Document (doc_id)
    
    alt Embedded Text Available
        Extractor->>Extractor: Extract text stream with bounding boxes
    else Scanned / Image Page
        Extractor->>Extractor: Run OCR (Tesseract/Paddle) with bounding boxes
    end

    alt Low Confidence (<0.65) or Unreadable
        Extractor->>DB: Save field with quality="LOW_CONFIDENCE", abstain
    else Successful Extraction
        Extractor->>DB: Save ExtractedFields & FieldProvenances
    end

    Extractor->>DB: Update Document (status="PROCESSED")
    Extractor-->>User: Document Processed with Extracted Fields
```

### 3.2 Deterministic Validation Run & Evidence Graph Construction

```mermaid
sequenceDiagram
    autonumber
    actor Officer as Scrutiny Officer
    participant API as Rule Engine Service
    participant DB as PostgreSQL DB
    participant Graph as Evidence Graph Builder

    Officer->>API: POST /applications/{id}/validation-runs
    API->>DB: Fetch Active RulePack for Application Category
    API->>DB: Fetch ExtractedFields & Prior AICTE Approved Records
    API->>API: Execute Deterministic Rules (Completeness, Expiry, FSR, Area)
    API->>DB: Persist Immutable ValidationRun & Findings
    API->>Graph: Build Graph Nodes (Claims, Docs, Rules, Records, Findings)
    API->>Graph: Build Graph Edges (ExtractedFrom, EvaluatedBy, ComparedTo)
    API->>DB: Log AuditEvent (RUN_COMPLETED, hash_chained)
    API-->>Officer: Validation Run Summary + Graph Topology
```

### 3.3 Verification Ladder Execution

```mermaid
sequenceDiagram
    autonumber
    actor Officer as Scrutiny Officer
    participant Hub as Verification Hub
    participant SigVerifier as Digital Signature Engine
    participant Adapter as Simulated Issuer Adapter
    participant DB as PostgreSQL DB

    Officer->>Hub: POST /documents/{id}/verification-attempts
    
    alt Document has Digital Signature
        Hub->>SigVerifier: Validate PKCS#7 / CMS Signature
        SigVerifier-->>Hub: Valid / Invalid / Self-Signed
    else Document has Reference Number / QR
        Hub->>Adapter: Query Issuer Registry (ref_no, timeout=5s)
        alt Issuer Responds OK & Matches
            Adapter-->>Hub: Status: "verified"
        else Issuer Responds OK & Differs
            Adapter-->>Hub: Status: "mismatch detected"
        else Issuer Responds Document Expired
            Adapter-->>Hub: Status: "expired"
        else Connection Timeout / 503
            Adapter-->>Hub: Status: "source unavailable"
        end
    else No Automated Path Feasible
        Hub-->>Hub: Status: "manual review required"
    end

    Hub->>DB: Insert VerificationAttempt (status, response_payload, timestamp)
    Hub->>DB: Log AuditEvent (VERIFICATION_ATTEMPTED)
    Hub-->>Officer: Updated Document Verification State
```

---

## 4. Evidence Graph Architecture

The Evidence Graph forms the primary cognitive bridge between raw documentation and regulatory compliance. It is modeled as a Directed Acyclic Graph (DAG) queryable via `GET /applications/{id}/evidence-graph`.

### Graph Entity Classes (Nodes)
1. `DocumentNode`: Represents an uploaded PDF/image (e.g., `DOC-NOC-FIRE-2026`).
2. `ClaimNode`: An extracted field asserting a factual statement (e.g., `Built-Up Area: 12,400 sq.m`).
3. `RuleNode`: A versioned regulatory clause from the APH (e.g., `RULE-APH-003 v1.0`).
4. `ReferenceNode`: Baseline record from authorized AICTE historical database (e.g., `Prior Approved Intake: 180`).
5. `FindingNode`: Result of rule evaluation (e.g., `DEFICIENCY: Area deficit of 800 sq.m`).
6. `VerificationNode`: External issuer confirmation record (e.g., `VERIFIED: State Fire Service`).

### Graph Relational Predicates (Edges)
- `EXTRACTED_FROM`: `ClaimNode` $\to$ `DocumentNode` (carries page number and bounding box coordinates).
- `EVALUATED_AGAINST`: `ClaimNode` $\to$ `RuleNode`.
- `COMPARED_WITH`: `ClaimNode` $\to$ `ReferenceNode`.
- `PRODUCED_FINDING`: `RuleNode` $\to$ `FindingNode`.
- `AUTHENTICATED_BY`: `DocumentNode` $\to$ `VerificationNode`.

---

## 5. Security Architecture & Document Isolation

1. **Path Traversal Protection:** User-supplied filenames are never used as filesystem paths. Uploads are renamed to UUIDv4 keys and stored under structured partition directories (`storage/documents/{tenant_id}/{uuid}.bin`).
2. **Strict MIME & Magic Byte Validation:** File extensions (.pdf, .png, .jpg) must match the file's binary magic header (`%PDF-`, `\xFF\xD8\xFF`, `\x89PNG`). Executable or script files (SVG, HTML, JS) are rejected immediately.
3. **Internal Path Sanitization:** No internal filesystem paths or database connection credentials are leaked in API error responses or stack traces.
4. **Append-Only Hash-Chained Audit Trail:**
   Every significant system action generates an `AuditEvent` with:
   $$\text{CurrentHash}_i = \text{SHA256}(\text{PreviousHash}_{i-1} \parallel \text{Timestamp} \parallel \text{ActorID} \parallel \text{ActionType} \parallel \text{PayloadHash})$$
   Any modification of past records invalidates the chain and is detected by `POST /audit/verify-chain`.

---

## 6. Deployment & Resource Footprint

- **Target Deployment for Prototype:** Local laptop or standalone VM with 16GB RAM.
- **Service Containerization:** Optional Docker Compose containing:
  - `pramaan-backend`: Python 3.11+ FastAPI (Uvicorn).
  - `pramaan-frontend`: Vite production build served via Nginx.
  - `pramaan-db`: PostgreSQL 16 Alpine.
  - `pramaan-storage`: Local volume mounted directory (isolated permissions).
- **Resource Limits:**
  - Max upload size: 25MB per document.
  - Max pages per document: 50 pages.
  - Request timeouts on external simulated adapters: 5 seconds bounded timeout.
