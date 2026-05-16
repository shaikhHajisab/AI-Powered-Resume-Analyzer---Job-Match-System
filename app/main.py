# app/main.py — final version for Week 1

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings
from app.api.routes import resume as resume_router
from app.api.routes import auth as auth_router      # NEW

app = FastAPI(
    title=settings.APP_NAME,
    description="AI-powered resume analysis and job matching",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router.router, prefix="/auth", tags=["Auth"])
app.include_router(resume_router.router, prefix="/resume", tags=["Resume"])

@app.get("/")
async def root():
    return {"message": f"Welcome to {settings.APP_NAME}", "docs": "/docs"}

@app.get("/health")
async def health_check():
    return {"status": "healthy"}