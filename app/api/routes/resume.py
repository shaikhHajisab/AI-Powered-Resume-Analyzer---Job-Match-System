# app/api/routes/resume.py — updated version

from fastapi import APIRouter, UploadFile, File, Form, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import Optional

from app.db.deps import get_db
from app.api.deps import get_current_user          # NEW
from app.models.user import User                    # NEW
from app.models.resume import Resume
from app.services.pdf_parser import extract_text_from_pdf, validate_pdf_file

router = APIRouter()


@router.post("/upload")
async def upload_resume(
    file: UploadFile = File(...),
    job_description: str = Form(...),
    job_title: Optional[str] = Form(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),  # NEW — requires valid token
):
    validate_pdf_file(filename=file.filename, file_size_bytes=file.size or 0)

    file_bytes = await file.read()

    if len(file_bytes) > 5 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="File too large. Maximum 5MB.")

    resume_text = extract_text_from_pdf(file_bytes)

    resume = Resume(
        user_id=current_user.id,  # FIXED — no longer hardcoded
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
        "preview": resume_text[:300] + "..."
    }


@router.get("/my-resumes")
async def get_my_resumes(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get all resumes belonging to the logged-in user"""
    resumes = db.query(Resume).filter(Resume.user_id == current_user.id).all()

    return {
        "total": len(resumes),
        "resumes": [
            {
                "id": r.id,
                "filename": r.filename,
                "job_title": r.job_title,
                "status": r.status,
                "final_score": r.final_score,
                "created_at": r.created_at,
            }
            for r in resumes
        ]
    }


@router.get("/{resume_id}")
async def get_resume(
    resume_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    resume = db.query(Resume).filter(
        Resume.id == resume_id,
        Resume.user_id == current_user.id  # users can only see their own resumes
    ).first()

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