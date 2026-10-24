"""
PRAMAAN-AI Cryptographic Hash-Chained Audit Ledger Service
Implements an append-only ledger where each event is chained via SHA-256.
H_i = SHA256(H_{i-1} || timestamp || actor || event_type || details)
"""
from typing import List, Optional, Dict, Any
from datetime import datetime, timezone
import hashlib
import json
import os
import uuid
from pydantic import BaseModel, Field

from app.core.config import settings
from app.core.persistence import ensure_dir, append_jsonl, read_jsonl


class AuditEvent(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    sequence: int
    timestamp: str
    actor_id: str
    event_type: str
    details: Dict[str, Any]
    application_id: Optional[str] = None
    finding_id: Optional[str] = None
    previous_hash: str
    event_hash: str


class AuditChainVerificationResult(BaseModel):
    is_valid: bool
    events_evaluated: int
    genesis_hash: str
    latest_hash: str
    corrupted_event_id: Optional[str] = None
    corrupted_sequence: Optional[int] = None
    detail: str


class AuditService:
    GENESIS_HASH = "0000000000000000000000000000000000000000000000000000000000000000"

    def __init__(self, data_dir: Optional[str] = None):
        self._events: List[AuditEvent] = []
        self._tamper_backup: Dict[int, Dict[str, Any]] = {}
        self._ledger_path: Optional[str] = None
        data_dir = ensure_dir(data_dir)
        if data_dir:
            self._ledger_path = os.path.join(data_dir, "audit_ledger.jsonl")
            self._events = [AuditEvent(**rec) for rec in read_jsonl(self._ledger_path)]
        if not self._events:
            self._seed_initial_events()

    def _compute_hash(self, prev_hash: str, timestamp: str, actor: str, event_type: str, details: Dict[str, Any]) -> str:
        payload = f"{prev_hash}|{timestamp}|{actor}|{event_type}|{json.dumps(details, sort_keys=True)}"
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()

    def _seed_initial_events(self):
        """
        Seeds initial audit events demonstrating immutable ledger functionality.
        """
        self.record_event(
            actor_id="system",
            event_type="SYSTEM_INITIALIZED",
            details={"service": "PRAMAAN-AI", "version": "1.0.0", "mode": "DEMO / SIMULATED"},
            application_id=None
        )
        self.record_event(
            actor_id="system",
            event_type="RULE_PACK_LOADED",
            details={"rule_pack_id": "rp-aicte-aph-2024-eoa", "version": "1.0.0", "status": "ACTIVE"},
            application_id=None
        )

    def record_event(
        self,
        actor_id: str,
        event_type: str,
        details: Dict[str, Any],
        application_id: Optional[str] = None,
        finding_id: Optional[str] = None
    ) -> AuditEvent:
        prev_hash = self._events[-1].event_hash if self._events else self.GENESIS_HASH
        seq = len(self._events) + 1
        ts = datetime.now(timezone.utc).isoformat()
        evt_hash = self._compute_hash(prev_hash, ts, actor_id, event_type, details)

        event = AuditEvent(
            sequence=seq,
            timestamp=ts,
            actor_id=actor_id,
            event_type=event_type,
            details=details,
            application_id=application_id,
            finding_id=finding_id,
            previous_hash=prev_hash,
            event_hash=evt_hash
        )
        self._events.append(event)
        if self._ledger_path:
            append_jsonl(self._ledger_path, event.model_dump(mode="json"))
        return event

    def get_events(self, application_id: Optional[str] = None) -> List[AuditEvent]:
        if application_id:
            return [e for e in self._events if e.application_id == application_id or e.application_id is None]
        return list(self._events)

    def verify_chain(self) -> AuditChainVerificationResult:
        if not self._events:
            return AuditChainVerificationResult(
                is_valid=True,
                events_evaluated=0,
                genesis_hash=self.GENESIS_HASH,
                latest_hash=self.GENESIS_HASH,
                detail="Ledger is empty; genesis valid."
            )

        expected_prev = self.GENESIS_HASH
        for event in self._events:
            # Check previous hash pointer
            if event.previous_hash != expected_prev:
                return AuditChainVerificationResult(
                    is_valid=False,
                    events_evaluated=len(self._events),
                    genesis_hash=self.GENESIS_HASH,
                    latest_hash=self._events[-1].event_hash,
                    corrupted_event_id=event.id,
                    corrupted_sequence=event.sequence,
                    detail=f"Previous hash link mismatch at sequence #{event.sequence}."
                )

            # Recompute content hash
            computed = self._compute_hash(
                event.previous_hash,
                event.timestamp,
                event.actor_id,
                event.event_type,
                event.details
            )
            if computed != event.event_hash:
                return AuditChainVerificationResult(
                    is_valid=False,
                    events_evaluated=len(self._events),
                    genesis_hash=self.GENESIS_HASH,
                    latest_hash=self._events[-1].event_hash,
                    corrupted_event_id=event.id,
                    corrupted_sequence=event.sequence,
                    detail=f"Hash mismatch at sequence #{event.sequence}. Content modified."
                )

            expected_prev = event.event_hash

        return AuditChainVerificationResult(
            is_valid=True,
            events_evaluated=len(self._events),
            genesis_hash=self.GENESIS_HASH,
            latest_hash=self._events[-1].event_hash,
            detail=f"Cryptographic hash chain intact. All {len(self._events)} events verified."
        )

    def simulate_tamper(self, sequence: Optional[int] = None) -> Dict[str, Any]:
        """
        Deliberately alters a disposable audit event to test tamper-detection capabilities.
        Modifies stored event details without recomputing the cryptographic hash.
        """
        if not self._events:
            raise ValueError("Audit ledger is empty; cannot simulate tampering.")

        target_seq = sequence if sequence is not None and 1 <= sequence <= len(self._events) else max(1, len(self._events) // 2)
        event = self._events[target_seq - 1]

        # Backup original details if not already backed up
        if target_seq not in self._tamper_backup:
            self._tamper_backup[target_seq] = dict(event.details)

        # Mutate the event payload illegally
        event.details["UNAUTHORIZED_MUTATION"] = "SQL_INJECTION_OR_DATABASE_ROW_ALTERATION"
        event.details["tampered_at"] = datetime.now(timezone.utc).isoformat()

        return {
            "status": "TAMPER_SIMULATED",
            "tampered_sequence": target_seq,
            "tampered_event_id": event.id,
            "original_hash": event.event_hash,
            "notice": "Event details modified in-memory without hash recalculation. Running verify_chain() will detect this tampering immediately."
        }

    def restore_chain(self) -> Dict[str, Any]:
        """
        Restores original event details from backup to return the chain to a mathematically valid state.
        """
        restored = []
        for seq, original_details in self._tamper_backup.items():
            if 1 <= seq <= len(self._events):
                self._events[seq - 1].details = dict(original_details)
                restored.append(seq)
        self._tamper_backup.clear()
        return {
            "status": "CHAIN_RESTORED",
            "restored_sequences": restored,
            "restored_events_count": len(restored),
            "detail": f"Restored {len(restored)} tampered event(s) to original signed state."
        }

    @staticmethod
    def get_limitation_statement() -> str:
        """
        Plain-language statutory explanation of the mathematical boundaries of hash chaining.
        """
        return (
            "LIMITATION OF HASH CHAINING: Cryptographic hash chaining within the application database reliably "
            "exposes unauthorized modifications, deletions, or localized updates by application users, compromised API accounts, "
            "or SQL injection. However, it does NOT provide absolute immutability against a privileged database superuser who could "
            "maliciously rewrite the entire database table and recompute all hashes sequentially from the corrupted point forward. "
            "For production deployment, periodic checkpoint hashes must be signed with a hardware security module (HSM) and "
            "anchored to a Write-Once-Read-Many (WORM) storage bucket or public timestamping notary."
        )


global_audit_service = AuditService(data_dir=settings.DATA_DIR or None)

