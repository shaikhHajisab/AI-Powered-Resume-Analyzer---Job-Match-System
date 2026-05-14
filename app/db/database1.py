# app/db/database.py

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, DeclarativeBase
from app.core.config import settings

# engine = the connection to PostgreSQL
# pool_pre_ping checks if connection is alive before using it
# echo=True prints SQL queries in terminal (good for learning/debugging)
engine = create_engine(
    settings.DATABASE_URL,
    pool_pre_ping=True,
    echo=settings.DEBUG
)

# SessionLocal is a class that creates sessions
# one session = one transaction with the database
SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine
)

# All models inherit from Base
# Base tracks all table definitions → Alembic uses this
class Base(DeclarativeBase):
    pass