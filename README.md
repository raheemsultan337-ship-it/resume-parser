# Resume Parser

A FastAPI service that accepts PDF and DOCX resume uploads and returns extracted plain text.

## Project structure

```
backend/
├── app/
│   ├── api/
│   │   └── routes.py        # POST /api/v1/upload endpoint
│   ├── services/
│   │   └── extractor.py     # PDF / DOCX extraction logic
│   └── main.py              # FastAPI app, CORS middleware, router
├── .env.example             # environment variable reference
├── .gitignore
└── requirements.txt
```

## Prerequisites

| Dependency | Purpose |
|---|---|
| Python 3.10+ | Runtime |
| [Tesseract OCR](https://github.com/tesseract-ocr/tesseract) | OCR fallback for scanned PDFs |
| [Poppler](https://poppler.freedesktop.org/) | Required by `pdf2image` to render PDF pages |

**Install Tesseract:**
- Windows: download the installer from [UB Mannheim](https://github.com/UB-Mannheim/tesseract/wiki)
- macOS: `brew install tesseract`
- Ubuntu/Debian: `sudo apt install tesseract-ocr`

**Install Poppler:**
- Windows: download from [oschwartz10612/poppler-windows](https://github.com/oschwartz10612/poppler-windows/releases) and add `bin/` to PATH
- macOS: `brew install poppler`
- Ubuntu/Debian: `sudo apt install poppler-utils`

## Setup

```bash
# 1. Clone and navigate
git clone <repo-url>
cd resume-parser/backend

# 2. Create and activate a virtual environment
python -m venv .venv
# Windows
.venv\Scripts\activate
# macOS / Linux
source .venv/bin/activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Configure environment (optional — only needed if Tesseract is not on PATH)
cp .env.example .env
# Edit .env and set TESSERACT_CMD if required
```

## Running the API

```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

The API will be available at `http://localhost:8000`.

Interactive docs: `http://localhost:8000/docs`

## Endpoints

### `GET /`
Health check.

```json
{ "status": "ok", "message": "Resume Parser API is running." }
```

### `POST /api/v1/upload`
Upload a PDF or DOCX resume for text extraction.

**Request:** `multipart/form-data` with a `file` field.

**Response:**
```json
{
  "filename": "resume.pdf",
  "file_type": "pdf",
  "character_count": 3421,
  "extracted_text": "John Doe\nSoftware Engineer\n..."
}
```

**Error codes:**
| Code | Reason |
|------|--------|
| 400 | Unsupported file type (not `.pdf` or `.docx`) |
| 422 | File is corrupted or cannot be parsed |
| 500 | Unexpected server error |

## PDF extraction strategy

The service uses a three-tier approach so both text-based and scanned PDFs are handled:

1. **pdfplumber** — primary extractor, accurate for machine-generated PDFs
2. **pypdf** — lightweight fallback for digital PDFs pdfplumber struggles with
3. **Tesseract OCR** — last resort for fully scanned / image-based PDFs

Tier 2 and 3 are only invoked when the previous tier returns fewer than 50 characters.

## CORS

`CORSMiddleware` is configured with `allow_origins=["*"]` so any frontend (local dev or deployed) can connect without CORS issues. Restrict `allow_origins` to specific domains before deploying to production.

## Branch

`feature/file-extraction`
