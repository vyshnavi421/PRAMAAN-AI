"""
Reproducible field-level evaluation of the real document extractor against 30
small, generated synthetic PDFs. This is a format-coverage measurement, not a
production accuracy estimate. It does not evaluate OCR or real-world documents.
Run from repository root:
    python backend/evaluate_document_extraction.py
    python backend/evaluate_document_extraction.py --report-path docs/EXTRACTION_EVALUATION.md
"""
import argparse
import json
import os
import sys
from collections import Counter
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.models.enums import DocumentType
from app.services.document_extractor import global_document_extractor


def make_text_pdf(text: str) -> bytes:
    """Build a tiny, valid one-page PDF with one text line and a Helvetica font."""
    escaped = text.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")
    stream = f"BT /F1 12 Tf 50 720 Td ({escaped}) Tj ET\n".encode("ascii")
    objects = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] "
        b"/Resources << /Font << /F1 4 0 R >> >> /Contents 5 0 R >>",
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
        b"<< /Length " + str(len(stream)).encode("ascii") + b" >>\nstream\n" + stream + b"endstream",
    ]
    pdf = bytearray(b"%PDF-1.4\n")
    offsets = [0]
    for index, obj in enumerate(objects, start=1):
        offsets.append(len(pdf))
        pdf.extend(f"{index} 0 obj\n".encode("ascii"))
        pdf.extend(obj)
        pdf.extend(b"\nendobj\n")
    xref_offset = len(pdf)
    pdf.extend(f"xref\n0 {len(objects) + 1}\n".encode("ascii"))
    pdf.extend(b"0000000000 65535 f \n")
    for offset in offsets[1:]:
        pdf.extend(f"{offset:010d} 00000 n \n".encode("ascii"))
    pdf.extend(
        f"trailer\n<< /Size {len(objects) + 1} /Root 1 0 R >>\n"
        f"startxref\n{xref_offset}\n%%EOF\n".encode("ascii")
    )
    return bytes(pdf)


def build_cases() -> List[Dict[str, Any]]:
    """Return 30 small cases with explicit ground truth for each expected claim."""
    cases: List[Dict[str, Any]] = []

    # Six supported Fire Safety NOCs: issue date, expiry date, issuing authority.
    for i in range(1, 7):
        issue = f"2023-{i:02d}-15"
        expiry = f"2027-{i:02d}-28"
        authority = f"State Fire Services Unit {i:02d}"
        text = f"Issued on: {issue}, Valid until: {expiry}, Issuing authority: {authority}"
        cases.append({
            "case_id": f"NOC-SUPPORTED-{i:02d}",
            "document_type": DocumentType.FIRE_SAFETY_NOC,
            "text": text,
            "expected": {
                "noc_issue_date": issue,
                "noc_expiry_date": expiry,
                "issuing_authority": authority,
            },
        })

    # Four known expiry claims expressed in month-name wording not supported by the
    # current parser patterns. Correct behavior is abstention/manual review.
    for i in range(1, 5):
        expiry = f"January {10 + i}, 2024"
        text = f"Fire safety certificate validity ends on {expiry}; reference FS-ALT-{i:02d}"
        cases.append({
            "case_id": f"NOC-UNSUPPORTED-DATE-WORDING-{i:02d}",
            "document_type": DocumentType.FIRE_SAFETY_NOC,
            "text": text,
            "expected": {"noc_expiry_date": f"2024-01-{10 + i:02d}"},
        })

    # Eight affidavits with an institution name and declared intake.
    for i in range(1, 9):
        name = f"Synthetic College {i:02d}"
        intake = str(100 + 10 * i)
        cases.append({
            "case_id": f"AFFIDAVIT-{i:02d}",
            "document_type": DocumentType.AFFIDAVIT_GENERAL,
            "text": f"Institution: {name}, Intake: {intake}",
            "expected": {
                "institution_name": name,
                "total_intake": intake,
            },
        })

    # Six land-use certificates with a stated land area.
    for i in range(1, 7):
        area = f"{4 + i / 2:.1f}"
        cases.append({
            "case_id": f"LAND-AREA-{i:02d}",
            "document_type": DocumentType.LAND_USE_CERTIFICATE,
            "text": f"Land area: {area} acres",
            "expected": {"land_area_acres": area},
        })

    # Six architect/building-plan documents with built-up area.
    for i in range(1, 7):
        area = str(10000 + i * 500)
        cases.append({
            "case_id": f"BUILT-UP-AREA-{i:02d}",
            "document_type": DocumentType.BUILDING_PLAN_ARCHITECT,
            "text": f"Built-up area: {area} sqm",
            "expected": {"builtup_area_sqm": area},
        })

    assert len(cases) == 30
    return cases


def run_evaluation() -> Dict[str, Any]:
    cases = build_cases()
    correct = 0
    wrong = 0
    abstained = 0
    bbox_available = 0
    method_counts: Counter[str] = Counter()
    status_counts: Counter[str] = Counter()
    per_case: List[Dict[str, Any]] = []

    for case in cases:
        pdf_bytes = make_text_pdf(case["text"])
        fields, status, note = global_document_extractor.extract_document(
            content_bytes=pdf_bytes,
            doc_type=case["document_type"],
            original_filename=f"{case['case_id'].lower()}.pdf",
        )
        expected: Dict[str, str] = case["expected"]
        actual_by_key: Dict[str, List[Any]] = {}
        for field in fields:
            actual_by_key.setdefault(field.field_key, []).append(field)
            method_counts[field.extraction_method] += 1
            if field.provenance.bounding_box is not None:
                bbox_available += 1

        case_correct = 0
        case_wrong = 0
        case_abstained = 0
        outcomes = []
        for key, expected_value in expected.items():
            predictions = actual_by_key.get(key, [])
            if not predictions:
                abstained += 1
                case_abstained += 1
                outcomes.append({
                    "field": key, "expected": expected_value, "actual": None, "outcome": "ABSTAINED"
                })
                continue

            field = predictions[0]
            if field.field_value == expected_value:
                correct += 1
                case_correct += 1
                outcome = "CORRECT"
            else:
                wrong += 1
                case_wrong += 1
                outcome = "WRONG"
            outcomes.append({
                "field": key,
                "expected": expected_value,
                "actual": field.field_value,
                "outcome": outcome,
            })

            # Repeated claims with the same key are extra unsupported predictions.
            if len(predictions) > 1:
                extra = len(predictions) - 1
                wrong += extra
                case_wrong += extra

        # Any claim outside the expected schema is an unexpected prediction.
        for key, predictions in actual_by_key.items():
            if key not in expected:
                wrong += len(predictions)
                case_wrong += len(predictions)
                outcomes.append({
                    "field": key,
                    "expected": None,
                    "actual": [field.field_value for field in predictions],
                    "outcome": "UNEXPECTED_PREDICTION",
                })

        status_value = status.value if hasattr(status, "value") else str(status)
        status_counts[status_value] += 1
        per_case.append({
            "case_id": case["case_id"],
            "document_type": case["document_type"].value,
            "status": status_value,
            "expected_fields": len(expected),
            "extracted_fields": len(fields),
            "correct": case_correct,
            "wrong": case_wrong,
            "abstained": case_abstained,
            "note": note,
            "outcomes": outcomes,
        })

    expected_fields = sum(len(case["expected"]) for case in cases)
    exact_match_rate = 100.0 * correct / expected_fields if expected_fields else 0.0
    return {
        "dataset": "30 generated synthetic one-page PDFs; text-stream extraction only",
        "document_count": len(cases),
        "expected_field_count": expected_fields,
        "correct": correct,
        "wrong": wrong,
        "abstained": abstained,
        "exact_match_rate_pct": round(exact_match_rate, 2),
        "bbox_available_claim_count": bbox_available,
        "extraction_methods": dict(sorted(method_counts.items())),
        "document_statuses": dict(sorted(status_counts.items())),
        "per_case": per_case,
    }


def render_report(results: Dict[str, Any], generated_at: Optional[str] = None) -> str:
    timestamp = generated_at or datetime.now(timezone.utc).isoformat(timespec="seconds")
    lines = [
        "# PRAMAAN-AI Synthetic Document Extraction Evaluation",
        "",
        f"Generated (UTC): {timestamp}  ",
        f"Dataset: {results['dataset']}  ",
        "Scope: deterministic regression/evaluation set; not production accuracy and not an OCR benchmark.",
        "",
        "## Field-level results",
        "",
        "| Measure | Observed result |",
        "|---|---:|",
        f"| Synthetic documents | {results['document_count']} |",
        f"| Expected field slots | {results['expected_field_count']} |",
        f"| Correct exact field matches | {results['correct']} |",
        f"| Wrong or unexpected extracted claims | {results['wrong']} |",
        f"| Expected fields abstained / not extracted | {results['abstained']} |",
        f"| Correct matches / expected field slots | {results['exact_match_rate_pct']:.2f}% |",
        f"| Claims with a source bounding box | {results['bbox_available_claim_count']} |",
        "",
        "The exact-match rate is correct field matches divided by all expected field slots. Abstentions remain in the denominator; they are not counted as correct.",
        "",
        "## Document processing outcomes",
        "",
        "| Outcome | Count |",
        "|---|---:|",
    ]
    for status, count in results["document_statuses"].items():
        lines.append(f"| {status} | {count} |")
    lines.extend([
        "",
        "## Scope and interpretation",
        "",
        "- The PDFs are generated by this script and contain known synthetic text. This tests supported field patterns and deliberate unsupported wording, not the variability of real institutional documents.",
        "- The evaluation uses PDF text streams only; it does not measure scan OCR, real-world accuracy, issuer verification, or the complete scrutiny workflow.",
        "- Four Fire Safety NOC cases use month-name expiry wording outside the supported parser patterns. Their expected expiry fields are treated as abstentions, so the demo should route such input for manual review rather than claim the expiry was verified.",
        "- Re-run with python backend/evaluate_document_extraction.py --report-path docs/EXTRACTION_EVALUATION.md to regenerate the report from the current extractor.",
        "",
        "## Per-case outcomes",
        "",
        "| Case | Document type | Status | Expected fields | Extracted | Correct | Wrong | Abstained |",
        "|---|---|---|---:|---:|---:|---:|---:|",
    ])
    for case in results["per_case"]:
        lines.append(
            f"| {case['case_id']} | {case['document_type']} | {case['status']} | "
            f"{case['expected_fields']} | {case['extracted_fields']} | {case['correct']} | "
            f"{case['wrong']} | {case['abstained']} |"
        )
    return "\n".join(lines) + "\n"


def main() -> None:
    parser = argparse.ArgumentParser(description="Evaluate extraction on 30 generated synthetic PDFs.")
    parser.add_argument("--report-path", help="Optional Markdown path for the generated evaluation report.")
    parser.add_argument("--json", action="store_true", help="Print machine-readable JSON instead of Markdown.")
    args = parser.parse_args()

    results = run_evaluation()
    report = render_report(results)
    if args.report_path:
        parent = os.path.dirname(os.path.abspath(args.report_path))
        os.makedirs(parent, exist_ok=True)
        with open(args.report_path, "w", encoding="utf-8") as output:
            output.write(report)
    if args.json:
        print(json.dumps(results, indent=2))
    else:
        print(report)


if __name__ == "__main__":
    main()
