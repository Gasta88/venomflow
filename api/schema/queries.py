"""
VenomFlow GraphQL Query Resolvers

Implements Query resolvers for:
- peptide(accession): Fetch peptide by UniProt ID
- searchPeptides(query, filters): Full-text search with Elasticsearch
- similarPeptides(accession, threshold): Similarity search using PostgreSQL
- peptidesByProperties(filters): Filter peptides by physicochemical properties
"""

import os
from math import ceil
from typing import List, Optional
from uuid import UUID

import strawberry

from .types import (
    Bioactivity,
    Organism,
    PageInfo,
    Peptide,
    PeptideFilters,
    PeptideSearchResult,
    Properties,
    PropertiesFilter,
    SimilaritySearchResult,
    SimilarPeptide,
)

# =============================================================================
# DATABASE AND ELASTICSEARCH CONNECTION UTILITIES
# =============================================================================


def get_postgres_connection():
    """Get PostgreSQL database connection using asyncpg"""
    import asyncpg

    return asyncpg.connect(
        host=os.getenv("POSTGRES_HOST", "postgres"),
        port=int(os.getenv("POSTGRES_PORT", "5432")),
        database=os.getenv("POSTGRES_DB", "venomflow"),
        user=os.getenv("POSTGRES_USER", "venomflow"),
        password=os.getenv("POSTGRES_PASSWORD", "venomflow"),
    )


def get_elasticsearch_client():
    """Get Elasticsearch client"""
    from elasticsearch import Elasticsearch

    return Elasticsearch(
        hosts=[
            f"http://{os.getenv('ELASTIC_HOST', 'elasticsearch')}:{os.getenv('ELASTIC_PORT', '9200')}"
        ],
        basic_auth=("elastic", os.getenv("ELASTIC_PASSWORD", "changeme")),
    )


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================


def row_to_peptide(row: dict, organism: Optional[Organism] = None) -> Peptide:
    """Convert database row to Peptide type"""
    return Peptide(
        id=row["id"],
        uniprot_id=row.get("uniprot_id"),
        name=row["name"],
        sequence=row["sequence"],
        sequence_length=row["sequence_length"],
        molecular_weight=float(row["molecular_weight"]) if row.get("molecular_weight") else None,
        function_description=row.get("function_description"),
        family=row.get("family"),
        source=row["source"],
        quality_score=float(row["quality_score"]) if row.get("quality_score") else None,
        created_at=row.get("created_at"),
        updated_at=row.get("updated_at"),
        organism=organism,
        bioactivities=None,
        properties=None,
    )


def row_to_organism(row: dict) -> Organism:
    """Convert database row to Organism type"""
    return Organism(
        id=row["id"],
        name=row["name"],
        common_name=row.get("common_name"),
        taxonomy_id=row.get("taxonomy_id"),
        venom_type=row.get("venom_type"),
        description=row.get("description"),
        source=row.get("source"),
        created_at=row.get("created_at"),
        updated_at=row.get("updated_at"),
    )


def row_to_bioactivity(row: dict) -> Bioactivity:
    """Convert database row to Bioactivity type"""
    return Bioactivity(
        id=row["id"],
        activity_type=row["activity_type"],
        target=row.get("target"),
        value=float(row["value"]) if row.get("value") else None,
        unit=row.get("unit"),
        assay_type=row.get("assay_type"),
        organism_tested=row.get("organism_tested"),
        confidence_level=row.get("confidence_level"),
        reference=row.get("reference"),
        pubmed_id=row.get("pubmed_id"),
        source=row["source"],
        created_at=row.get("created_at"),
    )


def row_to_properties(row: dict) -> Properties:
    """Convert database row to Properties type"""
    return Properties(
        id=row["id"],
        molecular_formula=row.get("molecular_formula"),
        isoelectric_point=float(row["isoelectric_point"]) if row.get("isoelectric_point") else None,
        hydrophobicity=float(row["hydrophobicity"]) if row.get("hydrophobicity") else None,
        charge_at_ph7=float(row["charge_at_ph7"]) if row.get("charge_at_ph7") else None,
        instability_index=float(row["instability_index"]) if row.get("instability_index") else None,
        aliphatic_index=float(row["aliphatic_index"]) if row.get("aliphatic_index") else None,
        aromaticity=float(row["aromaticity"]) if row.get("aromaticity") else None,
        molar_extinction=float(row["molar_extinction"]) if row.get("molar_extinction") else None,
        half_life_mammalian=row.get("half_life_mammalian"),
        logp=float(row["logp"]) if row.get("logp") else None,
        tpsa=float(row["tpsa"]) if row.get("tpsa") else None,
        num_h_donors=row.get("num_h_donors"),
        num_h_acceptors=row.get("num_h_acceptors"),
        calculation_method=row.get("calculation_method"),
        calculated_at=row.get("calculated_at"),
    )


async def fetch_peptide_relations(conn, peptide_id: UUID) -> tuple:
    """Fetch organism, bioactivities, and properties for a peptide"""
    # Fetch organism
    organism = None
    organism_row = await conn.fetchrow(
        """
        SELECT o.* FROM organisms o
        JOIN peptides p ON p.organism_id = o.id
        WHERE p.id = $1
        """,
        peptide_id,
    )
    if organism_row:
        organism = row_to_organism(dict(organism_row))

    # Fetch bioactivities
    bioactivity_rows = await conn.fetch(
        "SELECT * FROM bioactivity WHERE peptide_id = $1", peptide_id
    )
    bioactivities = [row_to_bioactivity(dict(row)) for row in bioactivity_rows]

    # Fetch properties
    properties = None
    props_row = await conn.fetchrow(
        "SELECT * FROM properties WHERE peptide_id = $1", peptide_id
    )
    if props_row:
        properties = row_to_properties(dict(props_row))

    return organism, bioactivities, properties


# =============================================================================
# QUERY RESOLVERS
# =============================================================================


@strawberry.type
class Query:
    """Root Query type for VenomFlow GraphQL API"""

    @strawberry.field
    async def peptide(self, accession: str) -> Optional[Peptide]:
        """
        Fetch a single peptide by UniProt accession ID
        
        Uses PostgreSQL for direct ID lookup
        """
        conn = await get_postgres_connection()
        try:
            row = await conn.fetchrow(
                "SELECT * FROM peptides WHERE uniprot_id = $1", accession
            )
            if not row:
                return None

            row_dict = dict(row)
            organism, bioactivities, properties = await fetch_peptide_relations(
                conn, row_dict["id"]
            )

            peptide = row_to_peptide(row_dict, organism)
            peptide.bioactivities = bioactivities if bioactivities else None
            peptide.properties = properties
            return peptide
        finally:
            await conn.close()

    @strawberry.field
    async def search_peptides(
        self,
        query: Optional[str] = None,
        filters: Optional[PeptideFilters] = None,
        page: int = 1,
        page_size: int = 20,
    ) -> PeptideSearchResult:
        """
        Search peptides using Elasticsearch for full-text search
        
        Supports:
        - Full-text search on name, sequence, function_description
        - Filtering by various peptide attributes
        - Pagination
        """
        es = get_elasticsearch_client()
        conn = await get_postgres_connection()

        try:
            # Build Elasticsearch query
            must_clauses = []
            filter_clauses = []

            # Full-text search
            if query:
                must_clauses.append(
                    {
                        "multi_match": {
                            "query": query,
                            "fields": [
                                "name^3",
                                "uniprot_id^2",
                                "function_description",
                                "family",
                                "sequence",
                            ],
                            "type": "best_fields",
                            "fuzziness": "AUTO",
                        }
                    }
                )

            # Apply filters
            if filters:
                if filters.family:
                    filter_clauses.append({"term": {"family.keyword": filters.family}})
                if filters.venom_type:
                    filter_clauses.append(
                        {"term": {"venom_type.keyword": filters.venom_type}}
                    )
                if filters.organism_name:
                    filter_clauses.append(
                        {
                            "match": {
                                "organism_name": {
                                    "query": filters.organism_name,
                                    "fuzziness": "AUTO",
                                }
                            }
                        }
                    )
                if filters.source:
                    filter_clauses.append({"term": {"source.keyword": filters.source}})
                if filters.activity_type:
                    filter_clauses.append(
                        {"term": {"activity_types.keyword": filters.activity_type}}
                    )
                if filters.target:
                    filter_clauses.append(
                        {"match": {"targets": {"query": filters.target}}}
                    )

                # Range filters
                if filters.min_sequence_length or filters.max_sequence_length:
                    range_filter = {"range": {"sequence_length": {}}}
                    if filters.min_sequence_length:
                        range_filter["range"]["sequence_length"][
                            "gte"
                        ] = filters.min_sequence_length
                    if filters.max_sequence_length:
                        range_filter["range"]["sequence_length"][
                            "lte"
                        ] = filters.max_sequence_length
                    filter_clauses.append(range_filter)

                if filters.min_molecular_weight or filters.max_molecular_weight:
                    range_filter = {"range": {"molecular_weight": {}}}
                    if filters.min_molecular_weight:
                        range_filter["range"]["molecular_weight"][
                            "gte"
                        ] = filters.min_molecular_weight
                    if filters.max_molecular_weight:
                        range_filter["range"]["molecular_weight"][
                            "lte"
                        ] = filters.max_molecular_weight
                    filter_clauses.append(range_filter)

                if filters.min_quality_score:
                    filter_clauses.append(
                        {"range": {"quality_score": {"gte": filters.min_quality_score}}}
                    )

            # Build final query
            es_query = {"bool": {}}
            if must_clauses:
                es_query["bool"]["must"] = must_clauses
            else:
                es_query["bool"]["must"] = [{"match_all": {}}]

            if filter_clauses:
                es_query["bool"]["filter"] = filter_clauses

            # Execute search
            from_offset = (page - 1) * page_size

            try:
                response = es.search(
                    index="peptides",
                    query=es_query,
                    from_=from_offset,
                    size=page_size,
                    sort=[{"quality_score": "desc"}, "_score"],
                )
                
                total = response["hits"]["total"]["value"]
                hits = response["hits"]["hits"]
                peptide_ids = [hit["_source"]["id"] for hit in hits]
            except Exception:
                # Fallback to PostgreSQL if Elasticsearch is not available
                total = 0
                peptide_ids = []

            # If Elasticsearch returned no results or is unavailable, fall back to PostgreSQL
            if not peptide_ids:
                # Build PostgreSQL query
                sql = "SELECT * FROM peptides WHERE 1=1"
                params = []
                param_count = 0

                if query:
                    param_count += 1
                    sql += f" AND (name ILIKE ${param_count} OR uniprot_id ILIKE ${param_count} OR function_description ILIKE ${param_count})"
                    params.append(f"%{query}%")

                if filters:
                    if filters.family:
                        param_count += 1
                        sql += f" AND family = ${param_count}"
                        params.append(filters.family)
                    if filters.source:
                        param_count += 1
                        sql += f" AND source = ${param_count}"
                        params.append(filters.source)
                    if filters.min_sequence_length:
                        param_count += 1
                        sql += f" AND sequence_length >= ${param_count}"
                        params.append(filters.min_sequence_length)
                    if filters.max_sequence_length:
                        param_count += 1
                        sql += f" AND sequence_length <= ${param_count}"
                        params.append(filters.max_sequence_length)
                    if filters.min_quality_score:
                        param_count += 1
                        sql += f" AND quality_score >= ${param_count}"
                        params.append(filters.min_quality_score)

                # Get total count
                count_sql = sql.replace("SELECT *", "SELECT COUNT(*)")
                total = await conn.fetchval(count_sql, *params)

                # Add pagination
                sql += " ORDER BY quality_score DESC NULLS LAST, created_at DESC"
                param_count += 1
                sql += f" LIMIT ${param_count}"
                params.append(page_size)
                param_count += 1
                sql += f" OFFSET ${param_count}"
                params.append(from_offset)

                rows = await conn.fetch(sql, *params)
                peptide_ids = [row["id"] for row in rows]

            # Fetch full peptide data from PostgreSQL
            peptides = []
            if peptide_ids:
                for peptide_id in peptide_ids:
                    if isinstance(peptide_id, str):
                        peptide_id = UUID(peptide_id)
                    row = await conn.fetchrow(
                        "SELECT * FROM peptides WHERE id = $1", peptide_id
                    )
                    if row:
                        row_dict = dict(row)
                        organism, bioactivities, properties = (
                            await fetch_peptide_relations(conn, peptide_id)
                        )
                        peptide = row_to_peptide(row_dict, organism)
                        peptide.bioactivities = bioactivities if bioactivities else None
                        peptide.properties = properties
                        peptides.append(peptide)

            total_pages = ceil(total / page_size) if total > 0 else 0

            return PeptideSearchResult(
                items=peptides,
                page_info=PageInfo(
                    total=total,
                    page=page,
                    page_size=page_size,
                    total_pages=total_pages,
                    has_next=page < total_pages,
                    has_previous=page > 1,
                ),
            )
        finally:
            await conn.close()

    @strawberry.field
    async def similar_peptides(
        self,
        accession: str,
        threshold: float = 0.5,
        limit: int = 20,
    ) -> SimilaritySearchResult:
        """
        Find peptides similar to a given peptide by UniProt accession
        
        Uses PostgreSQL peptide_similarities table for pre-computed BLAST results
        """
        conn = await get_postgres_connection()

        try:
            # Get the query peptide ID
            query_peptide = await conn.fetchrow(
                "SELECT id FROM peptides WHERE uniprot_id = $1", accession
            )

            if not query_peptide:
                return SimilaritySearchResult(
                    query_accession=accession,
                    threshold=threshold,
                    items=[],
                    total=0,
                )

            query_peptide_id = query_peptide["id"]

            # Find similar peptides from pre-computed similarities
            similarity_rows = await conn.fetch(
                """
                SELECT 
                    CASE 
                        WHEN ps.peptide_id_1 = $1 THEN ps.peptide_id_2
                        ELSE ps.peptide_id_1
                    END as similar_peptide_id,
                    ps.similarity_score,
                    ps.alignment_method,
                    ps.alignment_length,
                    ps.identities,
                    ps.gaps,
                    ps.score as bit_score
                FROM peptide_similarities ps
                WHERE (ps.peptide_id_1 = $1 OR ps.peptide_id_2 = $1)
                AND ps.similarity_score >= $2
                ORDER BY ps.similarity_score DESC
                LIMIT $3
                """,
                query_peptide_id,
                threshold,
                limit,
            )

            similar_peptides = []
            for sim_row in similarity_rows:
                peptide_row = await conn.fetchrow(
                    "SELECT * FROM peptides WHERE id = $1",
                    sim_row["similar_peptide_id"],
                )
                if peptide_row:
                    row_dict = dict(peptide_row)
                    organism, bioactivities, properties = await fetch_peptide_relations(
                        conn, sim_row["similar_peptide_id"]
                    )
                    peptide = row_to_peptide(row_dict, organism)
                    peptide.bioactivities = bioactivities if bioactivities else None
                    peptide.properties = properties

                    similar_peptides.append(
                        SimilarPeptide(
                            peptide=peptide,
                            similarity_score=float(sim_row["similarity_score"]),
                            alignment_method=sim_row.get("alignment_method"),
                            alignment_length=sim_row.get("alignment_length"),
                            identities=sim_row.get("identities"),
                            gaps=sim_row.get("gaps"),
                            e_value=None,  # Not stored in current schema
                            bit_score=float(sim_row["bit_score"]) if sim_row.get("bit_score") else None,
                        )
                    )

            return SimilaritySearchResult(
                query_accession=accession,
                threshold=threshold,
                items=similar_peptides,
                total=len(similar_peptides),
            )
        finally:
            await conn.close()

    @strawberry.field
    async def peptides_by_properties(
        self,
        filters: PropertiesFilter,
        page: int = 1,
        page_size: int = 20,
    ) -> PeptideSearchResult:
        """
        Filter peptides by physicochemical properties
        
        Uses PostgreSQL for property-based filtering with joins
        """
        conn = await get_postgres_connection()

        try:
            # Build query with property filters
            sql = """
                SELECT p.* FROM peptides p
                JOIN properties pr ON p.id = pr.peptide_id
                WHERE 1=1
            """
            count_sql = """
                SELECT COUNT(*) FROM peptides p
                JOIN properties pr ON p.id = pr.peptide_id
                WHERE 1=1
            """
            params = []
            param_count = 0

            # Apply property filters
            if filters.min_hydrophobicity is not None:
                param_count += 1
                sql += f" AND pr.hydrophobicity >= ${param_count}"
                count_sql += f" AND pr.hydrophobicity >= ${param_count}"
                params.append(filters.min_hydrophobicity)

            if filters.max_hydrophobicity is not None:
                param_count += 1
                sql += f" AND pr.hydrophobicity <= ${param_count}"
                count_sql += f" AND pr.hydrophobicity <= ${param_count}"
                params.append(filters.max_hydrophobicity)

            if filters.min_isoelectric_point is not None:
                param_count += 1
                sql += f" AND pr.isoelectric_point >= ${param_count}"
                count_sql += f" AND pr.isoelectric_point >= ${param_count}"
                params.append(filters.min_isoelectric_point)

            if filters.max_isoelectric_point is not None:
                param_count += 1
                sql += f" AND pr.isoelectric_point <= ${param_count}"
                count_sql += f" AND pr.isoelectric_point <= ${param_count}"
                params.append(filters.max_isoelectric_point)

            if filters.min_instability_index is not None:
                param_count += 1
                sql += f" AND pr.instability_index >= ${param_count}"
                count_sql += f" AND pr.instability_index >= ${param_count}"
                params.append(filters.min_instability_index)

            if filters.max_instability_index is not None:
                param_count += 1
                sql += f" AND pr.instability_index <= ${param_count}"
                count_sql += f" AND pr.instability_index <= ${param_count}"
                params.append(filters.max_instability_index)

            if filters.min_logp is not None:
                param_count += 1
                sql += f" AND pr.logp >= ${param_count}"
                count_sql += f" AND pr.logp >= ${param_count}"
                params.append(filters.min_logp)

            if filters.max_logp is not None:
                param_count += 1
                sql += f" AND pr.logp <= ${param_count}"
                count_sql += f" AND pr.logp <= ${param_count}"
                params.append(filters.max_logp)

            if filters.min_tpsa is not None:
                param_count += 1
                sql += f" AND pr.tpsa >= ${param_count}"
                count_sql += f" AND pr.tpsa >= ${param_count}"
                params.append(filters.min_tpsa)

            if filters.max_tpsa is not None:
                param_count += 1
                sql += f" AND pr.tpsa <= ${param_count}"
                count_sql += f" AND pr.tpsa <= ${param_count}"
                params.append(filters.max_tpsa)

            if filters.max_h_donors is not None:
                param_count += 1
                sql += f" AND pr.num_h_donors <= ${param_count}"
                count_sql += f" AND pr.num_h_donors <= ${param_count}"
                params.append(filters.max_h_donors)

            if filters.max_h_acceptors is not None:
                param_count += 1
                sql += f" AND pr.num_h_acceptors <= ${param_count}"
                count_sql += f" AND pr.num_h_acceptors <= ${param_count}"
                params.append(filters.max_h_acceptors)

            # Get total count
            total = await conn.fetchval(count_sql, *params)

            # Add pagination
            from_offset = (page - 1) * page_size
            sql += " ORDER BY p.quality_score DESC NULLS LAST"
            param_count += 1
            sql += f" LIMIT ${param_count}"
            params.append(page_size)
            param_count += 1
            sql += f" OFFSET ${param_count}"
            params.append(from_offset)

            rows = await conn.fetch(sql, *params)

            # Build peptide objects
            peptides = []
            for row in rows:
                row_dict = dict(row)
                organism, bioactivities, properties = await fetch_peptide_relations(
                    conn, row_dict["id"]
                )
                peptide = row_to_peptide(row_dict, organism)
                peptide.bioactivities = bioactivities if bioactivities else None
                peptide.properties = properties
                peptides.append(peptide)

            total_pages = ceil(total / page_size) if total > 0 else 0

            return PeptideSearchResult(
                items=peptides,
                page_info=PageInfo(
                    total=total,
                    page=page,
                    page_size=page_size,
                    total_pages=total_pages,
                    has_next=page < total_pages,
                    has_previous=page > 1,
                ),
            )
        finally:
            await conn.close()

    @strawberry.field
    async def organisms(
        self,
        venom_type: Optional[str] = None,
        page: int = 1,
        page_size: int = 20,
    ) -> List[Organism]:
        """
        List organisms with optional venom type filter
        """
        conn = await get_postgres_connection()

        try:
            sql = "SELECT * FROM organisms WHERE 1=1"
            params = []
            param_count = 0

            if venom_type:
                param_count += 1
                sql += f" AND venom_type = ${param_count}"
                params.append(venom_type)

            sql += " ORDER BY name"
            from_offset = (page - 1) * page_size
            param_count += 1
            sql += f" LIMIT ${param_count}"
            params.append(page_size)
            param_count += 1
            sql += f" OFFSET ${param_count}"
            params.append(from_offset)

            rows = await conn.fetch(sql, *params)
            return [row_to_organism(dict(row)) for row in rows]
        finally:
            await conn.close()
