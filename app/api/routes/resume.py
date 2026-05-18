# app/api/routes/resume.py — updated version

from fastapi import APIRouter, UploadFile, File, Form, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import Optional

from app.services.semantic_scorer import calculate_semantic_score
from app.services.ml_scorer import calculate_tfidf_score, calculate_final_score
from datetime import datetime, timezone

from app.db.deps import get_db
from app.api.deps import get_current_user          # NEW
from app.models.user import User                    # NEW
from app.models.resume import Resume
from app.services.pdf_parser import extract_text_from_pdf, validate_pdf_file
from app.services.ml_scorer import calculate_tfidf_score
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
    
    
@router.post("/{resume_id}/analyze-tfidf")
async def analyze_tfidf(
    resume_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Run TF-IDF scoring on an uploaded resume"""
    # fetch resume — make sure it belongs to current user
    resume = db.query(Resume).filter(
        Resume.id == resume_id,
        Resume.user_id == current_user.id
    ).first()

    if not resume:
        raise HTTPException(status_code=404, detail="Resume not found")

    if not resume.resume_text or not resume.job_description:
        raise HTTPException(
            status_code=400,
            detail="Resume must have both resume text and job description"
        )

    # run ML scoring
    result = calculate_tfidf_score(resume.resume_text, resume.job_description)

    # save scores to database
    resume.tfidf_score = result["tfidf_score"]
    resume.matched_keywords = result["matched_keywords"]
    resume.missing_keywords = result["missing_keywords"]
    resume.status = "processing"
    db.commit()
    db.refresh(resume)

    return {
        "resume_id": resume.id,
        "tfidf_score": result["tfidf_score"],
        "matched_keywords": result["matched_keywords"],
        "missing_keywords": result["missing_keywords"],
        "interpretation": interpret_score(result["tfidf_score"])
    }


def interpret_score(score: float) -> str:
    """Human readable score interpretation"""
    if score >= 70:
        return "Strong match — your resume aligns well with this job"
    elif score >= 50:
        return "Moderate match — consider adding missing keywords"
    elif score >= 30:
        return "Weak match — significant gaps between resume and job requirements"
    else:
        return "Poor match — this role may not align with your current resume"


@router.post("/{resume_id}/analyze")
async def analyze_resume(
    resume_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Full analysis pipeline:
    1. TF-IDF keyword matching score
    2. Semantic similarity score  
    3. Combined final score
    4. Save everything to database
    """
    resume = db.query(Resume).filter(
        Resume.id == resume_id,
        Resume.user_id == current_user.id
    ).first()

    if not resume:
        raise HTTPException(status_code=404, detail="Resume not found")

    if not resume.resume_text or not resume.job_description:
        raise HTTPException(
            status_code=400,
            detail="Resume must have both resume text and job description"
        )

    # mark as processing
    resume.status = "processing"
    db.commit()

    try:
        # step 1 — TF-IDF
        tfidf_result = calculate_tfidf_score(
            resume.resume_text,
            resume.job_description
        )

        # step 2 — semantic (HuggingFace API call)
        semantic_result = calculate_semantic_score(
            resume.resume_text,
            resume.job_description
        )

        # step 3 — combine
        final = calculate_final_score(
            tfidf_result["tfidf_score"],
            semantic_result["semantic_score"]
        )

        # step 4 — save to database
        resume.tfidf_score = tfidf_result["tfidf_score"]
        resume.semantic_score = semantic_result["semantic_score"]
        resume.final_score = final
        resume.matched_keywords = tfidf_result["matched_keywords"]
        resume.missing_keywords = tfidf_result["missing_keywords"]
        resume.status = "completed"
        resume.completed_at = datetime.now(timezone.utc)
        db.commit()
        db.refresh(resume)

        return {
            "resume_id": resume.id,
            "status": "completed",
            "scores": {
                "tfidf_score": tfidf_result["tfidf_score"],
                "semantic_score": semantic_result["semantic_score"],
                "final_score": final,
            },
            "keywords": {
                "matched": tfidf_result["matched_keywords"],
                "missing": tfidf_result["missing_keywords"],
            },
            "interpretation": interpret_score(final),
            "completed_at": resume.completed_at,
        }

    except Exception as e:
        # if anything fails — mark as failed in DB
        resume.status = "failed"
        db.commit()
        raise HTTPException(status_code=500, detail=f"Analysis failed: {str(e)}")
