"""
Database session management for the Bank Command Center.
"""
import os
from sqlalchemy import create_engine, text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from app.config import settings

# Create the SQLAlchemy engine
engine = create_engine(
    settings.database_url,
    connect_args={"check_same_thread": False} if "sqlite" in settings.database_url else {},
    echo=False  # Set to True for SQL query logging
)

# Create SessionLocal class
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Create Base class for models
Base = declarative_base()


def get_db() -> Session:
    """
    Dependency function to get database session.
    Used with FastAPI's Depends() for dependency injection.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def database_exists() -> bool:
    """Check if the database exists and is accessible."""
    try:
        with SessionLocal() as db:
            # Try to execute a simple query
            db.execute(text("SELECT 1"))
            return True
    except Exception:
        return False


def is_sqlite_database() -> bool:
    """Check if the current database is SQLite."""
    return "sqlite" in settings.database_url.lower()
