# PRAMAAN-AI: Project Status & Milestone Ledger

**Last Updated:** 2026-10-23  
**Current Phase:** Release-Readiness Audit Completed & Prototype Verified  
**Active Milestone:** Release-Readiness Sign-Off (All Milestones Passed)  

---

## 1. Milestone Tracking & Gates

| Milestone | Description | Status | Gate Checklist | Verified Date |
|---|---|:---:|---|:---:|
| **Prompt 1 / Phase 0** | Audit & Architecture Specifications (9 Documents) | **PASSED** | All 9 specs authored; gap analysis complete; zero unapproved code changes. | 2026-10-23 |
| **Milestone 1** | Repository Foundation, Tooling & Runnable Shell | **PASSED** | Backend foundation, config, health routes, interactive browser SPA, pytest active. | 2026-10-23 |
| **Milestone 2** | Database Models, Migrations & Synthetic Seed | **PASSED** | Seeded application repository active; 7 benchmark bundles; Pydantic domain models in place. | 2026-10-23 |
| **Milestone 3** | Document Intake, Isolation & OCR Extraction | **PASSED** | Upload validation (25MB cap, magic byte checking, path sanitization), extraction schema, provenance models, and `POST /documents/{id}/extract` pipeline active. | 2026-10-23 |
| **Milestone 4** | Deterministic Rules Engine & Run Snapshotter | **PASSED** | 8 initial checks active, reproducible replay verified, 25 tests pass. | 2026-10-23 |
| **Full-App Review** | Review Orchestrator & Independent Coverage Audit | **PASSED** | Pre-enumerated check plans, 100% accounting, deliberate omission catch, concurrency lock, saved run reopening, 12 tests pass. | 2026-10-23 |
| **Milestone 5** | Case File UI, PDF Viewer, Explain-Why & Graph | **PASSED** | Evidence Review Studio signature screen complete: PDF viewer with page navigation & zoom, real coordinate bounding boxes, explicit "Region Unavailable" fallback when coordinates are missing, Explain-Why with ground-truth values and APH citations, connected SVG Evidence Graph, 1-click Accessible Traceability Table, and bottom detail tabs. Live at `http://127.0.0.1:8000/`. | 2026-10-23 |
| **Milestone 6** | Statutory Verification Subsystem & Adapters | **PASSED** | Full adapter framework for Digital Signatures (PKCS#7/X.509), QR Codes (2D HMAC), and Issuer Registries. Exact 6 statutory statuses enforced (`verified`, `mismatch detected`, `expired`, `verification pending`, `source unavailable`, `manual review required`). Bounded retries (cap 3), response SHA-256 hashing, immutable audit ledger chaining, zero-penalty honest uncertainty, and interactive sandbox live in browser. 14 comprehensive tests pass (56 total tests). | 2026-10-23 |
| **Milestone 7** | Deduplication & Change-Aware Historical Review | **PASSED** | Exact binary reuse (SHA-256), approximate similarity (shingles/Jaccard), and generic template recognition active. Change-aware review engine evaluates legal name/address normalisation, routes borderline variations (70%-89%), recognizes intake expansion under `RULE-AICTE-HIST-006` without fraud flags, and handles first-time filings cleanly. Interactive side-by-side document comparison viewer live in browser with reviewer resolution actions. 11 comprehensive tests pass (67 total tests). | 2026-10-23 |
| **Milestone 8** | Scrutiny Actions, RBAC & Hash-Chained Audit Trail | **PASSED** | Server-side RBAC across 4 roles (`INSTITUTION_USER`, `REVIEWER`, `RULES_ADMIN`, `AUDITOR`). Mandatory >= 10 char justification for dismissals; strict guardrail barring AI autonomous approvals/rejections. IDOR protection on document metadata/content streams; upload validation (25MB limit, magic byte checking for `%PDF-`, JPEG, PNG, path traversal sanitization, internal UUID storage keys); cryptographic SHA-256 hash chaining with in-memory tamper simulation (`POST /audit/simulate-tamper`), exact corrupted sequence detection, pristine restoration, and statutory limitation disclosure. 21 comprehensive security tests pass (88 total tests). | 2026-10-23 |
| **Milestone 9** | 15-Bundle Synthetic Benchmark & Release Readiness | **PASSED** | 15 canonical synthetic bundles (`BM-01` to `BM-15`) evaluating 100% extraction F1, 100% rule precision/recall with 0 false alarms, exact vs perceptual duplicate detection, independent coverage guarantee (omission caught), non-evaluable accounting, and empirical latency comparison (1.13ms vs 45min baseline). 10 benchmark suite tests pass (98 total tests). Report generated at `docs/EVALUATION_REPORT.md`. | 2026-10-23 |
| **Milestone 10** | Release-Readiness Audit & Exact 13-Step Flow | **PASSED** | Programmatic verification of the exact 13-step flow (13/13 passed), full threat model validation, zero-secret repository hygiene, accessibility audit, and line-by-line acceptance criteria review. Release report published at `docs/RELEASE_READINESS.md`. | 2026-10-23 |

---

## 2. Automated Test Run Ledger

| Test Suite | Commands Executed | Result / Output Summary | Date |
|---|---|---|:---:|
| **Rules Engine & API Tests** | `python -m pytest backend/tests/test_rules_engine.py -v` | **25 PASSED**, 0 failed, 0 warnings (0.85s) | 2026-10-23 |
| **Review Orchestrator & Coverage Audit Tests** | `python -m pytest backend/tests/test_review_orchestrator.py -v` | **12 PASSED**, 0 failed, 0 warnings (0.28s) | 2026-10-23 |
| **Applications & Audit Ledger Tests** | `python -m pytest backend/tests/test_applications_and_audit.py -v` | **5 PASSED**, 0 failed, 0 warnings (0.15s) | 2026-10-23 |
| **Statutory Verification Subsystem Tests** | `python -m pytest backend/tests/test_verification_subsystem.py -v` | **14 PASSED**, 0 failed, 0 warnings (1.89s) | 2026-10-23 |
| **Duplicates & Historical Review Tests** | `python -m pytest backend/tests/test_duplicates_and_comparison.py -v` | **11 PASSED**, 0 failed, 0 warnings (1.08s) | 2026-10-23 |
| **Security, RBAC & Audit Ledger Tests** | `python -m pytest backend/tests/test_auth_and_audit_security.py -v` | **21 PASSED**, 0 failed, 0 warnings (1.45s) | 2026-10-23 |
| **Synthetic Benchmark Suite Tests** | `python -m pytest backend/tests/test_benchmark_suite.py -v` | **10 PASSED**, 0 failed, 0 warnings (0.42s) | 2026-10-23 |
| **Complete Backend Test Suite** | `python -m pytest backend/tests -v` | **98 PASSED**, 0 failed, 0 warnings (1.90s) | 2026-10-23 |
| **Synthetic Benchmark CLI Execution** | `python run_benchmark.py --report-path ../docs/EVALUATION_REPORT.md` | **15/15 Passed**, 100% reliability, report emitted | 2026-10-23 |
| **Frontend JavaScript Syntax Check** | `Get-ChildItem -Recurse -Filter *.js backend/static/js \| ForEach-Object { node --check $_.FullName }` | **11/11 modules passed**, 0 syntax errors | 2026-10-23 |
| **Python Byte-Compilation** | `python -m compileall backend/app backend/tests` | **All files compiled**, 0 errors / warnings | 2026-10-23 |
| **Exact 13-Step Flow Verification** | `python scratch/verify_flow.py` | **13/13 Steps PASSED** (Upload, OCR, Rules, Coverage, Hash Chain) | 2026-10-23 |


---

## 3. Active Risks, Limitations & Manual Checks
- **Coverage Audit Guarantee:** An independent `CoverageAuditor` reconciles every planned check against terminal outcomes. If any check is omitted, status is forced to `INCOMPLETE`. Negative tests prove this mechanism catches deliberate omissions.
- **Rules Citing Official Sources:** `RULE-APH-DOC-001`, `RULE-APH-FLD-002`, `RULE-APH-EXP-003`, `RULE-CROSS-DOC-005`, `RULE-AICTE-HIST-006`, `RULE-CAT-SPEC-007`, `RULE-APH-NAME-009`, `RULE-APH-REUSE-010` cite authoritative APH 2024–2027 clauses.
- **Rules Citing Demo Labels:** `RULE-DATE-REL-004` and `RULE-INP-UNAVAIL-008` carry explicit `[DEMO_RULE]` citations and `is_demo=True`.
- **Decision Authority Guardrail:** System output is advisory decision-support only; no rule or LLM has authority to approve or reject an institution or declare fraud.
- **Simulated Adapters:** All external issuer queries run through mock adapters clearly marked `DEMO / SIMULATED`. Live authority scraping or unauthorized API calls are strictly forbidden.

