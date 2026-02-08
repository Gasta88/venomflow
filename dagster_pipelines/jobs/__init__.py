"""
Dagster job definitions for VenomFlow pipeline.

Jobs group assets together for execution with a single click.
"""

from dagster import AssetSelection, define_asset_job


venom_flow_pipeline = define_asset_job(
    name="venom_flow_pipeline",
    description="Ingests venom peptides, enriches with properties and BLAST similarities, then indexes to Elasticsearch",
    selection=AssetSelection.all(),
)
