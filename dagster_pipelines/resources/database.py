"""Database resource for Dagster using shared/config/settings."""

from typing import Optional
import dagster as dg
from pydantic import Field, PrivateAttr
from sqlalchemy import create_engine, Engine
from sqlalchemy.orm import sessionmaker, Session

from shared.config.settings import settings


class DatabaseResource(dg.ConfigurableResource):
    """
    Configurable database resource using SQLAlchemy for PostgreSQL connections.

    This resource provides a get_client() method that returns a SQLAlchemy engine
    for database operations. Configuration is loaded via shared/config/settings
    which automatically loads environment variables from .env file.
    """

    # Connection pool settings (can be overridden via YAML)
    pool_size: int = Field(
        default=None,
        description="Number of connections to maintain in the connection pool. Defaults to settings.postgres_pool_size.",
    )

    max_overflow: int = Field(
        default=None,
        description="Maximum number of connections that can be created beyond pool_size. Defaults to settings.postgres_max_overflow.",
    )

    # Private attributes for storing client instances
    _engine: Optional[Engine] = PrivateAttr(default=None)
    _session_factory: Optional[sessionmaker] = PrivateAttr(default=None)

    def _get_connection_url(self) -> str:
        """Get database connection URL from settings."""
        return settings.postgres_url

    def _get_pool_size(self) -> int:
        """Get pool size from resource config or settings."""
        return (
            self.pool_size
            if self.pool_size is not None
            else settings.postgres_pool_size
        )

    def _get_max_overflow(self) -> int:
        """Get max overflow from resource config or settings."""
        return (
            self.max_overflow
            if self.max_overflow is not None
            else settings.postgres_max_overflow
        )

    def get_client(self) -> Engine:
        """
        Get SQLAlchemy engine client for database operations.

        Returns:
            SQLAlchemy Engine instance configured for PostgreSQL.
        """
        if self._engine is None:
            connection_url = self._get_connection_url()
            pool_size = self._get_pool_size()
            max_overflow = self._get_max_overflow()

            self._engine = create_engine(
                connection_url,
                pool_size=pool_size,
                max_overflow=max_overflow,
                echo=settings.app_debug,
                pool_pre_ping=True,
                pool_recycle=3600,
            )

            self._session_factory = sessionmaker(bind=self._engine)

        return self._engine

    def get_session(self) -> Session:
        """
        Get SQLAlchemy session for database operations.

        Returns:
            SQLAlchemy Session instance.
        """
        if self._session_factory is None:
            self.get_client()

        return self._session_factory()

    def setup_for_execution(self, context: dg.InitResourceContext) -> None:
        """Initialize the database connection when resource is set up."""
        self.get_client()

    def teardown_after_execution(self, context: dg.InitResourceContext) -> None:
        """Clean up database connections when resource is torn down."""
        if self._engine:
            self._engine.dispose()
            self._engine = None
            self._session_factory = None


# Configure resource using shared/settings for configuration
database_resource = DatabaseResource()
