"""
routes.py - API route definitions for the resume parser.

Endpoint:
  POST /upload
    - Accepts a single file upload (PDF or DOCX).
    - Validates the file extension.
    - Delegates text extraction to the appropriate service function.
    - Returns extracted text with metadata.
"""

import logging
import os

from fastapi import APIRouter, File, HTTPException, UploadFile
from fastapi.responses import JSONResponse

from app.services.extractor import extract_docx, extract_pdf

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Upload"])

# Allowed file extensions
_ALLOWED_EXTENSIONS = {".pdf", ".docx"}


@router.post("/upload", summary="Upload a resume file for text extraction")
async def upload_resume(file: UploadFile = File(...)):
    """Extract text from an uploaded PDF or DOCX resume file.

    The file is processed entirely in-memory; nothing is written to disk.

    Args:
        file: The uploaded file. Must be a `.pdf` or `.docx`.

    Returns:
        JSON object with the following fields:
          - filename (str): Original filename as uploaded.
          - file_type (str): Detected file type ("pdf" or "docx").
          - character_count (int): Number of characters in the extracted text.
          - extracted_text (str): The full extracted plain text.

    Raises:
        400 Bad Request: If the file extension is not `.pdf` or `.docx`.
        422 Unprocessable Entity: If the file is corrupted or cannot be parsed.
        500 Internal Server Error: For unexpected extraction failures.
    """
    # -----------------------------------------------------------------------
    # 1. Validate file extension
    # -----------------------------------------------------------------------
    filename = file.filename or ""
    _, ext = os.path.splitext(filename)
    ext = ext.lower()

    if ext not in _ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=(
                f"Unsupported file type '{ext}'. "
                f"Only {', '.join(sorted(_ALLOWED_EXTENSIONS))} files are accepted."
            ),
        )

    # -----------------------------------------------------------------------
    # 2. Read file bytes into memory (no disk writes)
    # -----------------------------------------------------------------------
    try:
        file_bytes = await file.read()
    except Exception as exc:
        logger.error("Failed to read uploaded file '%s': %s", filename, exc)
        raise HTTPException(
            status_code=500,
            detail="Failed to read the uploaded file.",
        ) from exc

    # -----------------------------------------------------------------------
    # 3. Route to the appropriate extractor
    # -----------------------------------------------------------------------
    file_type = ext.lstrip(".")  # "pdf" or "docx"

    try:
        if ext == ".pdf":
            extracted_text = extract_pdf(file_bytes)
        else:  # .docx
            extracted_text = extract_docx(file_bytes)
    except ValueError as exc:
        # Corrupted or unreadable file
        logger.warning("Extraction error for '%s': %s", filename, exc)
        raise HTTPException(
            status_code=422,
            detail=f"Could not extract text from the file: {exc}",
        ) from exc
    except RuntimeError as exc:
        # OCR or other runtime failures
        logger.error("Runtime extraction error for '%s': %s", filename, exc)
        raise HTTPException(
            status_code=500,
            detail=f"An error occurred during text extraction: {exc}",
        ) from exc
    except Exception as exc:
        logger.exception("Unexpected error while processing '%s'", filename)
        raise HTTPException(
            status_code=500,
            detail="An unexpected error occurred during file processing.",
        ) from exc

    # -----------------------------------------------------------------------
    # 4. Return structured JSON response
    # -----------------------------------------------------------------------
    return JSONResponse(
        content={
            "filename": filename,
            "file_type": file_type,
            "character_count": len(extracted_text),
            "extracted_text": extracted_text,
        }
    )
