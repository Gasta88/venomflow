"""
Dagster Resources Module

This module provides configurable resources for external services used in data pipelines.
Resources implement dependency injection with proper lifecycle management and are
configured via environment variables.

Available Resources:
- DatabaseResource: PostgreSQL connection using SQLAlchemy
- RedisResource: Redis client for caching and session storage
- ElasticsearchResource: Elasticsearch client for search and analytics
- MinIOResource: MinIO/S3 client for object storage

Usage Example:
    from dagster import asset, Definitions
    from dagster_pipelines.resources import (
        database_resource,
        redis_resource,
        elasticsearch_resource,
        minio_resource
    )

    @asset
    def my_data_asset(database: DatabaseResource):
        engine = database.get_client()
        # Use database connection...

    defs = Definitions(
        assets=[my_data_asset],
        resources={
            "database": database_resource,
            "redis": redis_resource,
            "elasticsearch": elasticsearch_resource,
            "minio": minio_resource,
        }
    )
"""

from .database import DatabaseResource, database_resource
from .redis import RedisResource, redis_resource
from .elasticsearch import ElasticsearchResource, elasticsearch_resource
from .minio import MinIOResource, minio_resource

__all__ = [
    "DatabaseResource",
    "database_resource",
    "RedisResource",
    "redis_resource",
    "ElasticsearchResource",
    "elasticsearch_resource",
    "MinIOResource",
    "minio_resource",
]
