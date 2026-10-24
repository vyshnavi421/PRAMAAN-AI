"""
PRAMAAN-AI Domain Models & Extraction Schemas
Defines structured input representations, documents, extracted fields, provenance,
and institutional reference records.
"""
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field
from datetime import datetime, date
import uuid

from app.models.enums import (
    DocumentType,
    DocumentVerificationStatus,
    ExtractionQuality,
    ApplicationCategory,
)

class FieldProvenance(BaseModel):
    """
    Every extracted claim retains page number, bounding box, snippet, and quality.
    """
    page_number: int = Field(..., ge=1, description="1-indexed document page number")
    bounding_box: Optional[List[float]] = Field(
        None,
        description="Normalized coordinates [x1, y1, x2, y2] where 0,0 is top-left"
    )
    surrounding_snippet: Optional[str] = Field(None, description="Nearby context text")
    quality_label: ExtractionQuality = Field(
        ExtractionQuality.HIGH,
        description="Confidence category"
    )

class ExtractedField(BaseModel):
    """
    Factual claim extracted from a document with traceable provenance.
    """
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    field_key: str = Field(..., description="Unique attribute key, e.g., 'noc_expiry_date'")
    field_value: str = Field(..., description="Normalized string value")
    raw_value: str = Field(..., description="Verbatim text from source")
    data_type: str = Field("STRING", description="STRING, INTEGER, NUMERIC, DATE, BOOLEAN")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Extraction confidence score")
    extraction_method: str = Field(
        "PDF_TEXT_STREAM",
        description="PDF_TEXT_STREAM, TESSERACT_OCR, LAYOUT_PARSER, MANUAL_ENTRY"
    )
    provenance: FieldProvenance

class Document(BaseModel):
    """
    Uploaded binary document entity with verification state and extracted fields.
    """
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    application_id: str
    document_type: DocumentType
    original_filename: str
    storage_key: str
    file_size_bytes: int = 0
    mime_type: str = "application/pdf"
    sha256_hash: str
    page_count: int = 1
    verification_status: DocumentVerificationStatus = DocumentVerificationStatus.VERIFICATION_PENDING
    extracted_fields: List[ExtractedField] = Field(default_factory=list)

    def get_field(self, key: str) -> Optional[ExtractedField]:
        for field in self.extracted_fields:
            if field.field_key == key:
                return field
        return None

class InstitutionalReferenceRecord(BaseModel):
    """
    Authorised baseline institutional records from AICTE master store or synthetic baseline.
    """
    institution_id: str
    aicte_permanent_id: str
    legal_name: str
    academic_year: str
    approved_intake: int
    approved_programmes: List[str] = Field(default_factory=list)
    approved_builtup_area_sqm: float
    is_synthetic: bool = True

class ApplicationInput(BaseModel):
    """
    Complete application dossier snapshot submitted to the rule validation engine.
    """
    application_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    institution_id: str
    application_number: str
    academic_year: str = "2026-2027"
    submission_date: date
    submission_cutoff_date: date
    category: ApplicationCategory = ApplicationCategory.EXTENSION_OF_APPROVAL
    declared_data: Dict[str, Any] = Field(default_factory=dict)
    documents: List[Document] = Field(default_factory=list)
    reference_record: Optional[InstitutionalReferenceRecord] = None

    def get_document_by_type(self, doc_type: DocumentType) -> Optional[Document]:
        for doc in self.documents:
            if doc.document_type == doc_type:
                return doc
        return None

    def get_documents_by_type(self, doc_type: DocumentType) -> List[Document]:
        return [doc for doc in self.documents if doc.document_type == doc_type]
