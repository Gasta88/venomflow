from dagster import (
    AssetExecutionContext,
    asset,
    MaterializeResult,
    MetadataValue,
)
import pandas as pd
import requests
import hashlib
import random
import time
from datetime import datetime
from typing import List, Dict, Any
import json

from sqlalchemy import text
from sqlalchemy.orm import Session

from resources.database import DatabaseResource


BATCH_SIZE = 500


def _calculate_sequence_hash(sequence: str) -> str:
    """Calculate SHA256 hash of peptide sequence for deduplication."""
    return hashlib.sha256(sequence.encode()).hexdigest()


def _get_or_create_organism(session, organism_name: str) -> str:
    """
    Get organism ID from database or create a new record.

    Args:
        session: SQLAlchemy session
        organism_name: Scientific name of organism

    Returns:
        Organism UUID as string
    """
    query = text("""
        SELECT id, name FROM organisms WHERE name = :name
    """)
    result = session.execute(query, {"name": organism_name}).fetchone()

    if result:
        return str(result[0])

    insert_query = text("""
        INSERT INTO organisms (name, source, taxonomy)
        VALUES (:name, 'uniprot', '{}'::jsonb)
        RETURNING id
    """)
    result = session.execute(insert_query, {"name": organism_name}).fetchone()
    return str(result[0])


def _batch_insert_peptides(
    session: Session, peptides_list: List[Dict[str, Any]]
) -> int:
    """
    Insert peptides into database using UPSERT.

    Args:
        session: SQLAlchemy session
        peptides_list: List of peptide dictionaries

    Returns:
        Number of peptides inserted
    """
    if not peptides_list:
        return 0

    insert_query = text("""
        INSERT INTO peptides (
            uniprot_id,
            name,
            sequence,
            sequence_hash,
            sequence_length,
            organism_id,
            function_description,
            source,
            metadata,
            external_ids,
            created_at,
            updated_at
        ) VALUES (
            :uniprot_id,
            :name,
            :sequence,
            :sequence_hash,
            :sequence_length,
            :organism_id,
            :function_description,
            :source,
            :metadata,
            :external_ids,
            NOW(),
            NOW()
        )
        ON CONFLICT (sequence_hash)
        DO UPDATE SET
            name = EXCLUDED.name,
            organism_id = EXCLUDED.organism_id,
            function_description = EXCLUDED.function_description,
            metadata = EXCLUDED.metadata,
            external_ids = EXCLUDED.external_ids,
            updated_at = NOW()
        RETURNING uniprot_id
    """)

    result = session.execute(insert_query, peptides_list)
    return result.rowcount


@asset(
    group_name="ingestion",
    description="""
    Fetches venom peptide data from UniProt REST API and stores in peptides table.

    Features:
    - Pagination: Fetches first 2 pages using offset based pagination
    - Rate Limiting: Sleeps 100-150ms between requests to stay under 10 req/sec limit
    - Error Handling: Handles HTTP errors and timeouts gracefully
    - Deduplication: Uses SHA256 sequence_hash to avoid duplicates
    - UPSERT: Handles duplicates gracefully
    - Batch Inserts: Inserts peptides in batches of 500
    """,
)
def venom_peptides_uniprot(
    context: AssetExecutionContext,
    database: DatabaseResource,
) -> MaterializeResult:
    """
    Dagster asset for fetching venom peptides from UniProt and storing in database.

    Fetches all reviewed venom peptides from UniProt REST API, processes them,
    and stores in the peptides table. Handles organism lookup/creation and
    uses SHA256 hash for sequence deduplication.

    Args:
        context: Dagster asset execution context
        database: Database resource for PostgreSQL connection

    Returns:
        MaterializeResult with metadata including peptides fetched,
        peptides inserted, duplicates found, and organism count.
    """
    BASE_URL = "https://rest.uniprot.org/uniprotkb/search"
    QUERY = "(venom OR toxin) AND reviewed:true"
    PAGE_SIZE = 5
    MAX_PAGES = 1
    MIN_SLEEP = 0.1
    MAX_SLEEP = 0.15

    all_records = []
    offset = 0
    pages_fetched = 0
    request_count = 0

    peptides_inserted = 0
    duplicates_found = 0
    organisms_created = 0

    headers = {"User-Agent": "VenomFlow/1.0 (venom peptide research pipeline)"}

    session = database.get_session()

    try:
        while pages_fetched < MAX_PAGES:
            params = {
                "query": QUERY,
                "format": "json",
                "size": PAGE_SIZE,
                "offset": offset,
            }

            try:
                request_count += 1
                context.log.info(
                    f"Fetching page {pages_fetched + 1}/{MAX_PAGES} (offset={offset})"
                )

                response = requests.get(
                    BASE_URL, params=params, headers=headers, timeout=30
                )

                if response.status_code == 429:
                    context.log.warning(f"Rate limit hit, backing off...")
                    time.sleep(2)
                    continue

                response.raise_for_status()
                data = response.json()
                results = data.get("results", [])

                if not results:
                    context.log.info(f"No more results at offset {offset}")
                    break

                context.log.info(
                    f"Fetched {len(results)} records from page {pages_fetched + 1}"
                )

                for record in results:
                    extracted = {}

                    extracted["accession"] = record.get("primaryAccession", "")
                    extracted["id"] = record.get("uniProtkbId", "")

                    organism_data = record.get("organism", {})
                    organism_name = organism_data.get("scientificName", "")
                    extracted["organism_name"] = organism_name

                    sequence_data = record.get("sequence", {})
                    sequence = sequence_data.get("value", "")
                    extracted["sequence"] = sequence
                    extracted["length"] = len(sequence)

                    comments = record.get("comments", [])
                    function_text = None
                    for comment in comments:
                        if comment.get("commentType") == "FUNCTION":
                            texts = comment.get("texts", [])
                            if texts:
                                function_text = texts[0].get("value", "")
                                break
                    extracted["function"] = function_text

                    all_records.append(extracted)

                pages_fetched += 1
                offset += len(results)

                context.log.info(f"Total records fetched: {len(all_records)}")

                if pages_fetched < MAX_PAGES:
                    sleep_time = MIN_SLEEP + (random.random() * (MAX_SLEEP - MIN_SLEEP))
                    time.sleep(sleep_time)

            except requests.exceptions.Timeout:
                context.log.error(f"Timeout error fetching page with offset {offset}")
                raise
            except requests.exceptions.RequestException as e:
                context.log.error(f"HTTP error fetching page: {e}")
                raise
            except Exception as e:
                context.log.error(f"Unexpected error: {e}")
                raise

        df = pd.DataFrame(all_records)

        context.log.info(f"Processing {len(df)} peptide records for database insertion")

        peptides_list: List[Dict[str, Any]] = []
        seen_hashes: set[str] = set()

        for i in range(0, len(df), BATCH_SIZE):
            batch = df.iloc[i : i + BATCH_SIZE]
            batch_num = (i // BATCH_SIZE) + 1
            total_batches = (len(df) + BATCH_SIZE - 1) // BATCH_SIZE

            context.log.info(
                f"Processing batch {batch_num}/{total_batches} ({len(batch)} peptides)"
            )

            for _, row in batch.iterrows():
                sequence = row["sequence"]
                sequence_hash = _calculate_sequence_hash(sequence)

                if sequence_hash in seen_hashes:
                    duplicates_found += 1
                    context.log.debug(
                        f"Duplicate sequence hash: {sequence_hash[:16]}..."
                    )
                    continue

                seen_hashes.add(sequence_hash)

                organism_id = _get_or_create_organism(session, row["organism_name"])
                organisms_created += 1

                peptide_record = {
                    "uniprot_id": row["accession"],
                    "name": row["id"],
                    "sequence": sequence,
                    "sequence_hash": sequence_hash,
                    "sequence_length": row["length"],
                    "organism_id": organism_id,
                    "function_description": row.get("function"),
                    "source": "uniprot",
                    "metadata": json.dumps({"page_fetched": batch_num}),
                    "external_ids": json.dumps({"uniprot_accession": row["accession"]}),
                }

                peptides_list.append(peptide_record)

            if peptides_list:
                insert_result = _batch_insert_peptides(session, peptides_list)
                peptides_inserted += insert_result
                context.log.info(
                    f"Inserted {insert_result} peptides in batch {batch_num}"
                )
                peptides_list.clear()

        session.commit()

        context.log.info(f"Successfully inserted {peptides_inserted} peptides")
        context.log.info(f"Duplicates skipped: {duplicates_found}")
        context.log.info(f"Organisms created: {organisms_created}")

        metadata = {
            "records_fetched": len(df),
            "peptides_inserted": MetadataValue.int(peptides_inserted),
            "duplicates_detected": MetadataValue.int(duplicates_found),
            "organisms_processed": MetadataValue.int(df["organism_name"].nunique()),
            "organisms_created": MetadataValue.int(organisms_created),
            "fetch_time": MetadataValue.text(datetime.now().isoformat()),
            "organism_count": MetadataValue.int(df["organism_name"].nunique()),
            "avg_length": MetadataValue.float(float(df["length"].mean())),
        }

        return MaterializeResult(metadata=metadata)

    except Exception as e:
        session.rollback()
        context.log.error(f"Error in venom_peptides_uniprot: {e}")
        raise
    finally:
        session.close()
