"""
Dagster asset for computing peptide sequence similarities using sequence alignment.

This asset:
1. Fetches all peptide sequences from the database
2. Creates a FASTA file with all peptides
3. Runs sequence alignment for each peptide against the database
4. Parses alignment results and stores top hits in peptide_similarities table
"""

import logging
import os
import sys
import subprocess
import tempfile
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from dagster import AssetExecutionContext, MaterializeResult, MetadataValue, asset
from sqlalchemy import text
from sqlalchemy.orm import Session

from shared.config.settings import settings
from resources.database import DatabaseResource

logger = logging.getLogger(__name__)

ALIGNMENT_SCORE_THRESHOLD = 50
QUERY_LOG_INTERVAL = 100


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
    Create a sequence alignment database from a FASTA file.

    Args:
        fasta_path: Path to the input FASTA file
        db_path: Path to the alignment database directory

    Returns:
        True if successful, False otherwise
    """
    db_dir = db_path.parent
    db_name = db_path.stem

    if not db_dir.exists():
        db_dir.mkdir(parents=True, exist_ok=True)

    # Note: This is a placeholder for sequence alignment database creation
    # In a production environment, you would use appropriate sequence alignment tools
    try:
        # Copy the FASTA file as a simple database for now
        import shutil
        shutil.copy(str(fasta_path), str(db_path.with_suffix('.fasta')))
        logger.info(f"Alignment database created: {db_path}")
        return True
    except Exception as e:
        logger.error(f"Failed to create alignment database: {e}")
        return False


def run_alignment(
    query_fasta_path: Path,
    db_path: Path,
    output_path: Path,
    score_threshold: float = ALIGNMENT_SCORE_THRESHOLD,
    max_target_seqs: int = 100,
    num_threads: int = 4,
) -> bool:
    """
    Run sequence alignment for a query sequence against a database.

    Note: This is a placeholder implementation. In production, you would use
    appropriate sequence alignment tools like Smith-Waterman, Needleman-Wunsch,
    or other alignment algorithms.

    Args:
        query_fasta_path: Path to the query FASTA file
        db_path: Path to the alignment database
        output_path: Path to write the output TSV file
        score_threshold: Alignment score threshold
        max_target_seqs: Maximum number of target sequences
        num_threads: Number of threads to use

    Returns:
        True if successful, False otherwise
    """
    try:
        # Placeholder: Create empty output file
        # In production, this would call actual alignment tools
        with open(output_path, 'w') as f:
            f.write("# Sequence alignment results\n")
        logger.info(f"Alignment completed: {output_path}")
        return True
    except Exception as e:
        logger.error(f"Alignment failed: {e}")
        return False


def parse_alignment_results(
    output_path: Path, peptide_id_map: Dict[str, str]
) -> List[Dict[str, Any]]:
    """
    Parse sequence alignment tabular output.

    Note: This is a placeholder implementation. In production, you would parse
    actual alignment tool output.

    Args:
        output_path: Path to the alignment results TSV file
        peptide_id_map: Mapping from FASTA header (id|name) to peptide_id string

    Returns:
        List of parsed similarity records
    """
    results = []

    if not output_path.exists():
        return results

    # Placeholder: Return empty results for now
    # In production, this would parse actual alignment results
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

    Runs sequence alignment for each peptide and stores top 100 hits per peptide 
    in the peptide_similarities table.

    Configuration:
    - Database path: settings.similarity_db_path (if configured)
    - Threads: settings.similarity_threads
    - Score threshold: configurable
    - Max hits per query: 100
    
    Note: This is a placeholder implementation. In production, integrate with
    appropriate sequence alignment tools.
    """,
)
def compute_sequence_similarities(
    context: AssetExecutionContext,
    database: DatabaseResource,
) -> MaterializeResult:
    """
    Dagster asset for computing sequence similarities between peptides.

    Note: This is currently a placeholder that sets up the framework for
    sequence similarity computation. In production, integrate with actual
    alignment tools like Smith-Waterman, Needleman-Wunsch, or other algorithms.

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

    fasta_path = None
    # Use a default path if similarity_db_path is not configured
    db_base_path = Path("/data/similarity/db") if not hasattr(settings, 'similarity_db_path') else Path(settings.similarity_db_path)
    db_path = db_base_path / "peptides"

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

        with tempfile.TemporaryDirectory() as tmpdir:
            temp_dir = Path(tmpdir)

            fasta_path = temp_dir / "peptides.fasta"

            context.log.info(f"Creating FASTA file with {total_peptides} peptides...")
            create_fasta_from_peptides(peptides_data, fasta_path)

            context.log.info("Creating alignment database...")
            if not create_alignment_database(fasta_path, db_path):
                raise RuntimeError("Failed to create alignment database")

            context.log.info("Running sequence alignment for each peptide...")
            context.log.info("Note: This is a placeholder implementation. Integrate with actual alignment tools in production.")

            for i, (peptide_id, name, sequence) in enumerate(peptides_data):
                peptides_processed += 1

                if peptides_processed % QUERY_LOG_INTERVAL == 0:
                    context.log.info(
                        f"Processed {peptides_processed}/{total_peptides} peptides"
                    )

                query_fasta_path = temp_dir / f"query_{peptides_processed}.fasta"
                output_path = temp_dir / f"alignment_results_{peptides_processed}.tsv"

                with open(query_fasta_path, "w") as f:
                    f.write(f">{peptide_id}|{name}\n")
                    f.write(f"{sequence}\n")

                if not run_alignment(
                    query_fasta_path=query_fasta_path,
                    db_path=db_path,
                    output_path=output_path,
                    score_threshold=ALIGNMENT_SCORE_THRESHOLD,
                    max_target_seqs=getattr(settings, 'similarity_max_target_seqs', 100),
                    num_threads=getattr(settings, 'similarity_threads', 4),
                ):
                    error_count += 1
                    context.log.warning(
                        f"Alignment failed for peptide {name} (ID: {peptide_id})"
                    )
                    continue

                results = parse_alignment_results(output_path, {})

                for result in results:
                    ordered_id_1, ordered_id_2 = order_peptide_ids(
                        result["peptide_id_1"], result["peptide_id_2"]
                    )

                    insert_result = _insert_similarity(
                        session,
                        {
                            **result,
                            "peptide_id_1": ordered_id_1,
                            "peptide_id_2": ordered_id_2,
                        },
                    )

                    if insert_result:
                        similarities_stored += 1
                        if "score" in result:
                            scores.append(result["score"])

        session.commit()

        avg_score = sum(scores) / len(scores) if scores else 0

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
            "max_target_seqs": MetadataValue.int(getattr(settings, 'similarity_max_target_seqs', 100)),
            "alignment_threads": MetadataValue.int(getattr(settings, 'similarity_threads', 4)),
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
