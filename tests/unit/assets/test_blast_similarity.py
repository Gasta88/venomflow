"""Unit tests for blast_similarity asset with BioPython alignment."""

import pytest
from unittest.mock import MagicMock
from pathlib import Path
from sqlalchemy.orm import Session


class TestOrderPeptideIds:
    """Test order_peptide_ids function."""

    def test_already_ordered(self):
        from dagster_pipelines.assets.blast_similarity import order_peptide_ids

        id1, id2 = order_peptide_ids("uuid-aaa-111", "uuid-zzz-999")
        assert id1 == "uuid-aaa-111"
        assert id2 == "uuid-zzz-999"

    def test_reversed_order(self):
        from dagster_pipelines.assets.blast_similarity import order_peptide_ids

        id1, id2 = order_peptide_ids("uuid-zzz-999", "uuid-aaa-111")
        assert id1 == "uuid-aaa-111"
        assert id2 == "uuid-zzz-999"

    def test_equal_ids(self):
        from dagster_pipelines.assets.blast_similarity import order_peptide_ids

        id1, id2 = order_peptide_ids("same-uuid", "same-uuid")
        assert id1 == "same-uuid"
        assert id2 == "same-uuid"


class TestGetAligner:
    """Test BioPython PairwiseAligner singleton."""

    def test_returns_singleton(self):
        from dagster_pipelines.assets.blast_similarity import get_aligner

        aligner1 = get_aligner()
        aligner2 = get_aligner()
        assert aligner1 is aligner2

    def test_local_mode(self):
        from dagster_pipelines.assets.blast_similarity import get_aligner

        aligner = get_aligner()
        assert aligner.mode == "local"


class TestRunAlignment:
    """Test run_alignment function."""

    def test_identical_sequences_score_above_zero(self):
        from dagster_pipelines.assets.blast_similarity import run_alignment

        seq = "ACDEFGHIKLMNPQR"
        targets = [("id-1", "Peptide1", seq)]
        results = run_alignment(
            query_sequence=seq,
            query_id="query-id",
            target_sequences=targets,
            score_threshold=0.0,
            max_target_seqs=10,
        )
        assert len(results) == 1
        assert results[0]["similarity_score"] > 0

    def test_skip_self_comparison(self):
        from dagster_pipelines.assets.blast_similarity import run_alignment

        seq = "ACDEFGHIKLMNPQR"
        query_id = "query-uuid"
        targets = [
            (query_id, "Query", seq),
            ("other-id", "Other", seq),
        ]
        results = run_alignment(
            query_sequence=seq,
            query_id=query_id,
            target_sequences=targets,
            score_threshold=0.0,
            max_target_seqs=10,
        )
        ids = [r["peptide_id_1"] for r in results]
        assert query_id not in ids

    def test_threshold_filtering(self):
        from dagster_pipelines.assets.blast_similarity import run_alignment

        seq = "ACDEFGHIKLM"
        targets = [
            ("id-1", "Same", "ACDEFGHIKLM"),
            ("id-2", "Different", "WVPQNSTYAR"),
        ]
        low = run_alignment(
            query_sequence=seq, query_id="q", target_sequences=targets,
            score_threshold=0.0, max_target_seqs=10,
        )
        high = run_alignment(
            query_sequence=seq, query_id="q", target_sequences=targets,
            score_threshold=0.8, max_target_seqs=10,
        )
        assert len(low) >= len(high)

    def test_max_target_seqs_limit(self):
        from dagster_pipelines.assets.blast_similarity import run_alignment

        seq = "ACDEFGHIKLM"
        targets = [(f"id-{i}", f"P{i}", seq) for i in range(100)]
        results = run_alignment(
            query_sequence=seq, query_id="q", target_sequences=targets,
            score_threshold=0.0, max_target_seqs=10,
        )
        assert len(results) <= 10

    def test_start_index_skips_earlier_targets(self):
        from dagster_pipelines.assets.blast_similarity import run_alignment

        seq = "ACDEFGHIKLM"
        targets = [(f"id-{i}", f"P{i}", seq) for i in range(5)]
        results = run_alignment(
            query_sequence=seq, query_id="q", target_sequences=targets,
            score_threshold=0.0, max_target_seqs=100, start_index=3,
        )
        # Only targets at index 3 and 4 should be compared
        assert len(results) <= 2

    def test_skips_none_target_id(self):
        from dagster_pipelines.assets.blast_similarity import run_alignment

        seq = "ACDEFGHIKLM"
        targets = [(None, "BadPeptide", seq), ("id-1", "Good", seq)]
        results = run_alignment(
            query_sequence=seq, query_id="q", target_sequences=targets,
            score_threshold=0.0, max_target_seqs=10,
        )
        ids = [r["peptide_id_1"] for r in results]
        assert None not in ids

    def test_result_fields(self):
        from dagster_pipelines.assets.blast_similarity import run_alignment

        seq = "ACDEFGHIKLM"
        targets = [("id-1", "P1", seq)]
        results = run_alignment(
            query_sequence=seq, query_id="q", target_sequences=targets,
            score_threshold=0.0, max_target_seqs=10,
        )
        assert len(results) == 1
        r = results[0]
        assert "peptide_id_1" in r
        assert "similarity_score" in r
        assert "alignment_method" in r
        assert r["alignment_method"] == "smith-waterman"
        assert 0.0 <= r["similarity_score"] <= 1.0


class TestCreateFastaFromPeptides:
    """Test FASTA file creation."""

    def test_writes_fasta(self, tmp_path):
        from dagster_pipelines.assets.blast_similarity import create_fasta_from_peptides

        fasta = tmp_path / "test.fasta"
        peptides = [("id1", "name1", "ACDEF"), ("id2", "name2", "GHIKL")]
        create_fasta_from_peptides(peptides, fasta)
        content = fasta.read_text()
        assert ">id1|name1" in content
        assert "ACDEF" in content
        assert ">id2|name2" in content


class TestParseAlignmentResults:
    """Test parse_alignment_results passthrough."""

    def test_returns_input_unchanged(self):
        from dagster_pipelines.assets.blast_similarity import parse_alignment_results

        results = [{"peptide_id_1": "id1", "score": 0.9}]
        parsed = parse_alignment_results(results, {})
        assert parsed is results


class TestCreateAlignmentDatabase:
    """Test placeholder function."""

    def test_always_returns_true(self, tmp_path):
        from dagster_pipelines.assets.blast_similarity import create_alignment_database

        assert create_alignment_database(tmp_path / "a", tmp_path / "b") is True


class TestInsertSimilarity:
    """Test _insert_similarity database function."""

    def test_insert_success(self, mock_session):
        from dagster_pipelines.assets.blast_similarity import _insert_similarity

        mock_session.execute.return_value.fetchone.return_value = ("id1",)
        sim = {
            "peptide_id_1": "id1", "peptide_id_2": "id2",
            "similarity_score": 0.9, "alignment_method": "smith-waterman",
            "alignment_length": 0, "identities": 0, "gaps": 0, "score": 5.0,
        }
        assert _insert_similarity(mock_session, sim) is True

    def test_insert_conflict_returns_false(self, mock_session):
        from dagster_pipelines.assets.blast_similarity import _insert_similarity

        mock_session.execute.return_value.fetchone.return_value = None
        sim = {
            "peptide_id_1": "id1", "peptide_id_2": "id2",
            "similarity_score": 0.9, "alignment_method": "smith-waterman",
            "alignment_length": 0, "identities": 0, "gaps": 0, "score": 5.0,
        }
        assert _insert_similarity(mock_session, sim) is False

    def test_insert_exception_returns_false(self, mock_session):
        from dagster_pipelines.assets.blast_similarity import _insert_similarity

        mock_session.execute.side_effect = Exception("DB error")
        sim = {
            "peptide_id_1": "id1", "peptide_id_2": "id2",
            "similarity_score": 0.9, "alignment_method": "smith-waterman",
            "alignment_length": 0, "identities": 0, "gaps": 0, "score": 5.0,
        }
        assert _insert_similarity(mock_session, sim) is False


class TestComputeSequenceSimilaritiesAsset:
    """Test the main Dagster asset."""

    def test_empty_database(self, mock_context, mock_database_resource):
        from dagster_pipelines.assets.blast_similarity import compute_sequence_similarities

        session = mock_database_resource.get_session.return_value
        session.execute.return_value.fetchall.return_value = []

        result = compute_sequence_similarities(mock_context, database=mock_database_resource)

        assert result.metadata["peptides_processed"].value == 0
        assert result.metadata["similarities_stored"].value == 0

    def test_single_peptide(self, mock_context, mock_database_resource):
        from dagster_pipelines.assets.blast_similarity import compute_sequence_similarities

        session = mock_database_resource.get_session.return_value
        session.execute.return_value.fetchall.return_value = [
            ("id1", "Peptide1", "ACDEFGHIK"),
        ]

        result = compute_sequence_similarities(mock_context, database=mock_database_resource)

        assert result.metadata["peptides_processed"].value == 1
        assert result.metadata["similarities_stored"].value == 0
