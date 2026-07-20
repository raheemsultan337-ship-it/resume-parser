"""
extractor.py - Text extraction service.

Provides two public functions for extracting plain text from uploaded files:
  - extract_pdf(file_bytes: bytes) -> str
  - extract_docx(file_bytes: bytes) -> str

PDF extraction strategy:
  1. Primary  : pdfplumber  – fast, accurate for text-based PDFs.
  2. Fallback : pdf2image + pytesseract (OCR) – used when the extracted text
               is less than 50 characters, which typically indicates a
               scanned / image-based PDF.

DOCX extraction:
  - python-docx reads all paragraphs via io.BytesIO (no disk I/O).
"""

import io
import logging

import pdfplumber
import pytesseract
from docx import Document
from pdf2image import convert_from_bytes
from PIL import Image

logger = logging.getLogger(__name__)

# Minimum character threshold to consider pdfplumber extraction successful.
_MIN_TEXT_LENGTH = 50


# ---------------------------------------------------------------------------
# PDF Extraction
# ---------------------------------------------------------------------------

def _extract_pdf_with_pdfplumber(file_bytes: bytes) -> str:
    """Extract text from a text-based PDF using pdfplumber.

    Args:
        file_bytes: Raw bytes of the PDF file.

    Returns:
        Concatenated text from all pages.

    Raises:
        ValueError: If pdfplumber cannot open or read the file.
    """
    text_parts: list[str] = []
    with pdfplumber.open(io.BytesIO(file_bytes)) as pdf:
        for page in pdf.pages:
            page_text = page.extract_text()
            if page_text:
                text_parts.append(page_text)
    return "\n".join(text_parts)


def _extract_pdf_with_ocr(file_bytes: bytes) -> str:
    """Extract text from a scanned PDF using pdf2image + pytesseract (OCR).

    Converts each PDF page into a PIL Image and runs OCR on it.

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


def extract_pdf(file_bytes: bytes) -> str:
    """Extract text from a PDF file (text-based or scanned).

    Tries pdfplumber first. If the result is under 50 characters, the PDF is
    assumed to be scanned and OCR is used as a fallback.

    Args:
        file_bytes: Raw bytes of the uploaded PDF.

    Returns:
        Extracted plain text string.

    Raises:
        ValueError: If the file cannot be parsed as a PDF.
        RuntimeError: If OCR extraction encounters an unexpected error.
    """
    try:
        text = _extract_pdf_with_pdfplumber(file_bytes)
    except Exception as exc:
        raise ValueError(f"pdfplumber could not read the PDF: {exc}") from exc

    if len(text.strip()) < _MIN_TEXT_LENGTH:
        logger.info(
            "pdfplumber returned %d characters (< %d). Switching to OCR.",
            len(text.strip()),
            _MIN_TEXT_LENGTH,
        )
        try:
            text = _extract_pdf_with_ocr(file_bytes)
        except Exception as exc:
            raise RuntimeError(f"OCR extraction failed: {exc}") from exc

    return text.strip()


# ---------------------------------------------------------------------------
# DOCX Extraction
# ---------------------------------------------------------------------------

def extract_docx(file_bytes: bytes) -> str:
    """Extract text from a DOCX file using python-docx.

    Reads paragraphs from the document entirely in-memory via io.BytesIO.

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
