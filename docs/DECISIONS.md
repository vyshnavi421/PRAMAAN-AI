# PRAMAAN-AI: Architectural Decision Records (ADRs)

**Document Status:** Approved Architecture Baseline (Planning Only)  
**Version:** 1.0.0  

---

## ADR-001: Modular Monolith vs. Distributed Microservices
- **Context:** The SIH prototype must be reliable, reproducible on a standard 16GB developer laptop, and easily demonstrated without distributed failure modes (e.g., Kafka lag, service discovery failures, network partitioning).
- **Decision:** Build PRAMAAN-AI as a clean **modular monolith** with FastAPI backend, React frontend, and PostgreSQL database. Services communicate via typed Python interfaces within the process boundary while maintaining strict domain separation.
- **Consequences:**
  - *Positive:* Fast local startup, atomic database transactions across modules, simple debugging, lower memory footprint.
  - *Negative:* High-scale horizontal autoscaling of single modules requires future extraction (which is enabled by the modular boundaries).

---

## ADR-002: Deterministic Rule Engine over Generative LLMs for Regulatory Compliance
- **Context:** Large Language Models (LLMs) suffer from non-deterministic behavior, stochastic drift, and hallucination risks. AICTE regulatory scrutiny requires legal accountability and exact citation of the Approval Process Handbook (APH).
- **Decision:** Regulatory rule evaluation will be **100% deterministic**. Rules are expressed as declarative condition trees evaluated over extracted facts. LLMs/OCR models are restricted exclusively to text parsing and layout perception; they never decide regulatory compliance.
- **Consequences:**
  - *Positive:* Total explainability, zero legal hallucination risk, instantaneous sub-second execution, bit-for-bit reproducible validation runs.
  - *Negative:* New regulatory rules require structured configuration rather than arbitrary free-text parsing.

---

## ADR-003: Strict Separation of Document Status, Finding Status, and Application Workflow Status
- **Context:** In naive validation systems, an external network timeout or a single missing document often erroneously flips the entire application into an ambiguous "FAILED" or "REJECTED" state.
- **Decision:** The system strictly separates three orthogonal state dimensions:
  1. *Document Verification Status:* Exactly one of the 6 official problem statement states (`verified`, `mismatch detected`, `expired`, `verification pending`, `source unavailable`, `manual review required`).
  2. *Finding Status:* Discrete evaluation per rule (`COMPLIANT`, `DEFICIENCY`, `ANOMALY_SIGNAL`, `INCONCLUSIVE`).
  3. *Application Workflow Status:* Procedural state (`DRAFT`, `SUBMITTED`, `UNDER_SCRUTINY`, `CLARIFICATION_REQUESTED`, `SCRUTINY_COMPLETED`).
- **Consequences:**
  - *Positive:* A network failure at an external issuer yields `source unavailable` and does not penalize the institution's compliance standing.
  - *Negative:* Requires clearer UI rendering to prevent officer confusion between individual document states and application recommendations.

---

## ADR-004: File Ingestion Security and Hash-Addressed Storage
- **Context:** Direct storage of user-provided filenames creates vulnerabilities to directory traversal (`../../etc/passwd`), null-byte injection, and filename collision attacks.
- **Decision:** Uploaded documents are stripped of original paths, verified against binary magic headers (PDF/PNG/JPEG), hashed via SHA-256, and stored under server-generated UUID keys in an isolated protected storage directory. Direct filesystem paths are never returned in API payloads.
- **Consequences:**
  - *Positive:* Complete immunity to path traversal and filename collisions; tamper detection via SHA-256.
  - *Negative:* Requires mapping database tables to serve document streams through authenticated proxy routes.

---

## ADR-005: Provider-Agnostic Adapter Pattern for Issuer Verification
- **Context:** AICTE applicants submit documents issued by diverse external bodies (State Fire Services, Town Planning Authorities, Universities, Revenue Departments). In a prototype setting, live government APIs are unavailable without statutory authorization.
- **Decision:** Implement a provider-agnostic `VerificationAdapter` interface. In prototype mode, concrete adapters operate as deterministic simulated services returning all 6 official states with realistic latency. In production, these adapters can be swapped with real authenticated API clients without changing core business logic.
- **Consequences:**
  - *Positive:* Honest, verifiable demonstration of all 6 states without illegally scraping or claiming fake government access.
  - *Negative:* Judges must understand that simulated adapters demonstrate technical capability, not pre-existing government connectivity.

---

## ADR-006: Cryptographic Hash-Chained Audit Ledger
- **Context:** Regulatory scrutiny decisions require auditable integrity. However, deploying a private blockchain introduces unnecessary complexity, consensus overhead, and infrastructure weight for an SIH prototype.
- **Decision:** Implement an append-only audit event table in PostgreSQL where each record contains the SHA-256 hash of its contents combined with the hash of the preceding event ($H_i = \text{SHA256}(H_{i-1} \parallel \dots)$). Expose a dedicated verification endpoint (`POST /audit/verify-chain`).
- **Consequences:**
  - *Positive:* Instantaneous mathematical proof of log integrity; detects unauthorized row updates or deletions.
  - *Negative:* Does not protect against a database administrator who maliciously recalculates the entire chain from scratch (disclosed in threat model).

---

## ADR-007: Graceful Abstention over Guessing for Low-Quality OCR
- **Context:** Optical Character Recognition (OCR) on degraded, skewed, or low-resolution scans often yields garbled strings or low-confidence values. Passing garbled text to rule engines creates false alarms.
- **Decision:** Extraction models compute a confidence score ($0.000$ to $1.000$). Any field extracted with confidence below $0.65$ or from an unreadable page is marked `LOW_CONFIDENCE`. The rule engine abstains from issuing a compliance verdict and routes the case to `manual review required`.
- **Consequences:**
  - *Positive:* Eliminates false fraud accusations; builds officer trust by acknowledging technological boundaries.
  - *Negative:* Low-quality scans require human intervention, preventing 100% automated processing for degraded files.

---

## ADR-008: Independent Coverage Audit Guarantee for Full-Application Review Orchestration
- **Context:** An institutional application contains diverse documents and claims subject to statutory rules, external verification adapters, and cross-application duplicate checks. If an orchestrator silently drops or skips a check due to an unhandled exception, loop failure, or improper filtering, an incomplete scrutiny could be mistakenly presented to human reviewers as a clean pass.
- **Decision:** Implement an independent `CoverageAuditor` operating on a strict pre-execution plan contract:
  1. *Pre-Enumeration:* Prior to evaluating any rule or calling any adapter, the orchestrator computes a frozen `CheckPlan` enumerating every check that must be performed.
  2. *Exhaustive Accounting:* Every planned check must terminate in an unambiguous outcome: a `Finding`, a `VerificationRecord`, a `DuplicateAlert`, or an explicitly recorded skipped check with a documented rationale (`SKIPPED_NOT_APPLICABLE`, `SKIPPED_MISSING_DOCUMENT`, `SKIPPED_EXTRACTION_UNAVAILABLE`).
  3. *Reconciliation Guardrail:* The `CoverageAuditor` reconciles planned checks against recorded outcomes. If any check is unaccounted for, or if an unprompted outcome appears without a plan entry, the audit status is forced to `INCOMPLETE` (`is_complete=False`). A review report is never marked `COMPLETE` unless coverage audit reconciliation passes 100%.
- **Consequences:**
  - *Positive:* Eliminates silent bypasses; provides mathematical proof of complete pre-scrutiny; establishes transparent accountability for vigilance and supervisory review.
  - *Negative:* Developers adding new check types or rules must register both the planning enumeration and terminal outcome handling, preventing ad-hoc unmonitored execution.

