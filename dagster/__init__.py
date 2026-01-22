"""
VenomFlow Dagster Repository

This module defines the Dagster repository containing all assets, jobs,
schedules, and sensors for the VenomFlow data orchestration platform.
"""

from dagster import Definitions, load_assets_from_modules

from . import assets
from .resources import database

# Load all assets
all_assets = load_assets_from_modules([assets])

# Define the Dagster repository
defs = Definitions(
    assets=all_assets,
    resources={
        "database": database.DatabaseResource(),
    },
)
