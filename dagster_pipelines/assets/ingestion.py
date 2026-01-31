from dagster import (
    AssetExecutionContext,
    asset,
    MaterializeResult,
    MetadataValue,
)
import pandas as pd
import requests
import time
import random
from datetime import datetime


@asset(
    group_name="ingestion",
    description="Fetches venom peptide data from UniProt REST API with pagination and rate limiting",
)
def venom_peptides_uniprot(context: AssetExecutionContext) -> MaterializeResult:
    """
    Fetches all reviewed venom peptides from UniProt REST API.

    Features:
    - Pagination: Fetches first 2 pages using offset based pagination
    - Rate Limiting: Sleeps 100-150ms between requests to stay under 10 req/sec limit
    - Error Handling: Handles HTTP errors and timeouts gracefully
    - Metadata: Includes row count, preview, and quality metrics
    """
    BASE_URL = "https://rest.uniprot.org/uniprotkb/search"
    QUERY = "(venom OR toxin) AND reviewed:true"
    PAGE_SIZE = 50
    MAX_PAGES = 2
    MIN_SLEEP = 0.1
    MAX_SLEEP = 0.15

    all_records = []
    offset = 0
    pages_fetched = 0
    request_count = 0

    headers = {"User-Agent": "VenomFlow/1.0 (venom peptide research pipeline)"}

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
                extracted["organism"] = organism_data.get("scientificName", "")

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

    metadata = {
        "num_records": len(df),
        "preview": MetadataValue.md(df.head().to_markdown()),
        "fetch_time": MetadataValue.text(datetime.now().isoformat()),
        "organism_count": MetadataValue.int(df["organism"].nunique()),
        "avg_length": MetadataValue.float(df["length"].mean()),
    }

    context.log.info(f"Successfully fetched {len(df)} venom peptide records")

    return MaterializeResult(metadata=metadata)
