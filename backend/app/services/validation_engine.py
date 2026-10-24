"""
PRAMAAN-AI Deterministic Validation Engine Service
Coordinates versioned rule execution, input snapshotting, cryptographic hashing,
run immutability, and finding aggregation.
"""
from typing import List, Dict, Optional, Any
import hashlib
import json
from datetime import datetime, timezone
import uuid

from app.models.enums import FindingStatus
from app.models.domain import ApplicationInput
from app.models.validation import ValidationRun, Finding
from app.rules.base import BaseRule
from app.rules.catalog import get_default_rules

class ValidationRunRepository:
    """
    In-memory and persistent storage interface for validation runs.
    Ensures old runs are never overwritten; every execution is an immutable new record.
    """
    def __init__(self):
        # Maps application_id -> List of ValidationRun in chronological order
        self._runs_by_app: Dict[str, List[ValidationRun]] = {}
        # Maps run_id -> ValidationRun
        self._runs_by_id: Dict[str, ValidationRun] = {}

    def save(self, run: ValidationRun) -> ValidationRun:
        if run.application_id not in self._runs_by_app:
            self._runs_by_app[run.application_id] = []
        self._runs_by_app[run.application_id].append(run)
        self._runs_by_id[run.id] = run
        return run

    def get_by_id(self, run_id: str) -> Optional[ValidationRun]:
        return self._runs_by_id.get(run_id)

    def get_by_application_id(self, application_id: str) -> List[ValidationRun]:
        return self._runs_by_app.get(application_id, [])

# Global singleton repository instance for the service layer
validation_repository = ValidationRunRepository()

class ValidationEngine:
    """
    Executes deterministic rules against an ApplicationInput snapshot.
    Produces reproducible, evidence-linked findings without non-deterministic LLMs.
    """
    def __init__(self, repository: Optional[ValidationRunRepository] = None):
        self.repository = repository or validation_repository

    @staticmethod
    def compute_input_snapshot_hash(application: ApplicationInput) -> str:
        """
        Computes a deterministic SHA-256 fingerprint of the canonical JSON-serialized input.
        Ensures replay verification can prove whether identical inputs were provided.
        """
        payload = application.model_dump(mode="json")
        serialized = json.dumps(payload, sort_keys=True, default=str)
        return hashlib.sha256(serialized.encode("utf-8")).hexdigest()

    def run_validation(
        self,
        application: ApplicationInput,
        rule_pack_id: str = "rp-aicte-aph-2024-eoa",
        rule_pack_version: str = "1.0.0",
        custom_rules: Optional[List[BaseRule]] = None
    ) -> ValidationRun:
        """
        Executes all active rules in the specified rule pack.
        Persists and returns an immutable ValidationRun record.
        """
        input_hash = self.compute_input_snapshot_hash(application)
        rules = custom_rules if custom_rules is not None else get_default_rules(pack_version=rule_pack_version)

        findings: List[Finding] = []
        errors: List[str] = []

        for rule in rules:
            try:
                finding = rule.evaluate(application)
                findings.append(finding)
            except Exception as exc:
                error_msg = f"Error evaluating rule {rule.rule_id} v{rule.rule_version}: {str(exc)}"
                errors.append(error_msg)
                # Fail gracefully by recording INCONCLUSIVE finding rather than crashing
                findings.append(
                    Finding(
                        rule_id=rule.rule_id,
                        rule_version=rule.rule_version,
                        rule_name=rule.meta.name,
                        clause_citation=rule.meta.source_citation,
                        is_demo=rule.meta.is_demo,
                        status=FindingStatus.INCONCLUSIVE,
                        severity=rule.meta.severity,
                        reason=f"Evaluation aborted due to unexpected internal processing error: {str(exc)}",
                        recommended_action="System engineer review required.",
                        evidence=[]
                    )
                )

        # Aggregate findings summary
        summary: Dict[str, int] = {
            "compliant": sum(1 for f in findings if f.status == FindingStatus.COMPLIANT),
            "deficiency": sum(1 for f in findings if f.status == FindingStatus.DEFICIENCY),
            "anomaly_signal": sum(1 for f in findings if f.status == FindingStatus.ANOMALY_SIGNAL),
            "inconclusive": sum(1 for f in findings if f.status == FindingStatus.INCONCLUSIVE),
            "not_applicable": sum(1 for f in findings if f.status == FindingStatus.NOT_APPLICABLE),
        }

        # Overall result categorization (decision-support advisory summary only; never approves/rejects institution)
        if summary["deficiency"] > 0:
            overall_result = "DEFICIENCIES_DETECTED"
        elif summary["anomaly_signal"] > 0:
            overall_result = "ANOMALIES_REQUIRING_REVIEW"
        elif summary["inconclusive"] > 0:
            overall_result = "INCONCLUSIVE_REVIEWS_PENDING"
        else:
            overall_result = "ALL_RULES_COMPLIANT"

        validation_run = ValidationRun(
            id=str(uuid.uuid4()),
            application_id=application.application_id,
            rule_pack_id=rule_pack_id,
            rule_pack_version=rule_pack_version,
            executed_at=datetime.now(timezone.utc),
            input_snapshot_hash=input_hash,
            overall_result=overall_result,
            findings_summary=summary,
            findings=findings,
            processing_errors=errors
        )

        # Persist to repository (preserves old runs)
        self.repository.save(validation_run)
        return validation_run
