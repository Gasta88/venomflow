"""MinIO resource for Dagster using shared/config/settings."""

from typing import Optional
import dagster as dg
from pydantic import Field, PrivateAttr
from minio import Minio
from minio.api import Minio as MinioClient
import boto3
from botocore.client import BaseClient

from shared.config.settings import settings


class MinIOResource(dg.ConfigurableResource):
    """
    Configurable MinIO resource for object storage operations.

    This resource provides get_client() methods that return both MinIO and S3-compatible
    clients for object storage operations. Configuration is loaded via shared/config/settings
    which automatically loads environment variables from .env file.
    """

    # Connection settings (can be overridden via YAML)
    http_client: Optional[str] = Field(
        default=None,
        description="Custom HTTP client configuration (advanced usage).",
    )

    # Private attributes for storing client instances
    _minio_client: Optional[MinioClient] = PrivateAttr(default=None)
    _s3_client: Optional["BaseClient"] = PrivateAttr(default=None)

    def _build_endpoint_url(self) -> str:
        """Build complete endpoint URL."""
        protocol = "https" if settings.minio_secure else "http"
        return f"{protocol}://{settings.minio_endpoint}"

    def get_minio_client(self) -> MinioClient:
        """
        Get MinIO native client for object storage operations.

        Returns:
            MinIO client instance.
        """
        if self._minio_client is None:
            endpoint = settings.minio_endpoint.replace("http://", "").replace(
                "https://", ""
            )

            self._minio_client = Minio(
                endpoint=endpoint,
                access_key=settings.minio_access_key,
                secret_key=settings.minio_secret_key,
                secure=settings.minio_secure,
                region=settings.minio_secure,
            )

        return self._minio_client

    def get_s3_client(self) -> BaseClient:
        """
        Get S3-compatible client for object storage operations.

        Returns:
            boto3 S3 client instance.
        """
        if self._s3_client is None:
            endpoint_url = self._build_endpoint_url()

            self._s3_client = boto3.client(
                "s3",
                endpoint_url=endpoint_url,
                aws_access_key_id=settings.minio_access_key,
                aws_secret_access_key=settings.minio_secret_key,
                region_name="us-east-1",
                config=None,
            )

        return self._s3_client

    def get_client(self) -> MinioClient:
        """
        Get default MinIO client for object storage operations.

        Returns:
            MinIO client instance.
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
            client.make_bucket(bucket_name, location="us-east-1")

    def delete_bucket(self, bucket_name: str) -> None:
        """Delete bucket using MinIO client."""
        client = self.get_minio_client()
        if client.bucket_exists(bucket_name):
            client.remove_bucket(bucket_name)

    def setup_for_execution(self, context: dg.InitResourceContext) -> None:
        """Initialize MinIO connections when resource is set up."""
        self.get_minio_client()

    def teardown_after_execution(self, context: dg.InitResourceContext) -> None:
        """Clean up MinIO connections when resource is torn down."""
        self._minio_client = None
        self._s3_client = None


# Configure resource using shared/settings for configuration
minio_resource = MinIOResource()
