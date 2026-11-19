"""Shared test fixtures for VenomFlow test suite."""

from unittest.mock import MagicMock

import pytest
from dagster import build_asset_context
from sqlalchemy.orm import Session


@pytest.fixture
def mock_context():
    """Create a Dagster DirectAssetExecutionContext for asset invocation."""
    return build_asset_context()


@pytest.fixture
def mock_database_resource():
    """Create a mock DatabaseResource with session support."""
    resource = MagicMock()
    session = MagicMock(spec=Session)
    resource.get_session.return_value = session
    engine = MagicMock()
    resource.get_client.return_value = engine
    return resource


@pytest.fixture
def mock_session():
    """Create a standalone mock SQLAlchemy session."""
    return MagicMock(spec=Session)
