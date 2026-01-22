"""
Application settings and configuration

Uses Pydantic for settings management with environment variable support.
"""

from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    """Application settings."""
    
    # Database
    postgres_host: str = "postgres"
    postgres_port: int = 5432
    postgres_db: str = "venomflow"
    postgres_user: str = "venomflow_user"
    postgres_password: str = "password"
    
    # Redis
    redis_host: str = "redis"
    redis_port: int = 6379
    
    # API
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    api_debug: bool = True
    api_reload: bool = True
    
    # External APIs
    uniprot_api_base: str = "https://rest.uniprot.org"
    ncbi_api_key: Optional[str] = None
    
    # Application
    log_level: str = "INFO"
    environment: str = "development"
    
    class Config:
        """Pydantic config."""
        env_file = ".env"
        case_sensitive = False


# Global settings instance
settings = Settings()
