"""
Bioactivity data model
"""

from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime
from enum import Enum


class ActivityType(str, Enum):
    """Types of biological activities."""
    CYTOTOXIC = "cytotoxic"
    ANTIMICROBIAL = "antimicrobial"
    NEUROTOXIC = "neurotoxic"
    HEMOLYTIC = "hemolytic"
    ANTICOAGULANT = "anticoagulant"
    ENZYME_INHIBITOR = "enzyme_inhibitor"
    OTHER = "other"


class BioactivityBase(BaseModel):
    """Base bioactivity model."""
    peptide_id: str = Field(..., description="Related peptide ID")
    activity_type: ActivityType = Field(..., description="Type of biological activity")
    target: Optional[str] = Field(None, description="Target organism or molecule")
    potency: Optional[float] = Field(None, description="Potency value (e.g., IC50, LD50)")
    unit: Optional[str] = Field(None, description="Unit of measurement")
    assay_type: Optional[str] = Field(None, description="Type of assay used")
    reference: Optional[str] = Field(None, description="Literature reference")


class BioactivityCreate(BioactivityBase):
    """Model for creating a new bioactivity record."""
    pass


class BioactivityUpdate(BaseModel):
    """Model for updating a bioactivity record."""
    target: Optional[str] = None
    potency: Optional[float] = None
    unit: Optional[str] = None
    assay_type: Optional[str] = None
    reference: Optional[str] = None


class Bioactivity(BioactivityBase):
    """Complete bioactivity model with database fields."""
    id: str = Field(..., description="Unique identifier")
    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")
    
    class Config:
        """Pydantic config."""
        from_attributes = True
