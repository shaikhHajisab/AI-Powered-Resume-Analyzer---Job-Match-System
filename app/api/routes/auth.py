# app/api/routes/auth.py
from app.api.deps import get_current_user

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from datetime import timedelta

from app.db.deps import get_db
from app.models.user import User
from app.schemas.user import UserCreate, UserResponse, Token
from app.core.security import hash_password, verify_password, create_access_token
from app.core.config import settings

router = APIRouter()


@router.post("/register", response_model=UserResponse, status_code=201)
async def register(user_data: UserCreate, db: Session = Depends(get_db)):
    # check if email already exists
    existing = db.query(User).filter(User.email == user_data.email).first()
    if existing:
        raise HTTPException(
            status_code=400,
            detail="Email already registered"
        )

    # create user with HASHED password — never store plain text
    user = User(
        email=user_data.email,
        hashed_password=hash_password(user_data.password),
        full_name=user_data.full_name,
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    return user  # Pydantic UserResponse schema strips out hashed_password


@router.post("/login", response_model=Token)
async def login(
    # OAuth2PasswordRequestForm is a FastAPI built-in
    # It expects form fields: username + password (not JSON)
    # This is the OAuth2 standard — username field holds the email
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db)
):
    # find user by email (form_data.username holds the email)
    user = db.query(User).filter(User.email == form_data.username).first()

    # same error for "user not found" and "wrong password"
    # never tell attackers which one failed — that's information leakage
    if not user or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # create token with user_id in payload
    token = create_access_token(
        data={"user_id": user.id},
        expires_delta=timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    )

    return {"access_token": token, "token_type": "bearer"}


@router.get("/me", response_model=UserResponse)
async def get_me(current_user: User = Depends(get_current_user)):
    return current_user