"""Database resource for Dagster using SQLAlchemy with PostgreSQL."""

import os
from typing import Optional
import dagster as dg
from pydantic import Field, PrivateAttr
from sqlalchemy import create_engine, Engine
from sqlalchemy.orm import sessionmaker, Session


class DatabaseResource(dg.ConfigurableResource):
    """
    Configurable database resource using SQLAlchemy for PostgreSQL connections.

    This resource provides a get_client() method that returns a SQLAlchemy engine
    for database operations. Configuration is loaded from environment variables.

    Environment variables:
        - DATABASE_URL: Full PostgreSQL connection URL
        - DATABASE_HOST: Database host (optional if DATABASE_URL provided)
        - DATABASE_PORT: Database port (optional if DATABASE_URL provided)
        - DATABASE_NAME: Database name (optional if DATABASE_URL provided)
        - DATABASE_USER: Database user (optional if DATABASE_URL provided)
        - DATABASE_PASSWORD: Database password (optional if DATABASE_URL provided)
    """

    # Database connection configuration
    database_url: Optional[str] = Field(
        default=None,
        description="Full PostgreSQL connection URL. If provided, other connection fields are ignored.",
    )

    host: Optional[str] = Field(
        default="localhost",
        description="Database host. Used if database_url is not provided.",
    )

    port: int = Field(
        default=5432, description="Database port. Used if database_url is not provided."
    )

    database: Optional[str] = Field(
        default=None, description="Database name. Used if database_url is not provided."
    )

    username: Optional[str] = Field(
        default=None,
        description="Database username. Used if database_url is not provided.",
    )

    password: Optional[str] = Field(
        default=None,
        description="Database password. Used if database_url is not provided.",
    )

    # Connection pool settings
    pool_size: int = Field(
        default=5,
        description="Number of connections to maintain in the connection pool.",
    )

    max_overflow: int = Field(
        default=10,
        description="Maximum number of connections that can be created beyond pool_size.",
    )

    # Private attributes for storing client instances
    _engine: Optional[Engine] = PrivateAttr(default=None)
    _session_factory: Optional[sessionmaker] = PrivateAttr(default=None)

    def _build_connection_url(self) -> str:
        """Build database connection URL from individual components."""
        if self.database_url:
            return self.database_url

        if not all([self.database, self.username, self.password]):
            raise ValueError(
                "Either database_url or database, username, and password must be provided"
            )

        return f"postgresql://{self.username}:{self.password}@{self.host}:{self.port}/{self.database}"

    def get_client(self) -> Engine:
        """
        Get SQLAlchemy engine client for database operations.

        Returns:
            SQLAlchemy Engine instance configured for PostgreSQL.

        Raises:
            ValueError: If required configuration is missing.
        """
        if self._engine is None:
            connection_url = self._build_connection_url()

            self._engine = create_engine(
                connection_url,
                pool_size=self.pool_size,
                max_overflow=self.max_overflow,
                echo=False,  # Set to True for SQL logging in development
            )

            # Create session factory
            self._session_factory = sessionmaker(bind=self._engine)

        return self._engine

    def get_session(self) -> Session:
        """
        Get SQLAlchemy session for database operations.

        Returns:
            SQLAlchemy Session instance.
        """
        if self._session_factory is None:
            self.get_client()  # Initialize engine and session factory

        return self._session_factory()

    def setup_for_execution(self, context: dg.InitResourceContext) -> None:
        """Initialize the database connection when resource is set up."""
        # Test connection by creating the engine
        self.get_client()

        # Optionally test the connection
        with self._engine.connect() as conn:
            conn.execute("SELECT 1")

    def teardown_after_execution(self, context: dg.InitResourceContext) -> None:
        """Clean up database connections when resource is torn down."""
        if self._engine:
            self._engine.dispose()
            self._engine = None
            self._session_factory = None


# Configure resource to use environment variables by default
database_resource = DatabaseResource.configure_at_launch(
    database_url=dg.EnvVar("DATABASE_URL"),
    host=dg.EnvVar("DATABASE_HOST"),
    port=dg.EnvVar("DATABASE_PORT"),
    database=dg.EnvVar("DATABASE_NAME"),
    username=dg.EnvVar("DATABASE_USER"),
    password=dg.EnvVar("DATABASE_PASSWORD"),
    pool_size=dg.EnvVar("DATABASE_POOL_SIZE"),
    max_overflow=dg.EnvVar("DATABASE_MAX_OVERFLOW"),
)
