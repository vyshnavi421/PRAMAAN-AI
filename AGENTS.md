# PRAMAAN-AI Engineering Rules

## Product truth and scope
- The project is a prototype for SIH26261, not an official AICTE system.
- Use synthetic data by default. Do not claim live AICTE or issuer integration unless a real, authorised integration has been configured and verified.
- All mock sources, mock records and simulated results must be visibly labelled DEMO / SIMULATED in the UI and docs.
- Never scrape restricted portals, bypass login controls, or invent API access.
- The system is decision support only. It must not autonomously approve/reject institutions or state that a person/entity committed fraud.

## Architecture
- **Current prototype stack (as built):** FastAPI backend, dependency-free ES-module frontend served from `backend/static`, JSON/JSONL file persistence via `PRAMAAN_DATA_DIR`. React + TypeScript + PostgreSQL below is the production target, not what is implemented today.
- Begin as a modular monolith: React + TypeScript frontend, FastAPI backend, PostgreSQL database, protected document storage.
- Keep API routes, services, models, schemas and tests in separate modules.
- Do not add a framework, database, queue, vector store, LLM or microservice unless a requirement demonstrates the need.
- Keep API contracts documented and typed.
- Do not silently alter the agreed database schema or response contract.

## Evidence and findings
- Every extracted field must retain source document ID, page number, text/region reference when available, extraction method and extraction confidence/quality information.
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
