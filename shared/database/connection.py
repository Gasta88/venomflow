"""
Database connection management
"""

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.ext.declarative import declarative_base
from contextlib import contextmanager
import os

# Create base class for declarative models
Base = declarative_base()


def get_connection_string() -> str:
    """
    Build PostgreSQL connection string from environment variables.
    
    Returns:
        Database connection string
    """
    user = os.getenv("POSTGRES_USER", "venomflow_user")
    password = os.getenv("POSTGRES_PASSWORD", "password")
    host = os.getenv("POSTGRES_HOST", "postgres")
    port = os.getenv("POSTGRES_PORT", "5432")
    database = os.getenv("POSTGRES_DB", "venomflow")
    
    return f"postgresql://{user}:{password}@{host}:{port}/{database}"


def create_db_engine():
    """
    Create SQLAlchemy engine.
    
    Returns:
        SQLAlchemy engine instance
    """
    connection_string = get_connection_string()
    return create_engine(
        connection_string,
        pool_pre_ping=True,
        pool_size=10,
        max_overflow=20,
    )


# Create global engine and session factory
engine = create_db_engine()
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_session() -> Session:
    """
    Get a database session.
    
    Returns:
        SQLAlchemy session
    """
    return SessionLocal()


@contextmanager
def get_db_session():
    """
    Context manager for database sessions.
    
    Yields:
        SQLAlchemy session
    """
    session = SessionLocal()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
