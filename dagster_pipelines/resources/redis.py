"""Redis resource for Dagster using shared/config/settings."""

from typing import Optional
import dagster as dg
from pydantic import Field, PrivateAttr
import redis
from redis.client import Redis

from shared.config.settings import settings


class RedisResource(dg.ConfigurableResource):
    """
    Configurable Redis resource for caching and session storage.

    This resource provides a get_client() method that returns a Redis client
    for cache operations. Configuration is loaded via shared/config/settings
    which automatically loads environment variables from .env file.
    """

    # Connection settings (can be overridden via YAML)
    socket_timeout: Optional[float] = Field(
        default=None,
        description="Timeout in seconds for socket operations. Defaults to settings.redis_socket_timeout.",
    )

    socket_connect_timeout: Optional[float] = Field(
        default=None,
        description="Timeout in seconds for connecting to Redis. Defaults to settings.redis_socket_connect_timeout.",
    )

    max_connections: Optional[int] = Field(
        default=None,
        description="Maximum number of connections in the connection pool.",
    )

    # Private attributes for storing client instance
    _client: Optional[Redis] = PrivateAttr(default=None)

    def _get_connection_params(self) -> dict:
        """Get connection parameters for Redis client."""
        return {
            "url": settings.redis_url,
            "socket_timeout": self.socket_timeout
            if self.socket_timeout is not None
            else settings.redis_socket_timeout,
            "socket_connect_timeout": self.socket_connect_timeout
            if self.socket_connect_timeout is not None
            else settings.redis_socket_connect_timeout,
            "max_connections": self.max_connections,
        }

    def get_client(self) -> Redis:
        """
        Get Redis client for cache operations.

        Returns:
            Redis client instance.
        """
        if self._client is None:
            connection_params = self._get_connection_params()
            self._client = redis.from_url(**connection_params)
            self._client.ping()
        return self._client

    def setup_for_execution(self, context: dg.InitResourceContext) -> None:
        """Initialize Redis connection when resource is set up."""
        self.get_client()

    def teardown_after_execution(self, context: dg.InitResourceContext) -> None:
        """Clean up Redis connection when resource is torn down."""
        if self._client:
            self._client.close()
            self._client = None


# Configure resource using shared/settings for configuration
redis_resource = RedisResource()
