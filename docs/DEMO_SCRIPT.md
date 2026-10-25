# PRAMAAN-AI: 3–5 Minute Continuous Live Demonstration Script

**Event:** Smart India Hackathon (SIH26261)  
**System Target:** PRAMAAN-AI Pre-Scrutiny Decision Support System (v1.0.0)  
**Running Environment:** `http://127.0.0.1:8000/` (FastAPI backend with static ES Module frontend)  
**Data Scope:** Strictly Synthetic Dossiers & Ground-Truth Test Bundles (Labeled DEMO / SIMULATED)  
**Estimated Time:** 3 minutes 45 seconds (4 minutes 30 seconds with Q&A buffer)

---

## Pre-Demo Quick Checklist (T-minus 60s)
1. **Server Active:** Open terminal, ensure `python -m uvicorn app.main:app --host 127.0.0.1 --port 8000` is running in `backend`.
2. **Browser Ready:** Navigate to `http://127.0.0.1:8000/` in Chromium-based browser (Chrome, Edge, Brave).
3. **Health Indicator:** Confirm the green dot in header displays: `Backend: Operational (Port 8000)`.
4. **Header Banner:** Confirm visible banner: `DEMO DATA · NOT CONNECTED TO LIVE AICTE SYSTEMS`.
5. **Keyboard Shortcuts:** J/K (navigate findings), R (decision modal), P (PDF view), G (Evidence Graph).

---

## Continuous Demo Script: Step-by-Step

### Scene 1: Intake & Automated Complete Pre-Scrutiny (0:00 – 0:45)
- **Narrative:**  
  *"Good morning judges. PRAMAAN-AI is an evidence-first pre-scrutiny decision-support prototype for AICTE approval applications. It combines document parsing, configurable deterministic checks, cross-document comparisons, a coverage auditor, and traceable findings. Our benchmark uses synthetic dossiers; issuing-authority responses are simulated, and the system does not replace official scrutiny or final human decisions."*
- **Initial Setup:** On browser, select tab `Dossier Case File` (or route `case-file`), active bundle: `APP-2026-EOA-101 (Apex Institute of Technology)`.
- **Click Path:**
  1. Click top navigation tab: **Case File** (`data-route="case-file"`).
  2. Point out the loaded documents in table: General Affidavit, Fire Safety NOC, Architect Land Certificate, Building Plan.
  3. Click button: **⚡ Run Complete Pre-Scrutiny** (`#btn-run-full-scrutiny`).
- **Expected Screen:**
  - Status updates instantaneously to `100% COMPLETE` in green (`#cf-coverage-status`).
  - Toast appears: *"Pre-Scrutiny completed in ~2 ms with 100% Coverage Audit Guarantee!"*
  - Document inventory displays verified fingerprints and status tags.
- **Simulated Component Marker:** Application data and document binaries are synthetic files loaded from protected storage.
- **Fallback:** If button is already executed, click **Reopen Saved Run** (`#btn-reopen-run`) which retrieves the immutable persisted run via `GET /api/v1/applications/app-case-clean/full-review/latest`.
- **Evidence:** Terminal benchmark test `test_review_orchestrator.py::test_full_prescrutiny_clean_application` PASSED.

---

### Scene 2: Coverage Audit Guarantee & Summary Breakdown (0:45 – 1:15)
- **Narrative:**  
  *"A critical vulnerability in automated scrutiny is silent check omission—where an unexpected exception causes a rule to fail silently without alerting the scrutiny officer. PRAMAAN-AI introduces an independent Coverage Auditor that mathematically reconciles every planned check against terminal outcomes."*
- **Click Path:**
  1. Click button: **Evidence Studio →** (`#btn-goto-studio`) or top navigation tab **Evidence Studio** (`data-route="studio"`).
  2. Point to the top badge in Left Panel: **100% COVERAGE GUARANTEE** (`#studio-coverage-guarantee-badge`).
  3. Click filter tab: **All** (`#filter-findings-all`), then click **Deficiencies** (`#filter-findings-defects`), then **Compliant** (`#filter-findings-compliant`).
- **Expected Screen:**
  - Left pane displays categorized cards:
    - **Compliant Passes:** Land Contiguity, Contiguous Built-Up Area, Sponsoring Trust Resolution.
    - **Not Applicable:** Standalone New Category rules cleanly accounted as `NOT_APPLICABLE` rather than false failures.
- **Fallback:** If bundle `app-case-clean` is loaded, switch selector or navigate to `app-case-expired` from Reviewer Queue (`data-route="queue"`).
- **Evidence:** `test_review_orchestrator.py::test_coverage_audit_catches_deliberate_omission` proves that if a check is omitted, the audit forces status to `INCOMPLETE`.

---

### Scene 3: Evidence Studio — Traceable Coordinates & Explain-Why (1:15 – 2:00)
- **Narrative:**  
  *"PRAMAAN-AI never displays ungrounded AI hallucination. Every flag is anchored to physical document coordinates, ground-truth extracted values, and official regulatory clauses."*
- **Initial Setup:** Load `app-case-expired` (National Academy of Engineering) or click finding `RULE-APH-EXP-003` in findings list.
- **Click Path:**
  1. Click on finding card: **Fire Safety NOC Validity Expired (`RULE-APH-EXP-003`)**.
  2. Notice the Right Pane automatically loads the simulated Fire Safety NOC PDF sheet.
  3. Point to the yellow coordinate bounding box rendered over `Valid Until: 2024-01-14`.
  4. Point to the bottom Left **Explain-Why Card** (`#studio-explain-card`):
     - Extracted Value: `2024-01-14` (Confidence: 0.97, Method: `PDF_TEXT_STREAM`).
     - Benchmark Threshold: Must be valid on submission date `2026-04-10`.
     - Official Clause Citation: `AICTE Approval Process Handbook (APH) 2024-2027, Clause 4.2(b)`.
  5. Click button: **Evidence Graph** (`#btn-studio-mode-graph`) in the right pane toolbar.
  6. Show interactive SVG nodes connecting: `Application` → `Document` → `Extracted Claim` → `Rule Pack` → `Finding` → `Action`.
- **Expected Screen:**
  - PDF sheet displays bounding box overlay on Page 1.
  - Explain-Why card displays side-by-side comparison.
  - Evidence Graph displays connected SVG bezier curves with color-coded nodes.
- **Fallback:** If coordinates are absent on an arbitrary document, point out the amber callout: *"Region Coordinates Unavailable: Evidence extracted from text stream without discrete bounding box"*—proving the system never invents fake bounding boxes.
- **Evidence:** `backend/tests/test_rules_engine.py::test_finding_contains_aph_citation` and `test_explainability_payload_contains_required_fields` PASSED.

---

### Scene 4: Historical Comparison & Document Collision Deduplication (2:00 – 2:45)
- **Narrative:**  
  *"Institutions frequently evolve or share sponsoring trusts. PRAMAAN-AI distinguishes between legitimate expansion, benign name variations, and suspicious cross-college document collisions."*
- **Click Path:**
  1. Click top navigation tab: **Comparison & Duplicates** (`data-route="comparison"`).
  2. Tab 1 (**Historical Comparison**):
     - View delta table for `Apex Institute`: Legal Name normalized match (`Apex Inst. of Tech.` = `Apex Institute of Technology`).
     - Point out intake increase (+33.3% from 180 to 240): flagged under `RULE-AICTE-HIST-006` as a change-request, **never as fraud**.
  3. Click sub-tab: **Cross-Application Document Collisions** (`#tab-duplicates`).
  4. Click on match collision card: `doc-clean-fire` vs `doc-dup-fire` (Exact Binary Collision).
  5. Inspect side-by-side comparison:
     - Left Panel: Apex Institute of Technology (`SHA-256: d4676bef...`).
     - Right Panel: Horizon Polytechnic (`SHA-256: d4676bef...`).
     - Action buttons: *Confirm Shared Campus/Trust*, *Request Affiliation Clarification*, *Mark Unrelated Template*.
- **Expected Screen:**
  - Historical comparison delta table with color-coded change tags.
  - Interactive side-by-side document comparison viewer with exact SHA-256 digests and resolution buttons.
- **Simulated Component Marker:** Cross-application collision is seeded across synthetic benchmark dossiers `app-case-clean` and `app-case-duplicate`.
- **Fallback:** If side-by-side does not load immediately, click dropdown `#select-comp-app` and select `app-case-historical`.
- **Evidence:** `test_duplicates_and_comparison.py::test_exact_binary_duplicate_detection` and `test_historical_intake_increase_request` PASSED.

---

### Scene 5: Honest Uncertainty: Source Unavailable & Poor Scans (2:45 – 3:30)
- **Narrative:**  
  *"What happens when an external state revenue portal times out or a scan is unreadable? Traditional automation either crashes or falsely flags the college as non-compliant. PRAMAAN-AI enforces honest uncertainty: zero penalty, source unavailable status, and automatic routing to manual human review."*
- **Click Path:**
  1. Click top navigation tab: **Verification Subsystem** (`data-route="verification"`).
  2. Point to the banner: **Statutory Truthfulness Guardrail: External network conditions never penalize the applicant institution**.
  3. In the Interactive Sandbox:
     - Target Document: `doc-clean-fire`.
     - Adapter: `Simulated Issuer Registry Adapter`.
     - Fixture Override: Select **FIX-SOURCE-UNAVAIL (Simulated Gateway Timeout 504)** (`#select-fixture`).
     - Click button: **Execute Verification Attempt** (`#btn-trigger-verify`).
- **Expected Screen:**
  - Status updates to amber badge: `source unavailable`.
  - Retry counter shows: `3 / 3 retries bounded`.
  - Manual review task generated: `TASK-REV-SRC-UNAVAIL: External issuing authority portal did not respond. Verify via offline liaison. ZERO penalty levied.`
  - Safe response hash generated (`response_hash: 7a8f1b2c...`).
- **Evidence:** `test_verification_subsystem.py::test_issuer_adapter_source_unavailable_timeout` and `test_bounded_retries_and_retry_outcome` PASSED.

---

### Scene 6: Human Oversight & Tamper-Evident Cryptographic Ledger (3:30 – 4:15)
- **Narrative:**  
  *"AICTE regulations strictly forbid AI from autonomously approving or rejecting colleges. PRAMAAN-AI enforces human-in-the-loop governance: scrutiny officers record decisions with mandatory justification, immutably chained into a SHA-256 ledger."*
- **Click Path:**
  1. Press keyboard key **R** (or click **Record Decision (R)**).
  2. Decision Modal opens with trapped keyboard focus.
  3. Select radio: **Confirm Statutory Deficiency** (`CONFIRM_DEFICIENCY`).
  4. In Remarks, enter: `Defect notice issued to applicant college per APH 2024-2027 Chapter II Clause 4.2`.
  5. Click **Commit Review Action** (`#btn-modal-submit`). Toast confirms cryptographic signing.
  6. Click top navigation tab: **Audit Trail** (`data-route="audit"`).
  7. Point to green banner: **Cryptographic Audit Chain Intact**.
  8. Click button: **⚠️ Simulate Disposable Tamper** (`#btn-simulate-tamper`).
     - Banner turns red: `⚠️ TAMPER DETECTED: Hash chain broken at Block #X!`
  9. Click button: **🔄 Restore Chain** (`#btn-restore-chain`).
     - Banner restores to green: `Cryptographic Audit Chain Restored & Verified`.
- **Expected Screen:**
  - Decision modal renders radio choices and remarks textarea.
  - Audit Ledger table renders sequential blocks with `Previous Hash`, `Event Hash`, actor `usr-officer-01`, and payload.
  - Tamper detection identifies the exact corrupted sequence number.
- **Evidence:** `test_auth_and_audit_security.py::test_audit_chain_tamper_detection_and_restoration` and `test_guardrail_bars_autonomous_ai_approval` PASSED.

---

### Scene 7: Empirical Benchmark & Concluding Statement (4:15 – 4:45)
- **Narrative:**  
  *"We evaluate PRAMAAN-AI with 15 labelled synthetic bundles, including clean cases, expired certificates, conflicting fields, duplicate reuse, poor scans, source outages, and deliberate check omissions. The benchmark report records extraction and rule metrics, coverage accounting, and backend orchestration latency. These are measurements on a small synthetic fixture set—not production accuracy estimates or a measurement of the full human review process. Issuer-registry responses are simulated; live AICTE and issuing-authority integrations are not connected. PRAMAAN-AI remains a traceable decision-support copilot, with official scrutiny and final decisions retained by authorized people."*
- **Visual:** From the repository root, run `python backend/run_benchmark.py` immediately before recording. Show the newly generated `docs/EVALUATION_REPORT.md`; quote only the values and timestamp from that run, and explicitly label them as synthetic-fixture measurements. Avoid comparing backend milliseconds directly with end-to-end manual review time.

---

## Demo Fallback & Emergency Procedures

| Risk / Failure Mode | Root Cause | Immediate Backup Action |
|---|---|---|
| **Server Offline / Connection Refused** | Uvicorn process terminated | Run in terminal: `cd backend; python -m uvicorn app.main:app --host 127.0.0.1 --port 8000`. Takes 1.5 seconds to restart. |
| **Active Case Shows No Findings** | Clean bundle (`app-case-clean`) currently selected | In top bar or Reviewer Queue, click `APP-2026-EOA-102` (`app-case-expired`) or `APP-2026-NEW-201` (`app-case-mismatch`). |
| **Decision Modal Remarks Empty** | Dismissal requires >= 10 characters | Type at least 10 characters (e.g. `Statutory defect verified against Chapter II`). Server-side validation enforces this. |
| **Audit Verification Returns 403** | User role set to `INSTITUTION_USER` | Use top-right role dropdown (`#role-select`) and switch to `REVIEWER` or `AUDITOR`. |
| **PDF Viewer Shows White Blank Sheet** | Content stream render delayed | Click Zoom `+` or `-` or select document from dropdown (`#studio-doc-selector`). |
