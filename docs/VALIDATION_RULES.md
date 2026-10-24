# PRAMAAN-AI: Validation Rules Engine & Regulatory Rule Packs

**Document Status:** Approved Architecture Baseline (Planning Only)  
**Version:** 1.0.0  
**Rule Framework:** Deterministic Evaluator with Immutable Versioning  
**Authoritative Reference:** AICTE Approval Process Handbook (APH) 2024–2027 & Demo Rules  

---

## 1. Engine Philosophy: Deterministic Truth vs. AI Hallucination

In regulatory administration, **statutory decisions cannot be outsourced to a non-deterministic generative LLM**. A model cannot invent rules, adjust tolerances, or declare violations on intuition.

PRAMAAN-AI enforces:
1. **Deterministic Rule Execution:** Rules are declarative condition trees evaluated directly against parsed facts and approved reference baselines.
2. **Authoritative Citation:** Every rule references a specific chapter, clause, or table of the AICTE Approval Process Handbook (e.g., *APH 2024-27 Clause 4.2(b)*) or is visibly stamped `DEMO_RULE`.
3. **Reproducibility:** A validation run persists the exact rule pack version (`v1.2.0`) and input snapshot used. Re-evaluating historical runs produces bit-for-bit identical findings.
4. **Graceful Abstention:** If a field has low OCR confidence ($<0.65$) or is unreadable, the rule engine does not guess or generate a compliance failure—it abstains and outputs `INCONCLUSIVE` with a `manual review required` action.

---

## 2. Rule Pack Schema Specification

```json
{
  "$schema": "https://pramaan-ai.aicte.gov.in/schemas/rule-pack.json",
  "pack_id": "rp-aicte-aph-2024-eoa",
  "pack_name": "AICTE APH 2024-2027 Extension of Approval Core Pack",
  "version": "v1.0.0",
  "category": "EXTENSION_OF_APPROVAL",
  "effective_from": "2024-04-01",
  "effective_to": "2027-03-31",
  "is_demo": false,
  "rules": []
}
```

### Rule Object Schema
- `rule_code` (string): Unique identifier (e.g., `RULE-APH-001`).
- `title` (string): Human-readable name.
- `clause_citation` (string): Verbatim legal citation.
- `severity` (enum): `DEFICIENCY` (blocks approval), `ANOMALY_SIGNAL` (requires investigation), `OBSERVATION` (informational).
- `condition`: JSON declarative condition tree (comparison operators, existence checks, boundary ranges).
- `evidence_requirements`: Required document types and field keys.
- `explanation_template`: Markdown template populated with concrete runtime values.
- `remediation_hint`: Specific rectifying steps for the applicant institution.

---

## 3. Concrete Initial Rule Pack

### RULE-APH-001: Mandatory Document Completeness
- **Citation:** AICTE APH 2024–27 Chapter II, Clause 2.3 & Appendix 16.
- **Severity:** `DEFICIENCY`
- **Description:** Verifies that all mandatory supporting documents for an Extension of Approval (EoA) application are present in the dossier.
- **Mandatory Types:**
  1. `AFFIDAVIT_GENERAL` (Affidavit on ₹100 stamp paper per AICTE format)
  2. `LAND_USE_CERTIFICATE` (Issued by competent revenue/planning authority)
  3. `FIRE_SAFETY_NOC` (Issued by State Fire & Emergency Services)
  4. `BUILDING_PLAN_ARCHITECT` (Signed architect certificate of built-up area)
  5. `GOVERNING_BODY_RESOLUTION` (Trust/Society approval of proposed intake)
- **Logic:**
  ```python
  missing = set(mandatory_types) - set(application.uploaded_document_types)
  if missing:
      return Status.DEFICIENCY, f"Missing mandatory document(s): {', '.join(missing)}"
  return Status.COMPLIANT, "All mandatory documents present."
  ```

---

### RULE-APH-002: Document Validity & Expiry Check
- **Citation:** AICTE APH 2024–27 Clause 4.2(b).
- **Severity:** `DEFICIENCY`
- **Description:** Validates that time-bounded certificates (specifically Fire Safety NOC and Structural Stability Certificate) have not expired prior to the academic year submission cutoff (e.g., `2026-06-30`).
- **Input Fields:** `FIRE_SAFETY_NOC.noc_expiry_date`, `application.submission_cutoff_date`.
- **Logic:**
  ```python
  if noc_expiry_date is None:
      return Status.INCONCLUSIVE, "Expiry date unreadable; manual review required."
  if noc_expiry_date < application.submission_cutoff_date:
      return Status.DEFICIENCY, f"Fire Safety NOC expired on {noc_expiry_date}."
  return Status.COMPLIANT, f"Fire Safety NOC valid until {noc_expiry_date}."
  ```

---

### RULE-APH-003: Land Area & Built-Up Area Compliance
- **Citation:** AICTE APH 2024–27 Chapter IV, Table 4.1 & Clause 4.1.
- **Severity:** `DEFICIENCY`
- **Description:** Compares extracted built-up area from the Architect Certificate against the minimum prescribed norm based on total approved intake and institution category.
- **Prescribed Formula (Technical Degree Institute in Mega/Metro):**
  $$\text{Required Built-Up Area} = \text{Total Intake} \times 4.5\text{ sq.m per student}$$
- **Input Fields:** `BUILDING_PLAN_ARCHITECT.builtup_area_sqm`, `application.declared_data.total_intake`.
- **Logic:**
  ```python
  required_sqm = declared_intake * 4.5
  if extracted_builtup_area < required_sqm:
      deficit = required_sqm - extracted_builtup_area
      return Status.DEFICIENCY, f"Built-up area deficit of {deficit:.1f} sq.m."
  return Status.COMPLIANT, "Built-up area exceeds statutory threshold."
  ```

---

### RULE-APH-004: Faculty-Student Cadre Ratio (FSR)
- **Citation:** AICTE APH 2024–27 Chapter VII, Table 7.1.
- **Severity:** `DEFICIENCY`
- **Description:** Ensures the institution maintains a Faculty-to-Student Ratio of at least $1:20$ for Engineering & Technology undergraduate programmes.
- **Input Fields:** `application.declared_data.faculty_count`, `application.declared_data.total_intake`.
- **Calculation:**
  $$\text{FSR} = \frac{\text{Declared Faculty Count}}{\text{Declared Student Intake}}$$
- **Logic:**
  ```python
  if declared_faculty == 0:
      return Status.DEFICIENCY, "Zero faculty declared."
  actual_ratio = declared_intake / declared_faculty
  if actual_ratio > 20.0:
      return Status.DEFICIENCY, f"FSR is 1:{actual_ratio:.1f}, violating minimum 1:20 norm."
  return Status.COMPLIANT, f"FSR 1:{actual_ratio:.1f} meets prescribed norm."
  ```

---

### RULE-APH-005: Approved Intake Consistency vs. Historical Baseline
- **Citation:** AICTE APH 2024–27 Clause 3.1 & AICTE Historical Approval Records.
- **Severity:** `ANOMALY_SIGNAL`
- **Description:** Compares the declared intake in the current application against the AICTE baseline approved in the previous academic year snapshot. If an increase is claimed without an accompanying `INCREASE_IN_INTAKE` approval application, raises a preliminary anomaly signal.
- **Input Fields:** `application.declared_data.total_intake`, `application_snapshot.approved_intake`.
- **Logic:**
  ```python
  if application.category == "EXTENSION_OF_APPROVAL":
      if current_intake > prior_intake:
          return Status.ANOMALY_SIGNAL, (
              f"Declared intake ({current_intake}) exceeds prior approved baseline "
              f"({prior_intake}) in an Extension of Approval request."
          )
  return Status.COMPLIANT, "Declared intake matches prior approved baseline."
  ```

---

### RULE-APH-006: Institutional Name & Identifier Cross-Consistency
- **Citation:** AICTE APH 2024–27 Appendix 16 & Clause 2.4.
- **Severity:** `ANOMALY_SIGNAL`
- **Description:** Validates that the legal institution name extracted across the Affidavit, Land Use Certificate, and Fire Safety NOC matches the registered AICTE master record within a fuzzy similarity threshold ($\ge 90\%$).
- **Logic:**
  - If match $\ge 90\%$: `COMPLIANT`.
  - If match $75\% - 89\%$: `ANOMALY_SIGNAL` (e.g., "Apex College of Engineering" vs. "Apex Institute of Technology" — legitimate name variation or discrepancy).
  - If match $< 75\%$: `DEFICIENCY` (Potential submission of wrong institutional certificate).

---

### RULE-APH-007: Cross-Application Document Reuse Detection
- **Citation:** Synthetic Demonstration Rule (`DEMO_RULE_REUSE_001`).
- **Severity:** `ANOMALY_SIGNAL`
- **Description:** Searches the repository for exact binary SHA-256 matches or near-duplicate text hashes associated with a different institution ID.
- **Guardrail:** The finding is explicitly labeled **"Preliminary Indicator: Document Reuse Identified"** and provides side-by-side case links. It **never claims fraud or forgery**.

---

## 4. Edge Cases, Abstention & Fallbacks

| Scenario | Engine Evaluation | System Action |
|---|---|---|
| **Low-Quality Scan (OCR Confidence < 0.65)** | `INCONCLUSIVE` | Abstains from compliance check. Generates task: *Manual visual review required for unreadable certificate.* |
| **Missing Field in Document** | `INCONCLUSIVE` | Does not invent value. Notes: *Field 'issue_date' not found on page 1.* Routes to reviewer. |
| **Simulated Issuer Adapter Timeout (503)** | `SOURCE_UNAVAILABLE` | Retains document verification state as `source unavailable`. **Does not fail applicant's compliance status**. |
| **Legitimate Institution Name Variation** | `ANOMALY_SIGNAL` | Displays both strings with similarity score (e.g. 88%). Flags for officer confirmation. |
