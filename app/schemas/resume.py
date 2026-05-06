from pydantic import BaseModel, Field, field_validator
from typing import Optional, List
from datetime import datetime
from enum import Enum


class AnalysisStatus(str, Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class ResumeAnalysisRequest(BaseModel):
    job_description: str = Field(
        min_length=50,
        max_length=10000,
        description="The job description to match against"
    )

    job_title: Optional[str] = Field(
        default=None,
        max_length=200
    )

    @field_validator('job_description')
    @classmethod
    def job_description_must_have_content(cls, v: str) -> str:
        if not v.strip():
            raise ValueError('Job description cannot be empty or whitespace only')
        return v.strip()


class ScoreBreakdown(BaseModel):
    tfidf_score: float = Field(ge=0.0, le=100.0)
    semantic_score: float = Field(ge=0.0, le=100.0)
    final_score: float = Field(ge=0.0, le=100.0)

    matched_keywords: List[str] = Field(default_factory=list)
    missing_keywords: List[str] = Field(default_factory=list)


class ResumeSuggestion(BaseModel):
    category: str
    suggestion: str
    priority: str = Field(default="medium")


class AnalysisResponse(BaseModel):
    id: int
    status: AnalysisStatus
    job_title: Optional[str]

    scores: Optional[ScoreBreakdown] = None
    suggestions: Optional[List[ResumeSuggestion]] = None
    similar_jobs: Optional[List[str]] = None

    created_at: datetime
    completed_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


class ResumeUploadResponse(BaseModel):
    message: str
    resume_id: int
    filename: str
    status: AnalysisStatus = AnalysisStatus.PENDING