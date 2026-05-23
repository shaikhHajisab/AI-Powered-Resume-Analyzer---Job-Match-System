from fastapi import APIRouter, UploadFile, File, Form, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import Optional
from datetime import datetime, timezone

from app.db.deps import get_db
from app.api.deps import get_current_user
from app.models.user import User
from app.models.resume import Resume
from app.services.pdf_parser import extract_text_from_pdf, validate_pdf_file
from app.services.ml_scorer import calculate_tfidf_score, calculate_final_score
from app.services.semantic_scorer import (
    get_document_embedding,
    cosine_similarity_vectors,
    calculate_semantic_score
)
from app.services.llm_service import generate_resume_suggestions
from app.services.vector_store import get_similar_jobs

router = APIRouter()

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

def build_full_response(resume, cached: bool) -> dict:
    """Build consistent response structure"""
    return {
        "resume_id": resume.id,
        "filename": resume.filename,
        "job_title": resume.job_title,
        "status": resume.status,
        "cached": cached,
        "scores": {
            "tfidf_score": resume.tfidf_score,
            "semantic_score": resume.semantic_score,
            "final_score": resume.final_score,
            "interpretation": interpret_score(resume.final_score or 0),
        },
        "keywords": {
            "matched": resume.matched_keywords or [],
            "missing": resume.missing_keywords or [],
        },
        "suggestions": resume.suggestions or [],
        "similar_jobs": resume.similar_jobs or [],
        "completed_at": resume.completed_at,
    }


@router.post("/upload")
async def upload_resume(
    file: UploadFile = File(...),
    job_description: str = Form(...),
    job_title: Optional[str] = Form(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    validate_pdf_file(filename=file.filename, file_size_bytes=file.size or 0)

    file_bytes = await file.read()
    if len(file_bytes) > 5 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="File too large. Maximum 5MB.")

    resume_text = extract_text_from_pdf(file_bytes)

    resume = Resume(
        user_id=current_user.id,
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
        Resume.user_id == current_user.id
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

    result = calculate_tfidf_score(resume.resume_text, resume.job_description)

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


@router.post("/{resume_id}/analyze")
async def analyze_resume(
    resume_id: int,
    force_rerun: bool = False,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Run full score analysis (TF-IDF + Semantic)"""
    resume = db.query(Resume).filter(
        Resume.id == resume_id,
        Resume.user_id == current_user.id
    ).first()

    if not resume:
        raise HTTPException(status_code=404, detail="Resume not found")

    if not resume.resume_text or not resume.job_description:
        raise HTTPException(
            status_code=400,
            detail="Resume needs both text and job description"
        )

    if resume.status == "completed" and not force_rerun:
        return {
            "resume_id": resume.id,
            "status": "completed",
            "cached": True,
            "scores": {
                "tfidf_score": resume.tfidf_score,
                "semantic_score": resume.semantic_score,
                "final_score": resume.final_score,
            },
            "keywords": {
                "matched": resume.matched_keywords,
                "missing": resume.missing_keywords,
            },
            "interpretation": interpret_score(resume.final_score),
            "completed_at": resume.completed_at,
        }

    resume.status = "processing"
    db.commit()

    try:
        tfidf_result = calculate_tfidf_score(
            resume.resume_text,
            resume.job_description
        )

        if resume.resume_embedding and not force_rerun:
            resume_emb = resume.resume_embedding
        else:
            resume_emb = get_document_embedding(resume.resume_text)
            resume.resume_embedding = resume_emb

        if resume.jd_embedding and not force_rerun:
            jd_emb = resume.jd_embedding
        else:
            jd_emb = get_document_embedding(resume.job_description)
            resume.jd_embedding = jd_emb

        similarity = cosine_similarity_vectors(resume_emb, jd_emb)
        semantic_score = round(similarity * 100, 2)

        final = calculate_final_score(
            tfidf_result["tfidf_score"],
            semantic_score
        )

        resume.tfidf_score = tfidf_result["tfidf_score"]
        resume.semantic_score = semantic_score
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
            "cached": False,
            "scores": {
                "tfidf_score": tfidf_result["tfidf_score"],
                "semantic_score": semantic_score,
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
        resume.status = "failed"
        db.commit()
        raise HTTPException(status_code=500, detail=f"Analysis failed: {str(e)}")


@router.post("/{resume_id}/suggestions")
async def get_suggestions(
    resume_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Generate LLM-powered improvement suggestions for a resume"""
    resume = db.query(Resume).filter(
        Resume.id == resume_id,
        Resume.user_id == current_user.id
    ).first()

    if not resume:
        raise HTTPException(status_code=404, detail="Resume not found")

    if resume.status != "completed":
        raise HTTPException(
            status_code=400,
            detail="Run /analyze first before getting suggestions"
        )

    if resume.suggestions:
        return {
            "resume_id": resume.id,
            "cached": True,
            "suggestions": resume.suggestions
        }

    try:
        suggestions = generate_resume_suggestions(
            resume_text=resume.resume_text,
            job_description=resume.job_description,
            matched_keywords=resume.matched_keywords or [],
            missing_keywords=resume.missing_keywords or [],
            final_score=resume.final_score or 0
        )

        resume.suggestions = suggestions
        db.commit()

        return {
            "resume_id": resume.id,
            "cached": False,
            "final_score": resume.final_score,
            "suggestions": suggestions
        }
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"LLM suggestions unavailable: {str(e)}")


@router.get("/{resume_id}/similar-jobs")
async def find_similar_jobs(
    resume_id: int,
    top_k: int = 3,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Find jobs similar to the uploaded resume using RAG"""
    resume = db.query(Resume).filter(
        Resume.id == resume_id,
        Resume.user_id == current_user.id
    ).first()

    if not resume:
        raise HTTPException(status_code=404, detail="Resume not found")

    if not resume.resume_text:
        raise HTTPException(status_code=400, detail="No resume text found")

    if resume.similar_jobs:
        return {
            "resume_id": resume.id,
            "cached": True,
            "similar_jobs": resume.similar_jobs
        }

    try:
        similar = get_similar_jobs(resume.resume_text, top_k=top_k)

        resume.similar_jobs = similar
        db.commit()

        return {
            "resume_id": resume.id,
            "cached": False,
            "similar_jobs": similar
        }
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"Similar jobs unavailable: {str(e)}")


@router.post("/{resume_id}/full-analysis")
async def full_analysis(
    resume_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Runs everything in one call: TF-IDF, Semantic, LLM, and RAG.
    """
    resume = db.query(Resume).filter(
        Resume.id == resume_id,
        Resume.user_id == current_user.id
    ).first()

    if not resume:
        raise HTTPException(status_code=404, detail="Resume not found")

    if not resume.resume_text or not resume.job_description:
        raise HTTPException(status_code=400, detail="Resume needs text and job description")

    if (resume.status == "completed" and
        resume.suggestions and
        resume.similar_jobs):
        return build_full_response(resume, cached=True)

    resume.status = "processing"
    db.commit()

    errors = []

    try:
        tfidf_result = calculate_tfidf_score(
            resume.resume_text,
            resume.job_description
        )

        if resume.resume_embedding:
            resume_emb = resume.resume_embedding
        else:
            resume_emb = get_document_embedding(resume.resume_text)
            resume.resume_embedding = resume_emb

        if resume.jd_embedding:
            jd_emb = resume.jd_embedding
        else:
            jd_emb = get_document_embedding(resume.job_description)
            resume.jd_embedding = jd_emb

        similarity = cosine_similarity_vectors(resume_emb, jd_emb)
        semantic_score = round(similarity * 100, 2)
        final = calculate_final_score(tfidf_result["tfidf_score"], semantic_score)

        resume.tfidf_score = tfidf_result["tfidf_score"]
        resume.semantic_score = semantic_score
        resume.final_score = final
        resume.matched_keywords = tfidf_result["matched_keywords"]
        resume.missing_keywords = tfidf_result["missing_keywords"]
        db.commit()

    except Exception as e:
        resume.status = "failed"
        db.commit()
        raise HTTPException(status_code=500, detail=f"Scoring failed: {str(e)}")

    if not resume.suggestions:
        try:
            suggestions = generate_resume_suggestions(
                resume_text=resume.resume_text,
                job_description=resume.job_description,
                matched_keywords=resume.matched_keywords or [],
                missing_keywords=resume.missing_keywords or [],
                final_score=resume.final_score
            )
            resume.suggestions = suggestions
            db.commit()
        except Exception as e:
            errors.append(f"LLM suggestions unavailable: {str(e)}")

    if not resume.similar_jobs:
        try:
            similar = get_similar_jobs(resume.resume_text, top_k=3)
            resume.similar_jobs = similar
            db.commit()
        except Exception as e:
            errors.append(f"Similar jobs unavailable: {str(e)}")

    resume.status = "completed"
    resume.completed_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(resume)

    response = build_full_response(resume, cached=False)
    if errors:
        response["warnings"] = errors

    return response