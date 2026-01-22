"""
Organism data model
"""

from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime


class OrganismBase(BaseModel):
    """Base organism model."""
    name: str = Field(..., description="Organism scientific name")
    common_name: Optional[str] = Field(None, description="Common name")
    taxonomy_id: int = Field(..., description="NCBI taxonomy ID")
    lineage: Optional[str] = Field(None, description="Taxonomic lineage")


class OrganismCreate(OrganismBase):
    """Model for creating a new organism."""
    pass


class OrganismUpdate(BaseModel):
    """Model for updating an organism."""
    name: Optional[str] = None
    common_name: Optional[str] = None
    lineage: Optional[str] = None


class Organism(OrganismBase):
    """Complete organism model with database fields."""
    id: str = Field(..., description="Unique identifier")
    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")
    
    class Config:
        """Pydantic config."""
        from_attributes = True
