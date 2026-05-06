from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.schemas.user import UserCreate, UserResponse
from app.schemas.resume import ResumeAnalysisRequest

app = FastAPI(
    title=settings.APP_NAME,
    description="AI-powered resume analysis and job matching system",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
async def root():
    return {
        "message": f"Welcome to {settings.APP_NAME}",
        "docs": "/docs",
        "status": "running"
    }


@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "app": settings.APP_NAME,
        "debug_mode": settings.DEBUG
    }


@app.post(
    "/test/validate-user",
    response_model=dict,
    summary="Test endpoint to see Pydantic validation in action",
    tags=["Testing"]
)
async def test_validation(user: UserCreate):
    return {
        "message": "Validation passed!",
        "received": {
            "email": user.email,
            "full_name": user.full_name,
            "password_length": len(user.password)
        }
    }


@app.post("/test/validate-resume-request", tags=["Testing"])
async def test_resume_validation(request: ResumeAnalysisRequest):
    return {
        "message": "Resume request valid!",
        "job_title": request.job_title,
        "jd_word_count": len(request.job_description.split()),
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)