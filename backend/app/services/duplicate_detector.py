"""
PRAMAAN-AI Cross-Application Reuse & Duplicate Detection Engine
Identifies exact binary SHA-256 collisions and approximate text shingle overlap across application dossiers.
Enforces strict statutory guardrails:
- Similarity is treated as a preliminary review signal, NEVER as proof of misconduct.
- Sponsoring societies, shared educational trusts, common accredited architects, and standard statutory
  templates legitimately reuse materials.
"""
from typing import List, Dict, Optional, Tuple, Any, Set
from pydantic import BaseModel, Field
from datetime import datetime, timezone
from enum import Enum
import uuid
import re

from app.models.enums import FindingStatus, Severity
from app.models.domain import ApplicationInput, Document
from app.models.validation import Finding, FindingEvidence


class DuplicateMatchType(str, Enum):
    EXACT_BINARY_MATCH = "EXACT_BINARY_MATCH"
    APPROXIMATE_SIMILARITY = "APPROXIMATE_SIMILARITY"
    GENERIC_TEMPLATE = "GENERIC_TEMPLATE"


class DuplicateMatchMethod(str, Enum):
    SHA256_BYTE_HASH = "SHA256_BYTE_HASH"
    TEXT_SHINGLE_SIMILARITY = "TEXT_SHINGLE_SIMILARITY"
    BOILERPLATE_TEMPLATE_MATCH = "BOILERPLATE_TEMPLATE_MATCH"


class DocumentFingerprint(BaseModel):
    document_id: str
    application_id: str
    institution_id: str
    institution_name: Optional[str] = None
    document_type: str
    original_filename: str
    sha256_hash: str
    text_content: str = ""
    registered_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class DuplicateMatchRecord(BaseModel):
    """
    Timestamped record of a detected exact or approximate document match.
    """
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    match_type: DuplicateMatchType
    method: DuplicateMatchMethod
    similarity_score: float = Field(..., ge=0.0, le=1.0)
    source_doc: DocumentFingerprint
    target_doc: DocumentFingerprint
    detected_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    details: Dict[str, Any] = Field(default_factory=dict)
    legitimacy_assessment: str = Field(
        default=(
            "PRELIMINARY_ANOMALY_SIGNAL_NOT_FRAUD: Common architectural plans, shared sponsoring societies, "
            "or statutory legal boilerplate are frequent legitimate reasons for document reuse."
        )
    )
    reviewer_verdict: Optional[str] = None
    reviewer_notes: Optional[str] = None


def extract_document_text(doc: Document) -> str:
    """
    Combines extracted field values and snippets to construct
    a representative text stream for approximate similarity analysis.
    """
    parts = []
    for f in doc.extracted_fields:
        if f.field_value:
            parts.append(str(f.field_value))
        if f.provenance and f.provenance.surrounding_snippet:
            parts.append(f.provenance.surrounding_snippet)
    if not parts:
        parts = [doc.original_filename, doc.document_type.value]
    return " ".join(parts)


def compute_text_shingles(text: str, k: int = 3) -> Set[str]:
    """
    Computes k-character shingles from normalized text tokens.
    """
    norm = re.sub(r"[^a-zA-Z0-9\s]", " ", text).lower().split()
    joined = " ".join(norm)
    if len(joined) < k:
        return {joined} if joined else set()
    return {joined[i:i+k] for i in range(len(joined) - k + 1)}


def compute_shingle_similarity(text1: str, text2: str, k: int = 3) -> float:
    """
    Calculates Jaccard similarity across k-shingles and normalized word tokens.
    """
    # 1. Character k-shingle Jaccard
    s1 = compute_text_shingles(text1, k)
    s2 = compute_text_shingles(text2, k)
    char_sim = 0.0
    if s1 and s2:
        union_char = len(s1.union(s2))
        char_sim = float(len(s1.intersection(s2)) / union_char) if union_char > 0 else 0.0

    # 2. Word token Jaccard
    t1 = set(re.sub(r"[^a-zA-Z0-9\s]", " ", text1).lower().split())
    t2 = set(re.sub(r"[^a-zA-Z0-9\s]", " ", text2).lower().split())
    token_sim = 0.0
    if t1 and t2:
        union_tok = len(t1.union(t2))
        token_sim = float(len(t1.intersection(t2)) / union_tok) if union_tok > 0 else 0.0

    return max(char_sim, token_sim)


class DuplicateIndex:
    """
    Repository store indexing document binary hashes and text representations across applications.
    """
    def __init__(self):
        # sha256 -> List[DocumentFingerprint]
        self._hash_index: Dict[str, List[DocumentFingerprint]] = {}
        # doc_id -> DocumentFingerprint
        self._doc_fingerprints: Dict[str, DocumentFingerprint] = {}
        # match_id -> DuplicateMatchRecord
        self._match_records: Dict[str, DuplicateMatchRecord] = {}

    def register_document(self, app: ApplicationInput, doc: Document) -> DocumentFingerprint:
        text = extract_document_text(doc)
        inst_name = str(app.declared_data.get("institution_name", app.institution_id))
        fp = DocumentFingerprint(
            document_id=doc.id,
            application_id=app.application_id,
            institution_id=app.institution_id,
            institution_name=inst_name,
            document_type=doc.document_type.value,
            original_filename=doc.original_filename,
            sha256_hash=doc.sha256_hash,
            text_content=text,
        )
        self._doc_fingerprints[doc.id] = fp

        if doc.sha256_hash:
            if doc.sha256_hash not in self._hash_index:
                self._hash_index[doc.sha256_hash] = []
            if not any(x.document_id == doc.id for x in self._hash_index[doc.sha256_hash]):
                self._hash_index[doc.sha256_hash].append(fp)
        return fp

    def find_matches(self, doc: Document, current_app_id: str) -> List[DocumentFingerprint]:
        """
        Backward compatible exact SHA-256 match finder.
        """
        if not doc.sha256_hash or doc.sha256_hash not in self._hash_index:
            return []
        return [
            fp for fp in self._hash_index[doc.sha256_hash]
            if fp.application_id != current_app_id
        ]

    def record_match(self, match: DuplicateMatchRecord) -> None:
        self._match_records[match.id] = match

    def get_match(self, match_id: str) -> Optional[DuplicateMatchRecord]:
        return self._match_records.get(match_id)

    def list_matches(self) -> List[DuplicateMatchRecord]:
        return list(self._match_records.values())

    def clear(self) -> None:
        self._hash_index.clear()
        self._doc_fingerprints.clear()
        self._match_records.clear()


global_duplicate_index = DuplicateIndex()


class DuplicateDetector:
    """
    High-level scanner performing exact binary collision checks,
    approximate text shingle comparisons, and generic template detection.
    """
    def __init__(self, index: Optional[DuplicateIndex] = None):
        self.index = index or global_duplicate_index

    def seed_from_application_service(self, apps: List[ApplicationInput]) -> None:
        """
        Populates index with documents from seeded applications.
        """
        for app in apps:
            for doc in app.documents:
                self.index.register_document(app, doc)

    def scan_document(
        self,
        current_app: ApplicationInput,
        doc: Document,
        similarity_threshold: float = 0.80
    ) -> List[DuplicateMatchRecord]:
        """
        Compares a single document against all registered documents in other applications.
        Returns detailed DuplicateMatchRecord objects.
        """
        matches: List[DuplicateMatchRecord] = []
        current_text = extract_document_text(doc)
        source_inst_name = str(current_app.declared_data.get("institution_name", current_app.institution_id))

        source_fp = DocumentFingerprint(
            document_id=doc.id,
            application_id=current_app.application_id,
            institution_id=current_app.institution_id,
            institution_name=source_inst_name,
            document_type=doc.document_type.value,
            original_filename=doc.original_filename,
            sha256_hash=doc.sha256_hash,
            text_content=current_text,
        )

        for target_doc_id, target_fp in self.index._doc_fingerprints.items():
            # Skip documents in the same application
            if target_fp.application_id == current_app.application_id:
                continue

            # 1. Exact Binary Match (SHA-256 collision)
            if doc.sha256_hash and doc.sha256_hash == target_fp.sha256_hash:
                rec = DuplicateMatchRecord(
                    match_type=DuplicateMatchType.EXACT_BINARY_MATCH,
                    method=DuplicateMatchMethod.SHA256_BYTE_HASH,
                    similarity_score=1.0,
                    source_doc=source_fp,
                    target_doc=target_fp,
                    details={
                        "sha256_hash": doc.sha256_hash,
                        "shared_bytes": True,
                        "explanation": f"Identical byte stream found in application {target_fp.application_id} ({target_fp.institution_name})."
                    }
                )
                self.index.record_match(rec)
                matches.append(rec)
                continue

            # 2. Approximate Text Similarity
            sim = compute_shingle_similarity(current_text, target_fp.text_content, k=3)
            if sim >= similarity_threshold:
                # Distinguish generic statutory templates vs altered files
                is_template_type = (
                    doc.document_type.value in ["AFFIDAVIT_GENERAL", "GOVERNING_BODY_RESOLUTION"]
                    and target_fp.document_type in ["AFFIDAVIT_GENERAL", "GOVERNING_BODY_RESOLUTION"]
                )
                if is_template_type and sim < 0.98:
                    match_type = DuplicateMatchType.GENERIC_TEMPLATE
                    method = DuplicateMatchMethod.BOILERPLATE_TEMPLATE_MATCH
                    explanation = "Standard statutory affidavit or resolution format boilerplate shared across institutions."
                else:
                    match_type = DuplicateMatchType.APPROXIMATE_SIMILARITY
                    method = DuplicateMatchMethod.TEXT_SHINGLE_SIMILARITY
                    explanation = f"High text similarity ({round(sim * 100, 1)}%) detected. Possible altered document or shared drafting."

                rec = DuplicateMatchRecord(
                    match_type=match_type,
                    method=method,
                    similarity_score=round(sim, 3),
                    source_doc=source_fp,
                    target_doc=target_fp,
                    details={
                        "jaccard_similarity": round(sim, 3),
                        "explanation": explanation
                    }
                )
                self.index.record_match(rec)
                matches.append(rec)

        # Register document for future scans
        self.index.register_document(current_app, doc)
        return matches

    def check_application_duplicates(self, application: ApplicationInput) -> List[Finding]:
        """
        Backward-compatible method consumed by ReviewOrchestrator for RULE-APH-REUSE-010.
        Scans all documents in application for exact binary file reuse across institutions.
        """
        findings: List[Finding] = []

        for doc in application.documents:
            matches = self.index.find_matches(doc, application.application_id)
            if matches:
                m = matches[0]
                finding = Finding(
                    id=str(uuid.uuid4()),
                    rule_id="RULE-APH-REUSE-010",
                    rule_version="1.0.0",
                    rule_name="Cross-Application Document Reuse Detection",
                    clause_citation="[DEMO_RULE] PRAMAAN-AI Cross-Application Reuse Detection Norms v1.0",
                    is_demo=True,
                    status=FindingStatus.ANOMALY_SIGNAL,
                    severity=Severity.ANOMALY_SIGNAL,
                    reason=(
                        f"Exact file match (SHA-256: {doc.sha256_hash[:16]}...) detected across multiple "
                        f"applications: currently in {application.application_id} and also found in {m.application_id} "
                        f"({m.institution_name or m.institution_id}). Preliminary review indicator; NOT proof of misconduct."
                    ),
                    recommended_action=(
                        "Inspect both applications side-by-side to determine if documents belong to the same "
                        "sponsoring Trust/Society or represent improper reuse."
                    ),
                    evidence=[
                        FindingEvidence(
                            document_id=doc.id,
                            document_type=doc.document_type.value,
                            extracted_value=doc.sha256_hash,
                            comparison_value=m.sha256_hash,
                            comparison_source=f"Prior Application {m.application_id} ({m.original_filename})"
                        )
                    ]
                )
                findings.append(finding)
            else:
                self.index.register_document(application, doc)

        return findings

    def get_side_by_side_comparison(self, match_id: str) -> Optional[Dict[str, Any]]:
        """
        Constructs a detailed side-by-side payload for the reviewer UI.
        """
        match = self.index.get_match(match_id)
        if not match:
            return None

        return {
            "match_id": match.id,
            "match_type": match.match_type.value,
            "method": match.method.value,
            "similarity_score": match.similarity_score,
            "detected_at": match.detected_at.isoformat(),
            "legitimacy_assessment": match.legitimacy_assessment,
            "source_panel": {
                "document_id": match.source_doc.document_id,
                "application_id": match.source_doc.application_id,
                "institution_name": match.source_doc.institution_name,
                "filename": match.source_doc.original_filename,
                "document_type": match.source_doc.document_type,
                "sha256_hash": match.source_doc.sha256_hash,
                "text_preview": match.source_doc.text_content[:300]
            },
            "target_panel": {
                "document_id": match.target_doc.document_id,
                "application_id": match.target_doc.application_id,
                "institution_name": match.target_doc.institution_name,
                "filename": match.target_doc.original_filename,
                "document_type": match.target_doc.document_type,
                "sha256_hash": match.target_doc.sha256_hash,
                "text_preview": match.target_doc.text_content[:300]
            },
            "details": match.details,
            "reviewer_options": [
                "CONFIRM_SHARED_SPONSORING_TRUST",
                "CONFIRM_COMMON_LICENSED_ARCHITECT",
                "ACKNOWLEDGE_GENERIC_STATUTORY_TEMPLATE",
                "ISSUE_CLARIFICATION_NOTICE"
            ]
        }


# Global detector instance
global_duplicate_detector = DuplicateDetector()
