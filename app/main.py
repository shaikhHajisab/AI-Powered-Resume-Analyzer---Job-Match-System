# app/main.py — final complete version

from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from app.core.config import settings
from app.api.routes import resume as resume_router
from app.api.routes import auth as auth_router

from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from app.core.config import settings
from app.api.routes import resume as resume_router
from app.api.routes import auth as auth_router

@asynccontextmanager
async def lifespan(app: FastAPI):
    # runs on startup
    print("Starting up...")
    try:
        from app.services.vector_store import load_index
        load_index()
        print("Vector store ready")
    except Exception as e:
        # don't crash app if FAISS fails — just log it
        print(f"Vector store failed to load: {e}")

    yield  # app runs here

    # runs on shutdown
    print("Shutting down...")

app = FastAPI(
    title=settings.APP_NAME,
    description="AI-powered resume analysis and job matching",
    version="1.0.0",
    lifespan=lifespan, 
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# catches Pydantic validation errors (422)
# default FastAPI error is verbose — this makes it cleaner
@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    errors = []
    for error in exc.errors():
        errors.append({
            "field": " → ".join(str(x) for x in error["loc"]),
            "message": error["msg"]
        })
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={"detail": "Validation failed", "errors": errors}
    )


# catches any unhandled exception — prevents raw tracebacks reaching the user
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error", "type": type(exc).__name__}
    )


app.include_router(auth_router.router, prefix="/auth", tags=["Auth"])
app.include_router(resume_router.router, prefix="/resume", tags=["Resume"])


@app.get("/")
async def root():
    return {"message": f"Welcome to {settings.APP_NAME}", "docs": "/docs"}


@app.get("/health")
async def health_check():
    return {"status": "healthy"}