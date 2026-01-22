"""
Database resource for Dagster pipelines
"""

from dagster import ConfigurableResource
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
import os


class DatabaseResource(ConfigurableResource):
    """
    Database connection resource for Dagster assets.
    """
    
    def get_connection_string(self) -> str:
        """Build PostgreSQL connection string from environment variables."""
        user = os.getenv("POSTGRES_USER", "venomflow_user")
        password = os.getenv("POSTGRES_PASSWORD", "password")
        host = os.getenv("POSTGRES_HOST", "postgres")
        port = os.getenv("POSTGRES_PORT", "5432")
        database = os.getenv("POSTGRES_DB", "venomflow")
        
        return f"postgresql://{user}:{password}@{host}:{port}/{database}"
    
    def get_engine(self):
        """Create SQLAlchemy engine."""
        connection_string = self.get_connection_string()
        return create_engine(connection_string)
    
    def get_session(self):
        """Get database session."""
        engine = self.get_engine()
        Session = sessionmaker(bind=engine)
        return Session()
