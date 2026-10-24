"""
PRAMAAN-AI Validation Finding & Run Schemas
Represents findings, evidence references, and immutable validation execution runs.
"""
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field
from datetime import datetime, timezone
import uuid

from app.models.enums import FindingStatus, Severity

class FindingEvidence(BaseModel):
    """
    Every finding connects directly to its supporting extracted field, document, and comparison reference.
    """
    document_id: Optional[str] = None
    document_type: Optional[str] = None
    field_key: Optional[str] = None
    extracted_value: Optional[str] = None
    page_number: Optional[int] = None
    bounding_box: Optional[List[float]] = None
    comparison_value: Optional[str] = None
    comparison_source: Optional[str] = None

class Finding(BaseModel):
    """
    Discrete finding produced by a single versioned rule evaluation.
    """
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    rule_id: str
    rule_version: str
    rule_name: str
    clause_citation: str
    is_demo: bool = False
    status: FindingStatus
    severity: Severity
    reason: str
    recommended_action: str
    evidence: List[FindingEvidence] = Field(default_factory=list)

class ValidationRun(BaseModel):
    """
    Immutable record of a validation execution.
    """
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    application_id: str
    rule_pack_id: str
    rule_pack_version: str
    executed_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    input_snapshot_hash: str
    overall_result: str
    findings_summary: Dict[str, int] = Field(default_factory=dict)
    findings: List[Finding] = Field(default_factory=list)
    processing_errors: List[str] = Field(default_factory=list)
