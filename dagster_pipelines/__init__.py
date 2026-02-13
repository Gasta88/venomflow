"""
VenomFlow Dagster Definitions

This module defines the main Dagster assets and definitions for the VenomFlow project.
Includes assets for data ingestion, enrichment, computation, and indexing.
"""

from dagster import Definitions

from assets import (
    venom_peptides_uniprot,
    compute_sequence_similarities,
    index_peptides_to_elasticsearch,
)
from assets.enrichment import compute_peptide_properties
from resources.database import database_resource
from resources.elasticsearch import elasticsearch_resource
from jobs import venom_flow_pipeline


# Create the Dagster definitions
defs = Definitions(
    assets=[
        venom_peptides_uniprot,
        compute_peptide_properties,
        compute_sequence_similarities,
        index_peptides_to_elasticsearch,
    ],
    jobs=[venom_flow_pipeline],
    resources={
        "database": database_resource,
        "elasticsearch": elasticsearch_resource,
    },
    asset_checks=[],
)
