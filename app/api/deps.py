# app/api/deps.py

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session
from app.db.deps import get_db
from app.core.security import decode_access_token
from app.models.user import User

# OAuth2PasswordBearer tells FastAPI:
# "look for a Bearer token in the Authorization header"
# tokenUrl is where clients go to GET a token (our login endpoint)
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")


def get_current_user(
    token: str = Depends(oauth2_scheme),  # extracts token from header automatically
    db: Session = Depends(get_db)
) -> User:
    """
    Dependency that any endpoint can use.
    Extracts token → decodes it → loads user from DB → returns user object.
    Raises 401 if anything goes wrong.
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid or expired token",
        headers={"WWW-Authenticate": "Bearer"},  # standard header for 401
    )

    payload = decode_access_token(token)
    if payload is None:
        raise credentials_exception

    user_id: int = payload.get("user_id")
    if user_id is None:
        raise credentials_exception

    user = db.query(User).filter(User.id == user_id).first()
    if user is None:
        raise credentials_exception

    if not user.is_active:
        raise HTTPException(status_code=400, detail="Inactive user")

    return user  # endpoint receives this User object directly