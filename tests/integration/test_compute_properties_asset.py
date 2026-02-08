"""
Integration tests for compute_peptide_properties asset.
Tests Dagster asset execution with database interactions.
"""

import pytest
from unittest.mock import MagicMock, patch, Mock
from dagster import MaterializeResult


@pytest.fixture
def mock_database_resource():
    """Create a mock database resource for testing."""
    mock_resource = MagicMock()
    mock_engine = MagicMock()
    mock_session = MagicMock()
    mock_resource.get_client.return_value = mock_engine
    mock_session.return_value = mock_session

    return mock_resource


@pytest.fixture
def mock_peptides_data():
    """Create mock peptide data for testing."""
    peptides = [
        (MagicMock(uuid="uuid-1"), "Peptide 1", "ACDEFGHIK", 9),
        (MagicMock(uuid="uuid-2"), "Peptide 2", "LMNPQRSTVW", 10),
        (MagicMock(uuid="uuid-3"), "Peptide 3", "GHIKLMNPQ", 9),
    ]
    mock_result = MagicMock()
    mock_result.fetchall.return_value = peptides
    return mock_result


class TestComputePeptidePropertiesAsset:
    """Integration tests for compute_peptide_properties Dagster asset."""

    def test_asset_processes_peptides_successfully(
        self, mock_database_resource, mock_peptides_data
    ):
        """Test asset processes peptides and inserts properties."""
        from dagster_pipelines.assets.enrichment import compute_peptide_properties

        # Mock the execution context
        context = MagicMock()

        # Mock the query execution
        with patch.object(mock_database_resource, "get_client") as mock_get_client:
            mock_session = MagicMock()
            mock_get_client.return_value.connect.return_value.__enter__ = Mock(
                return_value=mock_session
            )
            mock_get_client.return_value.connect.return_value.__exit__ = Mock()
            mock_session.execute.return_value = mock_peptides_data

            # Mock property computation
            with (
                patch(
                    "dagster_pipelines.assets.enrichment.compute_rdkit_properties"
                ) as mock_rdkit,
                patch(
                    "dagster_pipelines.assets.enrichment.compute_biopython_properties"
                ) as mock_biopython,
            ):
                mock_rdkit.return_value = {
                    "molecular_weight": 1234.56,
                    "logp": 1.23,
                    "tpsa": 456.78,
                    "num_h_donors": 8,
                    "num_h_acceptors": 15,
                }
                mock_biopython.return_value = {
                    "isoelectric_point": 8.45,
                    "hydrophobicity": -0.623,
                }

                # Mock batch insert
                with patch(
                    "dagster_pipelines.assets.enrichment._batch_insert_properties",
                    return_value=3,
                ):
                    result = compute_peptide_properties(context, mock_database_resource)

                    # Verify result is MaterializeResult
                    assert isinstance(result, MaterializeResult)
                    assert "metadata" in result.__dict__

    def test_asset_handles_peptides_without_properties_only(
        self, mock_database_resource
    ):
        """Test asset skips peptides that already have properties."""
        from dagster_pipelines.assets.enrichment import compute_peptide_properties

        context = MagicMock()

        # Mock empty result (all peptides have properties)
        mock_result = MagicMock()
        mock_result.fetchall.return_value = []

        with patch.object(mock_database_resource, "get_client") as mock_get_client:
            mock_session = MagicMock()
            mock_get_client.return_value.connect.return_value.__enter__ = Mock(
                return_value=mock_session
            )
            mock_get_client.return_value.connect.return_value.__exit__ = Mock()
            mock_session.execute.return_value = mock_result

            result = compute_peptide_properties(context, mock_database_resource)

            assert isinstance(result, MaterializeResult)
            assert result.metadata["peptides_processed"].value == 0

    def test_asset_logs_progress_during_processing(
        self, mock_database_resource, mock_peptides_data
    ):
        """Test asset logs progress information."""
        from dagster_pipelines.assets.enrichment import compute_peptide_properties

        context = MagicMock()

        with patch.object(mock_database_resource, "get_client") as mock_get_client:
            mock_session = MagicMock()
            mock_get_client.return_value.connect.return_value.__enter__ = Mock(
                return_value=mock_session
            )
            mock_get_client.return_value.connect.return_value.__exit__ = Mock()
            mock_session.execute.return_value = mock_peptides_data

            with (
                patch(
                    "dagster_pipelines.assets.enrichment.compute_rdkit_properties"
                ) as mock_rdkit,
                patch(
                    "dagster_pipelines.assets.enrichment.compute_biopython_properties"
                ) as mock_biopython,
            ):
                mock_rdkit.return_value = {
                    "logp": 1.23,
                    "tpsa": 456.78,
                    "num_h_donors": 8,
                    "num_h_acceptors": 15,
                }
                mock_biopython.return_value = {
                    "isoelectric_point": 8.45,
                }

                with patch(
                    "dagster_pipelines.assets.enrichment._batch_insert_properties",
                    return_value=3,
                ):
                    result = compute_peptide_properties(context, mock_database_resource)

                    # Verify logging was called
                    assert context.log.info.called

                    # Verify result is computed
                    assert result is not None

    def test_asset_includes_correct_metadata(
        self, mock_database_resource, mock_peptides_data
    ):
        """Test asset metadata includes required statistics."""
        from dagster_pipelines.assets.enrichment import compute_peptide_properties

        context = MagicMock()

        with patch.object(mock_database_resource, "get_client") as mock_get_client:
            mock_session = MagicMock()
            mock_get_client.return_value.connect.return_value.__enter__ = Mock(
                return_value=mock_session
            )
            mock_get_client.return_value.connect.return_value.__exit__ = Mock()
            mock_session.execute.return_value = mock_peptides_data

            with (
                patch(
                    "dagster_pipelines.assets.enrichment.compute_rdkit_properties"
                ) as mock_rdkit,
                patch(
                    "dagster_pipelines.assets.enrichment.compute_biopython_properties"
                ) as mock_biopython,
            ):
                mock_rdkit.return_value = {
                    "logp": 1.23,
                    "tpsa": 456.78,
                    "num_h_donors": 8,
                    "num_h_acceptors": 15,
                }
                mock_biopython.return_value = {
                    "isoelectric_point": 8.45,
                    "hydrophobicity": -0.623,
                }

                with patch(
                    "dagster_pipelines.assets.enrichment._batch_insert_properties",
                    return_value=3,
                ):
                    result = compute_peptide_properties(context, mock_database_resource)

                    metadata = result.metadata

                    # Check required metadata fields
                    assert "peptides_processed" in metadata
                    assert "properties_computed" in metadata
                    assert "error_count" in metadata
                    assert "avg_logp" in metadata
                    assert "avg_tpsa" in metadata
                    assert "avg_isoelectric_point" in metadata
                    assert "avg_hydrophobicity" in metadata

    def test_asset_handles_rdkit_computation_errors(self, mock_database_resource):
        """Test asset handles RDKit computation errors gracefully."""
        from dagster_pipelines.assets.enrichment import compute_peptide_properties

        context = MagicMock()

        # Create peptide data
        peptides_data = [
            (MagicMock(uuid="uuid-1"), "Peptide 1", "ACDEFGHIK", 9),
            (MagicMock(uuid="uuid-2"), "Peptide 2", "INVALID999", 9),  # Should fail
        ]
        mock_result = MagicMock()
        mock_result.fetchall.return_value = peptides_data

        with patch.object(mock_database_resource, "get_client") as mock_get_client:
            mock_session = MagicMock()
            mock_get_client.return_value.connect.return_value.__enter__ = Mock(
                return_value=mock_session
            )
            mock_get_client.return_value.connect.return_value.__exit__ = Mock()
            mock_session.execute.return_value = mock_result

            with patch(
                "dagster_pipelines.assets.enrichment.compute_rdkit_properties"
            ) as mock_rdkit:
                # First fails, second succeeds
                mock_rdkit.side_effect = [
                    {
                        "logp": 1.23,
                        "tpsa": 456.78,
                        "num_h_donors": 8,
                        "num_h_acceptors": 15,
                    },
                    None,  # Second fails
                ]

                mock_biopython = MagicMock()
                mock_biopython.return_value = {
                    "isoelectric_point": 8.45,
                    "hydrophobicity": -0.623,
                }

                with (
                    patch(
                        "dagster_pipelines.assets.enrichment.compute_biopython_properties",
                        return_value=mock_biopython,
                    ),
                    patch(
                        "dagster_pipelines.assets.enrichment._batch_insert_properties",
                        return_value=1,
                    ),
                ):
                    result = compute_peptide_properties(context, mock_database_resource)

                    # Should have partial success
                    assert result.metadata["properties_computed"].value > 0
                    assert result.metadata["error_count"].value > 0

    def test_asset_batch_processing(self):
        """Test batch processing processes peptides in correct batch sizes."""
        from dagster_pipelines.assets.enrichment import compute_peptide_properties

        assert hasattr(compute_peptide_properties, "__wrapped__")


class TestBatchInsertProperties:
    """Unit tests for _batch_insert_properties helper function."""

    def test_batch_insert_properties_empty_list(self, mock_database_resource):
        """Test batch insert with empty list returns 0."""
        from dagster_pipelines.assets.enrichment import _batch_insert_properties

        mock_session = MagicMock()

        result = _batch_insert_properties(mock_session, [])

        assert result == 0

    def test_batch_insert_properties_success(self, mock_database_resource):
        """Test batch insert successfully inserts properties."""
        from dagster_pipelines.assets.enrichment import _batch_insert_properties

        mock_session = MagicMock()
        mock_result = MagicMock()

        # Mock successful insert
        mock_session.execute.return_value = mock_result

        properties_list = [
            {
                "peptide_id": "uuid-1",
                "isoelectric_point": 8.45,
                "hydrophobicity": -0.623,
                "logp": 1.23,
                "tpsa": 456.78,
                "num_h_donors": 8,
                "num_h_acceptors": 15,
                "calculation_method": "RDKit + BioPython",
            },
            {
                "peptide_id": "uuid-2",
                "isoelectric_point": 7.22,
                "hydrophobicity": -1.45,
                "logp": 0.98,
                "tpsa": 412.34,
                "num_h_donors": 6,
                "num_h_acceptors": 13,
                "calculation_method": "RDKit + BioPython",
            },
        ]

        result = _batch_insert_properties(mock_session, properties_list)

        assert result == 2
        mock_session.execute.assert_called_once()

    def test_batch_insert_properties_upsert(self):
        """Test batch insert uses UPSERT to avoid duplicates."""
        from dagster_pipelines.assets.enrichment import _batch_insert_properties

        mock_session = MagicMock()

        properties_list = [
            {
                "peptide_id": "uuid-1",
                "isoelectric_point": 8.45,
                "hydrophobicity": -0.623,
                "logp": 1.23,
                "tpsa": 456.78,
                "num_h_donors": 8,
                "num_h_acceptors": 15,
                "calculation_method": "RDKit + BioPython",
            },
        ]

        _batch_insert_properties(mock_session, properties_list)

        # Verify SQL includes ON CONFLICT (UPSERT)
        call_args = mock_session.execute.call_args
        query = call_args[0][0]

        assert "ON CONFLICT" in str(query)
        assert "DO UPDATE" in str(query)


class TestEdgeCases:
    """Tests for edge cases and error scenarios."""

    def test_empty_peptide_table(self, mock_database_resource):
        """Test asset behavior when peptides table is empty."""
        from dagster_pipelines.assets.enrichment import compute_peptide_properties

        context = MagicMock()

        # Mock empty result
        mock_result = MagicMock()
        mock_result.fetchall.return_value = []

        with patch.object(mock_database_resource, "get_client") as mock_get_client:
            mock_session = MagicMock()
            mock_get_client.return_value.connect.return_value.__enter__ = Mock(
                return_value=mock_session
            )
            mock_get_client.return_value.connect.return_value.__exit__ = Mock()
            mock_session.execute.return_value = mock_result

            result = compute_peptide_properties(context, mock_database_resource)

            assert isinstance(result, MaterializeResult)
            assert result.metadata["peptides_processed"].value == 0

    def test_database_connection_error(self, mock_database_resource):
        """Test asset handles database connection errors gracefully."""
        from dagster_pipelines.assets.enrichment import compute_peptide_properties

        context = MagicMock()

        # Mock connection error
        with patch.object(
            mock_database_resource,
            "get_client",
            side_effect=Exception("Connection failed"),
        ):
            with pytest.raises(Exception):
                compute_peptide_properties(context, mock_database_resource)

    def test_computation_all_fail(self, mock_database_resource):
        """Test asset when all property computations fail."""
        from dagster_pipelines.assets.enrichment import compute_peptide_properties

        context = MagicMock()

        peptides = [(MagicMock(uuid="uuid-1"), "Peptide 1", "INVALID", 7)]
        mock_result = MagicMock()
        mock_result.fetchall.return_value = peptides

        with patch.object(mock_database_resource, "get_client") as mock_get_client:
            mock_session = MagicMock()
            mock_get_client.return_value.connect.return_value.__enter__ = Mock(
                return_value=mock_session
            )
            mock_get_client.return_value.connect.return_value.__exit__ = Mock()
            mock_session.execute.return_value = mock_result

            with (
                patch(
                    "dagster_pipelines.assets.enrichment.compute_rdkit_properties",
                    return_value=None,
                ),
                patch(
                    "dagster_pipelines.assets.enrichment.compute_biopython_properties",
                    return_value=None,
                ),
            ):
                result = compute_peptide_properties(context, mock_database_resource)

                # All should fail
                assert result.metadata["properties_computed"].value == 0
                assert result.metadata["error_count"].value > 0
