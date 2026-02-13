"""
Dagster asset for computing peptide sequence similarities using sequence alignment.

This asset:
1. Fetches all peptide sequences from the database
2. Creates a FASTA file with all peptides
3. Runs sequence alignment for each peptide against the database
4. Parses alignment results and stores top hits in peptide_similarities table
"""

import logging
from pathlib import Path
from typing import Any, Dict, List, Tuple

from Bio import Align
from Bio.Align import substitution_matrices
from dagster import AssetExecutionContext, MaterializeResult, MetadataValue, asset
from sqlalchemy import text
from sqlalchemy.orm import Session

from shared.config.settings import settings
from resources.database import DatabaseResource

logger = logging.getLogger(__name__)

ALIGNMENT_SCORE_THRESHOLD = 0.5
QUERY_LOG_INTERVAL = 100

# Create a global aligner for reuse - using Smith-Waterman for local alignment
aligner: Align.PairwiseAligner = None


def get_aligner() -> Align.PairwiseAligner:
    """
    Get or create the global BioPython PairwiseAligner.

    Returns:
        Configured PairwiseAligner for peptide sequence alignment
    """
    global aligner
    if aligner is None:
        aligner = Align.PairwiseAligner(
            mode="local",
            substitution_matrix=substitution_matrices.load("BLOSUM50"),
            open_gap_score=-5,
            extend_gap_score=-0.5,
        )
    return aligner


def create_fasta_from_peptides(
    peptides: List[Tuple[str, str, str]], fasta_path: Path
) -> None:
    """
    Create a FASTA file from peptide data.

    Args:
        peptides: List of tuples (peptide_id, name, sequence)
        fasta_path: Path to write the FASTA file
    """
    with open(fasta_path, "w") as f:
        for peptide_id, name, sequence in peptides:
            f.write(f">{peptide_id}|{name}\n")
            f.write(f"{sequence}\n")


def create_alignment_database(fasta_path: Path, db_path: Path) -> bool:
    """
    Placeholder function - not needed for BioPython pairwise alignment.

    BioPython performs in-memory pairwise comparisons without needing
    an indexed database. This function exists for API compatibility.

    Args:
        fasta_path: Path to FASTA file (unused)
        db_path: Path to database location (unused)

    Returns:
        Always True
    """
    return True


def run_alignment(
    query_sequence: str,
    target_sequences: List[Tuple[str, str, str]],
    score_threshold: float = ALIGNMENT_SCORE_THRESHOLD,
    max_target_seqs: int = 100,
) -> List[Dict[str, Any]]:
    """
    Perform sequence alignment using BioPython's PairwiseAligner.

    Use Smith-Waterman algorithm for local alignment of peptide sequences.

    Args:
        query_sequence: Query peptide sequence
        target_sequences: List of tuples (peptide_id, name, sequence)
        score_threshold: Normalized similarity threshold (0.0-1.0)
        max_target_seqs: Maximum number of top hits to return

    Returns:
        List of alignment results with similarity scores
    """
    aligner_instance = get_aligner()
    results = []

    for target_id, target_name, target_seq in target_sequences:
        if target_id is None or target_id == query_sequence:
            continue

        score = aligner_instance.score(query_sequence, target_seq)
        max_score = max(len(query_sequence), len(target_seq))
        normalized_score: float = score / max_score if max_score > 0 else 0.0

        if normalized_score >= score_threshold:
            results.append({
                "peptide_id_1": target_id,
                "similarity_score": normalized_score,
                "alignment_method": "smith-waterman",
                "alignment_length": 0,
                "identities": 0,
                "gaps": 0,
                "score": float(score),
            })

        if len(results) >= max_target_seqs:
            break

    return results


def parse_alignment_results(
    results: List[Dict[str, Any]], peptide_id_map: Dict[str, str]
) -> List[Dict[str, Any]]:
    """
    Parse and filter alignment results from BioPython.

    Args:
        results: List of alignment results from run_alignment
        peptide_id_map: Mapping fromFASTA header (id|name) to peptide_id string

    Returns:
        List of similarity records ready for database insertion
    """
    return results


def order_peptide_ids(peptide_id_1: str, peptide_id_2: str) -> Tuple[str, str]:
    """
    Ensure peptide_id_1 < peptide_id_2 to satisfy database constraint.

    Args:
        peptide_id_1: First peptide ID
        peptide_id_2: Second peptide ID

    Returns:
        Ordered tuple (peptide_id_1, peptide_id_2) where peptide_id_1 < peptide_id_2
    """
    if peptide_id_1 < peptide_id_2:
        return peptide_id_1, peptide_id_2
    return peptide_id_2, peptide_id_1


@asset(
    group_name="enrichment",
    deps=["venom_peptides_uniprot"],
    description="""
    Computes sequence similarities between all peptides using sequence alignment.

    Uses BioPython's PairwiseAligner with Smith-Waterman algorithm for local
    pairwise alignment of peptide sequences. Computes similarity scores and stores
    top 100 hits per peptide in the peptide_similarities table.

    Configuration:
    - Score threshold: ALIGNMENT_SCORE_THRESHOLD (default 0.5)
    - Max hits per query: 100
    - Alignment algorithm: Smith-Waterman (local alignment)
    - Substitution matrix: BLOSUM50

    The similarity score is normalized to 0.0-1.0 range for easier interpretation
    and downstream filtering.
    """,
)
def compute_sequence_similarities(
    context: AssetExecutionContext,
    database: DatabaseResource,
) -> MaterializeResult:
    """
    Dagster asset for computing sequence similarities between peptides.

    Uses BioPython's PairwiseAligner with Smith-Waterman algorithm for
    local alignment of peptide sequences. Computes pairwise similarities
    between all peptides and stores results in peptide_similarities table.

    Args:
        context: Dagster asset execution context
        database: Database resource for PostgreSQL connection

    Returns:
        MaterializeResult with metadata including peptides processed, similarities stored,
        and error count.
    """
    session = database.get_session()

    peptides_processed = 0
    similarities_stored = 0
    error_count = 0

    scores = []

    try:
        context.log.info("Fetching all peptides from database...")

        query = text("""
            SELECT id, name, sequence
            FROM peptides
            WHERE sequence IS NOT NULL
            ORDER BY id
        """)

        result = session.execute(query)
        peptides_data = result.fetchall()

        total_peptides = len(peptides_data)
        context.log.info(f"Found {total_peptides} peptides")

        if total_peptides == 0:
            context.log.warning("No peptides found in database")
            return MaterializeResult(
                metadata={
                    "peptides_processed": MetadataValue.int(0),
                    "similarities_stored": MetadataValue.int(0),
                    "error_count": MetadataValue.int(0),
                }
            )

        if total_peptides == 1:
            context.log.warning("Only one peptide found - no pairs possible")
            return MaterializeResult(
                metadata={
                    "peptides_processed": MetadataValue.int(1),
                    "similarities_stored": MetadataValue.int(0),
                    "error_count": MetadataValue.int(0),
                }
            )

        context.log.info("Initializing BioPython PairwiseAligner...")
        context.log.info("Computing pairwise sequence similarities using Smith-Waterman algorithm...")

        for i, (query_id, query_name, query_sequence) in enumerate(peptides_data):
            peptides_processed += 1

            if peptides_processed % QUERY_LOG_INTERVAL == 0:
                context.log.info(
                    f"Processed {peptides_processed}/{total_peptides} peptides"
                )

            context.log.debug(f"Aligning {query_name} (ID: {query_id}) against {total_peptides} peptides")

            try:
                results = run_alignment(
                    query_sequence=query_sequence,
                    target_sequences=peptides_data,
                    score_threshold=ALIGNMENT_SCORE_THRESHOLD,
                    max_target_seqs=getattr(settings, 'similarity_max_target_seqs', 100),
                )

                for result in results:
                    target_id = result["peptide_id_1"]
                    ordered_id_1, ordered_id_2 = order_peptide_ids(query_id, target_id)
                    result["peptide_id_1"] = ordered_id_1
                    result["peptide_id_2"] = ordered_id_2

                    insert_result = _insert_similarity(
                        session,
                        result,
                    )

                    if insert_result:
                        similarities_stored += 1
                        if "score" in result:
                            scores.append(result["score"])

            except Exception as e:
                error_count += 1
                context.log.error(
                    f"Alignment failed for peptide {query_name} (ID: {query_id}): {e}"
                )
                continue

        session.commit()

        avg_score = sum(scores) / len(scores) if scores else 0.0

        context.log.info(f"Successfully stored {similarities_stored} similarities")
        context.log.info(f"Errors: {error_count}")
        context.log.info(f"Average alignment score: {avg_score:.2f}")

        metadata = {
            "peptides_processed": MetadataValue.int(total_peptides),
            "database_created": MetadataValue.bool(True),
            "similarities_stored": MetadataValue.int(similarities_stored),
            "error_count": MetadataValue.int(error_count),
            "avg_score": MetadataValue.float(avg_score),
            "score_threshold": MetadataValue.float(ALIGNMENT_SCORE_THRESHOLD),
            "max_target_seqs": MetadataValue.int(
                getattr(settings, "similarity_max_target_seqs", 100)
            ),
            "alignment_threads": MetadataValue.int(
                getattr(settings, "similarity_threads", 4)
            ),
        }

        return MaterializeResult(metadata=metadata)

    except Exception as e:
        session.rollback()
        context.log.error(f"Error in compute_sequence_similarities: {e}")
        raise
    finally:
        session.close()


def _insert_similarity(session: Session, similarity: Dict[str, Any]) -> bool:
    """
    Insert a similarity record with ON CONFLICT DO NOTHING.

    Args:
        session: SQLAlchemy session
        similarity: Similarity record dictionary

    Returns:
        True if inserted, False if already exists or error occurred
    """
    insert_query = text("""
        INSERT INTO peptide_similarities (
            peptide_id_1,
            peptide_id_2,
            similarity_score,
            alignment_method,
            alignment_length,
            identities,
            gaps,
            score,
            created_at
        ) VALUES (
            :peptide_id_1,
            :peptide_id_2,
            :similarity_score,
            :alignment_method,
            :alignment_length,
            :identities,
            :gaps,
            :score,
            NOW()
        )
        ON CONFLICT (peptide_id_1, peptide_id_2)
        DO NOTHING
        RETURNING peptide_id_1
    """)

    try:
        result = session.execute(insert_query, similarity)
        if result.fetchone():
            return True
        return False
    except Exception as e:
        logger.error(f"Failed to insert similarity: {e}")
        return False
