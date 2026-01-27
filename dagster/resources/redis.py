"""Redis resource for Dagster using redis-py."""

import os
from typing import Optional
import dagster as dg
from pydantic import Field, PrivateAttr
import redis
from redis.client import Redis


class RedisResource(dg.ConfigurableResource):
    """
    Configurable Redis resource for caching and session storage.

    This resource provides a get_client() method that returns a Redis client
    for cache operations. Configuration is loaded from environment variables.

    Environment variables:
        - REDIS_URL: Full Redis connection URL
        - REDIS_HOST: Redis host (optional if REDIS_URL provided)
        - REDIS_PORT: Redis port (optional if REDIS_URL provided)
        - REDIS_DB: Redis database number (optional if REDIS_URL provided)
        - REDIS_PASSWORD: Redis password (optional)
    """

    # Redis connection configuration
    redis_url: Optional[str] = Field(
        default=None,
        description="Full Redis connection URL. If provided, other connection fields are ignored.",
    )

    host: str = Field(
        default="localhost",
        description="Redis host. Used if redis_url is not provided.",
    )

    port: int = Field(
        default=6379, description="Redis port. Used if redis_url is not provided."
    )

    db: int = Field(
        default=0,
        description="Redis database number. Used if redis_url is not provided.",
    )

    password: Optional[str] = Field(
        default=None, description="Redis password. Optional."
    )

    # Connection settings
    socket_timeout: Optional[float] = Field(
        default=5.0, description="Timeout in seconds for socket operations."
    )

    socket_connect_timeout: Optional[float] = Field(
        default=5.0, description="Timeout in seconds for connecting to Redis."
    )

    max_connections: Optional[int] = Field(
        default=None,
        description="Maximum number of connections in the connection pool.",
    )

    # Private attributes for storing client instance
    _client: Optional[Redis] = PrivateAttr(default=None)

    def _get_connection_params(self) -> dict:
        """Get connection parameters for Redis client."""
        if self.redis_url:
            return {"url": self.redis_url}

        params = {
            "host": self.host,
            "port": self.port,
            "db": self.db,
        }

        if self.password:
            params["password"] = self.password

        if self.socket_timeout:
            params["socket_timeout"] = self.socket_timeout

        if self.socket_connect_timeout:
            params["socket_connect_timeout"] = self.socket_connect_timeout

        if self.max_connections:
            params["max_connections"] = self.max_connections

        return params

    def get_client(self) -> Redis:
        """
        Get Redis client for cache operations.

        Returns:
            Redis client instance.

        Raises:
            redis.ConnectionError: If connection to Redis fails.
        """
        if self._client is None:
            connection_params = self._get_connection_params()

            if self.redis_url:
                self._client = redis.from_url(**connection_params)
            else:
                self._client = redis.Redis(**connection_params)

            # Test connection
            self._client.ping()

        return self._client

    def setup_for_execution(self, context: dg.InitResourceContext) -> None:
        """Initialize Redis connection when resource is set up."""
        # Test connection by creating client
        self.get_client()

    def teardown_after_execution(self, context: dg.InitResourceContext) -> None:
        """Clean up Redis connection when resource is torn down."""
        if self._client:
            self._client.close()
            self._client = None


# Configure resource to use environment variables by default
redis_resource = RedisResource.configure_at_launch(
    redis_url=dg.EnvVar("REDIS_URL"),
    host=dg.EnvVar("REDIS_HOST", default="localhost"),
    port=dg.EnvVar("REDIS_PORT", default="6379"),
    db=dg.EnvVar("REDIS_DB", default="0"),
    password=dg.EnvVar("REDIS_PASSWORD"),
    socket_timeout=dg.EnvVar("REDIS_SOCKET_TIMEOUT", default="5.0"),
    socket_connect_timeout=dg.EnvVar("REDIS_SOCKET_CONNECT_TIMEOUT", default="5.0"),
    max_connections=dg.EnvVar("REDIS_MAX_CONNECTIONS", default=None),
)
