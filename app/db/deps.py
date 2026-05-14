
from sqlalchemy.orm import Session
from app.db.database import SessionLocal

def get_db():
    db = SessionLocal()   # open a session
    try:
        yield db          # give it to the endpoint
    finally:
        db.close()  