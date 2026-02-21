"""Unit tests for ingestion asset and helpers."""

import pytest
import responses

from dagster_pipelines.assets.ingestion import (
    _calculate_sequence_hash,
    _batch_insert_peptides,
    _get_or_create_organism,
)


class TestCalculateSequenceHash:
    """Test SHA256 sequence hashing for deduplication."""

    def test_deterministic(self):
        h1 = _calculate_sequence_hash("ACDEFGHIK")
        h2 = _calculate_sequence_hash("ACDEFGHIK")
        assert h1 == h2

    def test_different_sequences_differ(self):
        h1 = _calculate_sequence_hash("ACDEFGHIK")
        h2 = _calculate_sequence_hash("LMNPQRSTV")
        assert h1 != h2

    def test_returns_hex_string(self):
        h = _calculate_sequence_hash("ACDEF")
        assert isinstance(h, str)
        assert len(h) == 64  # SHA256 hex length

    def test_empty_sequence(self):
        h = _calculate_sequence_hash("")
        assert isinstance(h, str)
        assert len(h) == 64


class TestGetOrCreateOrganism:
    """Test organism lookup/creation."""

    def test_existing_organism_returned(self, mock_session):
        mock_session.execute.return_value.fetchone.return_value = ("uuid-org-1", "Naja naja")
        result = _get_or_create_organism(mock_session, "Naja naja")
        assert result == "uuid-org-1"

    def test_new_organism_created(self, mock_session):
        # First call: not found; second call: insert returning id
        mock_session.execute.return_value.fetchone.side_effect = [
            None,
            ("uuid-new-1",),
        ]
        result = _get_or_create_organism(mock_session, "New Species")
        assert result == "uuid-new-1"


class TestBatchInsertPeptides:
    """Test batch peptide insertion."""

    def test_empty_list_returns_zero(self, mock_session):
        assert _batch_insert_peptides(mock_session, []) == 0

    def test_inserts_list(self, mock_session):
        mock_session.execute.return_value.rowcount = 3
        peptides = [
            {
                "uniprot_id": f"P{i:05d}",
                "name": f"TEST{i}",
                "sequence": "ACDEF",
                "sequence_hash": f"hash{i}",
                "sequence_length": 5,
                "organism_id": "org1",
                "function_description": None,
                "source": "uniprot",
                "metadata": "{}",
                "external_ids": "{}",
            }
            for i in range(3)
        ]
        result = _batch_insert_peptides(mock_session, peptides)
        assert result == 3
        mock_session.execute.assert_called_once()


class TestVenomPeptidesUniprotAsset:
    """Test the main ingestion Dagster asset."""

    @responses.activate
    def test_successful_fetch_and_insert(self, mock_context, mock_database_resource):
        from dagster_pipelines.assets.ingestion import venom_peptides_uniprot

        session = mock_database_resource.get_session.return_value
        # _get_or_create_organism mock
        session.execute.return_value.fetchone.return_value = ("org-uuid",)
        # _batch_insert_peptides mock
        session.execute.return_value.rowcount = 1

        mock_response = {
            "results": [
                {
                    "primaryAccession": "P01589",
                    "uniProtkbId": "CYA1_CANFA",
                    "organism": {"scientificName": "Canis lupus"},
                    "sequence": {"value": "MALWMRLLPLLALLALWGPDPAAAFVNQHLCGSHLVEALYLVCGERGFFYTPK"},
                    "comments": [
                        {"commentType": "FUNCTION", "texts": [{"value": "Toxic"}]},
                    ],
                }
            ]
        }

        responses.add(
            responses.GET,
            "https://rest.uniprot.org/uniprotkb/search",
            json=mock_response,
            status=200,
        )

        result = venom_peptides_uniprot(mock_context, database=mock_database_resource)

        assert result.metadata["records_fetched"] == 1
        assert "fetch_time" in result.metadata

    @responses.activate
    def test_empty_response(self, mock_context, mock_database_resource):
        from dagster_pipelines.assets.ingestion import venom_peptides_uniprot

        responses.add(
            responses.GET,
            "https://rest.uniprot.org/uniprotkb/search",
            json={"results": []},
            status=200,
        )

        # Empty DataFrame lacks columns, so metadata construction raises KeyError
        with pytest.raises(KeyError):
            venom_peptides_uniprot(mock_context, database=mock_database_resource)

    @responses.activate
    def test_missing_function_field(self, mock_context, mock_database_resource):
        from dagster_pipelines.assets.ingestion import venom_peptides_uniprot

        session = mock_database_resource.get_session.return_value
        session.execute.return_value.fetchone.return_value = ("org-uuid",)
        session.execute.return_value.rowcount = 1

        responses.add(
            responses.GET,
            "https://rest.uniprot.org/uniprotkb/search",
            json={
                "results": [
                    {
                        "primaryAccession": "P12345",
                        "uniProtkbId": "TEST1",
                        "organism": {"scientificName": "Test"},
                        "sequence": {"value": "ACDEFGHIK"},
                        "comments": [],
                    }
                ]
            },
            status=200,
        )

        result = venom_peptides_uniprot(mock_context, database=mock_database_resource)
        assert result.metadata["records_fetched"] == 1

    @responses.activate
    def test_metadata_keys(self, mock_context, mock_database_resource):
        from dagster_pipelines.assets.ingestion import venom_peptides_uniprot

        session = mock_database_resource.get_session.return_value
        session.execute.return_value.fetchone.return_value = ("org-uuid",)
        session.execute.return_value.rowcount = 1

        responses.add(
            responses.GET,
            "https://rest.uniprot.org/uniprotkb/search",
            json={
                "results": [
                    {
                        "primaryAccession": "P12345",
                        "uniProtkbId": "TEST1",
                        "organism": {"scientificName": "Organism A"},
                        "sequence": {"value": "ACDEFGHIKLMNPQRSTVWY"},
                        "comments": [],
                    }
                ]
            },
            status=200,
        )

        result = venom_peptides_uniprot(mock_context, database=mock_database_resource)

        assert "records_fetched" in result.metadata
        assert "fetch_time" in result.metadata
        assert "organism_count" in result.metadata
        assert "avg_length" in result.metadata
