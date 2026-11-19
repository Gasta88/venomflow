"""Tests for the shared Pydantic models."""

import hashlib

import pytest
from pydantic import ValidationError

from shared.models.peptide import PeptideBase, PeptideCreate


def test_sequence_is_uppercased_and_stripped():
    peptide = PeptideCreate(name="Test", sequence=" acdefghik ", source="uniprot")

    assert peptide.sequence == "ACDEFGHIK"


def test_non_standard_amino_acids_are_accepted():
    peptide = PeptideCreate(name="Test", sequence="XBZUO", source="uniprot")

    assert peptide.sequence == "XBZUO"


@pytest.mark.parametrize("sequence", ["ACD-FGH", "ACD 12", "", "ACD*"])
def test_invalid_sequences_are_rejected(sequence):
    with pytest.raises(ValidationError):
        PeptideCreate(name="Test", sequence=sequence, source="uniprot")


def test_computed_sequence_length_and_hash():
    peptide = PeptideBase(name="Test", sequence="ACDEF", source="uniprot")

    assert peptide.sequence_length == 5
    assert peptide.sequence_hash == hashlib.sha256(b"ACDEF").hexdigest()


def test_empty_name_is_rejected():
    with pytest.raises(ValidationError):
        PeptideBase(name="   ", sequence="ACDEF", source="uniprot")


@pytest.mark.parametrize("score", [-0.1, 1.1])
def test_quality_score_outside_range_is_rejected(score):
    with pytest.raises(ValidationError):
        PeptideBase(
            name="Test",
            sequence="ACDEF",
            source="uniprot",
            quality_score=score,
        )
