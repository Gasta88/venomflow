"""
VenomFlow Configuration Settings Module

This module provides type-safe configuration management using Pydantic BaseSettings.
Environment variables are automatically loaded and validated.

Usage:
    from shared.config.settings import settings
    
    print(settings.postgres_url)
    print(settings.redis_url)
"""

from typing import List, Optional
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field, validator, PostgresDsn, RedisDsn


class Settings(BaseSettings):
    """
    Application settings loaded from environment variables.
    
    All settings are loaded from environment variables with automatic
    validation and type conversion. The .env file is automatically
    loaded if present.
    """
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore"
    )
    
    # =============================================================================
    # APPLICATION SETTINGS
    # =============================================================================
    app_name: str = Field(default="VenomFlow", description="Application name")
    app_env: str = Field(default="development", description="Environment (development, staging, production)")
    app_debug: bool = Field(default=True, description="Debug mode")
    app_log_level: str = Field(default="INFO", description="Logging level")
    
    # =============================================================================
    # POSTGRESQL DATABASE
    # =============================================================================
    postgres_host: str = Field(default="localhost", description="PostgreSQL host")
    postgres_port: int = Field(default=5432, description="PostgreSQL port")
    postgres_db: str = Field(default="venomflow", description="PostgreSQL database name")
    postgres_user: str = Field(default="venomflow_user", description="PostgreSQL username")
    postgres_password: str = Field(default="changeme", description="PostgreSQL password")
    postgres_schema: str = Field(default="public", description="PostgreSQL schema")
    
    # Connection pool settings
    postgres_pool_size: int = Field(default=20, description="Database connection pool size")
    postgres_max_overflow: int = Field(default=10, description="Max overflow connections")
    postgres_pool_timeout: int = Field(default=30, description="Pool timeout in seconds")
    
    @property
    def postgres_url(self) -> str:
        """Construct PostgreSQL connection URL."""
        return f"postgresql://{self.postgres_user}:{self.postgres_password}@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
    
    @property
    def postgres_async_url(self) -> str:
        """Construct async PostgreSQL connection URL."""
        return f"postgresql+asyncpg://{self.postgres_user}:{self.postgres_password}@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
    
    # =============================================================================
    # REDIS CACHE
    # =============================================================================
    redis_host: str = Field(default="localhost", description="Redis host")
    redis_port: int = Field(default=6379, description="Redis port")
    redis_db: int = Field(default=0, description="Redis database number")
    redis_password: Optional[str] = Field(default=None, description="Redis password")
    redis_socket_timeout: int = Field(default=5, description="Redis socket timeout")
    redis_socket_connect_timeout: int = Field(default=5, description="Redis connection timeout")
    
    @property
    def redis_url(self) -> str:
        """Construct Redis connection URL."""
        if self.redis_password:
            return f"redis://:{self.redis_password}@{self.redis_host}:{self.redis_port}/{self.redis_db}"
        return f"redis://{self.redis_host}:{self.redis_port}/{self.redis_db}"
    
    # =============================================================================
    # ELASTICSEARCH
    # =============================================================================
    elastic_host: str = Field(default="localhost", description="Elasticsearch host")
    elastic_port: int = Field(default=9200, description="Elasticsearch port")
    elastic_scheme: str = Field(default="http", description="Elasticsearch scheme (http/https)")
    elastic_user: str = Field(default="elastic", description="Elasticsearch username")
    elastic_password: str = Field(default="changeme", description="Elasticsearch password")
    elastic_index_prefix: str = Field(default="venomflow", description="Index prefix")
    
    @property
    def elastic_url(self) -> str:
        """Construct Elasticsearch connection URL."""
        return f"{self.elastic_scheme}://{self.elastic_user}:{self.elastic_password}@{self.elastic_host}:{self.elastic_port}"
    
    @property
    def elastic_hosts(self) -> List[dict]:
        """Construct Elasticsearch hosts configuration."""
        return [
            {
                "host": self.elastic_host,
                "port": self.elastic_port,
                "scheme": self.elastic_scheme,
            }
        ]
    
    # =============================================================================
    # DAGSTER ORCHESTRATION
    # =============================================================================
    dagster_home: str = Field(default="/opt/dagster/dagster_home", description="Dagster home directory")
    dagster_postgres_host: str = Field(default="localhost", description="Dagster PostgreSQL host")
    dagster_postgres_port: int = Field(default=5432, description="Dagster PostgreSQL port")
    dagster_postgres_db: str = Field(default="dagster", description="Dagster database name")
    dagster_postgres_user: str = Field(default="dagster_user", description="Dagster database user")
    dagster_postgres_password: str = Field(default="changeme", description="Dagster database password")
    
    @property
    def dagster_postgres_url(self) -> str:
        """Construct Dagster PostgreSQL connection URL."""
        return f"postgresql://{self.dagster_postgres_user}:{self.dagster_postgres_password}@{self.dagster_postgres_host}:{self.dagster_postgres_port}/{self.dagster_postgres_db}"
    
    # =============================================================================
    # FASTAPI GRAPHQL API
    # =============================================================================
    api_host: str = Field(default="0.0.0.0", description="API host")
    api_port: int = Field(default=8000, description="API port")
    api_workers: int = Field(default=4, description="Number of API workers")
    api_reload: bool = Field(default=True, description="Enable auto-reload in development")
    api_secret_key: str = Field(
        default="changeme_secret_key_at_least_32_characters",
        min_length=32,
        description="Secret key for JWT tokens"
    )
    api_access_token_expire_minutes: int = Field(
        default=30,
        description="JWT token expiration time in minutes"
    )
    
    # CORS Settings
    api_cors_origins: str = Field(
        default="http://localhost:3000,http://localhost:8000",
        description="Comma-separated list of allowed CORS origins"
    )
    
    @property
    def cors_origins_list(self) -> List[str]:
        """Parse CORS origins into a list."""
        return [origin.strip() for origin in self.api_cors_origins.split(",") if origin.strip()]
    
    # =============================================================================
    # MONITORING - PROMETHEUS
    # =============================================================================
    prometheus_port: int = Field(default=9090, description="Prometheus port")
    prometheus_retention_time: str = Field(default="15d", description="Prometheus data retention time")
    
    # =============================================================================
    # MONITORING - GRAFANA
    # =============================================================================
    grafana_port: int = Field(default=3000, description="Grafana port")
    grafana_admin_user: str = Field(default="admin", description="Grafana admin username")
    grafana_admin_password: str = Field(default="changeme", description="Grafana admin password")
    
    # =============================================================================
    # EXTERNAL APIS
    # =============================================================================
    ncbi_api_key: Optional[str] = Field(default=None, description="NCBI API key")
    ncbi_email: Optional[str] = Field(default=None, description="Email for NCBI API")
    uniprot_api_base_url: str = Field(
        default="https://rest.uniprot.org",
        description="UniProt API base URL"
    )
    pubchem_api_base_url: str = Field(
        default="https://pubchem.ncbi.nlm.nih.gov/rest/pug",
        description="PubChem API base URL"
    )
    
    # =============================================================================
    # BLAST CONFIGURATION
    # =============================================================================
    blast_db_path: str = Field(default="/data/blast/db", description="BLAST database path")
    blast_threads: int = Field(default=4, description="Number of BLAST threads")
    blast_max_target_seqs: int = Field(default=100, description="Maximum BLAST target sequences")
    
    # =============================================================================
    # DATA PROCESSING
    # =============================================================================
    batch_size: int = Field(default=100, description="Batch processing size")
    max_workers: int = Field(default=4, description="Maximum worker threads")
    enrichment_timeout_seconds: int = Field(default=300, description="Enrichment timeout in seconds")
    
    # =============================================================================
    # LOGGING
    # =============================================================================
    log_format: str = Field(default="json", description="Log format (json/text)")
    log_file_path: str = Field(default="/var/log/venomflow", description="Log file path")
    log_rotation: str = Field(default="1d", description="Log rotation interval")
    log_retention: str = Field(default="30d", description="Log retention period")
    
    # =============================================================================
    # VALIDATORS
    # =============================================================================
    @validator("app_env")
    def validate_app_env(cls, v):
        """Validate application environment."""
        allowed_envs = ["development", "staging", "production", "test"]
        if v.lower() not in allowed_envs:
            raise ValueError(f"app_env must be one of {allowed_envs}")
        return v.lower()
    
    @validator("app_log_level")
    def validate_log_level(cls, v):
        """Validate log level."""
        allowed_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
        if v.upper() not in allowed_levels:
            raise ValueError(f"app_log_level must be one of {allowed_levels}")
        return v.upper()
    
    @validator("elastic_scheme")
    def validate_elastic_scheme(cls, v):
        """Validate Elasticsearch scheme."""
        if v.lower() not in ["http", "https"]:
            raise ValueError("elastic_scheme must be 'http' or 'https'")
        return v.lower()
    
    @validator("log_format")
    def validate_log_format(cls, v):
        """Validate log format."""
        if v.lower() not in ["json", "text"]:
            raise ValueError("log_format must be 'json' or 'text'")
        return v.lower()
    
    # =============================================================================
    # COMPUTED PROPERTIES
    # =============================================================================
    @property
    def is_development(self) -> bool:
        """Check if running in development mode."""
        return self.app_env == "development"
    
    @property
    def is_production(self) -> bool:
        """Check if running in production mode."""
        return self.app_env == "production"
    
    @property
    def is_testing(self) -> bool:
        """Check if running in test mode."""
        return self.app_env == "test"
    
    def get_database_url(self, async_mode: bool = False) -> str:
        """Get database URL based on mode."""
        return self.postgres_async_url if async_mode else self.postgres_url


# =============================================================================
# GLOBAL SETTINGS INSTANCE
# =============================================================================
settings = Settings()


# =============================================================================
# SETTINGS VALIDATION
# =============================================================================
def validate_settings() -> None:
    """
    Validate that all required settings are properly configured.
    Raises ValueError if any critical setting is missing or invalid.
    """
    errors = []
    
    # Check critical database settings
    if settings.postgres_password == "changeme":
        errors.append("POSTGRES_PASSWORD must be changed from default value")
    
    # Check API secret key
    if "changeme" in settings.api_secret_key.lower():
        errors.append("API_SECRET_KEY must be changed from default value")
    
    # Check production-specific requirements
    if settings.is_production:
        if settings.app_debug:
            errors.append("APP_DEBUG must be False in production")
        
        if settings.redis_password is None or settings.redis_password == "changeme":
            errors.append("REDIS_PASSWORD must be set in production")
    
    if errors:
        raise ValueError(f"Configuration validation failed:\n" + "\n".join(f"  - {e}" for e in errors))


# =============================================================================
# EXPORTS
# =============================================================================
__all__ = ["settings", "Settings", "validate_settings"]
