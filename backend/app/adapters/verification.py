"""
PRAMAAN-AI Verification Adapters Implementation
Provides deterministic simulated adapters for:
1. Simulated Issuer Registry Adapter (Statutory state registry & portal lookups)
2. Simulated Digital Signature Adapter (X.509 PKI certificate chain & PKCS#7 signature validation)
3. Simulated QR Code Adapter (2D barcode encrypted payload decryption & HMAC validation)

All adapters are strictly DEMO / SIMULATED prototypes for SIH26261.
They return exactly the 6 statutory statuses:
- verified
- mismatch detected
- expired
- verification pending
- source unavailable
- manual review required
"""
from typing import Dict, Any, Optional, List
from datetime import datetime, timezone
import json

from app.models.enums import DocumentVerificationStatus, DocumentType, VerificationMethod
from app.adapters.base import BaseVerificationAdapter, VerificationAttemptRecord


# Documented fixtures for reproducible demonstration & testing
FIXTURE_DEFINITIONS = {
    "FIX-VERIFIED": {
        "status": DocumentVerificationStatus.VERIFIED,
        "description": "Valid active authority record matching document claims exactly.",
        "payload": {
            "status_code": 200,
            "registry_record_found": True,
            "status": "ACTIVE_VALID",
            "issuer": "State Statutory Authority Registry (DEMO)",
            "validation_timestamp": "2026-04-10T10:00:00Z",
            "claims_match": True,
            "demo_notice": "DEMO / SIMULATED: Deterministic statutory registry query result."
        }
    },
    "FIX-MISMATCH": {
        "status": DocumentVerificationStatus.MISMATCH_DETECTED,
        "description": "Authority record found but registered values differ from document claims.",
        "payload": {
            "status_code": 200,
            "registry_record_found": True,
            "status": "ACTIVE_VALID",
            "issuer": "State Revenue & Land Administration (DEMO)",
            "validation_timestamp": "2026-04-10T10:00:00Z",
            "claims_match": False,
            "discrepancies": [
                {
                    "attribute": "builtup_area_sqm",
                    "registered_value": "9500.0",
                    "document_claim": "12500.0",
                    "discrepancy_delta_pct": -24.0
                }
            ],
            "demo_notice": "DEMO / SIMULATED: Discrepancy detected between applicant submission and issuer record."
        }
    },
    "FIX-EXPIRED": {
        "status": DocumentVerificationStatus.EXPIRED,
        "description": "Authority record confirms clearance was valid previously but has lapsed.",
        "payload": {
            "status_code": 200,
            "registry_record_found": True,
            "status": "EXPIRED",
            "issuer": "State Fire & Emergency Services (DEMO)",
            "valid_until": "2024-01-14",
            "renewal_registered": False,
            "days_elapsed_since_expiry": 817,
            "demo_notice": "DEMO / SIMULATED: Validity period lapsed according to issuer registry."
        }
    },
    "FIX-PENDING": {
        "status": DocumentVerificationStatus.VERIFICATION_PENDING,
        "description": "Clearance application in progress at authority portal, final certificate pending issue.",
        "payload": {
            "status_code": 202,
            "registry_record_found": True,
            "status": "PROCESSING",
            "issuer": "Pollution Control Board Registry (DEMO)",
            "application_stage": "FIELD_INSPECTION_COMPLETED",
            "expected_completion_date": "2026-05-15",
            "demo_notice": "DEMO / SIMULATED: Authority verification currently in progress."
        }
    },
    "FIX-SOURCE-UNAVAIL": {
        "status": DocumentVerificationStatus.SOURCE_UNAVAILABLE,
        "description": "External authority API endpoint unreachable or timed out.",
        "payload": {
            "status_code": 504,
            "error": "GATEWAY_TIMEOUT",
            "issuer": "Municipal Town Planning Clearance Portal (DEMO)",
            "timeout_ms": 5000,
            "retry_eligible": True,
            "demo_notice": "DEMO / SIMULATED: Simulated external timeout; applicant must not be penalized."
        }
    },
    "FIX-MANUAL-REVIEW": {
        "status": DocumentVerificationStatus.MANUAL_REVIEW_REQUIRED,
        "description": "Registry record ambiguous, manual physical inspection of seals/records required.",
        "payload": {
            "status_code": 200,
            "registry_record_found": True,
            "status": "AMBIGUOUS_RECORDS",
            "issuer": "District Revenue Registry (DEMO)",
            "reason": "Multiple parcel survey numbers recorded with conflicting boundary demarcation",
            "demo_notice": "DEMO / SIMULATED: Honest uncertainty requires human scrutiny."
        }
    },
    "ERR-TIMEOUT": {
        "status": DocumentVerificationStatus.SOURCE_UNAVAILABLE,
        "description": "Simulated network timeout trigger for transient retry testing.",
        "payload": {
            "status_code": 504,
            "error": "CONNECTION_TIMED_OUT",
            "issuer": "State e-Governance Gateway (DEMO)",
            "transient": True,
            "demo_notice": "DEMO / SIMULATED: Transient outage test fixture."
        }
    },
    "ERR-MALFORMED": {
        "status": DocumentVerificationStatus.MANUAL_REVIEW_REQUIRED,
        "description": "Simulated malformed or corrupted payload from external portal.",
        "payload": {
            "status_code": 200,
            "error": "CORRUPT_PAYLOAD_STRUCTURE",
            "raw_text": "<!DOCTYPE html><html><body>Error 500 Internal Error</body></html>",
            "demo_notice": "DEMO / SIMULATED: Unparseable external response routed to manual review."
        }
    }
}


class SimulatedIssuerRegistryAdapter(BaseVerificationAdapter):
    """
    Simulated external issuing authority registry adapter for statutory documents
    (Fire NOC, Land Use Certificate, AICTE prior approvals, University affiliation, etc.).
    """
    def __init__(self, is_enabled: bool = True):
        self._is_enabled = is_enabled

    @property
    def adapter_id(self) -> str:
        return "SIMULATED_ISSUER_REGISTRY_ADAPTER"

    @property
    def adapter_name(self) -> str:
        return "Simulated Government & Statutory Issuer Registry"

    @property
    def supported_methods(self) -> List[VerificationMethod]:
        return [VerificationMethod.ISSUER_REGISTRY]

    @property
    def supported_document_types(self) -> List[DocumentType]:
        return list(DocumentType)

    @property
    def is_enabled(self) -> bool:
        return self._is_enabled

    def set_enabled(self, enabled: bool) -> None:
        self._is_enabled = enabled

    def verify(
        self,
        document_id: str,
        document_type: DocumentType,
        reference_id: str,
        method: VerificationMethod = VerificationMethod.ISSUER_REGISTRY,
        context: Optional[Dict[str, Any]] = None
    ) -> VerificationAttemptRecord:
        if not self.is_enabled:
            record = VerificationAttemptRecord(
                document_id=document_id,
                document_type=document_type,
                verification_method=method,
                adapter_id=self.adapter_id,
                adapter_name=self.adapter_name,
                request_reference=reference_id,
                status=DocumentVerificationStatus.SOURCE_UNAVAILABLE,
                response_payload={
                    "status_code": 503,
                    "error": "ADAPTER_DISABLED",
                    "message": "Simulated Issuer Registry Adapter is currently administratively disabled.",
                    "demo_notice": "DEMO / SIMULATED"
                },
                mechanism_performed="External authority registry query (Adapter Disabled)",
                scope_limitations=(
                    "Registry lookup queries the recorded state in the issuing authority's database. "
                    "It does NOT verify whether physical site modifications have occurred without authority knowledge."
                ),
                error_message="Adapter is disabled."
            )
            record.compute_response_hash()
            return record

        ref_upper = reference_id.strip().upper()
        sim_mode = ""
        if context and isinstance(context, dict):
            sim_mode = str(context.get("simulated_mode", "")).strip().lower()

        if sim_mode == "source_unavailable":
            fixture = FIXTURE_DEFINITIONS["FIX-SOURCE-UNAVAIL"]
        elif sim_mode == "expired":
            fixture = FIXTURE_DEFINITIONS["FIX-EXPIRED"]
        elif sim_mode == "mismatch":
            fixture = FIXTURE_DEFINITIONS["FIX-MISMATCH"]
        elif sim_mode == "pending":
            fixture = FIXTURE_DEFINITIONS["FIX-PENDING"]
        elif sim_mode == "manual_review":
            fixture = FIXTURE_DEFINITIONS["FIX-MANUAL-REVIEW"]
        else:
            fixture = FIXTURE_DEFINITIONS.get(ref_upper)

        # Context-based overrides or document-based heuristics

        # Context-based overrides or document-based heuristics
        if not fixture:
            # Check if reference contains known keywords
            if "EXPIRE" in ref_upper or "NOC-FS-2023" in ref_upper:
                fixture = FIXTURE_DEFINITIONS["FIX-EXPIRED"]
            elif "MISMATCH" in ref_upper or "SURV-MISMATCH" in ref_upper:
                fixture = FIXTURE_DEFINITIONS["FIX-MISMATCH"]
            elif "TIMEOUT" in ref_upper or "GATEWAY" in ref_upper or "504" in ref_upper:
                fixture = FIXTURE_DEFINITIONS["FIX-SOURCE-UNAVAIL"]
            elif "PENDING" in ref_upper:
                fixture = FIXTURE_DEFINITIONS["FIX-PENDING"]
            elif "MANUAL" in ref_upper or "AMBIGUOUS" in ref_upper:
                fixture = FIXTURE_DEFINITIONS["FIX-MANUAL-REVIEW"]
            elif "MALFORMED" in ref_upper or "CORRUPT" in ref_upper:
                fixture = FIXTURE_DEFINITIONS["ERR-MALFORMED"]
            else:
                # Default clean match for standard synthetic references
                fixture = FIXTURE_DEFINITIONS["FIX-VERIFIED"]

        status = fixture["status"]
        payload = dict(fixture["payload"])
        payload["query_reference_id"] = reference_id
        payload["document_id"] = document_id
        payload["document_type"] = document_type.value

        record = VerificationAttemptRecord(
            document_id=document_id,
            document_type=document_type,
            verification_method=method,
            adapter_id=self.adapter_id,
            adapter_name=self.adapter_name,
            request_reference=reference_id,
            status=status,
            response_payload=payload,
            mechanism_performed=(
                "REST API query against issuing authority portal (Simulated sandbox endpoint) "
                "with SHA-256 payload integrity check."
            ),
            scope_limitations=(
                "Registry lookup validates the recorded clearance status in the authority's database "
                "at query time. It does NOT establish that unrecorded physical site conditions or structural "
                "alterations comply with AICTE regulations."
            )
        )
        record.compute_response_hash()
        return record


class SimulatedDigitalSignatureAdapter(BaseVerificationAdapter):
    """
    Simulated PKCS#7 / X.509 Digital Signature Validator.
    Cryptographically verifies PDF signing certificates, revocation status (OCSP/CRL),
    and binary digest integrity.
    """
    def __init__(self, is_enabled: bool = True):
        self._is_enabled = is_enabled

    @property
    def adapter_id(self) -> str:
        return "SIMULATED_PKI_SIGNATURE_ADAPTER"

    @property
    def adapter_name(self) -> str:
        return "Simulated PKCS#7 / X.509 Digital Signature Validator"

    @property
    def supported_methods(self) -> List[VerificationMethod]:
        return [VerificationMethod.DIGITAL_SIGNATURE]

    @property
    def supported_document_types(self) -> List[DocumentType]:
        return list(DocumentType)

    @property
    def is_enabled(self) -> bool:
        return self._is_enabled

    def set_enabled(self, enabled: bool) -> None:
        self._is_enabled = enabled

    def verify(
        self,
        document_id: str,
        document_type: DocumentType,
        reference_id: str,
        method: VerificationMethod = VerificationMethod.DIGITAL_SIGNATURE,
        context: Optional[Dict[str, Any]] = None
    ) -> VerificationAttemptRecord:
        if not self.is_enabled:
            record = VerificationAttemptRecord(
                document_id=document_id,
                document_type=document_type,
                verification_method=method,
                adapter_id=self.adapter_id,
                adapter_name=self.adapter_name,
                request_reference=reference_id,
                status=DocumentVerificationStatus.SOURCE_UNAVAILABLE,
                response_payload={
                    "status_code": 503,
                    "error": "ADAPTER_DISABLED",
                    "demo_notice": "DEMO / SIMULATED"
                },
                mechanism_performed="X.509 Certificate Chain & PKCS#7 Signature Verification (Disabled)",
                scope_limitations="Adapter disabled.",
                error_message="Adapter is disabled."
            )
            record.compute_response_hash()
            return record

        ref_upper = reference_id.strip().upper()

        if "TAMPER" in ref_upper or "MISMATCH" in ref_upper or "SIG-MISMATCH" in ref_upper:
            status = DocumentVerificationStatus.MISMATCH_DETECTED
            payload = {
                "signature_valid": False,
                "digest_match": False,
                "error": "DOCUMENT_DIGEST_MISMATCH",
                "signer_common_name": "Er. K. S. Sharma (Structural Engineer)",
                "reason": "Byte-range hash does not match signature dictionary; document content modified post-signing.",
                "demo_notice": "DEMO / SIMULATED: Post-signing tampering detected."
            }
        elif "EXPIRED" in ref_upper or "SIG-EXPIRED" in ref_upper:
            status = DocumentVerificationStatus.EXPIRED
            payload = {
                "signature_valid": False,
                "certificate_status": "CERTIFICATE_EXPIRED",
                "valid_until": "2024-03-31",
                "signer_common_name": "Registrar, Visvesvaraya Technical University",
                "reason": "Signing certificate expired prior to document signing timestamp.",
                "demo_notice": "DEMO / SIMULATED: Expired signing certificate."
            }
        elif "TIMEOUT" in ref_upper or "SIG-TIMEOUT" in ref_upper or "OCSP-FAIL" in ref_upper:
            status = DocumentVerificationStatus.SOURCE_UNAVAILABLE
            payload = {
                "status_code": 504,
                "error": "OCSP_RESPONDER_TIMEOUT",
                "reason": "National Certifying Authority OCSP revocation endpoint did not respond within 5000ms.",
                "retry_eligible": True,
                "demo_notice": "DEMO / SIMULATED: OCSP responder timeout. Applicant not penalised."
            }
        elif "UNTRUSTED" in ref_upper or "SELF-SIGNED" in ref_upper or "SIG-MANUAL" in ref_upper:
            status = DocumentVerificationStatus.MANUAL_REVIEW_REQUIRED
            payload = {
                "signature_valid": False,
                "certificate_status": "UNTRUSTED_ROOT_CA",
                "signer_common_name": "Self-Signed Certificate Authority",
                "reason": "Certificate chain roots to an unrecognised or private trust anchor. Manual inspection required.",
                "demo_notice": "DEMO / SIMULATED: Untrusted PKI root CA."
            }
        elif "MALFORMED" in ref_upper or "CORRUPT" in ref_upper:
            status = DocumentVerificationStatus.MANUAL_REVIEW_REQUIRED
            payload = {
                "signature_valid": False,
                "error": "ASN1_DECODE_ERROR",
                "reason": "Malformed PKCS#7 signature container block.",
                "demo_notice": "DEMO / SIMULATED: Corrupt signature container."
            }
        elif "PENDING" in ref_upper:
            status = DocumentVerificationStatus.VERIFICATION_PENDING
            payload = {
                "status": "TIME_STAMP_AUTHORITY_SYNC_PENDING",
                "reason": "RFC 3161 cryptographic timestamp token awaiting CA notary receipt synchronization.",
                "demo_notice": "DEMO / SIMULATED: Signature timestamp pending confirmation."
            }
        else:
            status = DocumentVerificationStatus.VERIFIED
            payload = {
                "signature_valid": True,
                "digest_match": True,
                "certificate_status": "VALID",
                "signer_common_name": "Authorized Signatory / Licensed Architect",
                "issuer_ca": "e-Mudhra Sub-CA for Class 3 Digital Signatures (DEMO)",
                "signed_timestamp": "2026-03-25T14:22:10Z",
                "ocsp_revocation_checked": True,
                "demo_notice": "DEMO / SIMULATED: Valid cryptographic signature."
            }

        record = VerificationAttemptRecord(
            document_id=document_id,
            document_type=document_type,
            verification_method=method,
            adapter_id=self.adapter_id,
            adapter_name=self.adapter_name,
            request_reference=reference_id,
            status=status,
            response_payload=payload,
            mechanism_performed=(
                "X.509 PKI certificate chain validation, OCSP revocation check, "
                "and SHA-256 byte-range digest verification."
            ),
            scope_limitations=(
                "A valid digital signature cryptographically establishes document binary integrity "
                "(no bytes modified post-signing) and signer identity at the time of signing. "
                "It does NOT establish that every factual claim made inside the document is true, complete, "
                "or compliant with AICTE regulations."
            )
        )
        record.compute_response_hash()
        return record


class SimulatedQRCodeAdapter(BaseVerificationAdapter):
    """
    Simulated 2D Barcode & Encrypted QR Payload Decrypter.
    Extracts high-density QR symbols, decodes signed payloads, and cross-checks HMAC tokens.
    """
    def __init__(self, is_enabled: bool = True):
        self._is_enabled = is_enabled

    @property
    def adapter_id(self) -> str:
        return "SIMULATED_2D_QR_ADAPTER"

    @property
    def adapter_name(self) -> str:
        return "Simulated 2D Barcode & Encrypted QR Payload Decrypter"

    @property
    def supported_methods(self) -> List[VerificationMethod]:
        return [VerificationMethod.QR_CODE]

    @property
    def supported_document_types(self) -> List[DocumentType]:
        return list(DocumentType)

    @property
    def is_enabled(self) -> bool:
        return self._is_enabled

    def set_enabled(self, enabled: bool) -> None:
        self._is_enabled = enabled

    def verify(
        self,
        document_id: str,
        document_type: DocumentType,
        reference_id: str,
        method: VerificationMethod = VerificationMethod.QR_CODE,
        context: Optional[Dict[str, Any]] = None
    ) -> VerificationAttemptRecord:
        if not self.is_enabled:
            record = VerificationAttemptRecord(
                document_id=document_id,
                document_type=document_type,
                verification_method=method,
                adapter_id=self.adapter_id,
                adapter_name=self.adapter_name,
                request_reference=reference_id,
                status=DocumentVerificationStatus.SOURCE_UNAVAILABLE,
                response_payload={
                    "status_code": 503,
                    "error": "ADAPTER_DISABLED",
                    "demo_notice": "DEMO / SIMULATED"
                },
                mechanism_performed="2D QR Payload Extraction & Cryptographic Token Verification (Disabled)",
                scope_limitations="Adapter disabled.",
                error_message="Adapter is disabled."
            )
            record.compute_response_hash()
            return record

        ref_upper = reference_id.strip().upper()

        if "TAMPER" in ref_upper or "MISMATCH" in ref_upper or "QR-MISMATCH" in ref_upper:
            status = DocumentVerificationStatus.MISMATCH_DETECTED
            payload = {
                "qr_decoded": True,
                "hmac_valid": True,
                "embedded_data": {
                    "registered_intake": "120",
                    "document_claimed_intake": "180"
                },
                "discrepancy": "Embedded encrypted QR claims intake of 120, differing from printed value 180.",
                "demo_notice": "DEMO / SIMULATED: QR payload mismatch detected."
            }
        elif "EXPIRED" in ref_upper or "QR-EXPIRED" in ref_upper:
            status = DocumentVerificationStatus.EXPIRED
            payload = {
                "qr_decoded": True,
                "validity_period_end": "2024-01-31",
                "is_expired": True,
                "demo_notice": "DEMO / SIMULATED: QR metadata indicates certificate has expired."
            }
        elif "TIMEOUT" in ref_upper or "QR-TIMEOUT" in ref_upper:
            status = DocumentVerificationStatus.SOURCE_UNAVAILABLE
            payload = {
                "status_code": 504,
                "error": "KEY_STORE_TIMEOUT",
                "reason": "Decryption public key service timed out while fetching issuer token key.",
                "retry_eligible": True,
                "demo_notice": "DEMO / SIMULATED: Key store timeout."
            }
        elif "UNREADABLE" in ref_upper or "QR-MANUAL" in ref_upper or "DAMAGE" in ref_upper:
            status = DocumentVerificationStatus.MANUAL_REVIEW_REQUIRED
            payload = {
                "qr_decoded": False,
                "error": "REED_SOLOMON_ECC_FAILURE",
                "reason": "Barcode matrix corrupted or obscured beyond error-correction capability.",
                "demo_notice": "DEMO / SIMULATED: Damaged QR matrix requires manual inspection."
            }
        elif "PENDING" in ref_upper:
            status = DocumentVerificationStatus.VERIFICATION_PENDING
            payload = {
                "qr_decoded": True,
                "status": "REGISTRATION_IN_FLIGHT",
                "reason": "QR registration token issued within last 24h, awaiting central portal index publication.",
                "demo_notice": "DEMO / SIMULATED: QR indexing pending."
            }
        elif "MALFORMED" in ref_upper or "CORRUPT" in ref_upper:
            status = DocumentVerificationStatus.MANUAL_REVIEW_REQUIRED
            payload = {
                "qr_decoded": False,
                "error": "BASE64_CORRUPT_PAYLOAD",
                "reason": "Non-Base64 bytes in QR payload block.",
                "demo_notice": "DEMO / SIMULATED: Corrupted QR content."
            }
        else:
            status = DocumentVerificationStatus.VERIFIED
            payload = {
                "qr_decoded": True,
                "hmac_valid": True,
                "issuer": "National Board of Accreditation / AICTE Portal (DEMO)",
                "payload_digest": "7f83b1657ff1fc53b92dc18148a1d65dfc2d4b1fa3d677284addd200126d9069",
                "claims_match": True,
                "demo_notice": "DEMO / SIMULATED: 2D QR token verified successfully."
            }

        record = VerificationAttemptRecord(
            document_id=document_id,
            document_type=document_type,
            verification_method=method,
            adapter_id=self.adapter_id,
            adapter_name=self.adapter_name,
            request_reference=reference_id,
            status=status,
            response_payload=payload,
            mechanism_performed=(
                "2D QR symbol parsing, Base64 decoding, HMAC-SHA256 signature verification, "
                "and claim alignment."
            ),
            scope_limitations=(
                "Decoded QR data demonstrates that an encoded matrix was present on the document and decodable. "
                "It does NOT prove institutional authenticity unless backed by a cryptographically signed payload "
                "or real-time verification against the issuing authority's registry."
            )
        )
        record.compute_response_hash()
        return record


class VerificationAdapterRegistry:
    """
    Catalog of all registered external and cryptographic verification adapters.
    """
    def __init__(self):
        self._adapters: Dict[str, BaseVerificationAdapter] = {}
        self.register(SimulatedIssuerRegistryAdapter())
        self.register(SimulatedDigitalSignatureAdapter())
        self.register(SimulatedQRCodeAdapter())

    def register(self, adapter: BaseVerificationAdapter) -> None:
        self._adapters[adapter.adapter_id] = adapter

    def get(self, adapter_id: str) -> Optional[BaseVerificationAdapter]:
        return self._adapters.get(adapter_id)

    def list_adapters(self) -> List[Dict[str, Any]]:
        return [
            {
                "adapter_id": a.adapter_id,
                "adapter_name": a.adapter_name,
                "supported_methods": [m.value for m in a.supported_methods],
                "supported_document_types": [d.value for d in a.supported_document_types],
                "is_enabled": a.is_enabled,
                "is_simulated": True,
                "demo_notice": "DEMO / SIMULATED: Synthetic adapter for SIH26261 prototype."
            }
            for a in self._adapters.values()
        ]

    def find_adapter(
        self,
        method: Optional[VerificationMethod] = None,
        document_type: Optional[DocumentType] = None
    ) -> Optional[BaseVerificationAdapter]:
        for adapter in self._adapters.values():
            if method and method not in adapter.supported_methods:
                continue
            if document_type and document_type not in adapter.supported_document_types:
                continue
            return adapter
        return None

    def reset(self) -> None:
        self._adapters.clear()
        self.register(SimulatedIssuerRegistryAdapter())
        self.register(SimulatedDigitalSignatureAdapter())
        self.register(SimulatedQRCodeAdapter())


# Global registry singleton
adapter_registry = VerificationAdapterRegistry()


def get_adapter_for_document_type(document_type: DocumentType) -> Optional[BaseVerificationAdapter]:
    """
    Returns the primary verification adapter for the specified document type.
    """
    return adapter_registry.find_adapter(
        method=VerificationMethod.ISSUER_REGISTRY,
        document_type=document_type
    )
