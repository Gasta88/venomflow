"""
VenomFlow Dagster Definitions

This module defines the main Dagster assets and definitions for the VenomFlow project.
Includes example assets for data ingestion, processing, and validation.
"""

from dagster import (
    Definitions,
    AssetExecutionContext,
    asset,
    MaterializeResult,
    MetadataValue,
)
import pandas as pd
from datetime import datetime

from assets import venom_peptides_uniprot


@asset(
    group_name="ingestion",
    description="Fetches sample protein data from external API",
)
def sample_protein_data(context: AssetExecutionContext) -> MaterializeResult:
    """
    Example asset that fetches sample protein data.

    In a real implementation, this would connect to NCBI, UniProt, or other
    biological databases to fetch protein information.
    """
    # Sample data - in real implementation this would be API calls
    sample_data = {
        "protein_id": ["P12345", "Q67890", "R13579"],
        "sequence": ["MKTIIALSYIFCLVFAD", "MKTVRQERLKSIVRILDL", "MAVAVLWLSAGAGAA"],
        "organism": ["Homo sapiens", "Escherichia coli", "Mus musculus"],
        "length": [17, 18, 15],
        "fetch_timestamp": [datetime.now().isoformat()] * 3,
    }

    df = pd.DataFrame(sample_data)

    # Log metadata about the asset
    context.log.info(f"Fetched {len(df)} protein records")

    return MaterializeResult(
        metadata={
            "num_proteins": len(df),
            "organisms": MetadataValue.md(df["organism"].value_counts().to_markdown()),
            "avg_length": MetadataValue.float(df["length"].mean()),
            "fetch_time": MetadataValue.text(datetime.now().isoformat()),
        }
    )


@asset(
    group_name="processing",
    description="Processes and validates protein sequences",
)
def processed_protein_data(
    context: AssetExecutionContext, sample_protein_data: pd.DataFrame
) -> MaterializeResult:
    """
    Example asset that processes protein data.

    This asset demonstrates data transformation and validation workflows
    common in bioinformatics pipelines.
    """
    # Process the data
    processed_df = sample_protein_data.copy()

    # Add calculated columns
    processed_df["gc_content"] = processed_df["sequence"].apply(
        lambda seq: (seq.count("G") + seq.count("C")) / len(seq) * 100
    )
    processed_df["molecular_weight"] = processed_df["sequence"].apply(
        lambda seq: sum(
            [
                110.0
                if aa in ["A", "V", "L", "I", "P", "T", "M"]
                else 130.0
                if aa in ["S", "N", "Q", "C", "G", "D"]
                else 150.0
                if aa in ["K", "R", "H", "E", "F", "Y", "W"]
                else 110.0
                for aa in seq
            ]
        )
    )

    # Validation checks
    invalid_sequences = processed_df[processed_df["length"] < 10]
    if len(invalid_sequences) > 0:
        context.log.warning(
            f"Found {len(invalid_sequences)} sequences with invalid length"
        )

    context.log.info(f"Processed {len(processed_df)} protein records")

    return MaterializeResult(
        metadata={
            "num_processed": len(processed_df),
            "avg_gc_content": MetadataValue.float(processed_df["gc_content"].mean()),
            "avg_molecular_weight": MetadataValue.float(
                processed_df["molecular_weight"].mean()
            ),
            "validation_errors": len(invalid_sequences),
            "process_time": MetadataValue.text(datetime.now().isoformat()),
        }
    )


@asset(
    group_name="validation",
    description="Validates processed protein data against quality criteria",
)
def validation_report(
    context: AssetExecutionContext, processed_protein_data: pd.DataFrame
) -> MaterializeResult:
    """
    Example asset that validates processed data.

    Generates quality metrics and validation reports for the processed
    protein data pipeline.
    """
    # Quality checks
    quality_checks = {
        "total_sequences": len(processed_protein_data),
        "avg_length": processed_protein_data["length"].mean(),
        "min_length": processed_protein_data["length"].min(),
        "max_length": processed_protein_data["length"].max(),
        "avg_gc_content": processed_protein_data["gc_content"].mean(),
        "sequences_with_gc_content_ok": len(
            processed_protein_data[processed_protein_data["gc_content"] > 30]
        ),
        "unique_organisms": processed_protein_data["organism"].nunique(),
    }

    # Validation status
    validation_passed = (
        quality_checks["avg_length"] >= 10
        and quality_checks["avg_gc_content"] >= 30
        and quality_checks["sequences_with_gc_content_ok"]
        == quality_checks["total_sequences"]
    )

    context.log.info(f"Validation {'PASSED' if validation_passed else 'FAILED'}")

    return MaterializeResult(
        metadata={
            "validation_status": MetadataValue.text(
                "PASSED" if validation_passed else "FAILED"
            ),
            "total_sequences": quality_checks["total_sequences"],
            "avg_length": MetadataValue.float(quality_checks["avg_length"]),
            "avg_gc_content": MetadataValue.float(quality_checks["avg_gc_content"]),
            "quality_score": MetadataValue.int(100 if validation_passed else 50),
            "validation_time": MetadataValue.text(datetime.now().isoformat()),
        }
    )


# Create the Dagster definitions
defs = Definitions(
    assets=[
        venom_peptides_uniprot,
        sample_protein_data,
        processed_protein_data,
        validation_report,
    ],
    asset_checks=[],  # Can add data quality checks here
)
