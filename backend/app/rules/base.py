"""
PRAMAAN-AI Base Rule Definition
Defines the abstract interface and data contract for all versioned regulatory rules.
"""
from abc import ABC, abstractmethod
from typing import List, Optional, Set
from datetime import date
from pydantic import BaseModel, Field

from app.models.enums import (
    FindingStatus,
    Severity,
    RuleState,
    ApplicationCategory,
    DocumentType,
)
from app.models.domain import ApplicationInput
from app.models.validation import Finding

class RuleMetadata(BaseModel):
    """
    Metadata specification for every versioned rule.
    """
    rule_id: str = Field(..., description="Stable unique ID, e.g., 'RULE-APH-DOC-001'")
    rule_version: str = Field(..., description="Semantic version, e.g., '1.0.0'")
    name: str = Field(..., description="Human-readable rule name")
    explanation: str = Field(..., description="Human-readable rationale and policy description")
    applicable_categories: List[ApplicationCategory] = Field(
        ...,
        description="Application categories to which this rule applies"
    )
    effective_from: Optional[date] = None
    effective_to: Optional[date] = None
    required_document_types: List[DocumentType] = Field(default_factory=list)
    required_field_keys: List[str] = Field(default_factory=list)
    severity: Severity = Severity.DEFICIENCY
    severity_rationale: str = Field(..., description="Justification for chosen severity level")
    evidence_requirements: List[str] = Field(
        default_factory=list,
        description="Types of evidence needed to evaluate"
    )
    reviewer_next_action: str = Field(..., description="Actionable next step for scrutiny officer")
    source_citation: str = Field(
        ...,
        description="Official handbook URL/title/clause/page or explicit DEMO_RULE label"
    )
    is_demo: bool = Field(
        False,
        description="True if rule is synthetic demonstration; False if established from official APH"
    )
    state: RuleState = RuleState.ACTIVE

class BaseRule(ABC):
    """
    Abstract Base Class for all deterministic validation rules.
    """
    def __init__(self, metadata: RuleMetadata):
        self.meta = metadata

    @property
    def rule_id(self) -> str:
        return self.meta.rule_id

    @property
    def rule_version(self) -> str:
        return self.meta.rule_version

    def is_applicable(self, application: ApplicationInput) -> bool:
        """
        Verifies if the application's category falls within the rule's applicability.
        """
        return application.category in self.meta.applicable_categories

    def is_effective(self, target_date: date) -> bool:
        """
        Checks if rule is effective on the target date.
        """
        if self.meta.effective_from and target_date < self.meta.effective_from:
            return False
        if self.meta.effective_to and target_date > self.meta.effective_to:
            return False
        return True

    def evaluate(self, application: ApplicationInput) -> Finding:
        """
        Template method enforcing category applicability and effective date checks
        before executing specific evaluation logic.
        """
        # 1. Category Applicability Check
        if not self.is_applicable(application):
            return Finding(
                rule_id=self.meta.rule_id,
                rule_version=self.meta.rule_version,
                rule_name=self.meta.name,
                clause_citation=self.meta.source_citation,
                is_demo=self.meta.is_demo,
                status=FindingStatus.NOT_APPLICABLE,
                severity=Severity.OBSERVATION,
                reason=(
                    f"Rule {self.meta.rule_id} is not applicable to application category "
                    f"'{application.category.value}'. Applicable categories: "
                    f"{[c.value for c in self.meta.applicable_categories]}."
                ),
                recommended_action="No action required; rule skipped for this category.",
                evidence=[]
            )

        # 2. Effective Date Check
        if not self.is_effective(application.submission_date):
            return Finding(
                rule_id=self.meta.rule_id,
                rule_version=self.meta.rule_version,
                rule_name=self.meta.name,
                clause_citation=self.meta.source_citation,
                is_demo=self.meta.is_demo,
                status=FindingStatus.NOT_APPLICABLE,
                severity=Severity.OBSERVATION,
                reason=(
                    f"Rule {self.meta.rule_id} (version {self.meta.rule_version}) was not in effect "
                    f"on submission date {application.submission_date}."
                ),
                recommended_action="Verify applicable handbook edition for this submission date.",
                evidence=[]
            )

        # 3. Deterministic Evaluation
        return self._evaluate_logic(application)

    @abstractmethod
    def _evaluate_logic(self, application: ApplicationInput) -> Finding:
        """
        Subclasses implement deterministic evaluation.
        Must never call LLMs or external networks.
        """
        pass
