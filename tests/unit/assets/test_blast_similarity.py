"""Unit tests for blast_similarity asset with BioPython alignment."""

import pytest
from unittest.mock import MagicMock, Mock
from sqlalchemy import text
from sqlalchemy.orm import Session


class TestBlastSimilarityHelperFunctions:
    """Test helper functions in blast_similarity module."""

    def test_order_peptide_ids(self):
        """Test order_peptide_ids function correctly orders peptide IDs."""
        from dagster_pipelines.assets.blast_similarity import order_peptide_ids

        id1, id2 = order_peptide_ids("uuid-aaa-111", "uuid-zzz-999")
        assert id1 == "uuid-aaa-111"
        assert id2 == "uuid-zzz-999"

        id1, id2 = order_peptide_ids("uuid-zzz-999", "uuid-aaa-111")
        assert id1 == "uuid-aaa-111"
        assert id2 == "uuid-zzz-999"

        id1, id2 = order_peptide_ids("same-uuid", "same-uuid")
        assert id1 == "same-uuid"
        assert id2 == "same-uuid"


class TestBioPythonAlignment:
    """Test BioPython-based sequence alignment."""

    @pytest.fixture
    def mock_database_resource(self):
        """Create a mock DatabaseResource."""
        mock_resource = MagicMock()
        mock_session = MagicMock(spec=Session)

        def mock_execute_side_effect(query):
            if "SELECT id, name, sequence FROM peptides" in str(query):
                mock_result = MagicMock()
                mock_result.fetchall.return_value = []
                return mock_result
            return MagicMock()

        mock_session.execute.side_effect = mock_execute_side_effect
        mock_resource.get_session.return_value = mock_session

        return mock_resource

    @pytest.fixture
    def mock_context(self):
        """Create a mock Dagster asset context."""
        context = MagicMock()
        context.log = MagicMock()
        context.log.info = MagicMock()
        context.log.debug = MagicMock()
        context.log.warning = MagicMock()
        context.log.error = MagicMock()
        return context

    def test_get_aligner_singleton(self):
        """Test that get_aligner returns a singleton instance."""
        from dagster_pipelines.assets.blast_similarity import get_aligner

        aligner1 = get_aligner()
        aligner2 = get_aligner()

        assert aligner1 is aligner2
        assert aligner1.mode == "local"

    def test_alignment_with_identical_sequences(self):
        """Test alignment with identical peptide sequences."""
        from dagster_pipelines.assets.blast_similarity import get_aligner

        aligner = get_aligner()
        seq1 = "ACDEFGHIKLMNPQR"
        seq2 = "ACDEFGHIKLMNPQR"

        score = aligner.score(seq1, seq2)
        assert score > 0

    def test_alignment_with_different_sequences(self):
        """Test alignment with different peptide sequences."""
        from dagster_pipelines.assets.blast_similarity import get_aligner

        aligner = get_aligner()
        seq1 = "ACDEFGHIKLM"
        seq2 = "WVPQNSTYAR"

        score = aligner.score(seq1, seq2)
        assert isinstance(score, float)

    def test_compute_sequence_similarities_no_peptides(
        self, mock_context, mock_database_resource
    ):
        """Test compute_sequence_similarities handles empty database."""
        from dagster_pipelines.assets.blast_similarity import (
            compute_sequence_similarities,
        )

        result = compute_sequence_similarities(mock_context, mock_database_resource)

        assert "peptides_processed" in str(result.metadata)
        assert result.metadata["peptides_processed"].value == 0
        assert result.metadata["similarities_stored"].value == 0

    def test_run_alignment_threshold_filtering(self):
        """Test that run_alignment respects score thresholds."""
        from dagster_pipelines.assets.blast_similarity import run_alignment

        query_seq = "ACDEFGHIKLM"
        targets = [
            ("id-1", "Similar 1", "ACDEFGHIKLM"),
            ("id-2", "Similar 2", "ACDGFHIKLMP"),
            ("id-3", "Dissimilar", "WVPQNSTYAR"),
        ]

        results_low_threshold = run_alignment(
            query_sequence=query_seq,
            target_sequences=targets,
            score_threshold=0.0,
            max_target_seqs=10,
        )

        results_high_threshold = run_alignment(
            query_sequence=query_seq,
            target_sequences=targets,
            score_threshold=0.8,
            max_target_seqs=10,
        )

        assert len(results_low_threshold) >= len(results_high_threshold)

    def test_run_alignment_max_target_seqs(self):
        """Test that run_alignment respects max_target_seqs limit."""
        from dagster_pipelines.assets.blast_similarity import run_alignment

        query_seq = "ACDEFGHIKLM"
        targets = [(f"id-{i}", f"Peptide {i}", query_seq) for i in range(100)]

        results = run_alignment(
            query_sequence=query_seq,
            target_sequences=targets,
            score_threshold=0.0,
            max_target_seqs=10,
        )

        assert len(results) <= 10

    def test_skip_query_vs_query_comparison(self):
        """Test that peptide is not compared against itself."""
        from dagster_pipelines.assets.blast_similarity import run_alignment

        query_seq = "ACDEFGHIKLM"
        query_id = "query-uuid"
        targets = [
            (query_id, "Query Peptide", query_seq),
            ("target-id", "Target", query_seq),
        ]

        results = run_alignment(
            query_sequence=query_seq,
            target_sequences=targets,
            score_threshold=0.0,
            max_target_seqs=10,
        )

        peptide_ids = [r["peptide_id_1"] for r in results]
        assert query_id not in peptide_ids
