"""
Dagster job definitions for VenomFlow pipeline.

Jobs group assets together for execution with a single click.
"""

from dagster import AssetSelection, ScheduleDefinition, define_asset_job

venom_flow_pipeline = define_asset_job(
    name="venom_flow_pipeline",
    description="Ingests venom peptides, enriches with properties and BLAST similarities, then indexes to Elasticsearch",
    selection=AssetSelection.all(),
)

# Refresh the UniProt snapshot and re-enrich every day at 02:00 UTC.
venom_flow_daily_schedule = ScheduleDefinition(
    name="venom_flow_daily_schedule",
    job=venom_flow_pipeline,
    cron_schedule="0 2 * * *",
    description="Daily ingestion, enrichment and indexing run at 02:00 UTC",
)
