"""
Unit tests for Elasticsearch peptide indexer asset.
"""

import pytest
from unittest.mock import MagicMock, patch, Mock
from datetime import datetime
from elasticsearch import Elasticsearch

from dagster_pipelines.assets.elasticsearch_indexer import (
    _create_peptides_index,
    _get_kmer_analyzer_config,
    _get_peptides_index_mapping,
    _transform_peptide_to_doc,
    _bulk_index_documents,
)


class TestCreatePeptidesIndex:
    """Unit tests for index creation."""

    @patch("dagster_pipelines.assets.elasticsearch_indexer._get_kmer_analyzer_config")
    @patch("dagster_pipelines.assets.elasticsearch_indexer._get_peptides_index_mapping")
    def test_index_created_successfully(self, mock_get_mapping, mock_get_analyzer):
        """Test index creation returns True on success."""
        mock_es = MagicMock()
        mock_es.indices.exists.return_value = False
        mock_es.indices.create.return_value = {}

        mock_get_analyzer.return_value = {"tokenizer": {"kmer_tokenizer": {}}}
        mock_get_mapping.return_value = {"properties": {}}

        result = _create_peptides_index(mock_es, "peptides")

        assert result is True
        mock_es.indices.create.assert_called_once()

    def test_index_already_exists(self):
        """Test returns True if index already exists."""
        mock_es = MagicMock()
        mock_es.indices.exists.return_value = True

        result = _create_peptides_index(mock_es, "peptides")

        assert result is True
        mock_es.indices.create.assert_not_called()

    def test_index_creation_failure(self):
        """Test returns False on creation failure."""
        mock_es = MagicMock()
        mock_es.indices.exists.return_value = False
        mock_es.indices.create.side_effect = Exception("Connection failed")

        result = _create_peptides_index(mock_es, "peptides")

        assert result is False


class TestKmerAnalyzerConfig:
    """Unit tests for k-mer analyzer configuration."""

    def test_config_returns_tokenizer(self):
        """Test k-mer tokenizer is configured correctly."""
        config = _get_kmer_analyzer_config()

        assert "tokenizer" in config
        assert "kmer_tokenizer" in config["tokenizer"]
        assert config["tokenizer"]["kmer_tokenizer"]["type"] == "edge_ngram"
        assert config["tokenizer"]["kmer_tokenizer"]["min_gram"] == 3
        assert config["tokenizer"]["kmer_tokenizer"]["max_gram"] == 6

    def test_config_returns_analyzer(self):
        """Test k-mer analyzer is configured correctly."""
        config = _get_kmer_analyzer_config()

        assert "analyzer" in config
        assert "kmer_analyzer" in config["analyzer"]
        assert config["analyzer"]["kmer_analyzer"]["type"] == "custom"
        assert config["analyzer"]["kmer_analyzer"]["tokenizer"] == "kmer_tokenizer"


class TestPeptidesIndexMapping:
    """Unit tests for Elasticsearch mapping configuration."""

    def test_mapping_includes_accession_keyword(self):
        """Test accession field is mapped as keyword."""
        mapping = _get_peptides_index_mapping()

        assert "accession" in mapping["properties"]
        assert mapping["properties"]["accession"]["type"] == "keyword"

    def test_mapping_includes_sequence_with_analyzer(self):
        """Test sequence field is mapped with k-mer analyzer."""
        mapping = _get_peptides_index_mapping()

        assert "sequence" in mapping["properties"]
        assert mapping["properties"]["sequence"]["type"] == "text"
        assert mapping["properties"]["sequence"]["analyzer"] == "kmer_analyzer"
        assert "fields" in mapping["properties"]["sequence"]
        assert "exact" in mapping["properties"]["sequence"]["fields"]
        assert "raw" in mapping["properties"]["sequence"]["fields"]

    def test_mapping_includes_organism_fields(self):
        """Test organism fields are mapped correctly."""
        mapping = _get_peptides_index_mapping()

        assert "organism_name" in mapping["properties"]
        assert mapping["properties"]["organism_name"]["type"] == "text"
        assert "fields" in mapping["properties"]["organism_name"]
        assert "keyword" in mapping["properties"]["organism_name"]["fields"]

        assert "organism_common_name" in mapping["properties"]
        assert mapping["properties"]["organism_common_name"]["type"] == "text"

    def test_mapping_includes_function_description(self):
        """Test function_description is mapped as text."""
        mapping = _get_peptides_index_mapping()

        assert "function_description" in mapping["properties"]
        assert mapping["properties"]["function_description"]["type"] == "text"
        assert mapping["properties"]["function_description"]["analyzer"] == "standard"

    def test_mapping_includes_properties_nested(self):
        """Test properties object has nested numeric fields."""
        mapping = _get_peptides_index_mapping()

        assert "properties" in mapping["properties"]
        props_fields = mapping["properties"]["properties"]["properties"]
        assert "logp" in props_fields
        assert "tpsa" in props_fields
        assert "isoelectric_point" in props_fields
        assert "hydrophobicity" in props_fields
        assert props_fields["logp"]["type"] == "float"
        assert props_fields["num_h_donors"]["type"] == "integer"

    def test_mapping_includes_numeric_fields(self):
        """Test numeric fields are mapped correctly."""
        mapping = _get_peptides_index_mapping()

        assert "sequence_length" in mapping["properties"]
        assert mapping["properties"]["sequence_length"]["type"] == "integer"
        assert "quality_score" in mapping["properties"]
        assert mapping["properties"]["quality_score"]["type"] == "float"
        assert "bioactivity_count" in mapping["properties"]
        assert mapping["properties"]["bioactivity_count"]["type"] == "integer"

    def test_mapping_includes_date_fields(self):
        """Test timestamp fields are mapped as date."""
        mapping = _get_peptides_index_mapping()

        assert "created_at" in mapping["properties"]
        assert mapping["properties"]["created_at"]["type"] == "date"
        assert "updated_at" in mapping["properties"]
        assert mapping["properties"]["updated_at"]["type"] == "date"


class TestTransformPeptideToDoc:
    """Unit tests for document transformation."""

    def test_transform_with_all_fields(self):
        """Test transformation with all fields populated."""
        mock_row = Mock()
        mock_row.uniprot_id = "P12345"
        mock_row.name = "TEST_PEPTIDE"
        mock_row.sequence = "MALWMRLLPLLALLALWGPDPAAAFVNQHLCGSHLVEALYLVCGERGFFYTPK"
        mock_row.sequence_length = 50
        mock_row.molecular_weight = 5432.12
        mock_row.organism_name = "Naja naja"
        mock_row.organism_common_name = "Indian cobra"
        mock_row.venom_type = "snake"
        mock_row.function_description = "Toxic function"
        mock_row.family = "Three-finger toxin"
        mock_row.quality_score = 0.95
        mock_row.isoelectric_point = 8.5
        mock_row.hydrophobicity = -0.2
        mock_row.charge_at_ph7 = 1.0
        mock_row.instability_index = 40.5
        mock_row.aliphatic_index = 75.2
        mock_row.aromaticity = 0.08
        mock_row.logp = -1.2
        mock_row.tpsa = 150.3
        mock_row.num_h_donors = 5
        mock_row.num_h_acceptors = 10
        mock_row.bioactivity_count = 3
        mock_row.structure_count = 1
        mock_row.created_at = datetime(2026, 1, 1, 12, 0, 0)
        mock_row.updated_at = datetime(2026, 1, 2, 12, 0, 0)

        doc = _transform_peptide_to_doc(mock_row)

        assert doc["accession"] == "P12345"
        assert doc["name"] == "TEST_PEPTIDE"
        assert doc["sequence"] == mock_row.sequence
        assert doc["sequence_length"] == 50
        assert doc["molecular_weight"] == 5432.12
        assert doc["organism_name"] == "Naja naja"
        assert doc["venom_type"] == "snake"
        assert "properties" in doc
        assert doc["properties"]["logp"] == -1.2
        assert doc["properties"]["isoelectric_point"] == 8.5
        assert doc["created_at"] == "2026-01-01T12:00:00"

    def test_transform_with_null_fields(self):
        """Test transformation with None/null values."""
        mock_row = Mock()
        mock_row.uniprot_id = None
        mock_row.name = None
        mock_row.sequence = ""
        mock_row.sequence_length = 0
        mock_row.molecular_weight = None
        mock_row.organism_name = None
        mock_row.organism_common_name = None
        mock_row.venom_type = None
        mock_row.function_description = None
        mock_row.family = None
        mock_row.quality_score = None
        mock_row.isoelectric_point = None
        mock_row.hydrophobicity = None
        mock_row.charge_at_ph7 = None
        mock_row.instability_index = None
        mock_row.aliphatic_index = None
        mock_row.aromaticity = None
        mock_row.logp = None
        mock_row.tpsa = None
        mock_row.num_h_donors = None
        mock_row.num_h_acceptors = None
        mock_row.bioactivity_count = 0
        mock_row.structure_count = 0
        mock_row.created_at = None
        mock_row.updated_at = None

        doc = _transform_peptide_to_doc(mock_row)

        assert doc["accession"] == ""
        assert doc["name"] == ""
        assert doc["sequence"] == ""
        assert doc["molecular_weight"] is None
        assert doc["organism_name"] == ""
        assert doc["quality_score"] == 0.0
        assert doc["properties"]["logp"] is None

    def test_transform_properties_nested_object(self):
        """Test properties are properly nested."""
        mock_row = Mock()
        mock_row.uniprot_id = "P12345"
        mock_row.name = "TEST"
        mock_row.sequence = "MALWMRLLPLLALLALWGPDPAAAFVNQHLCGSHLVEALYLVCGERGFFYTPK"
        mock_row.sequence_length = 50
        mock_row.molecular_weight = 5432.12
        mock_row.organism_name = "Test"
        mock_row.organism_common_name = "Test"
        mock_row.venom_type = "snake"
        mock_row.function_description = "Test"
        mock_row.family = "Test"
        mock_row.quality_score = 0.9
        mock_row.isoelectric_point = 8.0
        mock_row.hydrophobicity = -0.1
        mock_row.charge_at_ph7 = 0.5
        mock_row.instability_index = 35.0
        mock_row.aliphatic_index = 70.0
        mock_row.aromaticity = 0.07
        mock_row.logp = -0.5
        mock_row.tpsa = 120.0
        mock_row.num_h_donors = 4
        mock_row.num_h_acceptors = 8
        mock_row.bioactivity_count = 0
        mock_row.structure_count = 0
        mock_row.created_at = None
        mock_row.updated_at = None

        doc = _transform_peptide_to_doc(mock_row)

        assert "properties" in doc
        assert isinstance(doc["properties"], dict)
        assert doc["properties"]["isoelectric_point"] == 8.0
        assert doc["properties"]["logp"] == -0.5
        assert doc["properties"]["num_h_donors"] == 4


class TestBulkIndexDocuments:
    """Unit tests for bulk document indexing."""

    @patch("dagster_pipelines.assets.elasticsearch_indexer.helpers.parallel_bulk")
    def test_bulk_index_success(self, mock_parallel_bulk):
        """Test bulk indexing returns success counts."""
        mock_es = MagicMock()
        mock_context = MagicMock()
        mock_parallel_bulk.return_value = [
            (True, {"status": 200}),
            (True, {"status": 200}),
            (True, {"status": 200}),
        ]

        documents = [{"accession": f"P{i:05d}", "sequence": "TEST"} for i in range(3)]

        success, error = _bulk_index_documents(
            mock_es, "peptides", documents, mock_context
        )

        assert success == 3
        assert error == 0

    @patch("dagster_pipelines.assets.elasticsearch_indexer.helpers.parallel_bulk")
    def test_bulk_index_with_errors(self, mock_parallel_bulk):
        """Test bulk indexing handles failures."""
        mock_es = MagicMock()
        mock_context = MagicMock()
        mock_parallel_bulk.return_value = [
            (True, {"status": 200}),
            (False, {"error": "Document error"}),
            (True, {"status": 200}),
        ]

        documents = [{"accession": f"P{i:05d}", "sequence": "TEST"} for i in range(3)]

        success, error = _bulk_index_documents(
            mock_es, "peptides", documents, mock_context
        )

        assert success == 2
        assert error == 1
        mock_context.log.warning.assert_called()

    @patch("dagster_pipelines.assets.elasticsearch_indexer.helpers.parallel_bulk")
    def test_bulk_index_exception_handling(self, mock_parallel_bulk):
        """Test bulk indexing exception is caught."""
        mock_es = MagicMock()
        mock_context = MagicMock()
        mock_parallel_bulk.side_effect = Exception("Bulk API failure")

        documents = [{"accession": "P00001", "sequence": "TEST"}]

        success, error = _bulk_index_documents(
            mock_es, "peptides", documents, mock_context
        )

        assert success == 0
        assert error == 1
        mock_context.log.error.assert_called()


class TestDocumentIdGeneration:
    """Unit tests for document ID generation."""

    def test_document_id_uses_accession(self):
        """Test document ID uses accession field."""
        mock_es = MagicMock()
        mock_context = MagicMock()

        documents = [
            {"accession": "P12345", "sequence": "TEST1"},
            {"accession": "P67890", "sequence": "TEST2"},
        ]

        def capture_actions(es_client, actions, **kwargs):
            for action in actions:
                assert "_id" in action
                yield True, {}

        with patch(
            "dagster_pipelines.assets.elasticsearch_indexer.helpers.parallel_bulk"
        ) as mock_bulk:
            mock_bulk.side_effect = capture_actions

            _bulk_index_documents(mock_es, "peptides", documents, mock_context)

            assert mock_bulk.called
            call_args = mock_bulk.call_args
            actions_passsed = call_args[0][1]
            assert actions_passsed[0]["_id"] == "P12345"
            assert actions_passsed[1]["_id"] == "P67890"

    def test_document_id_fallback_to_name(self):
        """Test document ID falls back to name if accession missing."""
        mock_es = MagicMock()
        mock_context = MagicMock()

        documents = [{"name": "TEST_PEPTIDE", "sequence": "TEST"}]

        def capture_actions(es_client, actions, **kwargs):
            for action in actions:
                assert "_id" in action
                yield True, {}

        with patch(
            "dagster_pipelines.assets.elasticsearch_indexer.helpers.parallel_bulk"
        ) as mock_bulk:
            mock_bulk.side_effect = capture_actions

            _bulk_index_documents(mock_es, "peptides", documents, mock_context)

            assert mock_bulk.called
            call_args = mock_bulk.call_args
            actions_passsed = call_args[0][1]
            assert actions_passsed[0]["_id"] == "TEST_PEPTIDE"
