"""
main.py - FastAPI application entry point.

Initializes the FastAPI app, configures CORS middleware,
and includes the upload API router.
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import router

app = FastAPI(
    title="Resume Parser API",
    description="API for uploading and extracting text from PDF and DOCX resumes.",
    version="1.0.0",
)

# ---------------------------------------------------------------------------
# CORS Middleware
# Allow all origins so that any frontend (local dev or deployed) can connect
# without CORS blocking issues.
# ---------------------------------------------------------------------------
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------------------------------------------------------------------
# Router inclusion
# All upload endpoints live under /api/v1
# ---------------------------------------------------------------------------
app.include_router(router, prefix="/api/v1")


@app.get("/", tags=["Health"])
async def health_check():
    """Simple health-check endpoint to confirm the service is running."""
    return {"status": "ok", "message": "Resume Parser API is running."}
