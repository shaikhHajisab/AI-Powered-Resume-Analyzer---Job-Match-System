# app/api/routes/resume.py

from fastapi import APIRouter, UploadFile, File, Form, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import Optional

from app.db.deps import get_db
from app.models.resume import Resume
from app.services.pdf_parser import extract_text_from_pdf, validate_pdf_file

# APIRouter is like a mini FastAPI app — groups related endpoints
# We register this router in main.py with a prefix
router = APIRouter()


@router.post("/upload")
async def upload_resume(
    # UploadFile = the uploaded PDF
    # File(...) means it's required (... = no default)
    file: UploadFile = File(...),
    
    # Form(...) reads from multipart form fields (not JSON body)
    # When sending files, everything must be form data — not JSON
    job_description: str = Form(...),
    job_title: Optional[str] = Form(None),  # optional field
    
    # Depends(get_db) → FastAPI calls get_db() and injects the session
    db: Session = Depends(get_db),
):
    # --- Step 1: validate before reading the file ---
    validate_pdf_file(
        filename=file.filename,
        file_size_bytes=file.size or 0
    )

    # --- Step 2: read file bytes ---
    # await because reading from upload stream is async I/O
    file_bytes = await file.read()

    # double-check size after reading (file.size can be None for some clients)
    if len(file_bytes) > 5 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="File too large. Maximum 5MB.")

    # --- Step 3: extract text ---
    resume_text = extract_text_from_pdf(file_bytes)

    # --- Step 4: save to database ---
    resume = Resume(
        user_id=1,  # hardcoded for now — Day 5 (JWT) will fix this
        filename=file.filename,
        resume_text=resume_text,
        job_description=job_description,
        job_title=job_title,
        status="pending"
    )
    db.add(resume)
    db.commit()
    db.refresh(resume)

    return {
        "message": "Resume uploaded successfully",
        "resume_id": resume.id,
        "filename": resume.filename,
        "status": resume.status,
        "text_length": len(resume_text),
        "preview": resume_text[:300] + "..."  # first 300 chars so you can verify extraction
    }


@router.get("/{resume_id}")
async def get_resume(resume_id: int, db: Session = Depends(get_db)):
    """Fetch a resume record by ID"""
    resume = db.query(Resume).filter(Resume.id == resume_id).first()

    if not resume:
        raise HTTPException(status_code=404, detail="Resume not found")

    return {
        "id": resume.id,
        "filename": resume.filename,
        "job_title": resume.job_title,
        "status": resume.status,
        "text_preview": resume.resume_text[:500] if resume.resume_text else None,
        "created_at": resume.created_at,
    }