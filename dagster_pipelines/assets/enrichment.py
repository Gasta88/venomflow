"""
Dagster assets for peptide enrichment operations.
Computes physicochemical properties for peptides using RDKit and BioPython.
"""

import logging
from typing import Any, Dict, List

from sqlalchemy import text
from sqlalchemy.orm import Session

from dagster import AssetExecutionContext, MaterializeResult, MetadataValue, asset

from assets.property_calculators import (
    compute_biopython_properties,
    compute_rdkit_properties,
)
from resources.database import DatabaseResource

logger = logging.getLogger(__name__)


BATCH_SIZE = 50


@asset(
    group_name="enrichment",
    description="""
    Computes physicochemical properties for peptides using RDKit and BioPython.

    Properties computed:
    - RDKit: molecular_weight, logp, tpsa, num_h_donors, num_h_acceptors
    - BioPython: isoelectric_point (pI), hydrophobicity (GRAVY)

    Results are stored in the PostgreSQL 'properties' table.
    Properties are only computed for peptides that don't already have properties.
    """,
)
def compute_peptide_properties(
    context: AssetExecutionContext,
    database: DatabaseResource,
    venom_peptides_uniprot,
) -> MaterializeResult:
    """
    Dagster asset for computing peptide physicochemical properties.

    Fetches peptides without properties from the database, computes properties
    using RDKit and BioPython, and inserts results in batches of 50.
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
    rdkit_errors = 0
    biopython_errors = 0

    logp_values = []
    tpsa_values = []
    isoelectric_point_values = []
    hydrophobicity_values = []

    try:
        context.log.info("Fetching peptides without properties...")

        query = text("""
            SELECT id, name, sequence, sequence_length
            FROM peptides
            WHERE id NOT IN (
                SELECT peptide_id FROM properties
            )
            ORDER BY sequence_length ASC
            LIMIT 1000
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

            for row in batch:
                peptide_id, peptide_name, sequence, sequence_length = row

                peptides_processed += 1

                context.log.debug(
                    f"Computing properties for peptide {peptide_name} (ID: {peptide_id})"
                )

                rdkit_props = compute_rdkit_properties(sequence)
                biopython_props = compute_biopython_properties(sequence)

                if rdkit_props is None:
                    rdkit_errors += 1
                    context.log.warning(
                        f"RDKit computation failed for peptide {peptide_id} ({peptide_name})"
                    )
                    continue

                if biopython_props is None:
                    biopython_errors += 1
                    context.log.warning(
                        f"BioPython computation failed for peptide {peptide_id} ({peptide_name})"
                    )

                property_record = {
                    "peptide_id": peptide_id,
                    "logp": rdkit_props.get("logp"),
                    "tpsa": rdkit_props.get("tpsa"),
                    "num_h_donors": rdkit_props.get("num_h_donors"),
                    "num_h_acceptors": rdkit_props.get("num_h_acceptors"),
                    "isoelectric_point": biopython_props.get("isoelectric_point")
                    if biopython_props
                    else None,
                    "hydrophobicity": biopython_props.get("hydrophobicity")
                    if biopython_props
                    else None,
                    "calculation_method": "RDKit + BioPython",
                }

                properties_list.append(property_record)

                logp_values.append(rdkit_props["logp"])
                tpsa_values.append(rdkit_props["tpsa"])
                if biopython_props:
                    isoelectric_point_values.append(
                        biopython_props["isoelectric_point"]
                    )
                    hydrophobicity_values.append(biopython_props["hydrophobicity"])

                if peptides_processed % 10 == 0:
                    context.log.info(
                        f"Processed {peptides_processed}/{total_peptides} peptides"
                    )

            context.log.info(
                f"Computed properties for {len(batch)} peptides in batch {batch_num}"
            )

            if properties_list:
                insert_result = _batch_insert_properties(session, properties_list)
                properties_computed += insert_result
                properties_list.clear()

        remaining_properties = len(properties_list)
        if remaining_properties > 0:
            context.log.info(f"Inserting remaining {remaining_properties} properties")
            insert_result = _batch_insert_properties(session, properties_list)
            properties_computed += insert_result

        session.commit()

        error_count = rdkit_errors + biopython_errors

        avg_logp = sum(logp_values) / len(logp_values) if logp_values else 0
        avg_tpsa = sum(tpsa_values) / len(tpsa_values) if tpsa_values else 0
        avg_isoelectric_point = (
            sum(isoelectric_point_values) / len(isoelectric_point_values)
            if isoelectric_point_values
            else 0
        )
        avg_hydrophobicity = (
            sum(hydrophobicity_values) / len(hydrophobicity_values)
            if hydrophobicity_values
            else 0
        )

        context.log.info(
            f"Successfully computed properties for {properties_computed} peptides"
        )
        context.log.info(
            f"Errors: {error_count} (RDKit: {rdkit_errors}, BioPython: {biopython_errors})"
        )
        context.log.info(f"Average LogP: {avg_logp:.3f}")
        context.log.info(f"Average TPSA: {avg_tpsa:.2f} Å²")
        context.log.info(f"Average isoelectric_point: {avg_isoelectric_point:.2f}")
        context.log.info(f"Average hydrophobicity (GRAVY): {avg_hydrophobicity:.3f}")

        metadata = {
            "peptides_processed": MetadataValue.int(peptides_processed),
            "properties_computed": MetadataValue.int(properties_computed),
            "error_count": MetadataValue.int(error_count),
            "rdkit_errors": MetadataValue.int(rdkit_errors),
            "biopython_errors": MetadataValue.int(biopython_errors),
            "avg_logp": MetadataValue.float(avg_logp),
            "avg_tpsa": MetadataValue.float(avg_tpsa),
            "avg_isoelectric_point": MetadataValue.float(avg_isoelectric_point),
            "avg_hydrophobicity": MetadataValue.float(avg_hydrophobicity),
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
            isoelectric_point,
            hydrophobicity,
            logp,
            tpsa,
            num_h_donors,
            num_h_acceptors,
            calculation_method,
            calculated_at,
            created_at,
            updated_at
        ) VALUES (
            :peptide_id,
            :isoelectric_point,
            :hydrophobicity,
            :logp,
            :tpsa,
            :num_h_donors,
            :num_h_acceptors,
            :calculation_method,
            NOW(),
            NOW(),
            NOW()
        )
        ON CONFLICT (peptide_id)
        DO UPDATE SET
            isoelectric_point = EXCLUDED.isoelectric_point,
            hydrophobicity = EXCLUDED.hydrophobicity,
            logp = EXCLUDED.logp,
            tpsa = EXCLUDED.tpsa,
            num_h_donors = EXCLUDED.num_h_donors,
            num_h_acceptors = EXCLUDED.num_h_acceptors,
            calculation_method = EXCLUDED.calculation_method,
            calculated_at = NOW(),
            updated_at = NOW()
        RETURNING peptide_id
    """)

    result = session.execute(insert_query, properties_list)

    return result.rowcount
