"""
PRAMAAN-AI Benchmark Models & Ground-Truth Specifications
Defines schemas for benchmark fixtures, ground-truth labels,
and evaluation metrics across extraction, rule evaluation,
duplicate detection, verification, and coverage audit.
"""
from typing import List, Dict, Optional, Any, Set
from pydantic import BaseModel, Field
from datetime import datetime, timezone
from enum import Enum

from app.models.enums import (
    FindingStatus,
    DocumentVerificationStatus,
    DocumentType,
    ExtractionQuality,
)
from app.models.domain import ApplicationInput, Document, ExtractedField
from app.services.duplicate_detector import DuplicateMatchType


class ExpectedField(BaseModel):
    field_key: str
    expected_value: str
    expected_quality: Optional[ExtractionQuality] = None
    min_confidence: float = 0.65
    should_exist: bool = True


class ExpectedFinding(BaseModel):
    rule_id: str
    expected_status: FindingStatus
    expected_severity: Optional[str] = None
    expected_phrase_in_reason: Optional[str] = None


class ExpectedVerification(BaseModel):
    document_type: DocumentType
    expected_status: DocumentVerificationStatus
    expected_retry_outcome: Optional[str] = None


class ExpectedDuplicate(BaseModel):
    source_document_id: str
    target_application_id: str
    expected_match_type: DuplicateMatchType
    min_similarity: float = 0.70


class BenchmarkFixture(BaseModel):
    """
    Standardized benchmark unit coupling a synthetic application bundle with
    its ground-truth expectations.
    """
    bundle_id: str
    name: str
    category: str
    description: str
    application: ApplicationInput
    ground_truth_fields: Dict[str, List[ExpectedField]] = Field(
        default_factory=dict,
        description="doc_id -> List of ExpectedField"
    )
    ground_truth_rules: Dict[str, ExpectedFinding] = Field(
        default_factory=dict,
        description="rule_id -> ExpectedFinding"
    )
    ground_truth_verifications: Dict[str, ExpectedVerification] = Field(
        default_factory=dict,
        description="doc_id -> ExpectedVerification"
    )
    ground_truth_duplicates: List[ExpectedDuplicate] = Field(
        default_factory=list,
        description="Expected duplicate match records"
    )
    expected_coverage_complete: bool = True
    expected_overall_status: str = "COMPLETE_COMPLIANT"
    is_false_positive_trap: bool = False
    trap_explanation: Optional[str] = None
    injection_flags: Dict[str, Any] = Field(
        default_factory=dict,
        description="Injected testing flags like force_omit_check_id, simulated_timeout, etc."
    )


# ---------------------------------------------------------------------------
# Metric Schemas
# ---------------------------------------------------------------------------

class ExtractionMetrics(BaseModel):
    total_fields_evaluated: int = 0
    true_positives: int = 0
    false_positives: int = 0
    false_negatives: int = 0
    precision: float = 0.0
    recall: float = 0.0
    f1_score: float = 0.0
    value_exact_accuracy: float = 0.0
    is_measured: bool = True


class RuleEvaluationMetrics(BaseModel):
    total_rule_evaluations: int = 0
    compliant_count: int = 0
    deficiency_count: int = 0
    anomaly_count: int = 0
    not_applicable_count: int = 0
    inconclusive_count: int = 0
    true_positives: int = 0   # Correctly flagged deficiencies/anomalies
    true_negatives: int = 0   # Correctly passed compliant checks
    false_positives: int = 0  # Compliant erroneously flagged as deficient/anomaly
    false_negatives: int = 0  # Real deficiencies/anomalies missed
    precision: float = 0.0
    recall: float = 0.0
    f1_score: float = 0.0
    specificity: float = 0.0
    false_positive_rate: float = 0.0
    is_measured: bool = True


class DuplicateMetrics(BaseModel):
    exact_match_total_evaluations: int = 0
    exact_match_true_positives: int = 0
    exact_match_false_positives: int = 0
    exact_match_false_negatives: int = 0
    exact_match_precision: float = 0.0
    exact_match_recall: float = 0.0
    exact_match_f1: float = 0.0

    approx_match_total_evaluations: int = 0
    approx_match_true_positives: int = 0
    approx_match_false_positives: int = 0
    approx_match_false_negatives: int = 0
    approx_match_precision: float = 0.0
    approx_match_recall: float = 0.0
    approx_match_f1: float = 0.0
    is_measured: bool = True


class CoverageMetrics(BaseModel):
    total_planned_checks: int = 0
    total_accounted_checks: int = 0
    total_missing_checks: int = 0
    overall_coverage_percentage: float = 0.0
    bundles_audited: int = 0
    complete_bundles: int = 0
    incomplete_bundles: int = 0
    is_measured: bool = True


class NonEvaluableMetrics(BaseModel):
    uncertain_ocr_abstentions: int = 0
    source_unavailable_events: int = 0
    not_applicable_rules: int = 0
    manual_review_routed_tasks: int = 0
    is_measured: bool = True


class PerformanceMetrics(BaseModel):
    total_duration_ms: float = 0.0
    average_latency_ms_per_bundle: float = 0.0
    throughput_bundles_per_second: float = 0.0
    baseline_manual_minutes_per_dossier: float = 45.0  # Industry baseline reference standard
    automated_seconds_per_dossier: float = 0.0
    estimated_time_reduction_percentage: float = 0.0
    is_measured: bool = True
    baseline_is_reference: bool = True


class BundleSpotCheckResult(BaseModel):
    bundle_id: str
    bundle_name: str
    is_clean_case: bool = False
    is_false_positive_trap: bool = False
    planned_checks_count: int = 0
    coverage_verdict: str
    ground_truth_status: str
    actual_status: str
    deficiencies_found: int = 0
    anomalies_found: int = 0
    false_positives_detected: int = 0
    spot_check_passed: bool = True
    notes: str = ""


class BenchmarkEvaluationResult(BaseModel):
    benchmark_version: str = "1.0.0"
    random_seed: int = 42
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    total_bundles: int = 0
    bundles_passed: int = 0
    bundles_failed: int = 0

    extraction_metrics: ExtractionMetrics
    rule_metrics: RuleEvaluationMetrics
    duplicate_metrics: DuplicateMetrics
    coverage_metrics: CoverageMetrics
    non_evaluable_metrics: NonEvaluableMetrics
    performance_metrics: PerformanceMetrics
    spot_checks: List[BundleSpotCheckResult] = Field(default_factory=list)
