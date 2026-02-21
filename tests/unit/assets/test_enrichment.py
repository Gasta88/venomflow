"""Unit tests for enrichment asset and helpers."""

import pytest
from unittest.mock import patch
from dagster import MaterializeResult

from dagster_pipelines.assets.enrichment import (
    _batch_insert_properties,
    _update_peptide_molecular_weight,
    process_single_peptide,
)


class TestBatchInsertProperties:
    """Test _batch_insert_properties helper."""

    def test_empty_list_returns_zero(self, mock_session):
        assert _batch_insert_properties(mock_session, []) == 0

    def test_inserts_and_returns_count(self, mock_session):
        mock_session.execute.return_value.rowcount = 2
        props = [
            {
                "peptide_id": "uuid-1", "logp": 1.23, "tpsa": 456.78,
                "num_h_donors": 8, "num_h_acceptors": 15,
                "isoelectric_point": 8.45, "hydrophobicity": -0.623,
                "instability_index": 40.0, "aromaticity": 0.08,
                "charge_at_ph7": 1.0, "calculation_method": "RDKit+BioPython",
            },
            {
                "peptide_id": "uuid-2", "logp": 0.98, "tpsa": 412.34,
                "num_h_donors": 6, "num_h_acceptors": 13,
                "isoelectric_point": 7.22, "hydrophobicity": -1.45,
                "instability_index": 35.0, "aromaticity": 0.07,
                "charge_at_ph7": 0.5, "calculation_method": "RDKit+BioPython",
            },
        ]
        result = _batch_insert_properties(mock_session, props)
        assert result == 2
        mock_session.execute.assert_called_once()

    def test_sql_contains_upsert(self, mock_session):
        mock_session.execute.return_value.rowcount = 1
        props = [
            {
                "peptide_id": "uuid-1", "logp": 1.0, "tpsa": 400.0,
                "num_h_donors": 5, "num_h_acceptors": 10,
                "isoelectric_point": 8.0, "hydrophobicity": -0.5,
                "instability_index": 35.0, "aromaticity": 0.07,
                "charge_at_ph7": 0.5, "calculation_method": "Test",
            },
        ]
        _batch_insert_properties(mock_session, props)
        query = str(mock_session.execute.call_args[0][0])
        assert "ON CONFLICT" in query
        assert "DO UPDATE" in query


class TestUpdatePeptideMolecularWeight:
    """Test _update_peptide_molecular_weight helper."""

    def test_empty_list_returns_zero(self, mock_session):
        assert _update_peptide_molecular_weight(mock_session, []) == 0

    def test_skips_entries_without_weight(self, mock_session):
        mock_session.execute.return_value.rowcount = 0
        props = [{"peptide_id": "uuid-1", "molecular_weight": None}]
        result = _update_peptide_molecular_weight(mock_session, props)
        assert result == 0

    def test_updates_valid_weights(self, mock_session):
        mock_session.execute.return_value.rowcount = 1
        props = [{"peptide_id": "uuid-1", "molecular_weight": 5432.12}]
        result = _update_peptide_molecular_weight(mock_session, props)
        assert result == 1


class TestProcessSinglePeptide:
    """Test parallel peptide processing function."""

    def test_returns_property_record(self):
        with patch(
            "dagster_pipelines.assets.enrichment.compute_properties_cached",
            return_value={
                "molecular_weight": 1000.0, "logp": -1.5, "tpsa": 300.0,
                "num_h_donors": 5, "num_h_acceptors": 10,
                "isoelectric_point": 8.0, "hydrophobicity": -0.5,
                "instability_index": 35.0, "aromaticity": 0.07,
                "charge_at_ph7": 0.5, "calculation_method": "RDKit+BioPython",
            },
        ):
            row = ("uuid-1", "TestPeptide", "ACDEFGHIK", 9)
            result = process_single_peptide(row)

        assert result["peptide_id"] == "uuid-1"
        assert result["name"] == "TestPeptide"
        assert result["molecular_weight"] == 1000.0
        assert result["logp"] == -1.5
        assert result["calculation_method"] == "RDKit+BioPython"


class TestComputePeptidePropertiesAsset:
    """Test the main enrichment Dagster asset."""

    def test_no_peptides_to_process(self, mock_context, mock_database_resource):
        from dagster_pipelines.assets.enrichment import compute_peptide_properties

        session = mock_database_resource.get_session.return_value
        session.execute.return_value.fetchall.return_value = []

        result = compute_peptide_properties(mock_context, database=mock_database_resource)

        assert isinstance(result, MaterializeResult)
        assert result.metadata["peptides_processed"].value == 0

    def test_processes_peptides(self, mock_context, mock_database_resource):
        from dagster_pipelines.assets.enrichment import compute_peptide_properties

        session = mock_database_resource.get_session.return_value
        session.execute.return_value.fetchall.return_value = [
            ("uuid-1", "P1", "ACDEFGHIKLMNPQRSTVWY", 20),
        ]
        session.execute.return_value.rowcount = 1

        with patch(
            "dagster_pipelines.assets.enrichment.compute_properties_cached",
            return_value={
                "molecular_weight": 1000.0, "logp": -1.5, "tpsa": 300.0,
                "num_h_donors": 5, "num_h_acceptors": 10,
                "isoelectric_point": 8.0, "hydrophobicity": -0.5,
                "instability_index": 35.0, "aromaticity": 0.07,
                "charge_at_ph7": 0.5, "calculation_method": "Test",
            },
        ):
            result = compute_peptide_properties(mock_context, database=mock_database_resource)

        assert isinstance(result, MaterializeResult)
        assert "peptides_processed" in result.metadata
        assert "properties_computed" in result.metadata
        assert "error_count" in result.metadata

    def test_database_error_raises(self, mock_context, mock_database_resource):
        from dagster_pipelines.assets.enrichment import compute_peptide_properties

        session = mock_database_resource.get_session.return_value
        session.execute.side_effect = Exception("DB connection failed")

        with pytest.raises(Exception):
            compute_peptide_properties(mock_context, database=mock_database_resource)

        session.rollback.assert_called()
