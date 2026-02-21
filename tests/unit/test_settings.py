"""Unit tests for shared settings configuration."""

import pytest

from shared.config.settings import Settings


class TestSettings:
    """Test Settings pydantic model."""

    def test_default_values(self):
        s = Settings()
        assert s.app_name == "VenomFlow"
        assert s.app_env == "development"
        assert s.app_debug is True
        assert s.postgres_port == 5432
        assert s.redis_port == 6379
        assert s.elastic_port == 9200

    def test_postgres_url(self):
        s = Settings()
        url = s.postgres_url
        assert url.startswith("postgresql://")
        assert "venomflow" in url

    def test_postgres_async_url(self):
        s = Settings()
        url = s.postgres_async_url
        assert url.startswith("postgresql+asyncpg://")

    def test_redis_url_without_password(self):
        s = Settings(redis_password=None)
        url = s.redis_url
        assert url.startswith("redis://")
        assert "@" not in url.split("//")[1]

    def test_redis_url_with_password(self):
        s = Settings(redis_password="secret")
        url = s.redis_url
        assert ":secret@" in url

    def test_elastic_url(self):
        s = Settings()
        url = s.elastic_url
        assert "elastic" in url
        assert "9200" in url

    def test_elastic_hosts(self):
        # Test elastic_hosts property returns correctly formatted list
        s = Settings(elastic_host="localhost", elastic_port=9200)
        hosts = s.elastic_hosts
        assert isinstance(hosts, list)
        assert len(hosts) == 1
        assert hosts[0]["host"] == "localhost"
        assert hosts[0]["port"] == 9200

    def test_cors_origins_list(self):
        s = Settings(api_cors_origins="http://a.com,http://b.com")
        origins = s.cors_origins_list
        assert origins == ["http://a.com", "http://b.com"]

    def test_is_development(self):
        s = Settings(app_env="development")
        assert s.is_development is True
        assert s.is_production is False
        assert s.is_testing is False

    def test_is_production(self):
        s = Settings(app_env="production")
        assert s.is_production is True

    def test_is_testing(self):
        s = Settings(app_env="test")
        assert s.is_testing is True

    def test_get_database_url(self):
        s = Settings()
        assert "asyncpg" not in s.get_database_url(async_mode=False)
        assert "asyncpg" in s.get_database_url(async_mode=True)


class TestSettingsValidators:
    """Test settings field validators."""

    def test_invalid_app_env_raises(self):
        with pytest.raises(Exception):
            Settings(app_env="invalid_env")

    def test_invalid_log_level_raises(self):
        with pytest.raises(Exception):
            Settings(app_log_level="INVALID")

    def test_invalid_elastic_scheme_raises(self):
        with pytest.raises(Exception):
            Settings(elastic_scheme="ftp")

    def test_invalid_log_format_raises(self):
        with pytest.raises(Exception):
            Settings(log_format="xml")

    def test_valid_log_levels(self):
        for level in ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]:
            s = Settings(app_log_level=level)
            assert s.app_log_level == level
