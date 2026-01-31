"""MinIO resource for Dagster using boto3 and minio-py."""

import os
from typing import Optional
import dagster as dg
from pydantic import Field, PrivateAttr
from minio import Minio
from minio.api import Minio as MinioClient
import boto3
from botocore.client import BaseClient


class MinIOResource(dg.ConfigurableResource):
    """
    Configurable MinIO resource for object storage operations.

    This resource provides get_client() methods that return both MinIO and S3-compatible
    clients for object storage operations. Configuration is loaded from environment variables.

    Environment variables:
        - MINIO_ENDPOINT: MinIO endpoint URL
        - MINIO_ACCESS_KEY: MinIO access key
        - MINIO_SECRET_KEY: MinIO secret key
        - MINIO_REGION: MinIO region (optional, default is 'us-east-1')
        - MINIO_SECURE: Whether to use HTTPS (optional, default is True)
    """

    # MinIO connection configuration
    endpoint: str = Field(
        description="MinIO endpoint URL (e.g., 'localhost:9000' or 'play.min.io')"
    )

    access_key: str = Field(description="MinIO access key for authentication.")

    secret_key: str = Field(description="MinIO secret key for authentication.")

    region: str = Field(
        default="us-east-1", description="MinIO region. Default is 'us-east-1'."
    )

    secure: bool = Field(
        default=True,
        description="Whether to use HTTPS (True) or HTTP (False). Default is True.",
    )

    # Connection settings
    http_client: Optional[str] = Field(
        default=None, description="Custom HTTP client configuration (advanced usage)."
    )

    # Private attributes for storing client instances
    _minio_client: Optional[MinioClient] = PrivateAttr(default=None)
    _s3_client: Optional[BaseClient] = PrivateAttr(default=None)

    def _build_endpoint_url(self) -> str:
        """Build complete endpoint URL."""
        # Remove protocol if present
        endpoint = self.endpoint.replace("http://", "").replace("https://", "")

        # Add protocol based on secure flag
        protocol = "https" if self.secure else "http"
        return f"{protocol}://{endpoint}"

    def get_minio_client(self) -> MinioClient:
        """
        Get MinIO native client for object storage operations.

        Returns:
            MinIO client instance.

        Raises:
            S3Error: If connection to MinIO fails.
        """
        if self._minio_client is None:
            # Parse endpoint (remove protocol if present)
            endpoint = self.endpoint.replace("http://", "").replace("https://", "")

            self._minio_client = Minio(
                endpoint=endpoint,
                access_key=self.access_key,
                secret_key=self.secret_key,
                secure=self.secure,
                region=self.region,
            )

            # Test connection by listing buckets
            self._minio_client.list_buckets()

        return self._minio_client

    def get_s3_client(self) -> BaseClient:
        """
        Get S3-compatible client for object storage operations.

        Returns:
            boto3 S3 client instance.

        Raises:
        ClientError: If connection to MinIO fails.
        """
        if self._s3_client is None:
            endpoint_url = self._build_endpoint_url()

            self._s3_client = boto3.client(
                "s3",
                endpoint_url=endpoint_url,
                aws_access_key_id=self.access_key,
                aws_secret_access_key=self.secret_key,
                region_name=self.region,
                config=None,  # Use default config
            )

            # Test connection by listing buckets
            self._s3_client.list_buckets()

        return self._s3_client

    def get_client(self) -> MinioClient:
        """
        Get default MinIO client for object storage operations.

        Returns:
            MinIO client instance (default client).
        """
        return self.get_minio_client()

    def bucket_exists(self, bucket_name: str) -> bool:
        """Check if bucket exists using MinIO client."""
        client = self.get_minio_client()
        return client.bucket_exists(bucket_name)

    def create_bucket(self, bucket_name: str) -> None:
        """Create bucket using MinIO client."""
        client = self.get_minio_client()
        if not client.bucket_exists(bucket_name):
            client.make_bucket(bucket_name, location=self.region)

    def delete_bucket(self, bucket_name: str) -> None:
        """Delete bucket using MinIO client."""
        client = self.get_minio_client()
        if client.bucket_exists(bucket_name):
            client.remove_bucket(bucket_name)

    def setup_for_execution(self, context: dg.InitResourceContext) -> None:
        """Initialize MinIO connections when resource is set up."""
        # Test connections by creating both clients
        self.get_minio_client()
        self.get_s3_client()

    def teardown_after_execution(self, context: dg.InitResourceContext) -> None:
        """Clean up MinIO connections when resource is torn down."""
        # MinIO client doesn't have explicit close method
        # S3 client will be cleaned up by garbage collection
        self._minio_client = None
        self._s3_client = None


# Configure resource to use environment variables by default
minio_resource = MinIOResource.configure_at_launch(
    endpoint=dg.EnvVar("MINIO_ENDPOINT"),
    access_key=dg.EnvVar("MINIO_ACCESS_KEY"),
    secret_key=dg.EnvVar("MINIO_SECRET_KEY"),
    region=dg.EnvVar("MINIO_REGION"),
    secure=dg.EnvVar("MINIO_SECURE"),
    http_client=dg.EnvVar("MINIO_HTTP_CLIENT"),
)
