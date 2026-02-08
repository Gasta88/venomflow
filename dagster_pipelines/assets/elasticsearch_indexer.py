"""
Dagster asset for indexing enriched peptide data to Elasticsearch.

Creates peptides index with custom k-mer analyzer for sequence similarity search
and bulk indexes all peptides from peptides_enriched database view.
"""

import logging
from typing import Any, Dict, List, Tuple

from elasticsearch import Elasticsearch, helpers
from sqlalchemy import text

from dagster import AssetExecutionContext, MaterializeResult, MetadataValue, asset

from resources.database import DatabaseResource
from resources.elasticsearch import ElasticsearchResource

logger = logging.getLogger(__name__)

INDEX_NAME = "peptides"
BATCH_SIZE = 100


def _create_peptides_index(es_client: Elasticsearch, index_name: str) -> bool:
    """
    Create peptides index with custom k-mer analyzer and mapping.

    Args:
        es_client: Elasticsearch client instance
        index_name: Name of the index to create

    Returns:
        True if index created or already exists, False on error
    """
    analyzer_config = _get_kmer_analyzer_config()
    mapping = _get_peptides_index_mapping()

    index_config = {
        "settings": {
            "analysis": analyzer_config,
            "number_of_shards": 1,
            "number_of_replicas": 0,
        },
        "mappings": mapping,
    }

    if es_client.indices.exists(index=index_name):
        logger.info(f"Index '{index_name}' already exists")
        return True

    try:
        es_client.indices.create(index=index_name, body=index_config, ignore=400)
        logger.info(f"Created index '{index_name}' with k-mer analyzer")
        return True
    except Exception as e:
        logger.error(f"Failed to create index '{index_name}': {e}")
        return False


def _get_kmer_analyzer_config() -> Dict[str, Any]:
    """
    Return k-mer analyzer configuration for sequence similarity search.

    Uses edge_ngram tokenizer with 3-6 character sliding window to break
    sequences into overlapping k-mers for fuzzy matching.

    Returns:
        Analyzer configuration dictionary
    """
    return {
        "tokenizer": {
            "kmer_tokenizer": {
                "type": "edge_ngram",
                "min_gram": 3,
                "max_gram": 6,
                "token_chars": [],
            }
        },
        "analyzer": {
            "kmer_analyzer": {
                "type": "custom",
                "tokenizer": "kmer_tokenizer",
            }
        },
    }


def _get_peptides_index_mapping() -> Dict[str, Any]:
    """
    Return Elasticsearch mapping configuration for peptides index.

    Mapping includes:
    - accession/name: keyword for exact matching
    - sequence: text with k-mer analyzer for similarity search
    - organism_name/common_name: text + keyword for flexible searching
    - function_description: text for full-text search
    - properties: nested object for physicochemical properties

    Returns:
        Mapping configuration dictionary
    """
    return {
        "properties": {
            "accession": {"type": "keyword"},
            "name": {"type": "keyword"},
            "sequence": {
                "type": "text",
                "analyzer": "kmer_analyzer",
                "fields": {
                    "exact": {"type": "keyword"},
                    "raw": {"type": "text", "analyzer": "standard"},
                },
            },
            "sequence_length": {"type": "integer"},
            "molecular_weight": {"type": "float"},
            "organism_name": {
                "type": "text",
                "fields": {"keyword": {"type": "keyword"}},
            },
            "organism_common_name": {
                "type": "text",
                "fields": {"keyword": {"type": "keyword"}},
            },
            "venom_type": {"type": "keyword"},
            "function_description": {"type": "text", "analyzer": "standard"},
            "family": {"type": "keyword"},
            "quality_score": {"type": "float"},
            "properties": {
                "properties": {
                    "isoelectric_point": {"type": "float"},
                    "hydrophobicity": {"type": "float"},
                    "charge_at_ph7": {"type": "float"},
                    "instability_index": {"type": "float"},
                    "aliphatic_index": {"type": "float"},
                    "aromaticity": {"type": "float"},
                    "logp": {"type": "float"},
                    "tpsa": {"type": "float"},
                    "num_h_donors": {"type": "integer"},
                    "num_h_acceptors": {"type": "integer"},
                }
            },
            "bioactivity_count": {"type": "integer"},
            "structure_count": {"type": "integer"},
            "created_at": {"type": "date"},
            "updated_at": {"type": "date"},
        }
    }


def _transform_peptide_to_doc(row: Any) -> Dict[str, Any]:
    """
    Transform database row to Elasticsearch document format.

    Args:
        row: Database row from peptides_enriched view

    Returns:
        Dictionary representing Elasticsearch document
    """
    doc = {
        "accession": row.uniprot_id or "",
        "name": row.name or "",
        "sequence": row.sequence or "",
        "sequence_length": row.sequence_length or 0,
        "molecular_weight": float(row.molecular_weight)
        if row.molecular_weight
        else None,
        "organism_name": row.organism_name or "",
        "organism_common_name": row.organism_common_name or "",
        "venom_type": row.venom_type or "",
        "function_description": row.function_description or "",
        "family": row.family or "",
        "quality_score": float(row.quality_score) if row.quality_score else 0.0,
        "bioactivity_count": row.bioactivity_count or 0,
        "structure_count": row.structure_count or 0,
        "created_at": row.created_at.isoformat() if row.created_at else None,
        "updated_at": row.updated_at.isoformat() if row.updated_at else None,
    }

    properties = {
        "isoelectric_point": float(row.isoelectric_point)
        if row.isoelectric_point
        else None,
        "hydrophobicity": float(row.hydrophobicity) if row.hydrophobicity else None,
        "charge_at_ph7": float(row.charge_at_ph7) if row.charge_at_ph7 else None,
        "instability_index": float(row.instability_index)
        if row.instability_index
        else None,
        "aliphatic_index": float(row.aliphatic_index) if row.aliphatic_index else None,
        "aromaticity": float(row.aromaticity) if row.aromaticity else None,
        "logp": float(row.logp) if row.logp else None,
        "tpsa": float(row.tpsa) if row.tpsa else None,
        "num_h_donors": row.num_h_donors if row.num_h_donors is not None else None,
        "num_h_acceptors": row.num_h_acceptors
        if row.num_h_acceptors is not None
        else None,
    }

    doc["properties"] = properties

    return doc


def _bulk_index_documents(
    es_client: Elasticsearch,
    index_name: str,
    documents: List[Dict[str, Any]],
    context: AssetExecutionContext,
) -> Tuple[int, int]:
    """
    Bulk index documents to Elasticsearch.

    Args:
        es_client: Elasticsearch client instance
        index_name: Name of the index
        documents: List of documents to index
        context: Dagster asset execution context

    Returns:
        Tuple of (success_count, error_count)
    """
    success_count = 0
    error_count = 0

    actions = []
    for doc in documents:
        doc_id = doc.get("accession", doc.get("name", ""))
        actions.append(
            {
                "_index": index_name,
                "_id": doc_id,
                "_source": doc,
            }
        )

    try:
        for success, info in helpers.parallel_bulk(
            es_client,
            actions,
            chunk_size=BATCH_SIZE,
            raise_on_error=False,
            max_retries=3,
        ):
            if success:
                success_count += 1
            else:
                error_count += 1
                context.log.warning(f"Failed to index document: {info}")
    except Exception as e:
        context.log.error(f"Bulk indexing error: {e}")
        error_count += len(actions)

    return success_count, error_count


@asset(
    group_name="indexing",
    deps=["compute_peptide_properties", "compute_blast_similarities"],
    description="""
    Indexes enriched peptide data into Elasticsearch for fast search.

    Creates the 'peptides' index with custom k-mer analyzer for sequence similarity,
    then bulk indexes all peptides from the peptides_enriched view. Supports
    full-text search on sequence, function, and organism fields.

    Configuration:
    - Elasticsearch connection: via elasticsearch_resource
    - Index name: peptides
    - Batch size: 100 documents
    - k-mer tokenizer: 3-6 character sliding window
    """,
)
def index_peptides_to_elasticsearch(
    context: AssetExecutionContext,
    database: DatabaseResource,
    elasticsearch: ElasticsearchResource,
) -> MaterializeResult:
    """
    Dagster asset for indexing enriched peptides to Elasticsearch.

    Creates peptides index with k-mer analyzer, fetches peptides from
    peptides_enriched database view, transforms to Elasticsearch documents,
    and bulk indexes in batches of 100.

    Args:
        context: Dagster asset execution context
        database: Database resource for PostgreSQL connection
        elasticsearch: Elasticsearch resource for search operations

    Returns:
        MaterializeResult with metadata including documents indexed,
        batches processed, error count, and index creation status.
    """
    import time

    session = database.get_session()
    es_client = elasticsearch.get_client()

    documents_indexed = 0
    batch_count = 0
    error_count = 0
    index_created = False

    try:
        context.log.info("Creating Elasticsearch peptides index...")

        if not _create_peptides_index(es_client, INDEX_NAME):
            raise RuntimeError("Failed to create peptides index")

        index_created = True

        context.log.info("Fetching enriched peptides from database...")

        query = text("""
            SELECT
                id,
                uniprot_id,
                name,
                sequence,
                sequence_length,
                molecular_weight,
                organism_name,
                organism_common_name,
                venom_type,
                function_description,
                family,
                quality_score,
                isoelectric_point,
                hydrophobicity,
                charge_at_ph7,
                instability_index,
                aliphatic_index,
                aromaticity,
                logp,
                tpsa,
                num_h_donors,
                num_h_acceptors,
                bioactivity_count,
                structure_count,
                created_at,
                updated_at
            FROM peptides_enriched
            WHERE sequence IS NOT NULL
            AND length(sequence) > 0
            ORDER BY uniprot_id
        """)

        result = session.execute(query)
        peptides_data = result.fetchall()

        total_peptides = len(peptides_data)
        context.log.info(f"Found {total_peptides} peptides to index")

        if total_peptides == 0:
            context.log.warning("No peptides available to index")
            return MaterializeResult(
                metadata={
                    "index_created": MetadataValue.bool(True),
                    "documents_indexed": MetadataValue.int(0),
                    "batch_count": MetadataValue.int(0),
                    "error_count": MetadataValue.int(0),
                    "index_time_seconds": MetadataValue.float(0.0),
                    "index_name": MetadataValue.text(INDEX_NAME),
                    "kmer_analyzer": MetadataValue.text("3-6 gram sliding window"),
                }
            )

        start_time = time.time()

        documents_batch = []

        for i, row in enumerate(peptides_data):
            doc = _transform_peptide_to_doc(row)
            documents_batch.append(doc)

            if len(documents_batch) >= BATCH_SIZE or i == total_peptides - 1:
                batch_num = (i // BATCH_SIZE) + 1
                batch_count += 1

                context.log.info(
                    f"Processing batch {batch_num} ({len(documents_batch)} documents)"
                )

                success_count, batch_error_count = _bulk_index_documents(
                    es_client, INDEX_NAME, documents_batch, context
                )

                documents_indexed += success_count
                error_count += batch_error_count

                if error_count > 0:
                    context.log.warning(
                        f"Batch {batch_num} had {batch_error_count} errors"
                    )

                documents_batch.clear()

                if batch_num % 10 == 0:
                    context.log.info(
                        f"Progress: {documents_indexed}/{total_peptides} documents indexed"
                    )

        index_time_seconds = time.time() - start_time

        context.log.info(f"Successfully indexed {documents_indexed} documents")
        context.log.info(f"Completed {batch_count} batches")
        context.log.info(f"Errors: {error_count}")
        context.log.info(f"Index time: {index_time_seconds:.2f} seconds")

        metadata = {
            "index_created": MetadataValue.bool(index_created),
            "documents_indexed": MetadataValue.int(documents_indexed),
            "batch_count": MetadataValue.int(batch_count),
            "error_count": MetadataValue.int(error_count),
            "index_time_seconds": MetadataValue.float(index_time_seconds),
            "index_name": MetadataValue.text(INDEX_NAME),
            "kmer_analyzer": MetadataValue.text("3-6 gram sliding window"),
        }

        if documents_indexed > 0:
            context.log.info(f"Index name: {INDEX_NAME}")
            context.log.info("K-mer analyzer: 3-6 character sliding window")

        return MaterializeResult(metadata=metadata)

    except Exception as e:
        session.rollback()
        context.log.error(f"Error in index_peptides_to_elasticsearch: {e}")
        raise
    finally:
        session.close()
        if es_client:
            es_client.close()
