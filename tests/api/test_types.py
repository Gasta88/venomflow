"""Tests for the Strawberry GraphQL type definitions."""

from datetime import datetime, timezone
from uuid import uuid4

import strawberry

from api.schema.queries import Query
from api.schema.types import (
    Bioactivity,
    Organism,
    PageInfo,
    Peptide,
    PeptideSearchResult,
    Properties,
    SimilarPeptide,
)


def _peptide() -> Peptide:
    return Peptide(
        id=uuid4(),
        uniprot_id="P00974",
        name="Bungarotoxin",
        sequence="IVCHTTATSPISAVTCPPGENLCYKKKGKK",
        sequence_length=31,
        molecular_weight=8993.2,
        source="uniprot",
    )


def test_schema_compiles_and_exposes_query_fields():
    schema = strawberry.Schema(query=Query)
    sdl = schema.as_str()

    for field in (
        "peptide",
        "searchPeptides",
        "similarPeptides",
        "peptidesByProperties",
        "organisms",
    ):
        assert field in sdl


def test_schema_camel_cases_field_names():
    sdl = strawberry.Schema(query=Query).as_str()

    assert "searchPeptides(" in sdl
    assert "search_peptides" not in sdl


def test_peptide_type_defaults_relations_to_none():
    peptide = _peptide()

    assert peptide.organism is None
    assert peptide.bioactivities is None
    assert peptide.properties is None


def test_related_types_can_be_instantiated():
    organism = Organism(id=uuid4(), name="Naja naja")
    bioactivity = Bioactivity(
        id=uuid4(),
        activity_type="neurotoxin",
        source="uniprot",
    )
    properties = Properties(id=uuid4(), molecular_formula="C10H20")
    page_info = PageInfo(
        total=1,
        page=1,
        page_size=20,
        total_pages=1,
        has_next=False,
        has_previous=False,
    )

    now = datetime.now(timezone.utc)
    peptide = Peptide(
        id=uuid4(),
        name="Bungarotoxin",
        sequence="ACDEFGHIK",
        sequence_length=9,
        source="uniprot",
        created_at=now,
        organism=organism,
        bioactivities=[bioactivity],
        properties=properties,
    )
    result = PeptideSearchResult(items=[peptide], page_info=page_info)
    similar = SimilarPeptide(peptide=peptide, similarity_score=0.9)

    assert result.items[0].organism.name == "Naja naja"
    assert similar.peptide.id == peptide.id
    assert page_info.has_next is False
