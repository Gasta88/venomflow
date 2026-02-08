"""
Organism Pydantic Models
Represents organism taxonomy and classification data for venom research
"""

from datetime import datetime
from enum import Enum
from typing import Optional, Dict, Any
from uuid import UUID

from pydantic import BaseModel, Field, ConfigDict, field_validator


class VenomType(str, Enum):
    """Enumeration of venom-producing organism types"""
    SNAKE = "snake"
    SPIDER = "spider"
    SCORPION = "scorpion"
    CONE_SNAIL = "cone_snail"
    JELLYFISH = "jellyfish"
    BEE = "bee"
    WASP = "wasp"
    ANT = "ant"
    FROG = "frog"
    LIZARD = "lizard"
    FISH = "fish"
    OTHER = "other"


class DataSource(str, Enum):
    """Data source enumeration"""
    UNIPROT = "uniprot"
    MANUAL = "manual"
    GBIF = "gbif"
    OTHER = "other"


class OrganismBase(BaseModel):
    """Base organism model with common fields"""
    
    model_config = ConfigDict(
        from_attributes=True,
        use_enum_values=True,
        json_schema_extra={
            "example": {
                "name": "Naja naja",
                "common_name": "Indian cobra",
                "taxonomy_id": 35670,
                "taxonomy": {
                    "kingdom": "Animalia",
                    "phylum": "Chordata",
                    "class": "Reptilia",
                    "order": "Squamata",
                    "family": "Elapidae",
                    "genus": "Naja",
                    "species": "Naja naja"
                },
                "venom_type": "snake",
                "description": "The Indian cobra is a highly venomous snake species native to the Indian subcontinent",
                "source": "uniprot",
                "external_ids": {
                    "ncbi_taxonomy": "35670",
                    "uniprot_taxonomy": "35670",
                    "gbif": "2450804"
                }
            }
        }
    )
    
    name: str = Field(
        ...,
        min_length=1,
        max_length=255,
        description="Scientific name of the organism",
        json_schema_extra={"example": "Naja naja"}
    )
    
    common_name: Optional[str] = Field(
        None,
        max_length=255,
        description="Common name of the organism",
        json_schema_extra={"example": "Indian cobra"}
    )
    
    taxonomy_id: Optional[int] = Field(
        None,
        ge=1,
        description="Taxonomy ID for organism identification",
        json_schema_extra={"example": 35670}
    )
    
    taxonomy: Optional[Dict[str, Any]] = Field(
        None,
        description="Full taxonomic lineage as nested dictionary",
        json_schema_extra={
            "example": {
                "kingdom": "Animalia",
                "phylum": "Chordata",
                "class": "Reptilia",
                "order": "Squamata",
                "family": "Elapidae",
                "genus": "Naja",
                "species": "Naja naja"
            }
        }
    )
    
    venom_type: Optional[VenomType] = Field(
        None,
        description="Type of venom-producing organism",
        json_schema_extra={"example": "snake"}
    )
    
    description: Optional[str] = Field(
        None,
        description="Detailed description of the organism",
        json_schema_extra={"example": "The Indian cobra is a highly venomous snake species"}
    )
    
    source: Optional[DataSource] = Field(
        None,
        description="Data source from which organism was obtained",
        json_schema_extra={"example": "uniprot"}
    )
    
    external_ids: Optional[Dict[str, Any]] = Field(
        None,
        description="External database identifiers",
        json_schema_extra={
            "example": {
                "taxonomy_id": "35670",
                "uniprot_taxonomy": "35670",
                "gbif": "2450804"
            }
        }
    )
    
    @field_validator('name')
    @classmethod
    def validate_name(cls, v: str) -> str:
        """Validate that name is not empty"""
        if not v or not v.strip():
            raise ValueError("Organism name cannot be empty")
        return v.strip()
    
    @field_validator('taxonomy')
    @classmethod
    def validate_taxonomy(cls, v: Optional[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        """Validate taxonomy structure"""
        if v is not None:
            expected_ranks = ['kingdom', 'phylum', 'class', 'order', 'family', 'genus', 'species']
            # Ensure at least one taxonomic rank is present
            if not any(rank in v for rank in expected_ranks):
                raise ValueError("Taxonomy must contain at least one valid taxonomic rank")
        return v


class OrganismCreate(OrganismBase):
    """Model for creating a new organism"""
    
    name: str = Field(..., min_length=1, max_length=255)
    source: DataSource = Field(..., description="Data source is required on creation")


class OrganismUpdate(BaseModel):
    """Model for updating an existing organism"""
    
    model_config = ConfigDict(from_attributes=True, use_enum_values=True)
    
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    common_name: Optional[str] = Field(None, max_length=255)
    taxonomy_id: Optional[int] = Field(None, ge=1)
    taxonomy: Optional[Dict[str, Any]] = None
    venom_type: Optional[VenomType] = None
    description: Optional[str] = None
    source: Optional[DataSource] = None
    external_ids: Optional[Dict[str, Any]] = None


class Organism(OrganismBase):
    """Complete organism model with database fields"""
    
    id: UUID = Field(
        ...,
        description="Unique identifier for the organism"
    )
    
    created_at: datetime = Field(
        ...,
        description="Timestamp when the organism was created"
    )
    
    updated_at: datetime = Field(
        ...,
        description="Timestamp when the organism was last updated"
    )


class OrganismWithStats(Organism):
    """Organism model with additional statistics"""
    
    peptide_count: int = Field(
        default=0,
        ge=0,
        description="Number of peptides associated with this organism"
    )
    
    bioactivity_count: int = Field(
        default=0,
        ge=0,
        description="Total number of bioactivities across all peptides"
    )
