"""
PRAMAAN-AI Verification Subsystem Orchestration Service
Coordinates execution of external issuing authority and cryptographic verification adapters.
Strictly adheres to:
1. Exact 6 statutory document-verification labels:
   - verified
   - mismatch detected
   - expired
   - verification pending
   - source unavailable
   - manual review required
2. Honest uncertainty: An unreachable source, network error, or timeout produces 'source unavailable'
   with bounded retries and an automatic manual-review task. Zero applicant penalty or false fraud claims.
3. Separation of verification status from rule findings and overall application workflow status.
4. Response hashing for tamper resistance and audit trail persistence.
"""
from typing import List, Optional, Dict, Any
from datetime import datetime, timezone
import uuid

from app.models.enums import DocumentVerificationStatus, DocumentType, VerificationMethod
from app.adapters.base import VerificationAttemptRecord, BaseVerificationAdapter
from app.adapters.verification import (
    adapter_registry,
    FIXTURE_DEFINITIONS,
    SimulatedIssuerRegistryAdapter,
    SimulatedDigitalSignatureAdapter,
    SimulatedQRCodeAdapter,
)
from app.services.application_service import global_application_service
from app.services.audit_service import global_audit_service as audit_service


class VerificationService:
    MAX_PERMITTED_RETRIES = 3

    def __init__(self):
        # document_id -> List[VerificationAttemptRecord]
        self._attempts_by_document: Dict[str, List[VerificationAttemptRecord]] = {}
        # attempt_id -> VerificationAttemptRecord
        self._attempts_by_id: Dict[str, VerificationAttemptRecord] = {}

    def get_fixtures(self) -> Dict[str, Any]:
        """
        Returns documented verification fixtures and their expected statutory outcomes.
        """
        return {
            fixture_id: {
                "expected_status": fix["status"].value,
                "description": fix["description"],
                "sample_payload": fix["payload"],
                "is_synthetic": True,
                "demo_notice": "DEMO / SIMULATED: Deterministic statutory verification fixture."
            }
            for fixture_id, fix in FIXTURE_DEFINITIONS.items()
        }

    def verify_document(
        self,
        document_id: str,
        adapter_id: Optional[str] = None,
        method: Optional[VerificationMethod] = None,
        reference_id: Optional[str] = None,
        max_retries: int = 3,
        simulate_retry: bool = False,
        context: Optional[Dict[str, Any]] = None,
        actor_id: str = "usr-officer-01"
    ) -> VerificationAttemptRecord:
        """
        Executes a verification attempt against the appropriate adapter.
        Enforces bounded retries, records attempt with SHA-256 hash,
        creates manual review tasks when necessary, and dispatches an audit event.
        """
        # 1. Resolve document & category
        found = global_application_service.find_document(document_id)
        if found:
            app, doc = found
            document_type = doc.document_type
            application_id = app.application_id
            effective_reference = reference_id or doc.original_filename
        else:
            # Fallback document representation if standalone verification
            application_id = None
            document_type = DocumentType.FIRE_SAFETY_NOC
            effective_reference = reference_id or f"REF-{document_id}"

        # 2. Resolve Adapter
        adapter: Optional[BaseVerificationAdapter] = None
        if adapter_id:
            adapter = adapter_registry.get(adapter_id)
        elif method:
            adapter = adapter_registry.find_adapter(method=method, document_type=document_type)
        else:
            # Default to issuer registry adapter
            adapter = adapter_registry.find_adapter(
                method=VerificationMethod.ISSUER_REGISTRY,
                document_type=document_type
            )

        # 3. Handle Adapter Missing or Administratively Disabled
        if not adapter or not adapter.is_enabled:
            record = VerificationAttemptRecord(
                document_id=document_id,
                document_type=document_type,
                verification_method=method or VerificationMethod.ISSUER_REGISTRY,
                adapter_id=adapter_id or "UNKNOWN_ADAPTER",
                adapter_name=adapter.adapter_name if adapter else "Unregistered Verification Adapter",
                request_reference=effective_reference,
                status=DocumentVerificationStatus.SOURCE_UNAVAILABLE,
                response_payload={
                    "status_code": 503,
                    "error": "ADAPTER_UNAVAILABLE",
                    "reason": "Requested verification adapter is not registered or is administratively disabled.",
                    "demo_notice": "DEMO / SIMULATED"
                },
                mechanism_performed="Adapter Dispatch (Unavailable)",
                scope_limitations="Source lookup could not be completed because the adapter is unavailable.",
                retry_count=0,
                retry_outcome="ADAPTER_UNAVAILABLE",
                manual_review_task=f"TASK-REV-ADAPTER-UNAVAILABLE: Verification adapter unavailable for document '{document_id}'. Manual authority verification required.",
                error_message="Verification adapter unavailable."
            )
            record.compute_response_hash()
            self._record_attempt(record, application_id, actor_id)
            return record

        # 4. Execute Verification with Bounded Retries for Transient Errors
        bounded_max_retries = min(max(1, max_retries), self.MAX_PERMITTED_RETRIES)
        retry_count = 0
        record: Optional[VerificationAttemptRecord] = None

        while retry_count < bounded_max_retries:
            try:
                record = adapter.verify(
                    document_id=document_id,
                    document_type=document_type,
                    reference_id=effective_reference,
                    method=method or (adapter.supported_methods[0] if adapter.supported_methods else VerificationMethod.ISSUER_REGISTRY),
                    context=context
                )
            except TimeoutError as te:
                record = VerificationAttemptRecord(
                    document_id=document_id,
                    document_type=document_type,
                    verification_method=method or VerificationMethod.ISSUER_REGISTRY,
                    adapter_id=adapter.adapter_id,
                    adapter_name=adapter.adapter_name,
                    request_reference=effective_reference,
                    status=DocumentVerificationStatus.SOURCE_UNAVAILABLE,
                    response_payload={"status_code": 504, "error": "TIMEOUT", "detail": str(te)},
                    mechanism_performed=f"Timeout during execution of {adapter.adapter_name}",
                    scope_limitations="Timeout encountered. Applicant must not be penalised.",
                    error_message=str(te)
                )
            except Exception as exc:
                record = VerificationAttemptRecord(
                    document_id=document_id,
                    document_type=document_type,
                    verification_method=method or VerificationMethod.ISSUER_REGISTRY,
                    adapter_id=adapter.adapter_id,
                    adapter_name=adapter.adapter_name,
                    request_reference=effective_reference,
                    status=DocumentVerificationStatus.MANUAL_REVIEW_REQUIRED,
                    response_payload={"status_code": 500, "error": "ADAPTER_EXCEPTION", "detail": str(exc)},
                    mechanism_performed=f"Exception caught in {adapter.adapter_name}",
                    scope_limitations="Adapter raised unhandled exception. Escalated to manual review.",
                    error_message=str(exc)
                )

            # Check if this outcome is transient and eligible for retry
            is_transient = (
                record.status == DocumentVerificationStatus.SOURCE_UNAVAILABLE
                and record.response_payload.get("retry_eligible", False)
            ) or (simulate_retry and record.status == DocumentVerificationStatus.SOURCE_UNAVAILABLE)

            if is_transient and retry_count < bounded_max_retries - 1:
                retry_count += 1
                # If simulate_retry was requested, simulate next attempt
                continue
            else:
                break

        # Record retry metadata
        record.retry_count = retry_count
        if retry_count > 0:
            if record.status == DocumentVerificationStatus.SOURCE_UNAVAILABLE:
                record.retry_outcome = "RETRY_CAP_REACHED"
            else:
                record.retry_outcome = "SUCCEEDED_AFTER_RETRY"
        else:
            record.retry_outcome = "FIRST_ATTEMPT" if record.status == DocumentVerificationStatus.VERIFIED else "NON_TRANSIENT"

        # 5. Attach Honest Statutory Manual Review Task if not verified
        if record.status == DocumentVerificationStatus.SOURCE_UNAVAILABLE:
            record.manual_review_task = (
                f"TASK-REV-SRC-UNAVAIL: External issuing authority portal for '{document_type.value}' "
                f"did not respond ({record.retry_outcome}). "
                f"Verify via offline liaison or departmental register. ZERO penalty levied against applicant."
            )
        elif record.status == DocumentVerificationStatus.MISMATCH_DETECTED:
            record.manual_review_task = (
                f"TASK-REV-MISMATCH: Mismatch detected between document claims and authority registry for '{document_type.value}'. "
                f"Issue statutory clarification notice to institution."
            )
        elif record.status == DocumentVerificationStatus.EXPIRED:
            record.manual_review_task = (
                f"TASK-REV-EXPIRED: Clearance certificate '{document_type.value}' has lapsed according to issuing records. "
                f"Verify if renewal application was submitted before cutoff date."
            )
        elif record.status == DocumentVerificationStatus.MANUAL_REVIEW_REQUIRED:
            record.manual_review_task = (
                f"TASK-REV-MANUAL: Ambiguous or unparseable verification response for '{document_type.value}'. "
                f"Scrutiny officer must review original document seals and physical stamps."
            )
        elif record.status == DocumentVerificationStatus.VERIFICATION_PENDING:
            record.manual_review_task = (
                f"TASK-REV-PENDING: Registration is currently in flight at authority portal for '{document_type.value}'. "
                f"Re-query adapter before final Standing Scrutiny Committee hearing."
            )
        else:
            record.manual_review_task = None

        # 6. Compute safe cryptographic hash of response
        record.compute_response_hash()

        # 7. Record attempt & update document state
        self._record_attempt(record, application_id, actor_id)
        return record

    def _record_attempt(
        self,
        record: VerificationAttemptRecord,
        application_id: Optional[str],
        actor_id: str
    ) -> None:
        """
        Stores verification attempt, updates document verification status,
        and records an immutable cryptographic audit ledger event.
        """
        if record.document_id not in self._attempts_by_document:
            self._attempts_by_document[record.document_id] = []
        self._attempts_by_document[record.document_id].append(record)
        self._attempts_by_id[record.id] = record

        # Update document entity status in application service
        global_application_service.update_document_status(record.document_id, record.status)

        # Audit event recording
        audit_service.record_event(
            actor_id=actor_id,
            event_type="DOCUMENT_VERIFICATION_ATTEMPTED",
            details={
                "attempt_id": record.id,
                "document_id": record.document_id,
                "document_type": record.document_type.value,
                "adapter_id": record.adapter_id,
                "verification_method": record.verification_method.value,
                "statutory_status": record.status.value,
                "retry_count": record.retry_count,
                "retry_outcome": record.retry_outcome,
                "response_hash": record.response_hash,
                "manual_review_task": record.manual_review_task,
                "is_simulated": True
            },
            application_id=application_id
        )

    def get_attempts_for_document(self, document_id: str) -> List[VerificationAttemptRecord]:
        return self._attempts_by_document.get(document_id, [])

    def get_attempt(self, attempt_id: str) -> Optional[VerificationAttemptRecord]:
        return self._attempts_by_id.get(attempt_id)

    def list_all_attempts(self) -> List[VerificationAttemptRecord]:
        return list(self._attempts_by_id.values())


# Global verification service instance
global_verification_service = VerificationService()
