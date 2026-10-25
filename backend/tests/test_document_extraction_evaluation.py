"""Regression guard for the labelled 30-document extraction evaluation."""
from evaluate_document_extraction import build_cases, render_report, run_evaluation


def test_dataset_has_30_synthetic_documents_and_50_labelled_fields():
    cases = build_cases()
    assert len(cases) == 30
    assert sum(len(case["expected"]) for case in cases) == 50
    assert len({case["case_id"] for case in cases}) == 30


def test_extraction_evaluation_counts_are_reproducible():
    result = run_evaluation()
    assert result["document_count"] == 30
    assert result["expected_field_count"] == 50
    assert result["correct"] == 46
    assert result["wrong"] == 0
    assert result["abstained"] == 4
    assert result["exact_match_rate_pct"] == 92.0
    assert result["document_statuses"]["manual review required"] == 4
    assert result["document_statuses"]["verification pending"] == 26
    assert result["correct"] + result["abstained"] == result["expected_field_count"]


def test_report_discloses_synthetic_scope_and_abstention():
    result = run_evaluation()
    report = render_report(result, generated_at="2026-10-25T00:00:00+00:00")
    assert "not production accuracy" in report
    assert "does not measure scan OCR" in report
    assert "| Expected fields abstained / not extracted | 4 |" in report
    assert "NOC-UNSUPPORTED-DATE-WORDING" in report
