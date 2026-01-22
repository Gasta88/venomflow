"""
Peptide properties data model
"""

from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime


class PropertiesBase(BaseModel):
    """Base properties model."""
    peptide_id: str = Field(..., description="Related peptide ID")
    molecular_weight: Optional[float] = Field(None, description="Molecular weight (Da)")
    isoelectric_point: Optional[float] = Field(None, description="Isoelectric point (pI)")
    hydrophobicity: Optional[float] = Field(None, description="Grand average of hydropathicity (GRAVY)")
    net_charge: Optional[float] = Field(None, description="Net charge at pH 7")
    instability_index: Optional[float] = Field(None, description="Instability index")
    aliphatic_index: Optional[float] = Field(None, description="Aliphatic index")
    helix_fraction: Optional[float] = Field(None, description="Predicted helix fraction")
    turn_fraction: Optional[float] = Field(None, description="Predicted turn fraction")
    sheet_fraction: Optional[float] = Field(None, description="Predicted sheet fraction")


class PropertiesCreate(PropertiesBase):
    """Model for creating new properties."""
    pass


class PropertiesUpdate(BaseModel):
    """Model for updating properties."""
    molecular_weight: Optional[float] = None
    isoelectric_point: Optional[float] = None
    hydrophobicity: Optional[float] = None
    net_charge: Optional[float] = None
    instability_index: Optional[float] = None
    aliphatic_index: Optional[float] = None
    helix_fraction: Optional[float] = None
    turn_fraction: Optional[float] = None
    sheet_fraction: Optional[float] = None


class Properties(PropertiesBase):
    """Complete properties model with database fields."""
    id: str = Field(..., description="Unique identifier")
    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")
    
    class Config:
        """Pydantic config."""
        from_attributes = True
