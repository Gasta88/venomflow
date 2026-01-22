"""
GraphQL Query definitions for VenomFlow API
"""

import strawberry
from typing import List, Optional
from resolvers.peptide import get_peptide, get_all_peptides


@strawberry.type
class Organism:
    """Organism type for GraphQL."""
    id: str
    name: str
    taxonomy_id: int
    lineage: Optional[str] = None


@strawberry.type
class Bioactivity:
    """Bioactivity type for GraphQL."""
    id: str
    type: str
    target: Optional[str] = None
    potency: Optional[float] = None
    unit: Optional[str] = None


@strawberry.type
class Properties:
    """Peptide properties type for GraphQL."""
    molecular_weight: Optional[float] = None
    isoelectric_point: Optional[float] = None
    hydrophobicity: Optional[float] = None
    net_charge: Optional[float] = None


@strawberry.type
class Peptide:
    """Peptide type for GraphQL."""
    id: str
    uniprot_id: str
    sequence: str
    length: int
    organism: Optional[Organism] = None
    bioactivities: List[Bioactivity] = strawberry.field(default_factory=list)
    properties: Optional[Properties] = None


@strawberry.type
class Query:
    """Root Query type."""
    
    @strawberry.field
    def peptide(self, id: str) -> Optional[Peptide]:
        """Get a peptide by ID."""
        return get_peptide(id)
    
    @strawberry.field
    def peptides(self, limit: int = 10, offset: int = 0) -> List[Peptide]:
        """Get all peptides with pagination."""
        return get_all_peptides(limit=limit, offset=offset)
    
    @strawberry.field
    def search_peptides(self, query: str) -> List[Peptide]:
        """Search peptides by sequence or name."""
        # TODO: Implement search logic
        return []
