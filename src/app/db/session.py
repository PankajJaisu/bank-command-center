# database.py
import os
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from sqlalchemy.exc import OperationalError, ProgrammingError
from app.db.models import Base
from app.config import settings

# The database URL for a local SQLite file or PostgreSQL
SQLALCHEMY_DATABASE_URL = settings.database_url


# Determine database type
def is_sqlite_database():
    """Check if the configured database is SQLite."""
    return SQLALCHEMY_DATABASE_URL.startswith("sqlite")


def is_postgresql_database():
    """Check if the configured database is PostgreSQL."""
    return SQLALCHEMY_DATABASE_URL.startswith("postgresql")


def database_exists():
    """Check if the database exists and has tables."""
    try:
        if is_sqlite_database():
            # For SQLite, check if the file exists and has tables
            db_path = SQLALCHEMY_DATABASE_URL.replace("sqlite:///", "")
            if not os.path.exists(db_path):
                return False

            # Check if tables exist by trying to query one
            temp_engine = create_engine(
                SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False}
            )
            with temp_engine.connect() as conn:
                result = conn.execute(
                    text(
                        "SELECT name FROM sqlite_master WHERE type='table' AND name='invoices';"
                    )
                )
                return result.fetchone() is not None

        elif is_postgresql_database():
            # For PostgreSQL, try to connect and check if tables exist
            temp_engine = create_engine(SQLALCHEMY_DATABASE_URL)
            with temp_engine.connect() as conn:
                result = conn.execute(
                    text(
                        "SELECT EXISTS (SELECT FROM information_schema.tables WHERE table_name = 'invoices');"
                    )
                )
                return result.fetchone()[0]

        return False
    except (OperationalError, ProgrammingError, Exception):
        return False


def ensure_database_exists():
    """Ensure the database exists and create it if it doesn't."""
    if is_sqlite_database():
        # For SQLite, just ensure the directory exists
        db_path = SQLALCHEMY_DATABASE_URL.replace("sqlite:///", "")
        db_dir = os.path.dirname(db_path)
        if db_dir and not os.path.exists(db_dir):
            os.makedirs(db_dir, exist_ok=True)
        print(f"✅ SQLite database path ensured: {db_path}")

    elif is_postgresql_database():
        # For PostgreSQL, the database should already exist
        # We'll just test the connection
        try:
            temp_engine = create_engine(SQLALCHEMY_DATABASE_URL)
            with temp_engine.connect() as conn:
                conn.execute(text("SELECT 1"))
            print("✅ PostgreSQL database connection verified")
        except Exception as e:
            print(f"❌ PostgreSQL database connection failed: {e}")
            raise


# The engine is the main point of contact with the DB
if is_sqlite_database():
    engine = create_engine(
        SQLALCHEMY_DATABASE_URL,
        connect_args={
            "check_same_thread": False,
            "timeout": 30,
        },  # Set a 30-second timeout
    )
else:
    engine = create_engine(SQLALCHEMY_DATABASE_URL)

# A SessionLocal class to create DB sessions
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def create_db_and_tables():
    """Create all the tables defined in models.py."""
    try:
        print("Creating all database tables...")
        Base.metadata.create_all(bind=engine)
        print("✅ Database tables created successfully.")
    except Exception as e:
        print(f"❌ Error creating database tables: {e}")
        raise
