"""
VenomFlow GraphQL Types

Strawberry GraphQL type definitions for:
- Peptide: Core peptide data with sequences and metadata
- Organism: Organism taxonomy and classification
- Bioactivity: Biological activity measurements
- Properties: Physicochemical properties
- SimilarPeptide: Peptide similarity search results
- SearchResult: Paginated search results
"""

from datetime import datetime
from decimal import Decimal
from typing import List, Optional
from uuid import UUID

import strawberry


# =============================================================================
# ORGANISM TYPE
# =============================================================================


@strawberry.type
class Organism:
    """Organism taxonomy and classification data"""

    id: UUID
    name: str
    common_name: Optional[str] = None
    taxonomy_id: Optional[int] = None
    venom_type: Optional[str] = None
    description: Optional[str] = None
    source: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


# =============================================================================
# BIOACTIVITY TYPE
# =============================================================================


@strawberry.type
class Bioactivity:
    """Biological activity data for peptides"""

    id: UUID
    activity_type: str
    target: Optional[str] = None
    value: Optional[float] = None
    unit: Optional[str] = None
    assay_type: Optional[str] = None
    organism_tested: Optional[str] = None
    confidence_level: Optional[str] = None
    reference: Optional[str] = None
    pubmed_id: Optional[int] = None
    source: str
    created_at: Optional[datetime] = None


# =============================================================================
# PROPERTIES TYPE
# =============================================================================


@strawberry.type
class Properties:
    """Physicochemical properties of peptides"""

    id: UUID
    molecular_formula: Optional[str] = None
    isoelectric_point: Optional[float] = None
    hydrophobicity: Optional[float] = None
    charge_at_ph7: Optional[float] = None
    instability_index: Optional[float] = None
    aliphatic_index: Optional[float] = None
    aromaticity: Optional[float] = None
    molar_extinction: Optional[float] = None
    half_life_mammalian: Optional[int] = None
    logp: Optional[float] = None
    tpsa: Optional[float] = None
    num_h_donors: Optional[int] = None
    num_h_acceptors: Optional[int] = None
    calculation_method: Optional[str] = None
    calculated_at: Optional[datetime] = None


# =============================================================================
# PEPTIDE TYPE
# =============================================================================


@strawberry.type
class Peptide:
    """Core peptide data with sequences and metadata"""

    id: UUID
    uniprot_id: Optional[str] = None
    name: str
    sequence: str
    sequence_length: int
    molecular_weight: Optional[float] = None
    function_description: Optional[str] = None
    family: Optional[str] = None
    source: str
    quality_score: Optional[float] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    # Related data
    organism: Optional[Organism] = None
    bioactivities: Optional[List[Bioactivity]] = None
    properties: Optional[Properties] = None


# =============================================================================
# SIMILAR PEPTIDE TYPE (for similarity search results)
# =============================================================================


@strawberry.type
class SimilarPeptide:
    """Peptide similarity search result with BLAST-like scores"""

    peptide: Peptide
    similarity_score: float
    alignment_method: Optional[str] = None
    alignment_length: Optional[int] = None
    identities: Optional[int] = None
    gaps: Optional[int] = None
    e_value: Optional[float] = None
    bit_score: Optional[float] = None


# =============================================================================
# PAGINATION AND SEARCH TYPES
# =============================================================================


@strawberry.type
class PageInfo:
    """Pagination information for search results"""

    total: int
    page: int
    page_size: int
    total_pages: int
    has_next: bool
    has_previous: bool


@strawberry.type
class PeptideSearchResult:
    """Paginated peptide search results"""

    items: List[Peptide]
    page_info: PageInfo


@strawberry.type
class SimilaritySearchResult:
    """Results from similarity search"""

    query_accession: str
    threshold: float
    items: List[SimilarPeptide]
    total: int


# =============================================================================
# INPUT TYPES (Filters)
# =============================================================================


@strawberry.input
class PeptideFilters:
    """Filters for peptide searches"""

    family: Optional[str] = None
    venom_type: Optional[str] = None
    organism_name: Optional[str] = None
    min_sequence_length: Optional[int] = None
    max_sequence_length: Optional[int] = None
    min_molecular_weight: Optional[float] = None
    max_molecular_weight: Optional[float] = None
    min_quality_score: Optional[float] = None
    source: Optional[str] = None
    activity_type: Optional[str] = None
    target: Optional[str] = None


@strawberry.input
class PropertiesFilter:
    """Filter by physicochemical properties"""

    min_hydrophobicity: Optional[float] = None
    max_hydrophobicity: Optional[float] = None
    min_isoelectric_point: Optional[float] = None
    max_isoelectric_point: Optional[float] = None
    min_instability_index: Optional[float] = None
    max_instability_index: Optional[float] = None
    min_logp: Optional[float] = None
    max_logp: Optional[float] = None
    min_tpsa: Optional[float] = None
    max_tpsa: Optional[float] = None
    max_h_donors: Optional[int] = None
    max_h_acceptors: Optional[int] = None
