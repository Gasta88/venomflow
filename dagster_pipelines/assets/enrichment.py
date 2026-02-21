"""
Dagster assets for peptide enrichment operations.
Computes physicochemical properties for peptides using RDKit and BioPython.
"""

import logging
import hashlib
from typing import Any, Dict, List, Tuple
from concurrent.futures import ThreadPoolExecutor, as_completed

from sqlalchemy import text
from sqlalchemy.orm import Session

from dagster import AssetExecutionContext, MaterializeResult, MetadataValue, asset

from assets.property_calculators import (
    compute_properties_with_fallbacks,
)
from resources.database import DatabaseResource

logger = logging.getLogger(__name__)


BATCH_SIZE = 50
MAX_WORKERS = 4


def sequence_hash_cache_key(func):
    """Decorator to cache function results by sequence hash."""
    cache = {}

    def wrapper(sequence: str) -> Dict[str, Any]:
        seq_hash = hashlib.sha256(sequence.encode()).hexdigest()
        if seq_hash not in cache:
            cache[seq_hash] = func(sequence)
        return cache[seq_hash]

    return wrapper


@sequence_hash_cache_key
def compute_properties_cached(sequence: str) -> Dict[str, Any]:
    """Compute properties with sequence hash caching."""
    return compute_properties_with_fallbacks(sequence)


def process_single_peptide(row: Tuple) -> Dict[str, Any]:
    """Process a single peptide for parallel execution.

    Args:
        row: Tuple of (peptide_id, peptide_name, sequence, sequence_length)

    Returns:
        Dictionary with property_record for database insertion
    """
    peptide_id, peptide_name, sequence, sequence_length = row

    props = compute_properties_cached(sequence)
    calculation_method = props.get("calculation_method", "Unknown")

    return {
        "peptide_id": peptide_id,
        "name": peptide_name,
        "sequence": sequence,
        "molecular_weight": props.get("molecular_weight"),  # For peptides table update
        "logp": props.get("logp"),
        "tpsa": props.get("tpsa"),
        "num_h_donors": props.get("num_h_donors"),
        "num_h_acceptors": props.get("num_h_acceptors"),
        "isoelectric_point": props.get("isoelectric_point"),
        "hydrophobicity": props.get("hydrophobicity"),
        "instability_index": props.get("instability_index"),
        "aromaticity": props.get("aromaticity"),
        "charge_at_ph7": props.get("charge_at_ph7"),
        "calculation_method": calculation_method,
    }


@asset(
    group_name="enrichment",
    deps=["venom_peptides_uniprot"],
    description="""
    Computes physicochemical properties for peptides using RDKit and BioPython.

    Properties computed:
    - RDKit: molecular_weight, logp, tpsa, num_h_donors, num_h_acceptors
    - BioPython: isoelectric_point (pI), hydrophobicity (GRAVY), instability_index, aromaticity, charge_at_ph7

    Results are stored in the PostgreSQL 'properties' table.
    molecular_weight is also updated in the peptides table.
    Properties are only computed for peptides that don't already have properties.
    """,
)
def compute_peptide_properties(
    context: AssetExecutionContext,
    database: DatabaseResource,
) -> MaterializeResult:
    """
    Dagster asset for computing peptide physicochemical properties.

    Fetches peptides without properties from the database, computes properties
    using RDKit and BioPython, and inserts results in batches of 52.
    Logs progress for each batch and returns metadata with statistics.

    Args:
        context: Dagster asset execution context
        database: Database resource for PostgreSQL connection

    Returns:
        MaterializeResult with metadata including peptides processed,
        properties computed, error count, and average values.

    Example metadata:
        - peptides_processed: Number of peptides attempted
        - properties_computed: Number successfully computed
        - error_count: Number of failures
        - avg_logp, avg_tpsa, avg_isoelectric_point, avg_hydrophobicity
    """
    session = database.get_session()

    peptides_processed = 0
    properties_computed = 0
    error_count = 0
    molecular_weights_updated = 0

    logp_values = []
    tpsa_values = []
    isoelectric_point_values = []
    hydrophobicity_values = []
    instability_index_values = []
    aromaticity_values = []
    charge_at_ph7_values = []

    method_counts = {}

    try:
        context.log.info("Fetching peptides without properties...")

        query = text("""
            SELECT id, name, sequence, sequence_length
            FROM peptides
            WHERE id NOT IN (
                SELECT peptide_id FROM properties
            )
            ORDER BY sequence_length ASC
            LIMIT 50
        """)

        result = session.execute(query)
        peptides_data = result.fetchall()

        total_peptides = len(peptides_data)
        context.log.info(f"Found {total_peptides} peptides without properties")

        if total_peptides == 0:
            context.log.info(
                "All peptides already have properties, skipping computation"
            )
            return MaterializeResult(
                metadata={
                    "peptides_processed": MetadataValue.int(0),
                    "properties_computed": MetadataValue.int(0),
                    "error_count": MetadataValue.int(0),
                }
            )

        properties_list: List[Dict[str, Any]] = []

        for i in range(0, total_peptides, BATCH_SIZE):
            batch = peptides_data[i : i + BATCH_SIZE]
            batch_num = (i // BATCH_SIZE) + 1
            total_batches = (total_peptides + BATCH_SIZE - 1) // BATCH_SIZE

            context.log.info(
                f"Processing batch {batch_num}/{total_batches} ({len(batch)} peptides)"
            )

            batch_properties = []

            with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
                future_to_row = {
                    executor.submit(process_single_peptide, row): row for row in batch
                }

                for future in as_completed(future_to_row):
                    row = future_to_row[future]
                    try:
                        property_record = future.result()
                        batch_properties.append(property_record)
                        peptides_processed += 1

                        if peptides_processed % 10 == 0:
                            context.log.info(
                                f"Processed {peptides_processed}/{total_peptides} peptides"
                            )

                    except Exception as e:
                        error_count += 1
                        context.log.error(f"Error processing peptide row: {e}")
                        continue

            for property_record in batch_properties:
                properties_list.append(property_record)
                calculation_method = property_record.get(
                    "calculation_method", "Unknown"
                )

                method_counts[calculation_method] = (
                    method_counts.get(calculation_method, 0) + 1
                )

                if "logp" in property_record and property_record["logp"] is not None:
                    logp_values.append(property_record["logp"])
                if "tpsa" in property_record and property_record["tpsa"] is not None:
                    tpsa_values.append(property_record["tpsa"])
                if (
                    "isoelectric_point" in property_record
                    and property_record["isoelectric_point"] is not None
                ):
                    isoelectric_point_values.append(
                        property_record["isoelectric_point"]
                    )
                if (
                    "hydrophobicity" in property_record
                    and property_record["hydrophobicity"] is not None
                ):
                    hydrophobicity_values.append(property_record["hydrophobicity"])
                if (
                    "instability_index" in property_record
                    and property_record["instability_index"] is not None
                ):
                    instability_index_values.append(
                        property_record["instability_index"]
                    )
                if (
                    "aromaticity" in property_record
                    and property_record["aromaticity"] is not None
                ):
                    aromaticity_values.append(property_record["aromaticity"])
                if (
                    "charge_at_ph7" in property_record
                    and property_record["charge_at_ph7"] is not None
                ):
                    charge_at_ph7_values.append(property_record["charge_at_ph7"])

            context.log.info(
                f"Computed properties for {len(batch)} peptides in batch {batch_num}"
            )

            if properties_list:
                molecular_weights_updated += _update_peptide_molecular_weight(
                    session, properties_list
                )
                insert_result = _batch_insert_properties(session, properties_list)
                properties_computed += insert_result
                properties_list.clear()

        remaining_properties = len(properties_list)
        if remaining_properties > 0:
            context.log.info(f"Inserting remaining {remaining_properties} properties")
            molecular_weights_updated += _update_peptide_molecular_weight(
                session, properties_list
            )
            insert_result = _batch_insert_properties(session, properties_list)
            properties_computed += insert_result

        session.commit()

        error_count = peptides_processed - properties_computed

        avg_logp = sum(logp_values) / len(logp_values) if logp_values else 0.0
        avg_tpsa = sum(tpsa_values) / len(tpsa_values) if tpsa_values else 0.0
        avg_isoelectric_point = (
            sum(isoelectric_point_values) / len(isoelectric_point_values)
            if isoelectric_point_values
            else 0.0
        )
        avg_hydrophobicity = (
            sum(hydrophobicity_values) / len(hydrophobicity_values)
            if hydrophobicity_values
            else 0.0
        )

        context.log.info(
            f"Successfully computed properties for {properties_computed} peptides"
        )
        context.log.info(f"Errors: {error_count}")
        context.log.info(f"Molecular weights updated: {molecular_weights_updated}")
        context.log.info(f"Calculation methods used: {method_counts}")
        context.log.info(f"Average LogP: {avg_logp:.3f}")
        context.log.info(f"Average TPSA: {avg_tpsa:.2f} Å²")
        context.log.info(f"Average isoelectric_point: {avg_isoelectric_point:.2f}")
        context.log.info(f"Average hydrophobicity (GRAVY): {avg_hydrophobicity:.3f}")

        metadata = {
            "peptides_processed": MetadataValue.int(peptides_processed),
            "properties_computed": MetadataValue.int(properties_computed),
            "error_count": MetadataValue.int(error_count),
            "molecular_weights_updated": MetadataValue.int(molecular_weights_updated),
            "avg_logp": MetadataValue.float(float(avg_logp)),
            "avg_tpsa": MetadataValue.float(float(avg_tpsa)),
            "avg_isoelectric_point": MetadataValue.float(float(avg_isoelectric_point)),
            "avg_hydrophobicity": MetadataValue.float(float(avg_hydrophobicity)),
        }

        return MaterializeResult(metadata=metadata)

    except Exception as e:
        session.rollback()
        context.log.error(f"Error in compute_peptide_properties: {e}")
        raise
    finally:
        session.close()


def _batch_insert_properties(
    session: Session, properties_list: List[Dict[str, Any]]
) -> int:
    """
    Insert computed properties into the database using UPSERT.

    Args:
        session: SQLAlchemy session
        properties_list: List of property dictionaries

    Returns:
        Number of properties inserted
    """
    if not properties_list:
        return 0

    insert_query = text("""
        INSERT INTO properties (
            peptide_id,
            logp,
            tpsa,
            num_h_donors,
            num_h_acceptors,
            isoelectric_point,
            hydrophobicity,
            instability_index,
            aromaticity,
            charge_at_ph7,
            calculation_method,
            calculated_at,
            created_at,
            updated_at
        ) VALUES (
            :peptide_id,
            :logp,
            :tpsa,
            :num_h_donors,
            :num_h_acceptors,
            :isoelectric_point,
            :hydrophobicity,
            :instability_index,
            :aromaticity,
            :charge_at_ph7,
            :calculation_method,
            NOW(),
            NOW(),
            NOW()
        )
        ON CONFLICT (peptide_id)
        DO UPDATE SET
            logp = EXCLUDED.logp,
            tpsa = EXCLUDED.tpsa,
            num_h_donors = EXCLUDED.num_h_donors,
            num_h_acceptors = EXCLUDED.num_h_acceptors,
            isoelectric_point = EXCLUDED.isoelectric_point,
            hydrophobicity = EXCLUDED.hydrophobicity,
            instability_index = EXCLUDED.instability_index,
            aromaticity = EXCLUDED.aromaticity,
            charge_at_ph7 = EXCLUDED.charge_at_ph7,
            calculation_method = EXCLUDED.calculation_method,
            calculated_at = NOW(),
            updated_at = NOW()
        RETURNING peptide_id
    """)

    result = session.execute(insert_query, properties_list)

    return result.rowcount


def _update_peptide_molecular_weight(
    session: Session, properties_list: List[Dict[str, Any]]
) -> int:
    """
    Update molecular_weight in peptides table for peptides that have properties.

    Args:
        session: SQLAlchemy session
        properties_list: List of property dictionaries (includes peptide_id and molecular_weight)

    Returns:
        Number of peptides updated
    """
    if not properties_list:
        return 0

    peptide_weights = [
        {"peptide_id": p["peptide_id"], "molecular_weight": p["molecular_weight"]}
        for p in properties_list
        if p.get("peptide_id") and p.get("molecular_weight") is not None
    ]

    if not peptide_weights:
        return 0

    update_query = text("""
        UPDATE peptides
        SET molecular_weight = :molecular_weight
        WHERE id = :peptide_id
    """)

    result = session.execute(update_query, peptide_weights)
    return result.rowcount
