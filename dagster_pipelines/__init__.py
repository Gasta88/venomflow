"""
VenomFlow Dagster Definitions

This module defines the main Dagster assets and definitions for the VenomFlow project.
Includes assets for data ingestion, enrichment, and computation.
"""

from dagster import Definitions

from assets import venom_peptides_uniprot, compute_blast_similarities
from assets.enrichment import compute_peptide_properties
from resources.database import database_resource


# Create the Dagster definitions
defs = Definitions(
    assets=[
        venom_peptides_uniprot,
        compute_peptide_properties,
        compute_blast_similarities,
    ],
    resources={
        "database": database_resource,
    },
    asset_checks=[],
)
