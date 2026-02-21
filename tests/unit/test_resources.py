"""Unit tests for Dagster resource definitions."""

import pytest
from unittest.mock import patch, MagicMock

from dagster_pipelines.resources.database import DatabaseResource
from dagster_pipelines.resources.elasticsearch import ElasticsearchResource
from dagster_pipelines.resources.redis import RedisResource


class TestDatabaseResource:
    """Test DatabaseResource configuration."""

    def test_default_pool_settings(self):
        resource = DatabaseResource()
        assert resource.pool_size is None
        assert resource.max_overflow is None

    @patch("dagster_pipelines.resources.database.create_engine")
    @patch("dagster_pipelines.resources.database.sessionmaker")
    def test_get_client_creates_engine(self, mock_sessionmaker, mock_create_engine):
        resource = DatabaseResource()
        engine = resource.get_client()
        mock_create_engine.assert_called_once()
        assert engine is mock_create_engine.return_value

    @patch("dagster_pipelines.resources.database.create_engine")
    @patch("dagster_pipelines.resources.database.sessionmaker")
    def test_get_client_singleton(self, mock_sessionmaker, mock_create_engine):
        resource = DatabaseResource()
        e1 = resource.get_client()
        e2 = resource.get_client()
        assert e1 is e2
        mock_create_engine.assert_called_once()

    @patch("dagster_pipelines.resources.database.create_engine")
    @patch("dagster_pipelines.resources.database.sessionmaker")
    def test_get_session(self, mock_sessionmaker, mock_create_engine):
        resource = DatabaseResource()
        session = resource.get_session()
        assert session is mock_sessionmaker.return_value.return_value

    @patch("dagster_pipelines.resources.database.create_engine")
    @patch("dagster_pipelines.resources.database.sessionmaker")
    def test_teardown_disposes_engine(self, mock_sessionmaker, mock_create_engine):
        resource = DatabaseResource()
        resource.get_client()
        resource.teardown_after_execution(MagicMock())
        mock_create_engine.return_value.dispose.assert_called_once()


class TestElasticsearchResource:
    """Test ElasticsearchResource configuration."""

    def test_default_settings(self):
        resource = ElasticsearchResource()
        assert resource.timeout is None
        assert resource.max_retries is None
        assert resource.retry_on_timeout is None

    @patch("dagster_pipelines.resources.elasticsearch.Elasticsearch")
    def test_get_client_creates_client(self, mock_es_cls):
        resource = ElasticsearchResource()
        client = resource.get_client()
        mock_es_cls.assert_called_once()
        assert client is mock_es_cls.return_value

    @patch("dagster_pipelines.resources.elasticsearch.Elasticsearch")
    def test_get_client_singleton(self, mock_es_cls):
        resource = ElasticsearchResource()
        c1 = resource.get_client()
        c2 = resource.get_client()
        assert c1 is c2
        mock_es_cls.assert_called_once()

    @patch("dagster_pipelines.resources.elasticsearch.Elasticsearch")
    def test_teardown_closes_client(self, mock_es_cls):
        resource = ElasticsearchResource()
        resource.get_client()
        resource.teardown_after_execution(MagicMock())
        mock_es_cls.return_value.close.assert_called_once()


class TestRedisResource:
    """Test RedisResource configuration."""

    def test_default_settings(self):
        resource = RedisResource()
        assert resource.socket_timeout is None
        assert resource.max_connections is None

    @patch("dagster_pipelines.resources.redis.redis.from_url")
    def test_get_client_creates_connection(self, mock_from_url):
        resource = RedisResource()
        client = resource.get_client()
        mock_from_url.assert_called_once()
        mock_from_url.return_value.ping.assert_called_once()

    @patch("dagster_pipelines.resources.redis.redis.from_url")
    def test_teardown_closes_client(self, mock_from_url):
        resource = RedisResource()
        resource.get_client()
        resource.teardown_after_execution(MagicMock())
        mock_from_url.return_value.close.assert_called_once()
