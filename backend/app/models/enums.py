"""
PRAMAAN-AI Status Taxonomy and Enums
Enforces strict separation between document verification status, individual finding status,
extraction quality, and application workflow status.
"""
from enum import Enum

class FindingStatus(str, Enum):
    COMPLIANT = "COMPLIANT"
    DEFICIENCY = "DEFICIENCY"
    ANOMALY_SIGNAL = "ANOMALY_SIGNAL"
    INCONCLUSIVE = "INCONCLUSIVE"
    NOT_APPLICABLE = "NOT_APPLICABLE"

class DocumentVerificationStatus(str, Enum):
    """
    Exact six document-verification labels required by the problem statement.
    """
    VERIFIED = "verified"
    MISMATCH_DETECTED = "mismatch detected"
    EXPIRED = "expired"
    VERIFICATION_PENDING = "verification pending"
    SOURCE_UNAVAILABLE = "source unavailable"
    MANUAL_REVIEW_REQUIRED = "manual review required"

class ExtractionQuality(str, Enum):
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW_CONFIDENCE = "LOW_CONFIDENCE"
    UNREADABLE = "UNREADABLE"

class ApplicationWorkflowStatus(str, Enum):
    DRAFT = "DRAFT"
    PREFLIGHT_DEFICIENT = "PREFLIGHT_DEFICIENT"
    SUBMITTED = "SUBMITTED"
    UNDER_SCRUTINY = "UNDER_SCRUTINY"
    CLARIFICATION_REQUESTED = "CLARIFICATION_REQUESTED"
    SCRUTINY_COMPLETED = "SCRUTINY_COMPLETED"

class RuleState(str, Enum):
    DRAFT = "DRAFT"
    TESTED = "TESTED"
    ACTIVE = "ACTIVE"
    DEPRECATED = "DEPRECATED"

class Severity(str, Enum):
    DEFICIENCY = "DEFICIENCY"
    ANOMALY_SIGNAL = "ANOMALY_SIGNAL"
    OBSERVATION = "OBSERVATION"

class ApplicationCategory(str, Enum):
    EXTENSION_OF_APPROVAL = "EXTENSION_OF_APPROVAL"
    INCREASE_IN_INTAKE = "INCREASE_IN_INTAKE"
    NEW_COURSE = "NEW_COURSE"
    NEW_INSTITUTION = "NEW_INSTITUTION"
    CLOSURE = "CLOSURE"

class DocumentType(str, Enum):
    AFFIDAVIT_GENERAL = "AFFIDAVIT_GENERAL"
    LAND_USE_CERTIFICATE = "LAND_USE_CERTIFICATE"
    FIRE_SAFETY_NOC = "FIRE_SAFETY_NOC"
    BUILDING_PLAN_ARCHITECT = "BUILDING_PLAN_ARCHITECT"
    GOVERNING_BODY_RESOLUTION = "GOVERNING_BODY_RESOLUTION"
    AICTE_PREVIOUS_EOA = "AICTE_PREVIOUS_EOA"
    LAND_CONVERSION_ORDER = "LAND_CONVERSION_ORDER"

class VerificationMethod(str, Enum):
    DIGITAL_SIGNATURE = "DIGITAL_SIGNATURE"
    QR_CODE = "QR_CODE"
    ISSUER_REGISTRY = "ISSUER_REGISTRY"

