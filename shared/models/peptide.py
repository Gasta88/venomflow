"""
Peptide data model
"""

from pydantic import BaseModel, Field, validator
from typing import Optional, List
from datetime import datetime


class PeptideBase(BaseModel):
    """Base peptide model."""
    uniprot_id: str = Field(..., description="UniProt accession ID")
    sequence: str = Field(..., description="Amino acid sequence")
    name: Optional[str] = Field(None, description="Peptide name")
    description: Optional[str] = Field(None, description="Peptide description")
    organism_id: str = Field(..., description="Related organism ID")
    
    @validator('sequence')
    def validate_sequence(cls, v):
        """Validate that sequence contains only valid amino acids."""
        valid_aa = set('ACDEFGHIKLMNPQRSTVWY')
        if not all(c in valid_aa for c in v.upper()):
            raise ValueError('Sequence contains invalid amino acids')
        return v.upper()


class PeptideCreate(PeptideBase):
    """Model for creating a new peptide."""
    pass


class PeptideUpdate(BaseModel):
    """Model for updating a peptide."""
    name: Optional[str] = None
    description: Optional[str] = None
    sequence: Optional[str] = None


class Peptide(PeptideBase):
    """Complete peptide model with database fields."""
    id: str = Field(..., description="Unique identifier")
    length: int = Field(..., description="Sequence length")
    molecular_weight: Optional[float] = Field(None, description="Molecular weight (Da)")
    isoelectric_point: Optional[float] = Field(None, description="Isoelectric point")
    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")
    
    class Config:
        """Pydantic config."""
        from_attributes = True
