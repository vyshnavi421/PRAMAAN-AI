
"""
PRAMAAN-AI Real Document Extraction & OCR Fallback Service

Parses actual uploaded PDF text streams and bounding boxes using pypdf.
Uses local Tesseract OCR for scanned PDFs when available.
Checks that readable document contents match the selected document type.

If a document is scanned and OCR is unavailable or produces insufficient text,
the service abstains and routes it to MANUAL_REVIEW_REQUIRED.
"""

import io
import os
import re
import uuid
import shutil
import csv
import subprocess

from typing import List, Dict, Optional, Tuple, Any
from datetime import datetime

from pypdf import PdfReader
from pdf2image import convert_from_bytes

from app.models.enums import (
    DocumentType,
    DocumentVerificationStatus,
    ExtractionQuality,
)
from app.models.domain import ExtractedField, FieldProvenance, Document


class DocumentTypeMismatchError(ValueError):
    """Raised when readable document contents do not match the selected type."""


def normalize_date_string(val: str) -> str:
    """Normalize common date formats to ISO YYYY-MM-DD."""
    cleaned = re.sub(r"[^\d/\-\.]", "", val.strip())

    for fmt in (
        "%Y-%m-%d",
        "%d/%m/%Y",
        "%d-%m-%Y",
        "%d.%m.%Y",
        "%m/%d/%Y",
    ):
        try:
            return datetime.strptime(cleaned, fmt).strftime("%Y-%m-%d")
        except ValueError:
            continue

    return val.strip()


class RealDocumentExtractor:
    def __init__(self):
        # Detect whether the Tesseract OCR executable is available.
        self.has_tesseract = bool(shutil.which("tesseract"))

    def validate_document_type(
        self,
        text: str,
        doc_type: DocumentType,
    ) -> bool:
        """
        Perform a basic content-based document-type check.

        Each inner list is a group of related terms. At least one term from
        every group must appear in the extracted text.

        This is a heuristic screening check, not proof that a document is
        genuine or legally valid.
        """
        normalized_text = re.sub(
            r"\s+",
            " ",
            text.lower(),
        ).strip()

        # Require enough readable content for a meaningful type check.
        if len(normalized_text) < 15:
            return False

        required_groups = {
            DocumentType.FIRE_SAFETY_NOC: [
                [
                    "fire safety",
                    "fire prevention",
                    "fire protection",
                ],
                [
                    "no objection certificate",
                    "fire safety certificate",
                    "fire safety noc",
                ],
            ],
            DocumentType.AFFIDAVIT_GENERAL: [
                [
                    "affidavit",
                    "sworn statement",
                    "solemnly affirm",
                    "solemn affirmation",
                ],
            ],
            DocumentType.GOVERNING_BODY_RESOLUTION: [
                [
                    "governing body",
                    "board of directors",
                    "board meeting",
                    "management committee",
                    "resolution of the",
                ],
                [
                    "resolved that",
                    "resolution",
                    "minutes of meeting",
                ],
            ],
            DocumentType.LAND_CONVERSION_ORDER: [
                [
                    "land conversion",
                    "conversion of land",
                    "land conversion order",
                    "conversion order",
                ],
                [
                    "revenue department",
                    "competent authority",
                    "converted for",
                    "conversion is hereby",
                    "conversion permission",
                ],
            ],
            DocumentType.LAND_USE_CERTIFICATE: [
                [
                    "land use certificate",
                    "land-use certificate",
                    "land utilization certificate",
                    "land utilisation certificate",
                ],
            ],
            DocumentType.BUILDING_PLAN_ARCHITECT: [
                [
                    "building plan",
                    "building permission",
                    "architectural plan",
                    "floor plan",
                ],
                [
                    "built-up area",
                    "built up area",
                    "site plan",
                    "building area",
                    "floor area",
                ],
            ],
        }

        groups = required_groups.get(doc_type)

        # Unknown or unsupported types must not pass this check automatically.
        if not groups:
            return False

        for group in groups:
            if not any(term in normalized_text for term in group):
                return False

        return True

    def extract_text_and_spans(
        self,
        content_bytes: bytes,
    ) -> Tuple[List[Dict[str, Any]], int]:
        """
        Parse PDF bytes page by page.

        Each page dictionary contains:
        - page_number (1-indexed)
        - text
        - spans: text and normalized bounding boxes
        - width and height
        """
        pages_data = []

        try:
            reader = PdfReader(io.BytesIO(content_bytes))
            total_pages = len(reader.pages)

            for idx, page in enumerate(reader.pages):
                page_num = idx + 1
                mb = page.mediabox

                page_width = (
                    float(mb.width)
                    if mb and mb.width
                    else 595.0
                )
                page_height = (
                    float(mb.height)
                    if mb and mb.height
                    else 842.0
                )

                spans = []

                def visitor_body(
                    text,
                    cm,
                    tm,
                    font_dict,
                    font_size,
                ):
                    if text and text.strip():
                        # PDF coordinates originate at the bottom-left.
                        tx = float(tm[4]) if len(tm) > 4 else 0.0
                        ty = float(tm[5]) if len(tm) > 5 else 0.0
                        fsize = float(font_size) if font_size else 12.0

                        x1 = max(
                            0.0,
                            min(1.0, tx / page_width),
                        )
                        y1 = max(
                            0.0,
                            min(
                                1.0,
                                (page_height - (ty + fsize))
                                / page_height,
                            ),
                        )

                        approx_width = max(
                            len(text) * fsize * 0.5,
                            10.0,
                        )

                        x2 = max(
                            0.0,
                            min(
                                1.0,
                                (tx + approx_width) / page_width,
                            ),
                        )
                        y2 = max(
                            0.0,
                            min(1.0, (page_height - ty) / page_height),
                        )

                        spans.append({
                            "text": text,
                            "bbox": [
                                round(x1, 3),
                                round(y1, 3),
                                round(x2, 3),
                                round(y2, 3),
                            ],
                        })

                try:
                    full_text = (
                        page.extract_text(visitor_text=visitor_body) or ""
                    )
                except Exception:
                    full_text = page.extract_text() or ""

                pages_data.append({
                    "page_number": page_num,
                    "text": full_text,
                    "spans": spans,
                    "width": page_width,
                    "height": page_height,
                })

            return pages_data, total_pages

        except Exception:
            return [], 0

    def _ocr_pdf_pages(
        self,
        content_bytes: bytes,
    ) -> Tuple[List[Dict[str, Any]], int]:
        """
        Run local Tesseract OCR on PDF pages and retain normalized word boxes.

        If PDF rendering or OCR fails, return no pages so the caller can
        safely route the document for manual review.
        """
        if not self.has_tesseract:
            return [], 0

        pages_data: List[Dict[str, Any]] = []

        try:
            images = convert_from_bytes(content_bytes, dpi=200)

            for page_number, image in enumerate(images, start=1):
                image_buffer = io.BytesIO()
                image.save(image_buffer, format="PNG")

                result = subprocess.run(
                    [
                        "tesseract",
                        "stdin",
                        "stdout",
                        "-l",
                        "eng",
                        "tsv",
                    ],
                    input=image_buffer.getvalue(),
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    check=False,
                    timeout=60,
                )

                if result.returncode != 0:
                    return [], 0

                tsv_text = result.stdout.decode(
                    "utf-8",
                    errors="replace",
                )

                words = []
                spans = []
                width, height = image.size

                for row in csv.DictReader(
                    io.StringIO(tsv_text),
                    delimiter="\t",
                ):
                    if row.get("level") != "5":
                        continue

                    word = (row.get("text") or "").strip()

                    if not word:
                        continue

                    try:
                        x = int(row["left"])
                        y = int(row["top"])
                        w = int(row["width"])
                        h = int(row["height"])
                    except (KeyError, TypeError, ValueError):
                        continue

                    words.append(word)

                    spans.append({
                        "text": word,
                        "bbox": [
                            round(max(0, min(1, x / width)), 3),
                            round(max(0, min(1, y / height)), 3),
                            round(max(0, min(1, (x + w) / width)), 3),
                            round(max(0, min(1, (y + h) / height)), 3),
                        ],
                    })

                pages_data.append({
                    "page_number": page_number,
                    "text": " ".join(words),
                    "spans": spans,
                    "width": width,
                    "height": height,
                })

            return pages_data, len(pages_data)

        except Exception:
            # Includes invalid PDFs, unavailable Poppler, and OCR failures.
            return [], 0

    def extract_document(
        self,
        content_bytes: bytes,
        doc_type: DocumentType,
        original_filename: str,
    ) -> Tuple[
        List[ExtractedField],
        DocumentVerificationStatus,
        str,
    ]:
        """
        Extract structured fields from uploaded PDF bytes.

        Returns:
            (extracted_fields, recommended_status, note)

        Raises:
            DocumentTypeMismatchError:
                When readable text does not match the selected document type.

        If processing is unavailable or uncertain, routes the document
        for manual review.
        """
        pages_data, total_pages = self.extract_text_and_spans(
            content_bytes
        )

        combined_text = " ".join(
            page["text"] for page in pages_data
        ).strip()

        # Scanned PDFs: attempt OCR when required and available.
        used_ocr = False

        if len(combined_text) < 15:
            if not self.has_tesseract:
                return (
                    [],
                    DocumentVerificationStatus.MANUAL_REVIEW_REQUIRED,
                    "No usable PDF text layer and OCR engine unavailable; "
                    "manual review required.",
                )

            pages_data, total_pages = self._ocr_pdf_pages(
                content_bytes
            )

            combined_text = " ".join(
                page["text"] for page in pages_data
            ).strip()

            if len(combined_text) < 15:
                return (
                    [],
                    DocumentVerificationStatus.MANUAL_REVIEW_REQUIRED,
                    "OCR produced insufficient readable text; "
                    "manual review required.",
                )

            used_ocr = True

        # NEW: reject readable documents that do not match the selected type.
        if not self.validate_document_type(combined_text, doc_type):
            raise DocumentTypeMismatchError(
                "The uploaded document does not appear to match the "
                f"selected document type: {doc_type.value}. "
                "Please upload the correct document or select the "
                "matching document type."
            )

        extraction_method = (
            "TESSERACT_OCR"
            if used_ocr
            else "PDF_TEXT_STREAM"
        )

        fields: List[ExtractedField] = []

        # Find the page and bounding box associated with a matched value.
        def find_bbox(
            target_str: str,
        ) -> Tuple[int, Optional[List[float]], str]:
            target_lower = target_str.lower().strip()

            for page in pages_data:
                for span in page["spans"]:
                    span_lower = span["text"].lower()

                    if (
                        target_lower in span_lower
                        or span_lower in target_lower
                    ):
                        return (
                            page["page_number"],
                            span["bbox"],
                            span["text"],
                        )

            # Fallback to a snippet from page 1.
            p1_text = pages_data[0]["text"] if pages_data else ""
            idx = p1_text.lower().find(target_lower)

            snippet = (
                p1_text[
                    max(0, idx - 30):
                    min(len(p1_text), idx + len(target_str) + 30)
                ]
                if idx >= 0
                else target_str
            )

            return 1, None, snippet

        # ---------------------------------------------------------
        # FIRE SAFETY NOC
        # ---------------------------------------------------------
        if doc_type == DocumentType.FIRE_SAFETY_NOC:
            exp_match = re.search(
                r"(?:valid\s*(?:until|up\s*to|to|till)"
                r"|expiry\s*(?:date)?|expires\s*(?:on)?)"
                r"[:\s]+"
                r"(\d{4}-\d{2}-\d{2}"
                r"|\d{1,2}[/-]\d{1,2}[/-]\d{2,4})",
                combined_text,
                re.IGNORECASE,
            )

            if exp_match:
                raw_exp = exp_match.group(1).strip()
                norm_exp = normalize_date_string(raw_exp)
                pg, bbox, snip = find_bbox(raw_exp)

                fields.append(ExtractedField(
                    field_key="noc_expiry_date",
                    field_value=norm_exp,
                    raw_value=raw_exp,
                    data_type="DATE",
                    confidence=0.65 if used_ocr else 0.97,
                    extraction_method=extraction_method,
                    provenance=FieldProvenance(
                        page_number=pg,
                        bounding_box=bbox,
                        surrounding_snippet=(
                            snip or f"Valid until: {raw_exp}"
                        ),
                        quality_label=(
                            ExtractionQuality.MEDIUM
                            if used_ocr
                            else ExtractionQuality.HIGH
                        ),
                    ),
                ))

            issue_match = re.search(
                r"(?:issue[d]?\s*(?:date|on)?|dated)[:\s]+"
                r"(\d{4}-\d{2}-\d{2}"
                r"|\d{1,2}[/-]\d{1,2}[/-]\d{2,4})",
                combined_text,
                re.IGNORECASE,
            )

            if issue_match:
                raw_iss = issue_match.group(1).strip()
                norm_iss = normalize_date_string(raw_iss)
                pg, bbox, snip = find_bbox(raw_iss)

                fields.append(ExtractedField(
                    field_key="noc_issue_date",
                    field_value=norm_iss,
                    raw_value=raw_iss,
                    data_type="DATE",
                    confidence=0.65 if used_ocr else 0.96,
                    extraction_method=extraction_method,
                    provenance=FieldProvenance(
                        page_number=pg,
                        bounding_box=bbox,
                        surrounding_snippet=(
                            snip or f"Issued on: {raw_iss}"
                        ),
                        quality_label=(
                            ExtractionQuality.MEDIUM
                            if used_ocr
                            else ExtractionQuality.HIGH
                        ),
                    ),
                ))

            auth_match = re.search(
                r"(?:issuing\s*authority|department|office\s*of)"
                r"[:\s]+([^,\n\r]+)",
                combined_text,
                re.IGNORECASE,
            )

            if auth_match:
                raw_auth = auth_match.group(1).strip()
                pg, bbox, snip = find_bbox(raw_auth)

                fields.append(ExtractedField(
                    field_key="issuing_authority",
                    field_value=raw_auth,
                    raw_value=raw_auth,
                    data_type="STRING",
                    confidence=0.65 if used_ocr else 0.94,
                    extraction_method=extraction_method,
                    provenance=FieldProvenance(
                        page_number=pg,
                        bounding_box=bbox,
                        surrounding_snippet=snip or raw_auth,
                        quality_label=(
                            ExtractionQuality.MEDIUM
                            if used_ocr
                            else ExtractionQuality.HIGH
                        ),
                    ),
                ))

        # ---------------------------------------------------------
        # AFFIDAVIT / GOVERNING BODY RESOLUTION
        # ---------------------------------------------------------
        elif doc_type in (
            DocumentType.AFFIDAVIT_GENERAL,
            DocumentType.GOVERNING_BODY_RESOLUTION,
        ):
            inst_match = re.search(
                r"(?:institution|college|university|academy|"
                r"institute|affidavit\s*of)[:\s]+([^,\n\r]+)",
                combined_text,
                re.IGNORECASE,
            )

            if inst_match:
                raw_name = inst_match.group(1).strip()
                pg, bbox, snip = find_bbox(raw_name)

                fields.append(ExtractedField(
                    field_key="institution_name",
                    field_value=raw_name,
                    raw_value=raw_name,
                    data_type="STRING",
                    confidence=0.98,
                    extraction_method=extraction_method,
                    provenance=FieldProvenance(
                        page_number=pg,
                        bounding_box=bbox,
                        surrounding_snippet=snip or raw_name,
                        quality_label=(
                            ExtractionQuality.MEDIUM
                            if used_ocr
                            else ExtractionQuality.HIGH
                        ),
                    ),
                ))

            intake_match = re.search(
                r"(?:intake|total\s*intake|seats)[:\s]+(\d+)",
                combined_text,
                re.IGNORECASE,
            )

            if intake_match:
                raw_intake = intake_match.group(1).strip()
                pg, bbox, snip = find_bbox(raw_intake)

                fields.append(ExtractedField(
                    field_key="total_intake",
                    field_value=raw_intake,
                    raw_value=raw_intake,
                    data_type="INTEGER",
                    confidence=0.65 if used_ocr else 0.95,
                    extraction_method=extraction_method,
                    provenance=FieldProvenance(
                        page_number=pg,
                        bounding_box=bbox,
                        surrounding_snippet=(
                            snip or f"Intake: {raw_intake}"
                        ),
                        quality_label=(
                            ExtractionQuality.MEDIUM
                            if used_ocr
                            else ExtractionQuality.HIGH
                        ),
                    ),
                ))

        # ---------------------------------------------------------
        # LAND CONVERSION ORDER / LAND USE CERTIFICATE
        # ---------------------------------------------------------
        elif doc_type in (
            DocumentType.LAND_CONVERSION_ORDER,
            DocumentType.LAND_USE_CERTIFICATE,
        ):
            area_match = re.search(
                r"(?:land\s*area|total\s*area|area)[:\s]+"
                r"([\d\.]+)\s*(?:acres?|hectares?)?",
                combined_text,
                re.IGNORECASE,
            )

            if area_match:
                raw_area = area_match.group(1).strip()
                pg, bbox, snip = find_bbox(raw_area)

                fields.append(ExtractedField(
                    field_key="land_area_acres",
                    field_value=raw_area,
                    raw_value=raw_area,
                    data_type="NUMERIC",
                    confidence=0.65 if used_ocr else 0.95,
                    extraction_method=extraction_method,
                    provenance=FieldProvenance(
                        page_number=pg,
                        bounding_box=bbox,
                        surrounding_snippet=(
                            snip or f"Land Area: {raw_area}"
                        ),
                        quality_label=(
                            ExtractionQuality.MEDIUM
                            if used_ocr
                            else ExtractionQuality.HIGH
                        ),
                    ),
                ))

        # ---------------------------------------------------------
        # BUILDING PLAN / ARCHITECT
        # ---------------------------------------------------------
        elif doc_type == DocumentType.BUILDING_PLAN_ARCHITECT:
            b_match = re.search(
                r"(?:built[\s\-]?up\s*area|total\s*area|area)"
                r"[:\s]+([\d\.,]+)\s*(?:sq\.?\s*m|sqm)?",
                combined_text,
                re.IGNORECASE,
            )

            if b_match:
                raw_original = b_match.group(1).strip()
                raw_b = raw_original.replace(",", "")
                pg, bbox, snip = find_bbox(raw_original)

                fields.append(ExtractedField(
                    field_key="builtup_area_sqm",
                    field_value=raw_b,
                    raw_value=raw_original,
                    data_type="NUMERIC",
                    confidence=0.65 if used_ocr else 0.94,
                    extraction_method=extraction_method,
                    provenance=FieldProvenance(
                        page_number=pg,
                        bounding_box=bbox,
                        surrounding_snippet=(
                            snip or f"Built-up area: {raw_b}"
                        ),
                        quality_label=(
                            ExtractionQuality.MEDIUM
                            if used_ocr
                            else ExtractionQuality.HIGH
                        ),
                    ),
                ))

        # ---------------------------------------------------------
        # FALLBACK: readable matching document with no target fields
        # ---------------------------------------------------------
        if not fields:
            any_date = re.search(
                r"(\d{4}-\d{2}-\d{2}"
                r"|\d{1,2}[/-]\d{1,2}[/-]\d{2,4})",
                combined_text,
            )

            if any_date:
                raw_d = any_date.group(1).strip()
                norm_d = normalize_date_string(raw_d)
                pg, bbox, snip = find_bbox(raw_d)

                fields.append(ExtractedField(
                    field_key="document_date",
                    field_value=norm_d,
                    raw_value=raw_d,
                    data_type="DATE",
                    confidence=0.65 if used_ocr else 0.85,
                    extraction_method=extraction_method,
                    provenance=FieldProvenance(
                        page_number=pg,
                        bounding_box=bbox,
                        surrounding_snippet=snip or raw_d,
                        quality_label=ExtractionQuality.MEDIUM,
                    ),
                ))

            else:
                fields.append(ExtractedField(
                    field_key="document_title",
                    field_value=original_filename,
                    raw_value=original_filename,
                    data_type="STRING",
                    confidence=0.65 if used_ocr else 0.80,
                    extraction_method=extraction_method,
                    provenance=FieldProvenance(
                        page_number=1,
                        bounding_box=None,
                        surrounding_snippet=f"File: {original_filename}",
                        quality_label=ExtractionQuality.MEDIUM,
                    ),
                ))

        if used_ocr:
            return (
                fields,
                DocumentVerificationStatus.MANUAL_REVIEW_REQUIRED,
                f"OCR extracted {len(fields)} field(s); "
                "human verification is required.",
            )

        return (
            fields,
            DocumentVerificationStatus.VERIFICATION_PENDING,
            f"Extracted {len(fields)} fields from PDF text stream.",
        )


global_document_extractor = RealDocumentExtractor()
