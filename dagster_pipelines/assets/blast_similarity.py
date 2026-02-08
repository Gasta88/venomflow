"""
Dagster asset for computing peptide sequence similarities using NCBI BLAST+.

This asset:
1. Fetches all peptide sequences from the database
2. Creates a FASTA file with all peptides
3. Creates a BLAST database using makeblastdb
4. Runs BLASTp for each peptide against the database
5. Parses BLAST results and stores top hits in peptide_similarities table
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

BLAST_EVALUE_THRESHOLD = 1e-5
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


def create_blast_database(fasta_path: Path, db_path: Path) -> bool:
    """
    Create a BLAST database from a FASTA file using makeblastdb.

    Args:
        fasta_path: Path to the input FASTA file
        db_path: Path to the BLAST database directory

    Returns:
        True if successful, False otherwise
    """
    db_dir = db_path.parent
    db_name = db_path.stem

    if not db_dir.exists():
        db_dir.mkdir(parents=True, exist_ok=True)

    cmd = [
        "makeblastdb",
        "-in",
        str(fasta_path),
        "-dbtype",
        "prot",
        "-title",
        "VenomFlow Peptides",
        "-parse_seqids",
        "-out",
        str(db_path),
    ]

    try:
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        logger.info(f"BLAST database created: {db_path}")
        return True
    except subprocess.CalledProcessError as e:
        logger.error(f"Failed to create BLAST database: {e}")
        logger.error(f"stdout: {e.stdout}")
        logger.error(f"stderr: {e.stderr}")
        return False


def run_blast(
    query_fasta_path: Path,
    blast_db_path: Path,
    output_path: Path,
    evalue: float = BLAST_EVALUE_THRESHOLD,
    max_target_seqs: int = 100,
    num_threads: int = 4,
) -> bool:
    """
    Run BLASTp for a query sequence against a database.

    Args:
        query_fasta_path: Path to the query FASTA file
        blast_db_path: Path to the BLAST database
        output_path: Path to write the output TSV file
        evalue: E-value threshold
        max_target_seqs: Maximum number of target sequences
        num_threads: Number of threads to use

    Returns:
        True if successful, False otherwise
    """
    cmd = [
        "blastp",
        "-query",
        str(query_fasta_path),
        "-db",
        str(blast_db_path),
        "-evalue",
        str(evalue),
        "-outfmt",
        "6",
        "-max_target_seqs",
        str(max_target_seqs),
        "-num_threads",
        str(num_threads),
        "-out",
        str(output_path),
    ]

    try:
        subprocess.run(cmd, capture_output=True, text=True, check=True)
        return True
    except subprocess.CalledProcessError as e:
        logger.error(f"BLASTp failed: {e}")
        logger.error(f"stdout: {e.stdout}")
        logger.error(f"stderr: {e.stderr}")
        return False


def parse_blast_results(
    output_path: Path, peptide_id_map: Dict[str, str]
) -> List[Dict[str, Any]]:
    """
    Parse BLAST tabular output (outfmt 6).

    Args:
        output_path: Path to the BLAST results TSV file
        peptide_id_map: Mapping from FASTA header (id|name) to peptide_id string

    Returns:
        List of parsed similarity records

    Tabular format (outfmt 6) columns:
    1. qseqid - Query sequence ID
    2. sseqid - Subject (target) sequence ID
    3. pident - Percentage of identical matches
    4. length - Alignment length
    5. mismatch - Number of mismatches
    6. gapopen - Number of gap openings
    7. qstart - Start of alignment in query
    8. qend - End of alignment in query
    9. sstart - Start of alignment in subject
    10. send - End of alignment in subject
    11. evalue - Expect value
    12. bit_score - Bit score
    """
    results = []

    if not output_path.exists():
        return results

    with open(output_path, "r") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue

            parts = line.split("\t")
            if len(parts) < 12:
                continue

            query_header = parts[0]
            subject_header = parts[1]
            pident = float(parts[2])
            length = int(parts[3])
            mismatch = int(parts[4])
            gapopen = int(parts[5])
            evalue = float(parts[10])
            bit_score = float(parts[11])

            # Extract peptide IDs from headers
            query_id = query_header.split("|")[0]
            subject_id = subject_header.split("|")[0]

            # Skip self-similarity
            if query_id == subject_id:
                continue

            # Parse peptide IDs from UUID strings
            try:
                peptide_id_1 = query_id
                peptide_id_2 = subject_id
            except ValueError:
                logger.warning(
                    f"Invalid peptide ID format: {query_header}, {subject_header}"
                )
                continue

            # Convert identity percentage to similarity score (0.0-1.0)
            similarity_score = pident / 100.0

            results.append(
                {
                    "peptide_id_1": peptide_id_1,
                    "peptide_id_2": peptide_id_2,
                    "similarity_score": similarity_score,
                    "alignment_method": "blast",
                    "alignment_length": length,
                    "identities": int((pident / 100) * length),
                    "gaps": gapopen,
                    "e_value": evalue,
                    "bit_score": bit_score,
                }
            )

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
    Computes sequence similarities between all peptides using BLAST+.

    Creates a local BLAST database from peptide sequences, runs BLASTp for each
    peptide, and stores top 100 hits per peptide in the peptide_similarities table.

    Configuration:
    - BLAST database path: settings.blast_db_path
    - BLAST threads: settings.blast_threads
    - E-value threshold: 1e-5
    - Max hits per query: 100
    """,
)
def compute_blast_similarities(
    context: AssetExecutionContext,
    database: DatabaseResource,
) -> MaterializeResult:
    """
    Dagster asset for computing BLAST sequence similarities between peptides.

    Fetches all peptides from the database, creates a BLAST database, runs BLASTp
    for each peptide, parses results, and stores similarities in peptide_similarities table.

    Args:
        context: Dagster asset execution context
        database: Database resource for PostgreSQL connection

    Returns:
        MaterializeResult with metadata including peptides processed, similarities stored,
        error count, and average E-value and bit score.
    """
    session = database.get_session()

    peptides_processed = 0
    similarities_stored = 0
    error_count = 0

    e_values = []
    bit_scores = []

    fasta_path = None
    blast_db_path = Path(settings.blast_db_path) / "peptides"

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

            context.log.info("Creating BLAST database...")
            if not create_blast_database(fasta_path, blast_db_path):
                raise RuntimeError("Failed to create BLAST database")

            context.log.info("Running BLASTp for each peptide...")

            for i, (peptide_id, name, sequence) in enumerate(peptides_data):
                peptides_processed += 1

                if peptides_processed % QUERY_LOG_INTERVAL == 0:
                    context.log.info(
                        f"Processed {peptides_processed}/{total_peptides} peptides"
                    )

                query_fasta_path = temp_dir / f"query_{peptides_processed}.fasta"
                output_path = temp_dir / f"blast_results_{peptides_processed}.tsv"

                with open(query_fasta_path, "w") as f:
                    f.write(f">{peptide_id}|{name}\n")
                    f.write(f"{sequence}\n")

                if not run_blast(
                    query_fasta_path=query_fasta_path,
                    blast_db_path=blast_db_path,
                    output_path=output_path,
                    evalue=BLAST_EVALUE_THRESHOLD,
                    max_target_seqs=settings.blast_max_target_seqs,
                    num_threads=settings.blast_threads,
                ):
                    error_count += 1
                    context.log.warning(
                        f"BLAST failed for peptide {name} (ID: {peptide_id})"
                    )
                    continue

                results = parse_blast_results(output_path, {})

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
                        e_values.append(result["e_value"])
                        bit_scores.append(result["bit_score"])

        session.commit()

        avg_e_value = sum(e_values) / len(e_values) if e_values else 0
        avg_bit_score = sum(bit_scores) / len(bit_scores) if bit_scores else 0

        context.log.info(f"Successfully stored {similarities_stored} similarities")
        context.log.info(f"Errors: {error_count}")
        context.log.info(f"Average E-value: {avg_e_value:.2e}")
        context.log.info(f"Average bit score: {avg_bit_score:.2f}")

        metadata = {
            "peptides_processed": MetadataValue.int(total_peptides),
            "database_created": MetadataValue.bool(True),
            "similarities_stored": MetadataValue.int(similarities_stored),
            "error_count": MetadataValue.int(error_count),
            "avg_e_value": MetadataValue.float(avg_e_value),
            "avg_bit_score": MetadataValue.float(avg_bit_score),
            "e_value_threshold": MetadataValue.float(BLAST_EVALUE_THRESHOLD),
            "max_target_seqs": MetadataValue.int(settings.blast_max_target_seqs),
            "blast_threads": MetadataValue.int(settings.blast_threads),
        }

        return MaterializeResult(metadata=metadata)

    except Exception as e:
        session.rollback()
        context.log.error(f"Error in compute_blast_similarities: {e}")
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
            e_value,
            bit_score,
            created_at
        ) VALUES (
            :peptide_id_1,
            :peptide_id_2,
            :similarity_score,
            :alignment_method,
            :alignment_length,
            :identities,
            :gaps,
            :e_value,
            :bit_score,
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
