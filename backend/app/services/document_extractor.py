"""
PRAMAAN-AI Real Document Extraction & OCR Fallback Service
Parses actual uploaded PDF text streams and bounding boxes using pypdf.
If a document is a scanned raster without an embedded text layer and local OCR is unavailable,
the service honestly abstains, sets extraction quality to UNREADABLE / LOW_CONFIDENCE,
and routes the document to MANUAL_REVIEW_REQUIRED.
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

from app.models.enums import DocumentType, DocumentVerificationStatus, ExtractionQuality
from app.models.domain import ExtractedField, FieldProvenance, Document


def normalize_date_string(val: str) -> str:
    """Normalizes DD/MM/YYYY, DD-MM-YYYY, or YYYY-MM-DD to standard ISO YYYY-MM-DD."""
    cleaned = re.sub(r"[^\d/\-\.]", "", val.strip())
    for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y", "%d.%m.%Y", "%m/%d/%Y"):
        try:
            return datetime.strptime(cleaned, fmt).strftime("%Y-%m-%d")
        except ValueError:
            continue
    return val.strip()


MAX_OCR_PAGES = 10  # bound OCR work per upload


class RealDocumentExtractor:
    def __init__(self):
        # Detect if system tesseract binary is available for OCR fallback
        self.has_tesseract = bool(shutil.which("tesseract"))

    def extract_text_and_spans(self, content_bytes: bytes) -> Tuple[List[Dict[str, Any]], int]:
        """
        Parses PDF bytes page-by-page. Returns a list of page dicts containing:
        - page_number (1-indexed)
        - full_text
        - text_spans: list of (span_text, [x1, y1, x2, y2])
        - page_width, page_height
        """
        pages_data = []
        try:
            reader = PdfReader(io.BytesIO(content_bytes))
            total_pages = len(reader.pages)

            for idx, page in enumerate(reader.pages):
                page_num = idx + 1
                mb = page.mediabox
                page_width = float(mb.width) if mb and mb.width else 595.0
                page_height = float(mb.height) if mb and mb.height else 842.0

                spans = []

                def visitor_body(text, cm, tm, font_dict, font_size):
                    if text and text.strip():
                        # Calculate normalized top-left coordinates: [x1, y1, x2, y2]
                        # In PDF, origin is bottom-left
                        tx = float(tm[4]) if len(tm) > 4 else 0.0
                        ty = float(tm[5]) if len(tm) > 5 else 0.0
                        fsize = float(font_size) if font_size else 12.0
                        
                        x1 = max(0.0, min(1.0, tx / page_width))
                        y1 = max(0.0, min(1.0, (page_height - (ty + fsize)) / page_height))
                        approx_width = max(len(text) * fsize * 0.5, 10.0)
                        x2 = max(0.0, min(1.0, (tx + approx_width) / page_width))
                        y2 = max(0.0, min(1.0, (page_height - ty) / page_height))

                        spans.append({
                            "text": text,
                            "bbox": [round(x1, 3), round(y1, 3), round(x2, 3), round(y2, 3)]
                        })

                try:
                    full_text = page.extract_text(visitor_text=visitor_body) or ""
                except Exception:
                    full_text = page.extract_text() or ""

                pages_data.append({
                    "page_number": page_num,
                    "text": full_text,
                    "spans": spans,
                    "width": page_width,
                    "height": page_height
                })

            return pages_data, total_pages
        except Exception:
            return [], 0

    @staticmethod
    def count_pages(content_bytes: bytes, mime_type: str = "application/pdf") -> int:
        """Return a PDF's page count, or one for raster images/unsupported parse cases."""
        if mime_type != "application/pdf":
            return 1
        try:
            return max(1, len(PdfReader(io.BytesIO(content_bytes)).pages))
        except Exception:
            return 1

    @staticmethod
    def render_page_png(
        content_bytes: bytes,
        mime_type: str,
        page_number: int = 1,
        dpi: int = 110,
    ) -> Optional[bytes]:
        """Render a page from real stored bytes; return None if rendering is unavailable."""
        if page_number < 1:
            return None
        try:
            if mime_type in ("image/png", "image/jpeg"):
                if page_number != 1:
                    return None
                from PIL import Image
                with Image.open(io.BytesIO(content_bytes)) as image:
                    output = io.BytesIO()
                    image.convert("RGB").save(output, format="PNG")
                    return output.getvalue()
            from pdf2image import convert_from_bytes
            images = convert_from_bytes(
                content_bytes, dpi=dpi, first_page=page_number, last_page=page_number
            )
            if not images:
                return None
            output = io.BytesIO()
            images[0].save(output, format="PNG")
            return output.getvalue()
        except Exception:
            return None

    @staticmethod
    def _is_raster_image(content_bytes: bytes) -> bool:
        return (
            content_bytes.startswith(b"\xff\xd8\xff")
            or content_bytes.startswith(b"\x89PNG\r\n\x1a\n")
        )

    def _ocr_pdf_pages(self, content_bytes: bytes) -> Tuple[List[Dict[str, Any]], int]:
        """OCR a raster upload or at most MAX_OCR_PAGES pages of a PDF."""
        if not self.has_tesseract:
            return [], 0

        is_image = self._is_raster_image(content_bytes)
        convert_from_bytes = None
        if not is_image:
            try:
                from pdf2image import convert_from_bytes
            except ImportError:
                return [], 0

        pages_data: List[Dict[str, Any]] = []
        try:
            if is_image:
                from PIL import Image
                with Image.open(io.BytesIO(content_bytes)) as source_image:
                    images = [source_image.convert("RGB")]
            else:
                images = convert_from_bytes(
                    content_bytes, dpi=200, first_page=1, last_page=MAX_OCR_PAGES
                )

            for page_number, image in enumerate(images, start=1):
                image_buffer = io.BytesIO()
                image.save(image_buffer, format="PNG")
                result = subprocess.run(
                    ["tesseract", "stdin", "stdout", "-l", "eng", "tsv"],
                    input=image_buffer.getvalue(),
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    check=False,
                    timeout=60,
                )
                if result.returncode != 0:
                    return [], 0

                words = []
                spans = []
                width, height = image.size
                tsv_text = result.stdout.decode("utf-8", errors="replace")
                for row in csv.DictReader(io.StringIO(tsv_text), delimiter="\t"):
                    if row.get("level") != "5":
                        continue
                    word = (row.get("text") or "").strip()
                    if not word:
                        continue
                    try:
                        x, y = int(row["left"]), int(row["top"])
                        w, h = int(row["width"]), int(row["height"])
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
            # Includes invalid images/PDFs, missing Poppler, and OCR timeouts.
            return [], 0

    def extract_document(
        self,
        content_bytes: bytes,
        doc_type: DocumentType,
        original_filename: str
    ) -> Tuple[List[ExtractedField], DocumentVerificationStatus, str]:
        """
        Extracts structured fields from uploaded bytes.
        Returns (extracted_fields, recommended_status, note).
        If processing is unavailable or uncertain, abstains and routes for manual review.
        """
        pages_data, total_pages = self.extract_text_and_spans(content_bytes)
        combined_text = " ".join(p["text"] for p in pages_data).strip()

        # Scanned PDFs: attempt OCR only when the required tools are available.
        used_ocr = False
        if len(combined_text) < 15:
            is_pdf = content_bytes.startswith(b"%PDF-")
            total_pdf_pages = self.count_pages(content_bytes, "application/pdf") if is_pdf else 1
            if not self.has_tesseract:
                return [], DocumentVerificationStatus.MANUAL_REVIEW_REQUIRED, (
                    "No usable PDF text layer and OCR engine unavailable; manual review required."
                )
            pages_data, total_pages = self._ocr_pdf_pages(content_bytes)
            combined_text = " ".join(page["text"] for page in pages_data).strip()
            if len(combined_text) < 15:
                return [], DocumentVerificationStatus.MANUAL_REVIEW_REQUIRED, (
                    "OCR produced insufficient readable text; manual review required."
                )
            used_ocr = True

        extraction_method = "TESSERACT_OCR" if used_ocr else "PDF_TEXT_STREAM"

        # Real text extraction from parsed text stream
        fields: List[ExtractedField] = []

        # Helper to find span bbox for matched text
        def find_bbox(target_str: str) -> Tuple[int, Optional[List[float]], str]:
            target_lower = target_str.lower().strip()
            # Prefer exact/containing spans; ignore tiny fragments that can match arbitrary evidence.
            for matcher in (
                lambda text: text == target_lower,
                lambda text: target_lower in text,
                lambda text: len(text) >= 4 and text in target_lower,
            ):
                for page_data in pages_data:
                    for span in page_data["spans"]:
                        if matcher(span["text"].lower().strip()):
                            return page_data["page_number"], span["bbox"], span["text"]
            # Fallback to page 1 snippet
            p1_text = pages_data[0]["text"] if pages_data else ""
            idx = p1_text.lower().find(target_lower)
            snippet = p1_text[max(0, idx - 30):min(len(p1_text), idx + len(target_str) + 30)] if idx >= 0 else target_str
            return 1, None, snippet

        # Document-specific regex extraction
        if doc_type == DocumentType.FIRE_SAFETY_NOC:
            # 1. Expiry Date
            exp_match = re.search(
                r"(?:valid\s*(?:until|up\s*to|to|till)|expiry\s*(?:date)?|expires\s*(?:on)?)[:\s]+(\d{4}-\d{2}-\d{2}|\d{1,2}[/-]\d{1,2}[/-]\d{2,4})",
                combined_text,
                re.IGNORECASE
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
                        surrounding_snippet=snip or f"Valid until: {raw_exp}",
                        quality_label=ExtractionQuality.MEDIUM if used_ocr else ExtractionQuality.HIGH
                    )
                ))

            # 2. Issue Date
            issue_match = re.search(
                r"(?:issue[d]?\s*(?:date|on)?|dated)[:\s]+(\d{4}-\d{2}-\d{2}|\d{1,2}[/-]\d{1,2}[/-]\d{2,4})",
                combined_text,
                re.IGNORECASE
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
                        surrounding_snippet=snip or f"Issued on: {raw_iss}",
                        quality_label=ExtractionQuality.MEDIUM if used_ocr else ExtractionQuality.HIGH
                    )
                ))

            # 3. Issuing Authority
            auth_match = re.search(
                r"(?:issuing\s*authority|department|office\s*of)[:\s]+([^,\n\r]+)",
                combined_text,
                re.IGNORECASE
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
                        quality_label=ExtractionQuality.MEDIUM if used_ocr else ExtractionQuality.HIGH
                    )
                ))

        elif doc_type in (DocumentType.AFFIDAVIT_GENERAL, DocumentType.GOVERNING_BODY_RESOLUTION):
            # 1. Institution Name
            inst_match = re.search(
                r"(?:institution|college|university|academy|institute|affidavit\s*of)[:\s]+([^,\n\r]+)",
                combined_text,
                re.IGNORECASE
            )
            if inst_match:
                raw_name = inst_match.group(1).strip()
                pg, bbox, snip = find_bbox(raw_name)
                fields.append(ExtractedField(
                    field_key="institution_name",
                    field_value=raw_name,
                    raw_value=raw_name,
                    data_type="STRING",
                    confidence=0.65 if used_ocr else 0.98,
                    extraction_method=extraction_method,
                    provenance=FieldProvenance(
                        page_number=pg,
                        bounding_box=bbox,
                        surrounding_snippet=snip or raw_name,
                        quality_label=ExtractionQuality.MEDIUM if used_ocr else ExtractionQuality.HIGH
                    )
                ))

            # 2. Intake if mentioned
            intake_match = re.search(r"(?:intake|total\s*intake|seats)[:\s]+(\d+)", combined_text, re.IGNORECASE)
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
                        surrounding_snippet=snip or f"Intake: {raw_intake}",
                        quality_label=ExtractionQuality.MEDIUM if used_ocr else ExtractionQuality.HIGH
                    )
                ))

        elif doc_type in (DocumentType.LAND_USE_CERTIFICATE,):
            area_match = re.search(r"(?:land\s*area|total\s*area|area)[:\s]+([\d\.]+)\s*(?:acres?|hectares?)?", combined_text, re.IGNORECASE)
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
                        surrounding_snippet=snip or f"Land Area: {raw_area}",
                        quality_label=ExtractionQuality.MEDIUM if used_ocr else ExtractionQuality.HIGH
                    )
                ))

        elif doc_type in (DocumentType.BUILDING_PLAN_ARCHITECT,):
            b_match = re.search(r"(?:built[\s\-]?up\s*area|total\s*area|area)[:\s]+([\d\.,]+)\s*(?:sq\.?\s*m|sqm)?", combined_text, re.IGNORECASE)
            if b_match:
                raw_b = b_match.group(1).replace(",", "").strip()
                pg, bbox, snip = find_bbox(b_match.group(1).strip())
                fields.append(ExtractedField(
                    field_key="builtup_area_sqm",
                    field_value=raw_b,
                    raw_value=b_match.group(1).strip(),
                    data_type="NUMERIC",
                    confidence=0.65 if used_ocr else 0.94,
                    extraction_method=extraction_method,
                    provenance=FieldProvenance(
                        page_number=pg,
                        bounding_box=bbox,
                        surrounding_snippet=snip or f"Built-up area: {raw_b}",
                        quality_label=ExtractionQuality.MEDIUM if used_ocr else ExtractionQuality.HIGH
                    )
                ))

        # Fallback if no specific fields matched but text exists
        if not fields:
            # Look for any date
            any_date = re.search(r"(\d{4}-\d{2}-\d{2}|\d{1,2}[/-]\d{1,2}[/-]\d{2,4})", combined_text)
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
                        quality_label=ExtractionQuality.MEDIUM
                    )
                ))
            else:
                # Readable text with no supported claim is not evidence. Do not invent a
                # document_title from the filename; abstain and route it for manual review.
                return [], DocumentVerificationStatus.MANUAL_REVIEW_REQUIRED, (
                    "Text was readable but no recognisable fields were found for this document type; "
                    "manual review required."
                )

        if used_ocr:
            return fields, DocumentVerificationStatus.MANUAL_REVIEW_REQUIRED, (
                f"OCR extracted {len(fields)} field(s); human verification is required."
            )
        return fields, DocumentVerificationStatus.VERIFICATION_PENDING, f"Extracted {len(fields)} fields from PDF text stream."


global_document_extractor = RealDocumentExtractor()
