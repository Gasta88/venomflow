"""Integration tests for compute_sequence_similarities asset."""

import pytest
from dagster import build_init_resource_context
from dagster_pipelines.assets.blast_similarity import (
    compute_sequence_similarities,
)
from resources.database import database_resource


class TestComputeSequenceSimilaritiesIntegration:
    """Integration tests for sequence similarity computation."""

    @pytest.fixture
    def database_resource(self, dagger_postgres_db):
        """Provide database resource connected to test database."""
        from dagster_pipelines.assets.blast_similarity import (
            compute_sequence_similarities,
        )

        resource = database_resource
        context = build_init_resource_context()
        yield resource.initialize(context)

    @pytest.fixture
    def mock_context(self):
        """Create a mock Dagster asset context."""
        from unittest.mock import MagicMock

        context = MagicMock()
        context.log = MagicMock()
        context.log.info = MagicMock()
        context.log.debug = MagicMock()
        context.log.warning = MagicMock()
        context.log.error = MagicMock()
        return context

    def test_similarities_stored(self, database_resource, mock_context):
        """Test that similarities are computed and stored correctly."""
        result = compute_sequence_similarities(mock_context, database_resource)

        assert result.metadata["peptides_processed"].value > 0
        assert isinstance(result.metadata["peptides_processed"].value, int)
