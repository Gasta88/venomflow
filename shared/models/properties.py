"""
Physicochemical Properties Pydantic Models
Represents calculated physicochemical properties of peptides
"""

from datetime import datetime
from typing import Optional, Dict, Any
from uuid import UUID

from pydantic import BaseModel, Field, ConfigDict, field_validator


class PropertiesBase(BaseModel):
    """Base physicochemical properties model"""
    
    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={
            "example": {
                "peptide_id": "550e8400-e29b-41d4-a716-446655440000",
                "molecular_formula": "C304H480N84O103S7",
                "isoelectric_point": 8.45,
                "hydrophobicity": -0.623,
                "charge_at_ph7": 2.5,
                "instability_index": 32.15,
                "aliphatic_index": 68.33,
                "aromaticity": 0.0476,
                "molar_extinction": 9970.0,
                "half_life_mammalian": 7200,
                "amino_acid_composition": {
                    "A": 4, "C": 8, "D": 2, "E": 3, "F": 1,
                    "G": 5, "H": 2, "I": 3, "K": 7, "L": 4,
                    "M": 1, "N": 6, "P": 4, "Q": 2, "R": 6,
                    "S": 4, "T": 5, "V": 3, "W": 1, "Y": 3
                },
                "calculation_method": "BioPython ProtParam",
                "metadata": {
                    "calculation_version": "1.79",
                    "calculation_date": "2024-01-24"
                }
            }
        }
    )
    
    peptide_id: UUID = Field(
        ...,
        description="Reference to the peptide these properties belong to"
    )
    
    molecular_formula: Optional[str] = Field(
        None,
        max_length=255,
        description="Molecular formula of the peptide",
        json_schema_extra={"example": "C304H480N84O103S7"}
    )
    
    isoelectric_point: Optional[float] = Field(
        None,
        ge=0.0,
        le=14.0,
        description="Isoelectric point (pI) - pH at which net charge is zero",
        json_schema_extra={"example": 8.45}
    )
    
    hydrophobicity: Optional[float] = Field(
        None,
        description="Grand average of hydropathicity (GRAVY) - measure of hydrophobicity",
        json_schema_extra={"example": -0.623}
    )
    
    charge_at_ph7: Optional[float] = Field(
        None,
        description="Net charge of the peptide at pH 7.0",
        json_schema_extra={"example": 2.5}
    )
    
    instability_index: Optional[float] = Field(
        None,
        ge=0.0,
        description="Instability index - estimate of protein stability in vitro (>40 is unstable)",
        json_schema_extra={"example": 32.15}
    )
    
    aliphatic_index: Optional[float] = Field(
        None,
        ge=0.0,
        le=200.0,
        description="Aliphatic index - relative volume of aliphatic side chains",
        json_schema_extra={"example": 68.33}
    )
    
    aromaticity: Optional[float] = Field(
        None,
        ge=0.0,
        le=1.0,
        description="Aromaticity - frequency of aromatic amino acids (Phe, Trp, Tyr)",
        json_schema_extra={"example": 0.0476}
    )
    
    molar_extinction: Optional[float] = Field(
        None,
        ge=0.0,
        description="Molar extinction coefficient at 280nm (M⁻¹cm⁻¹)",
        json_schema_extra={"example": 9970.0}
    )
    
    half_life_mammalian: Optional[int] = Field(
        None,
        ge=0,
        description="Estimated half-life in mammalian cells (seconds)",
        json_schema_extra={"example": 7200}
    )
    
    amino_acid_composition: Optional[Dict[str, int]] = Field(
        None,
        description="Count of each amino acid in the sequence",
        json_schema_extra={
            "example": {
                "A": 4, "C": 8, "D": 2, "E": 3, "F": 1,
                "G": 5, "H": 2, "I": 3, "K": 7, "L": 4
            }
        }
    )
    
    calculation_method: Optional[str] = Field(
        None,
        max_length=100,
        description="Tool or method used for property calculation",
        json_schema_extra={"example": "BioPython ProtParam"}
    )
    
    metadata: Optional[Dict[str, Any]] = Field(
        None,
        description="Additional metadata about calculations",
        json_schema_extra={
            "example": {
                "calculation_version": "1.79",
                "calculation_date": "2024-01-24"
            }
        }
    )
    
    @field_validator('isoelectric_point')
    @classmethod
    def validate_isoelectric_point(cls, v: Optional[float]) -> Optional[float]:
        """Validate isoelectric point is within valid pH range"""
        if v is not None and (v < 0.0 or v > 14.0):
            raise ValueError("Isoelectric point must be between 0.0 and 14.0")
        return v
    
    @field_validator('instability_index')
    @classmethod
    def validate_instability_index(cls, v: Optional[float]) -> Optional[float]:
        """Validate instability index is non-negative"""
        if v is not None and v < 0.0:
            raise ValueError("Instability index must be non-negative")
        return v
    
    @field_validator('aliphatic_index')
    @classmethod
    def validate_aliphatic_index(cls, v: Optional[float]) -> Optional[float]:
        """Validate aliphatic index is within valid range"""
        if v is not None and (v < 0.0 or v > 200.0):
            raise ValueError("Aliphatic index must be between 0.0 and 200.0")
        return v
    
    @field_validator('aromaticity')
    @classmethod
    def validate_aromaticity(cls, v: Optional[float]) -> Optional[float]:
        """Validate aromaticity is between 0 and 1"""
        if v is not None and (v < 0.0 or v > 1.0):
            raise ValueError("Aromaticity must be between 0.0 and 1.0")
        return v
    
    @field_validator('molar_extinction')
    @classmethod
    def validate_molar_extinction(cls, v: Optional[float]) -> Optional[float]:
        """Validate molar extinction coefficient is non-negative"""
        if v is not None and v < 0.0:
            raise ValueError("Molar extinction coefficient must be non-negative")
        return v
    
    @field_validator('amino_acid_composition')
    @classmethod
    def validate_amino_acid_composition(cls, v: Optional[Dict[str, int]]) -> Optional[Dict[str, int]]:
        """Validate amino acid composition"""
        if v is not None:
            valid_amino_acids = set('ACDEFGHIKLMNPQRSTVWY')
            for aa, count in v.items():
                if aa not in valid_amino_acids:
                    raise ValueError(f"Invalid amino acid code: {aa}")
                if count < 0:
                    raise ValueError(f"Amino acid count must be non-negative, got {count} for {aa}")
        return v


class PropertiesCreate(PropertiesBase):
    """Model for creating new physicochemical properties"""
    
    peptide_id: UUID = Field(..., description="Peptide ID is required")


class PropertiesUpdate(BaseModel):
    """Model for updating existing physicochemical properties"""
    
    model_config = ConfigDict(from_attributes=True)
    
    molecular_formula: Optional[str] = Field(None, max_length=255)
    isoelectric_point: Optional[float] = Field(None, ge=0.0, le=14.0)
    hydrophobicity: Optional[float] = None
    charge_at_ph7: Optional[float] = None
    instability_index: Optional[float] = Field(None, ge=0.0)
    aliphatic_index: Optional[float] = Field(None, ge=0.0, le=200.0)
    aromaticity: Optional[float] = Field(None, ge=0.0, le=1.0)
    molar_extinction: Optional[float] = Field(None, ge=0.0)
    half_life_mammalian: Optional[int] = Field(None, ge=0)
    amino_acid_composition: Optional[Dict[str, int]] = None
    calculation_method: Optional[str] = Field(None, max_length=100)
    metadata: Optional[Dict[str, Any]] = None


class PhysicochemicalProperties(PropertiesBase):
    """Complete physicochemical properties model with database fields"""
    
    id: UUID = Field(
        ...,
        description="Unique identifier for the properties record"
    )
    
    calculated_at: datetime = Field(
        ...,
        description="Timestamp when properties were calculated"
    )
    
    created_at: datetime = Field(
        ...,
        description="Timestamp when the record was created"
    )
    
    updated_at: datetime = Field(
        ...,
        description="Timestamp when the record was last updated"
    )


class PropertiesWithPeptide(PhysicochemicalProperties):
    """Properties model with related peptide information"""
    
    peptide_name: Optional[str] = Field(
        None,
        description="Name of the peptide"
    )
    
    peptide_sequence: Optional[str] = Field(
        None,
        description="Sequence of the peptide"
    )
    
    sequence_length: Optional[int] = Field(
        None,
        ge=0,
        description="Length of the peptide sequence"
    )


class PropertiesComparison(BaseModel):
    """Model for comparing properties of multiple peptides"""
    
    model_config = ConfigDict(from_attributes=True)
    
    peptide_id: UUID = Field(..., description="Peptide identifier")
    peptide_name: str = Field(..., description="Peptide name")
    molecular_weight: Optional[float] = None
    isoelectric_point: Optional[float] = None
    hydrophobicity: Optional[float] = None
    charge_at_ph7: Optional[float] = None
    instability_index: Optional[float] = None
    similarity_score: Optional[float] = Field(
        None,
        ge=0.0,
        le=1.0,
        description="Overall property similarity score to reference peptide"
    )
