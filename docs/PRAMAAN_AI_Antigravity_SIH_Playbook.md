# PRAMAAN-AI: SIH Build & Antigravity Playbook

**Purpose:** Build a credible, differentiated prototype for SIH26261 — AI-Powered Application Validation, Document Authentication and Regulatory Compliance Verification.

**Primary principle:** Build a smaller system that works end to end and can prove its findings. Do not build a large collection of screens or claim access to government systems that the team does not have.

**Important:** This playbook improves execution discipline; it cannot guarantee an SIH win or guarantee that Antigravity will never make mistakes. Use the review gates and tests in this document to catch mistakes early.

---

## 0. What PRAMAAN-AI is

**Name:** PRAMAAN-AI (working name; verify availability before public use)

**Tagline:** Every flag backed by evidence. Every decision stays human.

**One-line pitch:** An evidence-first validation copilot that extracts information from institutional applications, checks it against versioned rules and available records, supports authorised verification, and gives reviewers a traceable case file with clear next actions.

### Core differentiator

Every finding should connect:

1. A claim or field extracted from an application.
2. The source document and page/region supporting the extraction.
3. The reference value, record or rule used for comparison.
4. The actual comparison/check result.
5. The verification state and uncertainty, if any.
6. A human-review action and audit history.

The product is **decision support**, not an automatic approval/rejection or fraud-detection authority.

### Five priority features

1. **Evidence Graph:** visual connection between claims, documents, records, rules and findings.
2. **Explain-Why panel:** clicking a finding opens its document evidence, comparison, rule reference and next action.
3. **Verification Ladder:** supported checks for digital signature/QR, issuer source, record comparison and manual confirmation, with honest statuses.
4. **Cross-application reuse detection:** identifies exact or likely duplicate files for review; similarity is not proof of misconduct.
5. **Versioned rules and change-aware review:** makes the rule used in each run reproducible and compares current information to prior authorised/synthetic records.

### Do not prioritise at the start

- Training a large custom language model.
- A chatbot that is not grounded in authoritative handbook clauses.
- Advanced infrastructure object detection before the core pipeline works.
- Kubernetes, blockchain, many microservices, or elaborate infrastructure for a local prototype.
- Any claim that a document is forged based only on metadata, OCR, visual anomalies or an LLM score.

---

## 1. SIH submission first: protect the deadline

The screenshot shared by the team shows **28 October 2026** as the idea-submission deadline. Treat this as a reminder to verify the exact deadline and requirements in the live SIH portal and with the college SPOC; do not assume a screenshot overrides newer instructions.

Before anything else:

- Confirm the exact problem statement ID, title, category and theme in the portal.
- Confirm the active presentation template, slide limit, file format, character limits and whether a demo video is required with the college SPOC/official portal.
- Use the prescribed template rather than submitting this internal playbook or the 20-page planning pack as the idea presentation.
- Ensure every claim in the proposal is accurate. Mark mock integrations and planned capabilities clearly.
- Keep the final submitted PDF, portal confirmation and a backup copy.

### Submission proposal emphasis

The short idea submission should communicate:

- The real administrative problem.
- Why ordinary OCR plus a dashboard is insufficient.
- The evidence graph, verification ladder and versioned rule workflow.
- A feasible architecture with mock-to-authorised integration adapters.
- Privacy, access control and human review.
- How the team will evaluate the prototype using labelled synthetic data.
- What is implemented now versus planned later.

Do not claim production accuracy, live AICTE access, official issuer API access, or real fraud detection unless the team can demonstrate and prove it.

---

## 2. Prepare the workspace before asking Antigravity to code

### 2.1 Make the project folder

Create a new folder/repository named `pramaan-ai`. If there is already a repository, ask Antigravity to inspect it first and never replace it automatically.

Suggested initial layout:

```text
pramaan-ai/
  AGENTS.md
  README.md
  .gitignore
  docs/
    reference/
      PRAMAAN-AI-Winning-Pack.pdf
      problem-statement.md
    PRD.md
    ARCHITECTURE.md
    DATA_MODEL.md
    API_CONTRACTS.md
    VALIDATION_RULES.md
    THREAT_MODEL.md
    TEST_PLAN.md
    IMPLEMENTATION_PLAN.md
    DECISIONS.md
  frontend/
  backend/
  test-data/
    synthetic-fixtures/
    expected-results/
  scripts/
```

Put the planning PDF and problem-statement text into `docs/reference/`. ChatGPT file uploads are not automatically available inside the local Antigravity workspace; copy them into the project or attach them in Antigravity.

### 2.2 Use safe Antigravity permissions

- Prefer **Request Review** or a sandboxed execution mode; do not use unrestricted “Always Proceed”/Turbo mode for the project.
- Review file diffs and terminal commands before approving sensitive/destructive operations.
- Never put passwords, tokens, personal records or production credentials into prompts, source code, screenshots or Git commits.
- Do not approve `rm -rf`, database resets, destructive migrations, force pushes or commands outside the workspace unless you understand them and have a backup.
- Make a Git checkpoint after each working milestone. Never let an agent overwrite work merely because it wants to “start clean.”

Antigravity supports persistent workspace instructions, implementation-plan artifacts, and reviewable changes. Use those features for every phase rather than requesting a one-shot implementation.

---

## 3. Create `AGENTS.md` before implementation

Create this file at the repository root. It gives Antigravity persistent constraints for future requests.

```markdown
# PRAMAAN-AI Engineering Rules

## Product truth and scope
- The project is a prototype for SIH26261, not an official AICTE system.
- Use synthetic data by default. Do not claim live AICTE or issuer integration unless a real, authorised integration has been configured and verified.
- All mock sources, mock records and simulated results must be visibly labelled DEMO / SIMULATED in the UI and docs.
- Never scrape restricted portals, bypass login controls, or invent API access.
- The system is decision support only. It must not autonomously approve/reject institutions or state that a person/entity committed fraud.

## Architecture
- Begin as a modular monolith: React + TypeScript frontend, FastAPI backend, PostgreSQL database, protected document storage.
- Keep API routes, services, models, schemas and tests in separate modules.
- Do not add a framework, database, queue, vector store, LLM or microservice unless a requirement demonstrates the need.
- Keep frontend and backend API contracts documented and typed.
- Do not silently alter the agreed database schema or response contract.

## Evidence and findings
- Every extracted field must retain source document ID, page index/number, text/region reference when available, extraction method and confidence/quality information.
- Every finding must contain a rule ID and version (if rule-based), a reason, supporting evidence, status and recommended next action.
- Never create an evidence finding without a traceable source or explicit explanation that evidence is unavailable.
- Distinguish extraction confidence, authenticity verification, compliance checks and overall application workflow status.
- Metadata or image anomalies are weak indicators; never treat them alone as proof of forgery.
- AI/LLM output cannot invent or decide regulations. Regulatory checks must use approved, versioned rule configuration.
- If extraction or verification is uncertain, abstain and route to manual review.

## Verification states
Use the problem statement's exact document-verification labels where applicable:
- verified
- mismatch detected
- expired
- verification pending
- source unavailable
- manual review required

Do not turn a network error into a compliance failure. Do not equate a document status with an application's overall status.

## Security and privacy
- Use synthetic test data only unless explicit authorisation exists.
- Validate uploaded file type, size and content; prevent path traversal and unauthorised file access.
- Do not expose local filesystem paths or secret values in API responses/logs.
- Use environment variables for configuration; commit `.env.example`, never `.env`.
- Enforce role-based access in the backend, not merely by hiding UI buttons.
- Record reviewer actions and sensitive access events in the audit trail.
- Never disable authentication or validation merely to make the demo work.

## Coding workflow
- Inspect existing files before editing; preserve working code and user changes.
- Work only on the requested phase; do not add unrelated features.
- Start each major phase with a written plan and acceptance criteria.
- Make small, reviewable changes. Do not silently rewrite whole files/repositories.
- Add or update tests with every behaviour change.
- Run relevant tests, type checks, lint and build; report actual command outputs and failures.
- Never claim a test passed without running it.
- If a command fails, diagnose the root cause and fix it; do not hide or skip the failing test.
- After each phase, list files changed, tests run, results, limitations and the next smallest task.
- Do not change package managers or dependency versions without a reason.
- Do not run destructive commands, change Git history, force-push, or delete data without explicit approval.

## Definition of done
A feature is done only when:
1. Its acceptance criteria are met.
2. Relevant automated tests pass.
3. It works through the actual UI/API flow.
4. Error and empty states are handled.
5. Evidence and status labels are accurate.
6. Documentation is updated.
7. No unrelated regression is known.
```

After creating it, ask Antigravity to summarise these rules and confirm that it will follow them.

---

## 4. Prompt 1 — audit and design only (do not code)

Paste this first into Antigravity after making the PDF and problem statement available in the workspace.

```text
You are the lead architect for PRAMAAN-AI, a prototype for SIH26261.

Read the complete problem statement, the PRAMAAN-AI planning PDF and the root AGENTS.md. Inspect the current workspace before proposing changes.

IMPORTANT: This phase is planning only. Do not implement application code, install packages, run migrations or overwrite files.

Preserve the project's central concepts: Evidence Graph, Explain-Why panel, Verification Ladder, cross-application reuse detection, versioned rules, change-aware review, mock/authorised source adapters, and human-controlled decisions.

Create/revise these specification files:
- docs/PRD.md
- docs/ARCHITECTURE.md
- docs/DATA_MODEL.md
- docs/API_CONTRACTS.md
- docs/VALIDATION_RULES.md
- docs/THREAT_MODEL.md
- docs/TEST_PLAN.md
- docs/IMPLEMENTATION_PLAN.md
- docs/DECISIONS.md

Specifications must define:
1. User roles and workflows.
2. An MVP and explicitly deferred features.
3. Module boundaries and sequence/data-flow diagrams.
4. Database tables, fields, relationships, unique constraints and indexes.
5. API endpoints with typed request/response examples and error schemas.
6. The exact distinction between document verification status, findings, and application workflow status.
7. Provenance schema for extracted fields and page/region evidence.
8. Versioned rule schema and effective dates.
9. How validation runs are reproducible and historical runs are preserved.
10. Verification adapter interface, including all six required statuses.
11. Synthetic fixtures and expected outcomes for normal, missing, expired, mismatch, duplicate, poor-scan, source-unavailable and legitimate-variation cases.
12. Threat model, access controls, upload validation and audit-event design.
13. Exact test commands and acceptance criteria for each milestone.
14. Risks, assumptions and items requiring authorised integration.

Do not invent regulatory clauses. Every rule must either cite a specific official source and its effective period or be explicitly labelled a synthetic demonstration rule.
Do not claim live AICTE access or live issuer access. Use a mock database and simulated issuer adapter until authorised access exists.

Return a gap analysis against the problem statement and a dependency-ordered implementation plan. Stop after the plan. Wait for my review before coding.
```

### Human checkpoint 1

Read the specifications. Do not continue until:

- The plan covers every requirement in the problem statement or explains why an item is deferred.
- The document and verification statuses are clearly separated.
- Every table and API object has a purpose.
- Mock integrations are explicitly labelled.
- The MVP is small enough to complete.

If the plan is too big, tell Antigravity to reduce it before proceeding.

---

## 5. MVP scope: build this before advanced AI

### MVP user roles

- `institution_user`: creates/views their synthetic institution applications and sees pre-flight deficiencies.
- `reviewer`: inspects findings and records review actions.
- `rules_admin`: edits draft rules and tests them before activation.
- `auditor`: reads permitted case and audit history.

For a local demo, seed demo accounts rather than building real identity-provider integration. Even then, enforce backend permissions.

### Minimum screens

1. Dashboard/landing with a clear DEMO DATA banner.
2. Application list and create-application flow.
3. Document upload and document inventory.
4. Validation result summary.
5. Reviewer queue with filters.
6. Case detail: overview, documents, findings, verification, comparisons, review history.
7. PDF viewer with page navigation and region/text evidence.
8. Evidence Graph.
9. Rule pack viewer/editor with test-before-activate.
10. Audit trail with verification of the event chain.

### Minimum complete workflow

Create synthetic application → upload at least two document types → extract fields → run rules → create evidence-linked findings → open a finding in the PDF viewer → run mock verification → reviewer records a decision → audit trail records the steps.

Do not call the MVP complete until this workflow works end to end in a browser.

---

## 6. Prompt 2 — implement the skeleton only

Use only after approving the architecture documents.

```text
Implement Milestone 1 only: repository foundation and a runnable application shell.

First inspect the approved docs/IMPLEMENTATION_PLAN.md and AGENTS.md. Produce a concise implementation plan for this milestone and wait for approval if the plan differs from the approved specification.

Create a React + TypeScript + Vite + Tailwind frontend and a Python FastAPI backend, with PostgreSQL configuration, SQLAlchemy models, Alembic migrations, environment-based configuration, structured logging, health checks and test infrastructure.

Use a modular monolith. Do not implement OCR, AI, complex validation, advanced charts, external integrations or speculative features yet.

Requirements:
- Provide .env.example only; never create or commit a real .env.
- Provide a safe README with exact setup, migration, seed and run commands for Windows and general development where feasible.
- Add .gitignore entries for .env, virtual environments, node_modules, uploads, generated files and secrets.
- Add backend unit-test setup and frontend lint/type-check/build scripts.
- Add a GET /health endpoint and a database readiness check that does not expose secrets.
- Add an initial landing page with product name, clear synthetic-demo label, navigation shell and honest loading/error states.
- Add Docker Compose only if it materially simplifies local reproducibility; do not require Kubernetes.
- Preserve any existing user files and code.

Run all available tests, type checks and builds. Report exact commands and actual results. Do not claim success for unrun commands. Stop after this milestone and list changed files and any blockers.
```

### Gate 1

Confirm a clean start works from the README. Run the app yourself. Keep a Git checkpoint before moving on.

---

## 7. Prompt 3 — database models and synthetic seed data

```text
Implement Milestone 2: database schema and synthetic demo data only.

Read docs/DATA_MODEL.md and docs/VALIDATION_RULES.md before editing. Do not redesign the schema without explaining the need and updating the documents first.

Implement models/migrations for the approved entities, at minimum where specified by the architecture:
- users and roles
- institutions
- applications and previous-application snapshots
- documents
- extracted fields with provenance
- rule packs and versioned rules
- validation runs
- findings and evidence references
- verification attempts
- review actions
- audit events
- duplicate/reuse matches

Create repeatable synthetic seed data for at least one clean application and one deliberately flawed application. Include cases for a missing document, expired test document, cross-document mismatch, duplicate file, legitimate variation, source unavailable and low-quality scan.

All generated records and documents must be fictional and marked DEMO. Do not use real student, faculty or institutional personal data.

Add database constraints and indexes justified by the data model. Use migrations, not ad hoc schema creation during each request. Make seed commands safe to rerun or provide a clearly documented reset procedure for a disposable local demo database.

Write tests for relationships, constraints, seeding and migrations. Run them, report exact results and stop.
```

### Gate 2

Check the database tables, relationship integrity, and that re-running a seed does not unexpectedly duplicate data or wipe user work.

---

## 8. Prompt 4 — document upload, parsing, OCR and provenance

```text
Implement Milestone 3: secure document intake and field extraction.

Use the approved architecture and APIs. Do not implement all anomaly detection yet.

Requirements:
1. Accept only approved PDF/image formats and enforce documented file-size and page-count limits.
2. Validate MIME type/content; do not trust file extension alone. Generate safe server-side filenames; prevent path traversal.
3. Store uploaded files in protected local demo storage through a storage interface. Do not return filesystem paths or unrestricted public URLs.
4. Calculate SHA-256 for each original file and preserve the original bytes.
5. For PDFs, extract embedded text first. Use OCR only for pages with no usable text or scanned images.
6. Return structured extracted fields with document ID, page number/index, source text or bounding-box reference when available, extraction method and extraction-quality/confidence metadata.
7. Do not invent a field value when extraction fails. Represent it as missing/uncertain and route to review.
8. Add a document-processing status lifecycle with understandable failure states and retry behaviour.
9. Build the upload UI with progress, errors, accepted file types, removal/retry and visible DEMO labels.
10. Include sample fixtures: clean PDF, scanned PDF, rotated/poor-quality page, unsupported file and too-large file.

Add unit and integration tests. Test that invalid uploads are rejected safely, source pages are preserved, extracted fields are linked to the right document, and failures do not create fake values. Run tests and report results before stopping.
```

### Gate 3

Upload the same test PDFs manually. Make sure the viewer points to the right document/page and that unreadable text is not silently made up.

---

## 9. Prompt 5 — deterministic, versioned rules engine

```text
Implement Milestone 4: deterministic rules and cross-document validation.

Treat docs/VALIDATION_RULES.md as the contract. Regulatory requirements must never be invented by an LLM.

Implement versioned, effective-dated rule packs with:
- rule ID and version
- application categories to which the rule applies
- source citation/handbook clause and effective period, or explicit DEMO_RULE label
- inputs and deterministic condition
- severity and explanation template
- evidence requirements
- recommended next action
- activation state and test cases

Rules should cover demonstrable examples such as required-document completeness, configured expiry checks, required-field checks, identifier mismatches and a comparison with a synthetic institutional record.

For each validation run, persist the input snapshot/reference version, rule pack versions, extracted field values used, findings and timestamps so that the run can be reproduced. Do not overwrite prior runs when a rule changes.

Distinguish:
- document verification status
- individual validation findings
- overall application workflow status

Do not use a single opaque fraud/compliance score. If a priority/attention index is later added, show its components and label it as review prioritisation only.

Every finding must have an evidence reference or explicitly state that evidence was unavailable. Implement rule tests for passing, failing, boundary dates, missing fields, non-applicable rules and legitimate variation. Verify that an unavailable external source never becomes a compliance failure.

Run all tests and stop for review.
```

### Gate 4

Manually check at least five rule outcomes against their expected values. Confirm each finding shows the rule ID/version and the evidence used.

---

## 10. Prompt 6 — Explain-Why panel and Evidence Graph

```text
Implement Milestone 5: reviewer case file, PDF evidence viewer, Explain-Why panel and Evidence Graph.

Use the approved API contracts and actual backend responses. Do not hardcode fake findings into the frontend to make the screen look complete.

Reviewer UI requirements:
- Queue of synthetic applications with explicit workflow status and filters.
- Case-detail page with tabs for overview, documents, findings, verification, comparison and audit history.
- PDF.js document viewer with page navigation. Highlight exact text or regions when the backend supplied valid coordinates; gracefully show the page and extracted text when exact coordinates are not available.
- Clicking a finding opens its source document/page, extracted and reference values, source record/rule, evidence quality, explanation, status and next action.
- Evidence Graph nodes represent claims, fields, documents, records, rules, findings and verification results. Each node/edge must come from persisted backend data.
- Graph nodes must be keyboard accessible or have an equivalent accessible list view.
- Use clear visual labels for verified, mismatch, expired, pending, unavailable and manual review.
- Show DEMO/SIMULATED labels next to simulated sources.
- Include loading, empty, permission-denied and error states.
- Do not show a generic green tick for checks that were skipped or unavailable.

Use a clean government/workflow-oriented visual design: consistent typography, high contrast, restrained colours, clear hierarchy, responsive layouts and accessible labels. Avoid decorative animation that obscures review work.

Add UI tests for opening a finding, navigating to the right document/page, handling no bounding box, graph-to-finding navigation and empty/error states. Run the browser flow and report actual test evidence.
```

### Gate 5

The best visual test is to ask a teammate who did not build the screen to find why an application was flagged. If they cannot do it quickly, improve the UI before adding more features.

---

## 11. Prompt 7 — Verification Ladder and simulated issuer adapter

```text
Implement Milestone 6: verification adapters and honest verification states.

Create a provider-agnostic verification interface. The prototype must use a deterministic simulated issuer service unless a real authorised connection is explicitly available. Label the simulation in the user interface and documentation.

Support the exact states:
- verified
- mismatch detected
- expired
- verification pending
- source unavailable
- manual review required

For each attempt store source/adapter name, simulated-vs-real flag, request/reference identifier when safe, timestamp, response summary/hash where appropriate, status and reason. Never persist secrets or sensitive raw credentials in logs.

Implement sample responses for all six states, timeouts and malformed provider replies. Retry only transient failures with bounded retries/backoff. Do not repeatedly retry permanent mismatches. When the source is unavailable, keep the compliance result distinct and create a manual review task where appropriate.

If PDF digital-signature checks or QR decoding are implemented, only claim verification for the specific checks actually performed. A QR code containing a URL/reference is not proof that the content is authentic. A valid digital signature establishes particular integrity/signer facts, not overall regulatory compliance.

Add tests for every status, timeout, malformed response and UI display. Do not scrape sites or pretend the mock adapter is an official AICTE/issuer API. Stop after tests pass.
```

### Gate 6

During the demo deliberately make the test authority unavailable. The app must show `source unavailable` or a pending/manual-review state, not `mismatch detected` or `verified`.

---

## 12. Prompt 8 — duplicate/reuse detection and change-aware review

```text
Implement Milestone 7: conservative duplicate/reuse detection and previous-record comparison.

Duplicate detection:
- Use SHA-256 for exact file matches.
- Optionally use perceptual image hashes and normalized text fingerprints for likely near-duplicates where technically appropriate.
- Store method, similarity/evidence and compared document IDs.
- Show matched items side by side in the review UI.
- Clearly distinguish exact matches from approximate similarity.
- Treat all matches as preliminary review signals, not proof of wrongdoing.

Change-aware review:
- Compare a current synthetic application with a prior authorised/synthetic snapshot.
- Show old value, new value, source for each value and applicable rules affected.
- Handle legitimate institution-name/address changes, missing older values and schema changes without claiming non-compliance by default.
- Preserve the original validation run; new comparisons produce a new recorded result.

Add fixtures for exact reuse, benign visually similar documents, legitimate name variation, changed intake value and absent historical record. Test false-positive cases as well as positive matches. Report precision/recall only from the labelled fixtures actually evaluated.
```

### Gate 7

Include at least one legitimate variation that should not be called fraud. Confirm that duplicate similarity does not automatically create a forgery claim.

---

## 13. Prompt 9 — human review and tamper-evident audit trail

```text
Implement Milestone 8: review actions, role-based authorisation and audit trail.

Requirements:
- Enforce roles and permissions in backend APIs as well as the frontend.
- Reviewer actions must include the finding, action, reason/comment where required, actor ID, timestamp and relevant validation run.
- Available actions should include confirm finding, dismiss finding with reason, request further evidence and mark manual verification pending/completed, as applicable to the prototype.
- Do not include an automated approve/reject institution action driven by AI.
- Record validation runs, rule versions, source verification attempts, review actions and relevant access events.
- Use append-only audit-event application logic and a hash chain or equivalent tamper-evidence check for the demo. Document the limits: hash chaining detects certain modifications; it does not provide absolute immutability against a fully privileged administrator who can rewrite the entire chain.
- Provide a visible “verify audit chain” action showing pass/fail and the first broken event if detected.
- Protect personal data in logs and avoid storing unnecessary document text in audit events.

Tests must prove that a lower-privilege user cannot perform restricted actions, a review action is recorded, a normal chain verifies, and a deliberately modified test event makes chain verification fail.
```

### Gate 8

Log in as each demo role and test permissions through API requests, not just by hiding buttons. Then deliberately corrupt a disposable test audit record and verify that the chain checker catches it.

---

## 14. Prompt 10 — quality, security and final integration sweep

```text
Perform a release-readiness review of PRAMAAN-AI. Do not add new features during this pass unless required to fix a blocking defect.

First inspect AGENTS.md, the approved specification files, Git diff, and the current test suite.

Run and report, where configured:
- backend unit tests
- backend integration tests
- migration/seed tests
- frontend unit/component tests
- type checks and lint
- frontend production build
- end-to-end browser tests
- upload/security negative tests

Inspect for:
- fake or hardcoded UI data that bypasses the backend
- silent TODOs or non-functional controls
- broken routes and console errors
- missing loading/empty/error states
- status confusion (document status vs finding vs application status)
- untraceable findings or invented rules
- unauthorised source claims
- unsafe file paths/upload handling
- secrets committed to source or logs
- role checks missing from backend endpoints
- duplicate detection described as proof of fraud
- any claim that AI makes the final regulatory decision
- inaccessible controls and unusable PDF evidence navigation

Use browser testing for the main workflow: create/open seeded application, inspect documents, run validation, open a finding, view evidence, simulate source unavailable, compare documents, record reviewer action and verify audit chain.

Do not report tests as passing unless they were executed. For failures, show the root cause, fix the smallest relevant issue, and rerun the failed test. Produce docs/RELEASE_READINESS.md with pass/fail/blocking status, exact commands, measured outputs, limitations and steps to reproduce the demo. Stop after the review; do not falsely declare the product production ready.
```

---

## 15. Suggested API contract baseline

The approved API specification should be authoritative. The following list is a practical starting point, not a substitute for reviewing and accepting exact request/response schemas.

```text
GET    /health
GET    /applications
POST   /applications
GET    /applications/{application_id}
POST   /applications/{application_id}/documents
GET    /documents/{document_id}
GET    /documents/{document_id}/pages/{page_number}
POST   /applications/{application_id}/validation-runs
GET    /applications/{application_id}/validation-runs
GET    /findings/{finding_id}
POST   /findings/{finding_id}/review-actions
POST   /applications/{application_id}/compare-previous
POST   /documents/{document_id}/verification-attempts
GET    /applications/{application_id}/evidence-graph
GET    /applications/{application_id}/audit-events
POST   /audit/verify-chain
GET    /rule-packs
POST   /rule-packs/{rule_pack_id}/test
POST   /rule-packs/{rule_pack_id}/activate
```

For every endpoint, specify authentication, role permission, request/response types, status codes, error schema, idempotency expectations and audit behaviour. Avoid exposing local paths, secret details or entire documents in list endpoints.

---

## 16. Minimum synthetic test benchmark

Start with 10–20 application bundles to build and debug. Expand to a larger benchmark when the pipeline is stable. Make all labels known before evaluating the system.

Include at least:

1. Clean application — all checks should pass or be marked not applicable.
2. Missing required document — missing-document finding with checklist evidence.
3. Expired synthetic document — expiry finding tied to the configured date rule.
4. Application/document mismatch — both values and source locations shown.
5. Prior-record change — old/new value comparison, not automatic failure.
6. Exact duplicate file across two synthetic applications — exact-hash match.
7. Near-duplicate scan — similarity indicator and manual review, not a definitive conclusion.
8. Legitimate institution-name variation — no unsupported fraud label.
9. Badly scanned page — abstain or low extraction quality; request manual review.
10. Mock issuer unavailable — source-unavailable outcome and separate compliance state.
11. Malformed/unsupported upload — rejected safely with a clear message.
12. Tampered disposable audit event — chain verification fails.

Report only measured metrics. Useful metrics include field-level extraction precision/recall/F1, rule-check precision/recall, duplicate-match precision, false positives, latency and time taken by a reviewer to complete the same labelled cases with and without the tool. Do not copy aspirational targets into the results column.

---

## 17. Demo story for judges (about 4–5 minutes)

### Scene 1 — Institution pre-flight (45–60 seconds)

Upload a synthetic application bundle. Show one missing document, one expired test document and one field mismatch. The application screen explains which items need attention.

### Scene 2 — Officer queue and Evidence Graph (60–75 seconds)

Switch to the demo reviewer. Open the application and select the mismatch node. Show the application value, reference-record value, source page/region and rule version.

### Scene 3 — Reuse and verification (60–75 seconds)

Open a reused synthetic NOC. Show the two documents side by side and identify whether it is an exact hash match or only a similarity signal. Run the issuer adapter in a successful test state, then in an unavailable state.

### Scene 4 — Honest uncertainty and audit (45–60 seconds)

Use a bad scan that the extractor cannot reliably interpret. Show that the system abstains and requests manual review. Record the reviewer’s action and verify the audit chain.

### Close (20–30 seconds)

Show the measured benchmark panel with the dataset size, evaluation method and real results. State what is simulated and what would require authorised production integration.

**Always record a backup demo video.** Rehearse the live demo twice from a clean start. Keep a known-good synthetic seed dataset and a simple recovery path.

---

## 18. Visual quality: how to make it memorable without sacrificing truth

- Use an official-workflow aesthetic: restrained navy/blue, neutral surfaces, clear warning colours used semantically, readable type and strong contrast.
- Make the case file the centre of the product, not a dashboard of decorative charts.
- Use visual evidence: side-by-side source/reference values, page highlights, rule ID/version and clear next action.
- Keep all statuses legible without relying on colour alone.
- Keep the Evidence Graph interactive but provide a list/table fallback for accessibility.
- Avoid fake real-time animations, fabricated metrics, invented AICTE logos/seals and real institution personal data.
- Put “DEMO DATA — NOT CONNECTED TO LIVE AICTE SYSTEMS” somewhere unambiguous in demo mode.

---

## 19. How to use Antigravity safely and effectively

1. Put the approved specs and `AGENTS.md` in the workspace.
2. Use `/plan` or the UI's implementation-plan feature for every major phase.
3. Review the plan before approving implementation.
4. Limit each prompt to one milestone and its acceptance criteria.
5. Review diffs before accepting large edits.
6. Ask for exact test commands and output, not a verbal assurance.
7. Test the product in the browser yourself; Antigravity's walkthrough/screenshots help, but do not replace your own review.
8. Commit a Git checkpoint after every passing milestone.
9. Do not run parallel agents on the same files/branch unless the work is isolated and integration is planned.
10. Do not approve a change that replaces working code, removes tests or broadens scope without justification.
11. When a tool or dependency fails, ask Antigravity to diagnose the actual error and propose the smallest fix. Do not repeatedly paste “fix everything.”
12. Keep a short `docs/STATUS.md` updated with current milestone, working command, tests, known bugs and next task.

### Universal follow-up prompt after every milestone

```text
Before moving on, verify this milestone against its acceptance criteria in docs/IMPLEMENTATION_PLAN.md and AGENTS.md.

1. Inspect the Git diff and list every changed file with its purpose.
2. Run the exact relevant tests, type checks, lint and builds; include commands and actual output summaries.
3. Run the end-to-end browser path if the milestone affects the UI or API integration.
4. Identify missing, mocked, incomplete or untested behaviour honestly.
5. Fix failures caused by this milestone and rerun the failed tests.
6. Update docs/STATUS.md and relevant technical documentation.
7. Do not begin the next milestone. Stop and give me a clear pass/fail gate and any decisions I need to make.
```

---

## 20. Team responsibilities

For a six-person team, adapt this division to your actual strengths:

| Owner | Responsibility | First deliverable |
|---|---|---|
| Team lead/product | Scope, SIH format, user story, demo and judge Q&A | Approved MVP and pitch |
| Frontend lead | React pages, case file, PDF viewer, Evidence Graph | Clickable review flow wired to real APIs |
| Backend lead | FastAPI, database, migrations, permissions | Stable API and seed workflow |
| Document processing lead | Parsing, OCR, extraction and provenance | Fields with correct source pages |
| Validation/verification lead | Rules, cross-record checks, adapters and duplicates | Deterministic findings and all statuses tested |
| QA/data/documentation lead | Synthetic cases, expected results, security checks, README | Reproducible benchmark and release checklist |

Agree on API schemas before teammates build in parallel. Keep integration work owned by one person. The team lead should know every feature's actual state, even if they did not implement it.

---

## 21. Judge questions: answers you must be ready to defend

**Do you have access to AICTE records?**  
For the demo, state honestly whether the records are synthetic. Explain that production would require an authorised, read-only integration; do not claim access you do not have.

**How do you prove a document is authentic?**  
Explain that different mechanisms establish different facts. Signature validation, issuer response, QR/reference checks and cross-record comparisons are not interchangeable. An anomaly flag is preliminary, not proof of forgery.

**What happens when the issuer is unavailable?**  
The platform reports the source as unavailable or the verification as pending/manual review. It does not transform a connection failure into non-compliance.

**How do you prevent hallucinated rules?**  
Regulatory checks run using versioned rules tied to an official clause/effective period or are clearly labelled as synthetic demo rules. An LLM cannot create a regulatory verdict.

**How did you measure accuracy?**  
Show the labelled benchmark, expected outcomes, actual results, false positives, and test limitations. Use no unsupported percentages.

**Can the system reject an institution?**  
No. It supports preliminary scrutiny and records evidence. Authorised officials retain the required scrutiny, inspection and final decision-making.

**What is novel compared with OCR?**  
Demonstrate evidence linking, previous-record change comparison, verification fallbacks and reproducible rule versions. Do not rely only on slogans.

---

## 22. Final submission and demo checklist

### SIH submission

- [ ] Confirm current deadline and format with the official portal/SPOC.
- [ ] Use the exact SIH26261 title, category and theme from the portal.
- [ ] Follow the official template and slide limit.
- [ ] Explain innovation, feasibility, impact, security and human oversight.
- [ ] Label all simulated integrations and distinguish planned features from implemented ones.
- [ ] Include real references; verify the current applicable AICTE handbook and other rules.
- [ ] Save the final PDF, confirmation screenshot and backup.

### Prototype readiness

- [ ] Fresh setup succeeds using documented commands.
- [ ] Migrations and synthetic seed work reliably.
- [ ] Main application flow succeeds through the browser.
- [ ] Each finding has traceable evidence and rule/source context.
- [ ] All six verification states have tests.
- [ ] A poor scan and unavailable source are handled honestly.
- [ ] Legitimate variation does not trigger a definitive fraud claim.
- [ ] Reviewer actions and audit-chain verification work.
- [ ] Backend access control is tested directly.
- [ ] No secrets or real unauthorised personal data are present.
- [ ] Test results are real and reproducible.
- [ ] Demo works from a clean start and a backup recording exists.

### Final rule

**Do not add a new feature during the final stabilisation period unless it fixes a blocking bug.** A smaller, truthful, traceable and stable system is stronger than a larger system that only works on the happy path.

---

## References to keep with the project

- The official SIH 2026 portal, prescribed presentation template, official guidelines and notices; confirm the live versions with the institution's SPOC.
- AICTE Approval Process Handbook relevant to the application's time period and category, plus any applicable updated regulations/instructions.
- Google Antigravity official documentation for workspace rules (`AGENTS.md`), implementation plans, artifact review, permissions and browser walkthroughs.
- The team's uploaded 20-page planning document, `SIH Winning Pack: PRAMAAN-AI for AICTE Approvals`, as an internal blueprint—not as proof that any proposed feature or performance target has already been achieved.
