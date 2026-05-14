# app/models/resume.py

from sqlalchemy import Column, Integer, String, Float, DateTime, Text, ForeignKey, JSON, func
from sqlalchemy.orm import relationship
from app.db.database import Base

class Resume(Base):
    __tablename__ = "resumes"

    id = Column(Integer, primary_key=True, index=True)
    
    # ForeignKey links to users table
    # a resume must belong to an existing user
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    
    filename = Column(String(255), nullable=False)
    resume_text = Column(Text, nullable=True)       # extracted PDF text
    job_description = Column(Text, nullable=True)
    job_title = Column(String(255), nullable=True)
    
    # scores — null until analysis runs
    tfidf_score = Column(Float, nullable=True)
    semantic_score = Column(Float, nullable=True)
    final_score = Column(Float, nullable=True)
    
    # JSON columns store lists (keywords, suggestions)
    matched_keywords = Column(JSON, nullable=True)
    missing_keywords = Column(JSON, nullable=True)
    suggestions = Column(JSON, nullable=True)
    similar_jobs = Column(JSON, nullable=True)
    
    status = Column(String(50), default="pending")
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    completed_at = Column(DateTime(timezone=True), nullable=True)

    # other side of User.resumes relationship
    owner = relationship("User", back_populates="resumes")

    def __repr__(self):
        return f"<Resume id={self.id} status={self.status}>"