"""Elasticsearch resource for Dagster using shared/config/settings."""

from typing import Optional, Dict, Any
import dagster as dg
from pydantic import Field, PrivateAttr
from elasticsearch import Elasticsearch

from shared.config.settings import settings


class ElasticsearchResource(dg.ConfigurableResource):
    """
    Configurable Elasticsearch resource for search and analytics operations.

    This resource provides a get_client() method that returns an Elasticsearch client
    for search operations. Configuration is loaded via shared/config/settings
    which automatically loads environment variables from .env file.
    """

    # Connection settings (can be overridden via YAML)
    timeout: int = Field(
        default=None,
        description="Timeout in seconds for operations. Defaults to 30.",
    )

    max_retries: int = Field(
        default=None,
        description="Maximum number of retries for failed requests. Defaults to 3.",
    )

    retry_on_timeout: bool = Field(
        default=None,
        description="Whether to retry on timeout errors. Defaults to True.",
    )

    verify_certs: bool = Field(
        default=None,
        description="Whether to verify SSL certificates. Defaults to not settings.minio_secure.",
    )

    ca_certs: Optional[str] = Field(
        default=None,
        description="Path to CA certificate file.",
    )

    # Private attributes for storing client instance
    _client: Optional["Elasticsearch"] = PrivateAttr(default=None)

    def _build_connection_url(self) -> str:
        """Build Elasticsearch connection URL from settings."""
        return f"{settings.elastic_scheme}://{settings.elastic_host}:{settings.elastic_port}"

    def _get_auth_config(self) -> Dict[str, Any]:
        """Build authentication configuration for Elasticsearch client."""
        auth_config = {}
        if settings.elastic_user and settings.elastic_password:
            auth_config["http_auth"] = (
                settings.elastic_user,
                settings.elastic_password,
            )
        return auth_config

    def _get_ssl_config(self) -> Dict[str, Any]:
        """Build SSL configuration for Elasticsearch client."""
        ssl_config = {
            "verify_certs": self.verify_certs
            if self.verify_certs is not None
            else not settings.minio_secure
        }
        if self.ca_certs:
            ssl_config["ca_certs"] = self.ca_certs
        return ssl_config

    def get_client(self) -> "Elasticsearch":
        """
        Get Elasticsearch client for search operations.

        Returns:
            Elasticsearch client instance.
        """
        if self._client is None:
            client_config = {
                "hosts": settings.elastic_hosts,
                "timeout": self.timeout if self.timeout is not None else 30,
                "max_retries": self.max_retries if self.max_retries is not None else 3,
                "retry_on_timeout": self.retry_on_timeout
                if self.retry_on_timeout is not None
                else True,
                **self._get_auth_config(),
                **self._get_ssl_config(),
            }

            self._client = Elasticsearch(**client_config)

        return self._client

    def setup_for_execution(self, context: dg.InitResourceContext) -> None:
        """Initialize Elasticsearch connection when resource is set up."""
        self.get_client()

    def teardown_after_execution(self, context: dg.InitResourceContext) -> None:
        """Clean up Elasticsearch connection when resource is torn down."""
        if self._client:
            self._client.close()
            self._client = None


# Configure resource using shared/settings for configuration
elasticsearch_resource = ElasticsearchResource()
