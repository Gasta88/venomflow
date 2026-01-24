"""
Bioactivity Pydantic Models
Represents biological activity measurements and assay results
"""

from datetime import datetime
from enum import Enum
from typing import Optional, Dict, Any
from uuid import UUID

from pydantic import BaseModel, Field, ConfigDict, field_validator


class ActivityType(str, Enum):
    """Enumeration of common bioactivity measurement types"""
    IC50 = "IC50"
    EC50 = "EC50"
    KI = "Ki"
    KD = "Kd"
    LD50 = "LD50"
    MIC = "MIC"
    INHIBITION = "inhibition"
    ACTIVATION = "activation"
    CYTOTOXICITY = "cytotoxicity"
    NEUROTOXICITY = "neurotoxicity"
    ANTIMICROBIAL = "antimicrobial"
    HEMOLYTIC = "hemolytic"
    OTHER = "other"


class ActivityRelation(str, Enum):
    """Relation between measured value and activity (for inequality measurements)"""
    EQUAL = "="
    LESS_THAN = "<"
    GREATER_THAN = ">"
    LESS_THAN_EQUAL = "<="
    GREATER_THAN_EQUAL = ">="
    APPROXIMATELY = "~"


class ConfidenceLevel(str, Enum):
    """Confidence level in bioactivity measurement"""
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    UNKNOWN = "unknown"


class BioactivityBase(BaseModel):
    """Base bioactivity model with common fields"""
    
    model_config = ConfigDict(
        from_attributes=True,
        use_enum_values=True,
        json_schema_extra={
            "example": {
                "peptide_id": "550e8400-e29b-41d4-a716-446655440000",
                "activity_type": "IC50",
                "target": "Nicotinic acetylcholine receptor",
                "value": 5.2,
                "unit": "nM",
                "relation": "=",
                "assay_type": "radioligand binding",
                "organism_tested": "Rattus norvegicus",
                "confidence_level": "high",
                "reference": "Karlsson E, et al. (1972)",
                "pubmed_id": 4567890,
                "source": "chembl",
                "metadata": {
                    "assay_id": "CHEMBL123456",
                    "experimental_conditions": "pH 7.4, 25°C"
                }
            }
        }
    )
    
    peptide_id: UUID = Field(
        ...,
        description="Reference to the peptide this bioactivity belongs to"
    )
    
    activity_type: str = Field(
        ...,
        max_length=100,
        description="Type of biological activity measured",
        json_schema_extra={"example": "IC50"}
    )
    
    target: Optional[str] = Field(
        None,
        max_length=255,
        description="Biological target (receptor, ion channel, enzyme, etc.)",
        json_schema_extra={"example": "Nicotinic acetylcholine receptor"}
    )
    
    value: Optional[float] = Field(
        None,
        ge=0,
        description="Numeric activity value",
        json_schema_extra={"example": 5.2}
    )
    
    unit: Optional[str] = Field(
        None,
        max_length=50,
        description="Unit of measurement",
        json_schema_extra={"example": "nM"}
    )
    
    relation: Optional[ActivityRelation] = Field(
        ActivityRelation.EQUAL,
        description="Relation between value and activity (=, <, >, etc.)",
        json_schema_extra={"example": "="}
    )
    
    assay_type: Optional[str] = Field(
        None,
        max_length=100,
        description="Type of assay used for measurement",
        json_schema_extra={"example": "radioligand binding"}
    )
    
    organism_tested: Optional[str] = Field(
        None,
        max_length=255,
        description="Organism on which the peptide was tested",
        json_schema_extra={"example": "Rattus norvegicus"}
    )
    
    confidence_level: ConfidenceLevel = Field(
        ConfidenceLevel.UNKNOWN,
        description="Confidence level in the measurement",
        json_schema_extra={"example": "high"}
    )
    
    reference: Optional[str] = Field(
        None,
        description="Citation or reference for the data",
        json_schema_extra={"example": "Karlsson E, et al. (1972)"}
    )
    
    pubmed_id: Optional[int] = Field(
        None,
        gt=0,
        description="PubMed identifier for the publication",
        json_schema_extra={"example": 4567890}
    )
    
    source: str = Field(
        ...,
        max_length=100,
        description="Data source from which bioactivity was obtained",
        json_schema_extra={"example": "chembl"}
    )
    
    metadata: Optional[Dict[str, Any]] = Field(
        None,
        description="Additional metadata about the bioactivity",
        json_schema_extra={
            "example": {
                "assay_id": "CHEMBL123456",
                "experimental_conditions": "pH 7.4, 25°C"
            }
        }
    )
    
    @field_validator('activity_type')
    @classmethod
    def validate_activity_type(cls, v: str) -> str:
        """Validate and normalize activity type"""
        if not v or not v.strip():
            raise ValueError("Activity type cannot be empty")
        return v.strip()
    
    @field_validator('value')
    @classmethod
    def validate_value(cls, v: Optional[float]) -> Optional[float]:
        """Validate that value is non-negative if provided"""
        if v is not None and v < 0:
            raise ValueError("Activity value must be non-negative")
        return v
    
    @field_validator('pubmed_id')
    @classmethod
    def validate_pubmed_id(cls, v: Optional[int]) -> Optional[int]:
        """Validate PubMed ID is positive"""
        if v is not None and v <= 0:
            raise ValueError("PubMed ID must be a positive integer")
        return v


class BioactivityCreate(BioactivityBase):
    """Model for creating a new bioactivity record"""
    
    peptide_id: UUID = Field(..., description="Peptide ID is required")
    activity_type: str = Field(..., max_length=100)
    source: str = Field(..., max_length=100)


class BioactivityUpdate(BaseModel):
    """Model for updating an existing bioactivity record"""
    
    model_config = ConfigDict(from_attributes=True, use_enum_values=True)
    
    activity_type: Optional[str] = Field(None, max_length=100)
    target: Optional[str] = Field(None, max_length=255)
    value: Optional[float] = Field(None, ge=0)
    unit: Optional[str] = Field(None, max_length=50)
    relation: Optional[ActivityRelation] = None
    assay_type: Optional[str] = Field(None, max_length=100)
    organism_tested: Optional[str] = Field(None, max_length=255)
    confidence_level: Optional[ConfidenceLevel] = None
    reference: Optional[str] = None
    pubmed_id: Optional[int] = Field(None, gt=0)
    source: Optional[str] = Field(None, max_length=100)
    metadata: Optional[Dict[str, Any]] = None


class Bioactivity(BioactivityBase):
    """Complete bioactivity model with database fields"""
    
    id: UUID = Field(
        ...,
        description="Unique identifier for the bioactivity record"
    )
    
    created_at: datetime = Field(
        ...,
        description="Timestamp when the bioactivity was created"
    )
    
    updated_at: datetime = Field(
        ...,
        description="Timestamp when the bioactivity was last updated"
    )


class BioactivityWithPeptide(Bioactivity):
    """Bioactivity model with related peptide information"""
    
    peptide_name: Optional[str] = Field(
        None,
        description="Name of the peptide"
    )
    
    peptide_sequence: Optional[str] = Field(
        None,
        description="Sequence of the peptide"
    )
    
    organism_name: Optional[str] = Field(
        None,
        description="Scientific name of the source organism"
    )


class BioactivitySummary(BaseModel):
    """Summary statistics for bioactivity data"""
    
    model_config = ConfigDict(from_attributes=True)
    
    activity_type: str = Field(
        ...,
        description="Type of activity"
    )
    
    count: int = Field(
        ...,
        ge=0,
        description="Number of bioactivity records"
    )
    
    min_value: Optional[float] = Field(
        None,
        description="Minimum value observed"
    )
    
    max_value: Optional[float] = Field(
        None,
        description="Maximum value observed"
    )
    
    mean_value: Optional[float] = Field(
        None,
        description="Mean value"
    )
    
    median_value: Optional[float] = Field(
        None,
        description="Median value"
    )
    
    unit: Optional[str] = Field(
        None,
        description="Most common unit of measurement"
    )
