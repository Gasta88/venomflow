"""Unit tests for Elasticsearch peptide indexer asset."""

from unittest.mock import MagicMock, Mock, patch
from datetime import datetime

from dagster_pipelines.assets.elasticsearch_indexer import (
    _create_peptides_index,
    _get_kmer_analyzer_config,
    _get_peptides_index_mapping,
    _transform_peptide_to_doc,
    _bulk_index_documents,
)


class TestCreatePeptidesIndex:
    """Test index creation."""

    def test_index_created_successfully(self):
        mock_es = MagicMock()
        mock_es.indices.exists.return_value = False
        mock_es.indices.create.return_value = {}

        assert _create_peptides_index(mock_es, "peptides") is True
        mock_es.indices.create.assert_called_once()

    def test_index_already_exists(self):
        mock_es = MagicMock()
        mock_es.indices.exists.return_value = True

        assert _create_peptides_index(mock_es, "peptides") is True
        mock_es.indices.create.assert_not_called()

    def test_index_creation_failure(self):
        mock_es = MagicMock()
        mock_es.indices.exists.return_value = False
        mock_es.indices.create.side_effect = Exception("Connection failed")

        assert _create_peptides_index(mock_es, "peptides") is False


class TestKmerAnalyzerConfig:
    """Test k-mer analyzer configuration."""

    def test_tokenizer_config(self):
        config = _get_kmer_analyzer_config()
        assert "tokenizer" in config
        tok = config["tokenizer"]["kmer_tokenizer"]
        assert tok["type"] == "edge_ngram"
        assert tok["min_gram"] == 3
        assert tok["max_gram"] == 6

    def test_analyzer_config(self):
        config = _get_kmer_analyzer_config()
        assert "analyzer" in config
        analyzer = config["analyzer"]["kmer_analyzer"]
        assert analyzer["type"] == "custom"
        assert analyzer["tokenizer"] == "kmer_tokenizer"


class TestPeptidesIndexMapping:
    """Test Elasticsearch mapping configuration."""

    def test_accession_keyword(self):
        mapping = _get_peptides_index_mapping()
        assert mapping["properties"]["accession"]["type"] == "keyword"

    def test_sequence_with_kmer_analyzer(self):
        mapping = _get_peptides_index_mapping()
        seq = mapping["properties"]["sequence"]
        assert seq["type"] == "text"
        assert seq["analyzer"] == "kmer_analyzer"
        assert "exact" in seq["fields"]
        assert "raw" in seq["fields"]

    def test_organism_fields(self):
        mapping = _get_peptides_index_mapping()
        assert mapping["properties"]["organism_name"]["type"] == "text"
        assert "keyword" in mapping["properties"]["organism_name"]["fields"]
        assert mapping["properties"]["organism_common_name"]["type"] == "text"

    def test_function_description(self):
        mapping = _get_peptides_index_mapping()
        fd = mapping["properties"]["function_description"]
        assert fd["type"] == "text"
        assert fd["analyzer"] == "standard"

    def test_nested_properties(self):
        mapping = _get_peptides_index_mapping()
        props = mapping["properties"]["properties"]["properties"]
        assert props["logp"]["type"] == "float"
        assert props["tpsa"]["type"] == "float"
        assert props["isoelectric_point"]["type"] == "float"
        assert props["num_h_donors"]["type"] == "integer"

    def test_numeric_fields(self):
        mapping = _get_peptides_index_mapping()
        assert mapping["properties"]["sequence_length"]["type"] == "integer"
        assert mapping["properties"]["quality_score"]["type"] == "float"
        assert mapping["properties"]["bioactivity_count"]["type"] == "integer"

    def test_date_fields(self):
        mapping = _get_peptides_index_mapping()
        assert mapping["properties"]["created_at"]["type"] == "date"
        assert mapping["properties"]["updated_at"]["type"] == "date"


class TestTransformPeptideToDoc:
    """Test document transformation."""

    def _make_row(self, **overrides):
        row = Mock()
        defaults = dict(
            uniprot_id="P12345", name="TEST_PEPTIDE", sequence="ACDEFGHIK",
            sequence_length=9, molecular_weight=5432.12, organism_name="Naja naja",
            organism_common_name="Indian cobra", venom_type="snake",
            function_description="Toxic", family="3FTx", quality_score=0.95,
            isoelectric_point=8.5, hydrophobicity=-0.2, charge_at_ph7=1.0,
            instability_index=40.5, aliphatic_index=75.2, aromaticity=0.08,
            logp=-1.2, tpsa=150.3, num_h_donors=5, num_h_acceptors=10,
            bioactivity_count=3, structure_count=1,
            created_at=datetime(2026, 1, 1), updated_at=datetime(2026, 1, 2),
        )
        defaults.update(overrides)
        for k, v in defaults.items():
            setattr(row, k, v)
        return row

    def test_all_fields_populated(self):
        doc = _transform_peptide_to_doc(self._make_row())
        assert doc["accession"] == "P12345"
        assert doc["name"] == "TEST_PEPTIDE"
        assert doc["sequence"] == "ACDEFGHIK"
        assert doc["organism_name"] == "Naja naja"
        assert doc["venom_type"] == "snake"
        assert doc["properties"]["logp"] == -1.2
        assert doc["created_at"] == "2026-01-01T00:00:00"

    def test_null_fields(self):
        doc = _transform_peptide_to_doc(
            self._make_row(
                uniprot_id=None, name=None, sequence="", molecular_weight=None,
                organism_name=None, quality_score=None, logp=None,
                created_at=None, updated_at=None,
            )
        )
        assert doc["accession"] == ""
        assert doc["name"] == ""
        assert doc["molecular_weight"] is None
        assert doc["quality_score"] == 0.0
        assert doc["properties"]["logp"] is None
        assert doc["created_at"] is None

    def test_properties_nested_object(self):
        doc = _transform_peptide_to_doc(self._make_row())
        assert isinstance(doc["properties"], dict)
        assert doc["properties"]["isoelectric_point"] == 8.5
        assert doc["properties"]["num_h_donors"] == 5


class TestBulkIndexDocuments:
    """Test bulk document indexing."""

    @patch("dagster_pipelines.assets.elasticsearch_indexer.helpers.parallel_bulk")
    def test_success(self, mock_bulk, mock_context):
        mock_es = MagicMock()
        mock_bulk.return_value = [(True, {}), (True, {}), (True, {})]
        docs = [{"accession": f"P{i:05d}", "sequence": "TEST"} for i in range(3)]

        success, error = _bulk_index_documents(mock_es, "peptides", docs, mock_context)
        assert success == 3
        assert error == 0

    @patch("dagster_pipelines.assets.elasticsearch_indexer.helpers.parallel_bulk")
    def test_with_errors(self, mock_bulk):
        mock_es = MagicMock()
        mock_ctx = MagicMock()
        mock_bulk.return_value = [(True, {}), (False, {"error": "fail"}), (True, {})]
        docs = [{"accession": f"P{i:05d}"} for i in range(3)]

        success, error = _bulk_index_documents(mock_es, "peptides", docs, mock_ctx)
        assert success == 2
        assert error == 1
        mock_ctx.log.warning.assert_called()

    @patch("dagster_pipelines.assets.elasticsearch_indexer.helpers.parallel_bulk")
    def test_exception_handling(self, mock_bulk):
        mock_es = MagicMock()
        mock_ctx = MagicMock()
        mock_bulk.side_effect = Exception("Bulk API failure")
        docs = [{"accession": "P00001"}]

        success, error = _bulk_index_documents(mock_es, "peptides", docs, mock_ctx)
        assert success == 0
        assert error == 1
        mock_ctx.log.error.assert_called()

    @patch("dagster_pipelines.assets.elasticsearch_indexer.helpers.parallel_bulk")
    def test_document_id_uses_accession(self, mock_bulk, mock_context):
        mock_es = MagicMock()
        mock_bulk.return_value = []
        docs = [{"accession": "P12345", "sequence": "TEST"}]

        _bulk_index_documents(mock_es, "peptides", docs, mock_context)

        call_args = mock_bulk.call_args
        actions = call_args[0][1]
        assert actions[0]["_id"] == "P12345"

    @patch("dagster_pipelines.assets.elasticsearch_indexer.helpers.parallel_bulk")
    def test_document_id_fallback_to_name(self, mock_bulk, mock_context):
        mock_es = MagicMock()
        mock_bulk.return_value = []
        docs = [{"name": "TEST_PEPTIDE", "sequence": "TEST"}]

        _bulk_index_documents(mock_es, "peptides", docs, mock_context)

        call_args = mock_bulk.call_args
        actions = call_args[0][1]
        assert actions[0]["_id"] == "TEST_PEPTIDE"
