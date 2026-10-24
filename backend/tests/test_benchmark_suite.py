"""
PRAMAAN-AI Benchmark Quality Assurance & Ground-Truth Test Suite
Verifies:
1. All 15 canonical benchmark fixtures are deterministic and schema-valid.
2. Benchmark evaluator computes empirical metrics from actual runtime executions.
3. Field extraction achieves >= 95% precision, recall, and value accuracy.
4. Regulatory rules achieve >= 95% precision and recall with 0 false alarms.
5. Exact duplicate detection is evaluated separately from approximate similarity.
6. Coverage guarantee enforces INCOMPLETE verdict when a check is deliberately omitted.
7. Spot-checks independently verify clean cases and false-positive traps.
8. Non-evaluable checks (OCR uncertainty, gateway timeouts, inapplicable rules) are accounted for honestly.
"""
import pytest
import os
from datetime import datetime

from app.models.enums import FindingStatus, DocumentVerificationStatus
from app.benchmark.fixtures import get_canonical_benchmark_fixtures
from app.benchmark.evaluator import BenchmarkEvaluator
from app.benchmark.runner import generate_markdown_report


@pytest.fixture(scope="module")
def benchmark_results():
    """
    Executes the benchmark once for the test module to verify empirical outputs.
    """
    fixtures = get_canonical_benchmark_fixtures()
    evaluator = BenchmarkEvaluator(fixtures=fixtures, random_seed=42)
    return evaluator.run_benchmark(verbose=False)


def test_canonical_fixtures_catalog_completeness():
    """Verifies that all 15 required benchmark fixtures exist and have ground truths."""
    fixtures = get_canonical_benchmark_fixtures()
    assert len(fixtures) == 15

    bundle_ids = {f.bundle_id for f in fixtures}
    required_bundles = {
        "BM-01-CLEAN",
        "BM-02-MISSING-DOC",
        "BM-03-MISSING-FIELD",
        "BM-04-EXPIRED-DOC",
        "BM-05-CONFLICTING-FIELDS",
        "BM-06-HISTORICAL-DIFF",
        "BM-07-EXACT-DUPLICATE",
        "BM-08-APPROX-DUPLICATE",
        "BM-09-NAME-VARIATION",
        "BM-10-POOR-SCAN",
        "BM-11-MISSING-REF",
        "BM-12-SOURCE-TIMEOUT",
        "BM-13-NON-APPLICABLE",
        "BM-14-OMITTED-CHECK",
        "BM-15-ALTERED-ARTIFACT",
    }
    assert required_bundles.issubset(bundle_ids)

    # Every fixture must have application and ground-truth specifications
    for f in fixtures:
        assert f.application is not None
        assert f.bundle_id.startswith("BM-")
        assert len(f.name) > 0


def test_benchmark_evaluator_overall_reliability(benchmark_results):
    """100% of benchmark bundles reach their expected ground-truth terminal states."""
    assert benchmark_results.total_bundles == 15
    assert benchmark_results.bundles_passed == 15
    assert benchmark_results.bundles_failed == 0


def test_field_extraction_empirical_metrics(benchmark_results):
    """Field extraction achieves high accuracy and empirical ground-truth matching."""
    ext = benchmark_results.extraction_metrics
    assert ext.total_fields_evaluated > 0
    assert ext.precision >= 0.95
    assert ext.recall >= 0.95
    assert ext.f1_score >= 0.95
    assert ext.value_exact_accuracy >= 0.95
    assert ext.is_measured is True


def test_regulatory_rule_precision_recall_and_zero_false_alarms(benchmark_results):
    """
    Rules engine detects all injected deficiencies and anomalies with zero false alarms.
    FPR must be exactly 0.0 (no compliant check flagged as deficiency).
    """
    rule = benchmark_results.rule_metrics
    assert rule.total_rule_evaluations > 0
    assert rule.true_positives > 0
    assert rule.true_negatives > 0
    assert rule.false_positives == 0  # Zero false alarms on compliant cases!
    assert rule.false_negatives == 0  # No missed deficiencies!
    assert rule.precision == 1.0
    assert rule.recall == 1.0
    assert rule.f1_score == 1.0
    assert rule.false_positive_rate == 0.0
    assert rule.is_measured is True


def test_duplicate_detection_exact_vs_approximate_separation(benchmark_results):
    """Exact binary duplicates are evaluated separately from approximate similarity."""
    dup = benchmark_results.duplicate_metrics
    # Exact binary matching (SHA-256)
    assert dup.exact_match_total_evaluations >= 1
    assert dup.exact_match_precision == 1.0
    assert dup.exact_match_recall == 1.0

    # Approximate similarity / boilerplate template matching
    assert dup.approx_match_total_evaluations >= 1
    assert dup.approx_match_precision >= 0.90
    assert dup.approx_match_recall >= 0.90


def test_coverage_guarantee_enforces_incomplete_on_omission(benchmark_results):
    """
    Independent Coverage Auditor proves that when a check is deliberately omitted,
    the review CANNOT be labeled complete.
    """
    cov = benchmark_results.coverage_metrics
    assert cov.bundles_audited == 15
    assert cov.complete_bundles == 14
    assert cov.incomplete_bundles == 1  # BM-14-OMITTED-CHECK

    # Locate spot check for BM-14
    omission_spot = next(s for s in benchmark_results.spot_checks if s.bundle_id == "BM-14-OMITTED-CHECK")
    assert omission_spot.coverage_verdict == "INCOMPLETE"
    assert omission_spot.actual_status == "INCOMPLETE"
    assert omission_spot.spot_check_passed is True


def test_spot_check_clean_case(benchmark_results):
    """Spot check BM-01-CLEAN has 0 deficiencies, 0 anomalies, and COMPLETE_COMPLIANT status."""
    clean_spot = next(s for s in benchmark_results.spot_checks if s.bundle_id == "BM-01-CLEAN")
    assert clean_spot.is_clean_case is True
    assert clean_spot.deficiencies_found == 0
    assert clean_spot.anomalies_found == 0
    assert clean_spot.actual_status == "COMPLETE_COMPLIANT"
    assert clean_spot.spot_check_passed is True


def test_spot_check_false_positive_trap(benchmark_results):
    """
    Spot check BM-09-NAME-VARIATION:
    'Apex Inst. of Tech.' vs 'Apex Institute of Technology' must NOT be flagged as defect.
    """
    trap_spot = next(s for s in benchmark_results.spot_checks if s.bundle_id == "BM-09-NAME-VARIATION")
    assert trap_spot.is_false_positive_trap is True
    assert trap_spot.deficiencies_found == 0
    assert trap_spot.anomalies_found == 0
    assert trap_spot.false_positives_detected == 0
    assert trap_spot.spot_check_passed is True


def test_non_evaluable_checks_accounting(benchmark_results):
    """Statutory abstentions and non-evaluable events are tracked honestly."""
    non_eval = benchmark_results.non_evaluable_metrics
    assert non_eval.uncertain_ocr_abstentions >= 1
    assert non_eval.source_unavailable_events >= 1
    assert non_eval.not_applicable_rules >= 1
    assert non_eval.manual_review_routed_tasks >= 1


def test_markdown_report_generation(tmp_path, benchmark_results):
    """Verifies that docs/EVALUATION_REPORT.md generates cleanly with valid markdown tables."""
    report_file = tmp_path / "EVALUATION_REPORT.md"
    generate_markdown_report(benchmark_results, str(report_file))

    assert report_file.exists()
    content = report_file.read_text(encoding="utf-8")
    assert "# PRAMAAN-AI: Empirical Benchmark Evaluation Report" in content
    assert "Extraction Precision" in content
    assert "Rule Check Precision" in content
    assert "BM-01-CLEAN" in content
    assert "BM-09-NAME-VARIATION" in content
    assert "BM-14-OMITTED-CHECK" in content
    assert "MEASURED RESULT" in content
    assert "REFERENCE STANDARD" in content
