"""Tests for the GraphQL query resolvers and row conversion helpers."""

import asyncio
from datetime import datetime, timezone
from uuid import uuid4

import pytest

from api.schema import queries
from api.schema.queries import (
    Query,
    row_to_bioactivity,
    row_to_organism,
    row_to_peptide,
    row_to_properties,
)


class FakeConnection:
    """Minimal asyncpg-like connection returning queued results."""

    def __init__(self, fetchrow_results=(), fetch_results=()):
        self._fetchrow_results = list(fetchrow_results)
        self._fetch_results = list(fetch_results)
        self.closed = False

    async def fetchrow(self, *args, **kwargs):
        return self._fetchrow_results.pop(0) if self._fetchrow_results else None

    async def fetch(self, *args, **kwargs):
        return self._fetch_results.pop(0) if self._fetch_results else []

    async def close(self):
        self.closed = True


def _patch_connection(monkeypatch, conn: FakeConnection):
    async def fake_connect():
        return conn

    monkeypatch.setattr(queries, "get_postgres_connection", fake_connect)


def _peptide_row(**overrides):
    row = {
        "id": uuid4(),
        "uniprot_id": "P00974",
        "name": "Bungarotoxin",
        "sequence": "IVCHTTATSPISAVTCPPGENLCYKKKGKK",
        "sequence_length": 31,
        "molecular_weight": 8993.2,
        "function_description": "Test peptide",
        "family": "Three-finger toxin",
        "source": "uniprot",
        "quality_score": 0.9,
        "created_at": datetime.now(timezone.utc),
        "updated_at": datetime.now(timezone.utc),
    }
    row.update(overrides)
    return row


def test_row_to_peptide_maps_and_coerces_numeric_fields():
    row = _peptide_row(molecular_weight="8993.2", quality_score="0.9")

    peptide = row_to_peptide(row)

    assert peptide.uniprot_id == "P00974"
    assert peptide.molecular_weight == pytest.approx(8993.2)
    assert peptide.quality_score == pytest.approx(0.9)
    assert peptide.organism is None


def test_row_to_organism_maps_optional_fields():
    organism = row_to_organism({"id": uuid4(), "name": "Naja naja"})

    assert organism.name == "Naja naja"
    assert organism.taxonomy_id is None


def test_row_to_bioactivity_coerces_value():
    bioactivity = row_to_bioactivity(
        {
            "id": uuid4(),
            "activity_type": "neurotoxin",
            "value": "12.5",
            "source": "uniprot",
        }
    )

    assert bioactivity.value == pytest.approx(12.5)
    assert bioactivity.activity_type == "neurotoxin"


def test_row_to_properties_coerces_optional_numbers():
    properties = row_to_properties({"id": uuid4(), "isoelectric_point": "8.4"})

    assert properties.isoelectric_point == pytest.approx(8.4)
    assert properties.molecular_formula is None


def test_peptide_returns_none_for_unknown_accession(monkeypatch):
    conn = FakeConnection(fetchrow_results=[None])
    _patch_connection(monkeypatch, conn)

    result = asyncio.run(Query().peptide("MISSING"))

    assert result is None
    assert conn.closed is True


def test_peptide_returns_peptide_without_relations(monkeypatch):
    row = _peptide_row()
    # fetchrow: peptide row, organism row, properties row
    conn = FakeConnection(fetchrow_results=[row, None, None], fetch_results=[[]])
    _patch_connection(monkeypatch, conn)

    peptide = asyncio.run(Query().peptide("P00974"))

    assert peptide is not None
    assert peptide.uniprot_id == "P00974"
    assert peptide.organism is None
    assert peptide.bioactivities is None
    assert peptide.properties is None
    assert conn.closed is True


def test_similar_peptides_returns_empty_for_unknown_accession(monkeypatch):
    conn = FakeConnection(fetchrow_results=[None])
    _patch_connection(monkeypatch, conn)

    result = asyncio.run(Query().similar_peptides("MISSING"))

    assert result.total == 0
    assert result.items == []
    assert result.query_accession == "MISSING"
    assert conn.closed is True


def test_similar_peptides_maps_similarity_rows(monkeypatch):
    sim_peptide = _peptide_row()
    similarity_row = {
        "similar_peptide_id": sim_peptide["id"],
        "similarity_score": 0.92,
        "alignment_method": "smith-waterman",
        "alignment_length": 30,
        "identities": 28,
        "gaps": 0,
        "bit_score": 120.5,
    }
    conn = FakeConnection(
        # fetchrow: query id, similar peptide row, organism, properties
        fetchrow_results=[{"id": uuid4()}, sim_peptide, None, None],
        fetch_results=[[similarity_row], []],
    )
    _patch_connection(monkeypatch, conn)

    result = asyncio.run(Query().similar_peptides("P00974", threshold=0.5, limit=10))

    assert result.total == 1
    match = result.items[0]
    assert match.similarity_score == pytest.approx(0.92)
    assert match.alignment_method == "smith-waterman"
    assert match.bit_score == pytest.approx(120.5)
    assert match.peptide.id == sim_peptide["id"]
    assert conn.closed is True
