"""
PRAMAAN-AI Verification Adapter Base Interface & Attempt Schemas
Defines the standard contract for digital signature, QR code, and issuer registry verification.
Strictly returns the exact 6 statutory document-verification statuses:
- verified
- mismatch detected
- expired
- verification pending
- source unavailable
- manual review required
"""
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, List
from datetime import datetime, timezone
from pydantic import BaseModel, Field
import hashlib
import json
import uuid

from app.models.enums import DocumentVerificationStatus, DocumentType, VerificationMethod


class VerificationAttemptRecord(BaseModel):
    """
    Timestamped record of an external or cryptographic verification attempt.
    """
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    document_id: str
    document_type: DocumentType
    verification_method: VerificationMethod
    adapter_id: str
    adapter_name: str
    is_simulated: bool = True
    request_reference: str
    status: DocumentVerificationStatus
    response_payload: Dict[str, Any] = Field(default_factory=dict)
    response_hash: Optional[str] = None
    mechanism_performed: str = Field(
        ...,
        description="Exact verification mechanism executed, e.g. PKCS#7 signature check or e-Gov portal lookup."
    )
    scope_limitations: str = Field(
        ...,
        description="Plain-language explanation of what this mechanism establishes and what it does NOT establish."
    )
    attempted_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    retry_count: int = 0
    retry_outcome: Optional[str] = None
    manual_review_task: Optional[str] = None
    error_message: Optional[str] = None

    def compute_response_hash(self) -> str:
        safe_data = json.dumps(self.response_payload, sort_keys=True)
        h = hashlib.sha256(safe_data.encode("utf-8")).hexdigest()
        self.response_hash = h
        return h


class BaseVerificationAdapter(ABC):
    """
    Provider-agnostic interface for authority and cryptographic document verification.
    """
    @property
    @abstractmethod
    def adapter_id(self) -> str:
        """Unique machine identifier, e.g. 'SIMULATED_STATE_FIRE_SERVICE_ADAPTER'."""
        pass

    @property
    @abstractmethod
    def adapter_name(self) -> str:
        """Human-readable display name."""
        pass

    @property
    @abstractmethod
    def supported_methods(self) -> List[VerificationMethod]:
        """Verification mechanisms supported by this adapter."""
        pass

    @property
    @abstractmethod
    def supported_document_types(self) -> List[DocumentType]:
        """Document categories this adapter can scrutinize."""
        pass

    @property
    def is_enabled(self) -> bool:
        """Whether this adapter is currently operational."""
        return True

    @abstractmethod
    def verify(
        self,
        document_id: str,
        document_type: DocumentType,
        reference_id: str,
        method: VerificationMethod = VerificationMethod.ISSUER_REGISTRY,
        context: Optional[Dict[str, Any]] = None
    ) -> VerificationAttemptRecord:
        """
        Executes a verification attempt returning exactly one of the 6 official statuses.
        """
        pass
