"""
Peptide Pydantic Models
Represents peptide sequences with metadata and computed fields
"""

import hashlib
import re
from datetime import datetime
from typing import Optional, Dict, Any
from uuid import UUID

from pydantic import BaseModel, Field, ConfigDict, field_validator, computed_field


class PeptideBase(BaseModel):
    """Base peptide model with common fields"""
    
    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={
            "example": {
                "uniprot_id": "P01420",
                "name": "Cobrotoxin",
                "sequence": "LECHNQQSSQPPTTKTCSGETNCYKKRWRDHRGYRTERGCGCPKVKPGVNLNCCRTDRCNN",
                "molecular_weight": 6927.98,
                "organism_id": "550e8400-e29b-41d4-a716-446655440000",
                "function_description": "Neurotoxin that binds to nicotinic acetylcholine receptors",
                "family": "Snake three-finger toxin",
                "source": "uniprot",
                "quality_score": 0.95,
                "metadata": {
                    "literature_count": 156,
                    "structure_available": True
                },
                "external_ids": {
                    "uniprot": "P01420",
                    "pdb": "1CTX",
                    "ncbi_protein": "CAA26146.1"
                }
            }
        }
    )
    
    uniprot_id: Optional[str] = Field(
        None,
        max_length=20,
        description="UniProt accession identifier",
        json_schema_extra={"example": "P01420"}
    )
    
    name: str = Field(
        ...,
        min_length=1,
        max_length=255,
        description="Peptide name or designation",
        json_schema_extra={"example": "Cobrotoxin"}
    )
    
    sequence: str = Field(
        ...,
        min_length=1,
        description="Amino acid sequence (single-letter code)",
        json_schema_extra={"example": "MKTLLLTLVVVTIACSLPLFA"}
    )
    
    molecular_weight: Optional[float] = Field(
        None,
        gt=0,
        description="Molecular weight in Daltons",
        json_schema_extra={"example": 6927.98}
    )
    
    organism_id: Optional[UUID] = Field(
        None,
        description="Reference to the organism this peptide comes from"
    )
    
    function_description: Optional[str] = Field(
        None,
        description="Functional description of the peptide",
        json_schema_extra={"example": "Neurotoxin that binds to nicotinic acetylcholine receptors"}
    )
    
    family: Optional[str] = Field(
        None,
        max_length=100,
        description="Protein family classification",
        json_schema_extra={"example": "Snake three-finger toxin"}
    )
    
    source: str = Field(
        ...,
        max_length=100,
        description="Data source from which peptide was obtained",
        json_schema_extra={"example": "uniprot"}
    )
    
    quality_score: Optional[float] = Field(
        None,
        ge=0.0,
        le=1.0,
        description="Data completeness score (0.00-1.00)",
        json_schema_extra={"example": 0.95}
    )
    
    metadata: Optional[Dict[str, Any]] = Field(
        None,
        description="Flexible metadata storage",
        json_schema_extra={
            "example": {
                "literature_count": 156,
                "structure_available": True
            }
        }
    )
    
    external_ids: Optional[Dict[str, Any]] = Field(
        None,
        description="Cross-references to other databases",
        json_schema_extra={
            "example": {
                "uniprot": "P01420",
                "pdb": "1CTX",
                "ncbi_protein": "CAA26146.1"
            }
        }
    )
    
    @field_validator('sequence')
    @classmethod
    def validate_sequence(cls, v: str) -> str:
        """Validate that sequence contains only valid amino acid codes"""
        v = v.upper().strip()
        
        # Check if sequence contains only valid amino acids
        valid_amino_acids = re.compile(r'^[ACDEFGHIKLMNPQRSTVWY]+$')
        if not valid_amino_acids.match(v):
            raise ValueError(
                "Sequence must contain only valid single-letter amino acid codes (ACDEFGHIKLMNPQRSTVWY)"
            )
        
        return v
    
    @field_validator('name')
    @classmethod
    def validate_name(cls, v: str) -> str:
        """Validate that name is not empty"""
        if not v or not v.strip():
            raise ValueError("Peptide name cannot be empty")
        return v.strip()
    
    @field_validator('quality_score')
    @classmethod
    def validate_quality_score(cls, v: Optional[float]) -> Optional[float]:
        """Validate quality score is between 0 and 1"""
        if v is not None and (v < 0.0 or v > 1.0):
            raise ValueError("Quality score must be between 0.0 and 1.0")
        return v
    
    @computed_field
    @property
    def sequence_length(self) -> int:
        """Compute the length of the peptide sequence"""
        return len(self.sequence)
    
    @computed_field
    @property
    def sequence_hash(self) -> str:
        """Compute SHA256 hash of the sequence for deduplication"""
        return hashlib.sha256(self.sequence.encode('utf-8')).hexdigest()


class PeptideCreate(PeptideBase):
    """Model for creating a new peptide"""
    
    name: str = Field(..., min_length=1, max_length=255)
    sequence: str = Field(..., min_length=1)
    source: str = Field(..., max_length=100)


class PeptideUpdate(BaseModel):
    """Model for updating an existing peptide"""
    
    model_config = ConfigDict(from_attributes=True)
    
    uniprot_id: Optional[str] = Field(None, max_length=20)
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    sequence: Optional[str] = Field(None, min_length=1)
    molecular_weight: Optional[float] = Field(None, gt=0)
    organism_id: Optional[UUID] = None
    function_description: Optional[str] = None
    family: Optional[str] = Field(None, max_length=100)
    source: Optional[str] = Field(None, max_length=100)
    quality_score: Optional[float] = Field(None, ge=0.0, le=1.0)
    metadata: Optional[Dict[str, Any]] = None
    external_ids: Optional[Dict[str, Any]] = None


class Peptide(PeptideBase):
    """Complete peptide model with database fields"""
    
    id: UUID = Field(
        ...,
        description="Unique identifier for the peptide"
    )
    
    created_at: datetime = Field(
        ...,
        description="Timestamp when the peptide was created"
    )
    
    updated_at: datetime = Field(
        ...,
        description="Timestamp when the peptide was last updated"
    )


class PeptideWithRelations(Peptide):
    """Peptide model with related organism and bioactivity data"""
    
    organism_name: Optional[str] = Field(
        None,
        description="Scientific name of the source organism"
    )
    
    bioactivity_count: int = Field(
        default=0,
        ge=0,
        description="Number of bioactivities associated with this peptide"
    )
    
    structure_count: int = Field(
        default=0,
        ge=0,
        description="Number of structures associated with this peptide"
    )
    
    has_properties: bool = Field(
        default=False,
        description="Whether physicochemical properties have been calculated"
    )


class PeptideSearchResult(BaseModel):
    """Model for peptide search results with relevance scoring"""
    
    model_config = ConfigDict(from_attributes=True)
    
    peptide: Peptide = Field(..., description="The peptide data")
    
    score: float = Field(
        ...,
        ge=0.0,
        description="Relevance score from search engine",
        json_schema_extra={"example": 0.87}
    )
    
    highlights: Optional[Dict[str, list[str]]] = Field(
        None,
        description="Highlighted matching text snippets",
        json_schema_extra={
            "example": {
                "function_description": ["<em>neurotoxin</em> that binds to receptors"]
            }
        }
    )
