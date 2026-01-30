"""Elasticsearch resource for Dagster using elasticsearch-py."""

import os
from typing import Optional, Dict, Any
import dagster as dg
from pydantic import Field, PrivateAttr
from elasticsearch import Elasticsearch
from elasticsearch.client import ElasticsearchClient


class ElasticsearchResource(dg.ConfigurableResource):
    """
    Configurable Elasticsearch resource for search and analytics operations.

    This resource provides a get_client() method that returns an Elasticsearch client
    for search operations. Configuration is loaded from environment variables.

    Environment variables:
        - ELASTICSEARCH_URL: Elasticsearch connection URL (multiple URLs separated by commas)
        - ELASTICSEARCH_HOST: Elasticsearch host (optional if ELASTICSEARCH_URL provided)
        - ELASTICSEARCH_PORT: Elasticsearch port (optional if ELASTICSEARCH_URL provided)
        - ELASTICSEARCH_USERNAME: Elasticsearch username (optional)
        - ELASTICSEARCH_PASSWORD: Elasticsearch password (optional)
        - ELASTICSEARCH_API_KEY: Elasticsearch API key (optional, alternative to username/password)
    """

    # Elasticsearch connection configuration
    elasticsearch_url: Optional[str] = Field(
        default=None,
        description="Elasticsearch connection URL. Can be single URL or comma-separated list. If provided, other connection fields are ignored.",
    )

    hosts: Optional[str] = Field(
        default=None,
        description="Elasticsearch host(s). Can be single host or comma-separated list. Used if elasticsearch_url is not provided.",
    )

    port: Optional[int] = Field(
        default=9200,
        description="Elasticsearch port. Used if elasticsearch_url is not provided and hosts is a single host.",
    )

    username: Optional[str] = Field(
        default=None, description="Elasticsearch username for authentication."
    )

    password: Optional[str] = Field(
        default=None, description="Elasticsearch password for authentication."
    )

    api_key: Optional[str] = Field(
        default=None,
        description="Elasticsearch API key for authentication (alternative to username/password).",
    )

    # Connection settings
    timeout: int = Field(default=30, description="Timeout in seconds for operations.")

    max_retries: int = Field(
        default=3, description="Maximum number of retries for failed requests."
    )

    retry_on_timeout: bool = Field(
        default=True, description="Whether to retry on timeout errors."
    )

    verify_certs: bool = Field(
        default=True, description="Whether to verify SSL certificates."
    )

    ca_certs: Optional[str] = Field(
        default=None, description="Path to CA certificate file."
    )

    # Private attributes for storing client instance
    _client: Optional[ElasticsearchClient] = PrivateAttr(default=None)

    def _build_hosts_config(self) -> list:
        """Build hosts configuration for Elasticsearch client."""
        if self.elasticsearch_url:
            # Split comma-separated URLs
            urls = [url.strip() for url in self.elasticsearch_url.split(",")]
            return [
                {
                    "host": url.replace("http://", "")
                    .replace("https://", "")
                    .split(":")[0],
                    "url": url,
                }
                for url in urls
            ]

        if self.hosts:
            # Handle comma-separated hosts
            host_list = [host.strip() for host in self.hosts.split(",")]
            if len(host_list) == 1:
                # Single host with port
                return [{"host": host_list[0], "port": self.port}]
            else:
                # Multiple hosts (assumed to include ports or use default)
                hosts_config = []
                for host in host_list:
                    if ":" in host:
                        host_name, host_port = host.rsplit(":", 1)
                        hosts_config.append({"host": host_name, "port": int(host_port)})
                    else:
                        hosts_config.append({"host": host, "port": self.port})
                return hosts_config

        # Default configuration
        return [{"host": "localhost", "port": 9200}]

    def _build_auth_config(self) -> Dict[str, Any]:
        """Build authentication configuration for Elasticsearch client."""
        auth_config = {}

        if self.api_key:
            auth_config["api_key"] = self.api_key
        elif self.username and self.password:
            auth_config["http_auth"] = (self.username, self.password)

        return auth_config

    def _build_ssl_config(self) -> Dict[str, Any]:
        """Build SSL configuration for Elasticsearch client."""
        ssl_config = {"verify_certs": self.verify_certs}

        if self.ca_certs:
            ssl_config["ca_certs"] = self.ca_certs

        return ssl_config

    def get_client(self) -> ElasticsearchClient:
        """
        Get Elasticsearch client for search operations.

        Returns:
            Elasticsearch client instance.

        Raises:
            ConnectionError: If connection to Elasticsearch fails.
        """
        if self._client is None:
            hosts = self._build_hosts_config()
            auth_config = self._build_auth_config()
            ssl_config = self._build_ssl_config()

            # Build client configuration
            client_config = {
                "hosts": hosts,
                "timeout": self.timeout,
                "max_retries": self.max_retries,
                "retry_on_timeout": self.retry_on_timeout,
                **auth_config,
                **ssl_config,
            }

            self._client = Elasticsearch(**client_config)

            # Test connection
            if not self._client.ping():
                raise ConnectionError("Failed to connect to Elasticsearch")

        return self._client

    def setup_for_execution(self, context: dg.InitResourceContext) -> None:
        """Initialize Elasticsearch connection when resource is set up."""
        # Test connection by creating client
        self.get_client()

    def teardown_after_execution(self, context: dg.InitResourceContext) -> None:
        """Clean up Elasticsearch connection when resource is torn down."""
        if self._client:
            self._client.close()
            self._client = None


# Configure resource to use environment variables by default
elasticsearch_resource = ElasticsearchResource.configure_at_launch(
    elasticsearch_url=dg.EnvVar("ELASTICSEARCH_URL"),
    hosts=dg.EnvVar("ELASTICSEARCH_HOST"),
    port=dg.EnvVar("ELASTICSEARCH_PORT", default="9200"),
    username=dg.EnvVar("ELASTICSEARCH_USERNAME"),
    password=dg.EnvVar("ELASTICSEARCH_PASSWORD"),
    api_key=dg.EnvVar("ELASTICSEARCH_API_KEY"),
    timeout=dg.EnvVar("ELASTICSEARCH_TIMEOUT", default="30"),
    max_retries=dg.EnvVar("ELASTICSEARCH_MAX_RETRIES", default="3"),
    retry_on_timeout=dg.EnvVar("ELASTICSEARCH_RETRY_ON_TIMEOUT", default="true"),
    verify_certs=dg.EnvVar("ELASTICSEARCH_VERIFY_CERTS", default="true"),
    ca_certs=dg.EnvVar("ELASTICSEARCH_CA_CERTS"),
)
