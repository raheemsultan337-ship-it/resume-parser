"""
extractor.py - Text extraction service.

Provides two public functions for extracting plain text from uploaded files:
  - extract_pdf(file_bytes: bytes) -> str
  - extract_docx(file_bytes: bytes) -> str

PDF extraction strategy (three tiers):
  1. Primary   : pdfplumber  – accurate for machine-generated (text-based) PDFs.
  2. Secondary : pypdf       – lightweight fallback for text-based PDFs that
                               pdfplumber struggles with.
  3. OCR       : pdf2image + pytesseract – last resort for scanned/image PDFs.
                 Triggered when both pdfplumber and pypdf return fewer than
                 MIN_TEXT_LENGTH characters.

DOCX extraction:
  - python-docx reads all paragraphs via io.BytesIO (no disk I/O).

System requirement for OCR:
  - Tesseract must be installed on the host machine.
  - Set TESSDATA_PREFIX or pytesseract.pytesseract.tesseract_cmd in your .env
    if Tesseract is not on PATH.
"""

import io
import logging
import os

import pdfplumber
import pytesseract
from docx import Document
from pdf2image import convert_from_bytes
from PIL import Image
from pypdf import PdfReader

logger = logging.getLogger(__name__)

# Minimum character threshold to consider digital extraction successful.
_MIN_TEXT_LENGTH = 50

# Allow the Tesseract binary location to be configured via environment variable.
_tesseract_cmd = os.getenv("TESSERACT_CMD")
if _tesseract_cmd:
    pytesseract.pytesseract.tesseract_cmd = _tesseract_cmd


# ---------------------------------------------------------------------------
# PDF Extraction — Tier 1: pdfplumber
# ---------------------------------------------------------------------------

def _extract_pdf_with_pdfplumber(file_bytes: bytes) -> str:
    """Extract text from a text-based PDF using pdfplumber.

    Args:
        file_bytes: Raw bytes of the PDF file.

    Returns:
        Concatenated text from all pages (may be empty for scanned PDFs).

    Raises:
        ValueError: If pdfplumber cannot open or parse the file.
    """
    text_parts: list[str] = []
    with pdfplumber.open(io.BytesIO(file_bytes)) as pdf:
        for page in pdf.pages:
            page_text = page.extract_text()
            if page_text:
                text_parts.append(page_text)
    return "\n".join(text_parts)


# ---------------------------------------------------------------------------
# PDF Extraction — Tier 2: pypdf
# ---------------------------------------------------------------------------

def _extract_pdf_with_pypdf(file_bytes: bytes) -> str:
    """Extract text from a PDF using pypdf as a secondary fallback.

    pypdf (the modern successor to PyPDF2) handles some PDFs that pdfplumber
    cannot parse, and is useful as a lightweight bridge before expensive OCR.

    Args:
        file_bytes: Raw bytes of the PDF file.

    Returns:
        Concatenated text from all pages (may be empty for scanned PDFs).

    Raises:
        ValueError: If pypdf cannot open or parse the file.
    """
    reader = PdfReader(io.BytesIO(file_bytes))
    text_parts: list[str] = []
    for page in reader.pages:
        page_text = page.extract_text()
        if page_text:
            text_parts.append(page_text)
    return "\n".join(text_parts)


# ---------------------------------------------------------------------------
# PDF Extraction — Tier 3: OCR (Tesseract via pdf2image)
# ---------------------------------------------------------------------------

def _extract_pdf_with_ocr(file_bytes: bytes) -> str:
    """Extract text from a scanned PDF using pdf2image + pytesseract (OCR).

    Converts each PDF page to a PIL Image, then runs Tesseract OCR on it.

    Args:
        file_bytes: Raw bytes of the PDF file.

    Returns:
        Concatenated OCR text from all pages.

    Raises:
        RuntimeError: If image conversion or OCR fails.
    """
    logger.info("Falling back to OCR extraction for scanned PDF.")
    images: list[Image.Image] = convert_from_bytes(file_bytes)
    text_parts: list[str] = []
    for page_num, image in enumerate(images, start=1):
        try:
            ocr_text = pytesseract.image_to_string(image)
            text_parts.append(ocr_text)
        except pytesseract.TesseractError as exc:
            logger.warning("OCR failed on page %d: %s", page_num, exc)
    return "\n".join(text_parts)


# ---------------------------------------------------------------------------
# Public: extract_pdf
# ---------------------------------------------------------------------------

def extract_pdf(file_bytes: bytes) -> str:
    """Extract text from a PDF file (text-based or scanned).

    Applies a three-tier strategy:
      1. pdfplumber  — fast, accurate for machine-generated PDFs.
      2. pypdf       — secondary fallback for digital PDFs.
      3. OCR         — Tesseract-based fallback for scanned/image PDFs.

    Tiers 2 and 3 are only invoked when the previous tier yields fewer than
    MIN_TEXT_LENGTH (50) characters, which strongly indicates a scanned PDF.

    Args:
        file_bytes: Raw bytes of the uploaded PDF.

    Returns:
        Extracted plain text string (stripped of leading/trailing whitespace).

    Raises:
        ValueError: If the file cannot be parsed as a PDF.
        RuntimeError: If OCR extraction encounters an unexpected error.
    """
    # Tier 1: pdfplumber
    try:
        text = _extract_pdf_with_pdfplumber(file_bytes)
    except Exception as exc:
        raise ValueError(f"pdfplumber could not read the PDF: {exc}") from exc

    if len(text.strip()) >= _MIN_TEXT_LENGTH:
        return text.strip()

    logger.info(
        "pdfplumber returned %d chars (< %d). Trying pypdf.",
        len(text.strip()),
        _MIN_TEXT_LENGTH,
    )

    # Tier 2: pypdf
    try:
        text = _extract_pdf_with_pypdf(file_bytes)
    except Exception as exc:
        logger.warning("pypdf extraction failed: %s. Proceeding to OCR.", exc)
        text = ""

    if len(text.strip()) >= _MIN_TEXT_LENGTH:
        return text.strip()

    logger.info(
        "pypdf returned %d chars (< %d). Switching to OCR.",
        len(text.strip()),
        _MIN_TEXT_LENGTH,
    )

    # Tier 3: OCR
    try:
        text = _extract_pdf_with_ocr(file_bytes)
    except Exception as exc:
        raise RuntimeError(f"OCR extraction failed: {exc}") from exc

    return text.strip()


# ---------------------------------------------------------------------------
# Public: extract_docx
# ---------------------------------------------------------------------------

def extract_docx(file_bytes: bytes) -> str:
    """Extract text from a DOCX file using python-docx.

    Reads all paragraphs from the document entirely in-memory via io.BytesIO.
    Table cells and headers/footers are not included — only body paragraphs.

    Args:
        file_bytes: Raw bytes of the uploaded DOCX file.

    Returns:
        Extracted plain text with paragraphs joined by newlines.

    Raises:
        ValueError: If the file cannot be parsed as a valid DOCX document.
    """
    try:
        doc = Document(io.BytesIO(file_bytes))
    except Exception as exc:
        raise ValueError(f"python-docx could not read the DOCX file: {exc}") from exc

    paragraphs = [para.text for para in doc.paragraphs if para.text.strip()]
    return "\n".join(paragraphs).strip()
