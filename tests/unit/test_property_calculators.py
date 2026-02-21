"""Unit tests for property calculation functions.

Tests BioPython property computation for peptide sequences.
RDKit is not available in test environment, so those paths are tested via mock.
"""

import pytest
from unittest.mock import patch, MagicMock

from dagster_pipelines.assets.property_calculators import (
    sanitize_sequence,
    calculate_molecular_weight_from_sequence,
    calculate_basic_properties,
    compute_biopython_properties,
    compute_rdkit_properties,
    compute_all_properties,
    compute_properties_with_fallbacks,
    BIOPYTHON_AVAILABLE,
    STANDARD_AMINO_ACIDS,
    AMINO_ACID_MAPPING,
)


class TestSanitizeSequence:
    """Test non-standard amino acid mapping."""

    def test_standard_sequence_unchanged(self):
        assert sanitize_sequence("ACDEFGHIK") == "ACDEFGHIK"

    def test_maps_x_to_g(self):
        assert sanitize_sequence("AXC") == "AGC"

    def test_maps_all_non_standard(self):
        result = sanitize_sequence("XBZUO")
        assert result == "GDECK"

    def test_empty_sequence(self):
        assert sanitize_sequence("") == ""


class TestCalculateMolecularWeight:
    """Test molecular weight estimation from sequence."""

    def test_known_single_residue(self):
        # Single amino acid: just the AA weight (no water loss for length 1)
        mw = calculate_molecular_weight_from_sequence("A")
        # Should be ~89.09 (no peptide bonds to subtract)
        assert abs(mw - 89.09) < 0.01

    def test_longer_sequence(self):
        mw = calculate_molecular_weight_from_sequence("ACDEF")
        assert mw > 0
        assert isinstance(mw, float)

    def test_empty_sequence(self):
        assert calculate_molecular_weight_from_sequence("") == 0.0

    def test_non_standard_uses_default(self):
        # 'J' is not in AMINO_ACID_MW, should use default 110.0
        mw = calculate_molecular_weight_from_sequence("J")
        assert abs(mw - 110.0) < 0.01


class TestCalculateBasicProperties:
    """Test basic property fallback computation."""

    def test_returns_required_keys(self):
        props = calculate_basic_properties("ACDEF")
        assert "molecular_weight" in props
        assert "sequence_length" in props
        assert "calculation_method" in props
        assert props["calculation_method"] == "Basic-Estimated"

    def test_sequence_length_correct(self):
        props = calculate_basic_properties("ACDEF")
        assert props["sequence_length"] == 5


class TestComputeRDKitProperties:
    """Test RDKit property computation."""

    def test_returns_none_when_unavailable(self):
        with patch("dagster_pipelines.assets.property_calculators.RDKIT_AVAILABLE", False):
            assert compute_rdkit_properties("ACDEF") is None

    def test_returns_none_for_empty_sequence(self):
        with patch("dagster_pipelines.assets.property_calculators.RDKIT_AVAILABLE", True):
            assert compute_rdkit_properties("") is None

    def test_returns_none_for_non_standard_aas(self):
        with patch("dagster_pipelines.assets.property_calculators.RDKIT_AVAILABLE", True):
            assert compute_rdkit_properties("ACX123") is None

    def test_valid_sequence_with_mocked_rdkit(self):
        mock_mol = MagicMock()
        mock_chem = MagicMock()
        mock_chem.MolFromSequence.return_value = mock_mol
        mock_chem.AddHs.return_value = mock_mol
        mock_descriptors = MagicMock()
        mock_descriptors.ExactMolWt.return_value = 1000.0
        mock_descriptors.MolLogP.return_value = -1.5
        mock_descriptors.TPSA.return_value = 300.0
        mock_descriptors.NumHDonors.return_value = 5
        mock_descriptors.NumHAcceptors.return_value = 10

        import dagster_pipelines.assets.property_calculators as pc
        orig_rdkit = pc.RDKIT_AVAILABLE
        orig_chem = getattr(pc, 'Chem', None)
        orig_desc = getattr(pc, 'Descriptors', None)
        try:
            pc.RDKIT_AVAILABLE = True
            pc.Chem = mock_chem
            pc.Descriptors = mock_descriptors
            props = pc.compute_rdkit_properties("ACDEFGHIK")
        finally:
            pc.RDKIT_AVAILABLE = orig_rdkit
            if orig_chem is not None:
                pc.Chem = orig_chem
            elif hasattr(pc, 'Chem'):
                delattr(pc, 'Chem')
            if orig_desc is not None:
                pc.Descriptors = orig_desc
            elif hasattr(pc, 'Descriptors'):
                delattr(pc, 'Descriptors')

        assert props is not None
        assert props["molecular_weight"] == 1000.0
        assert props["logp"] == -1.5
        assert props["calculation_method"] == "RDKit"


class TestComputeBioPythonProperties:
    """Test BioPython property computation."""

    @pytest.mark.skipif(not BIOPYTHON_AVAILABLE, reason="BioPython not installed")
    def test_valid_standard_sequence(self):
        props = compute_biopython_properties("ACDEFGHIKLMNPQRSTVWY")
        assert props is not None
        assert "isoelectric_point" in props
        assert "hydrophobicity" in props
        assert "instability_index" in props
        assert "aromaticity" in props
        assert "charge_at_ph7" in props

    def test_empty_sequence_returns_none(self):
        assert compute_biopython_properties("") is None

    def test_returns_none_when_unavailable(self):
        with patch("dagster_pipelines.assets.property_calculators.BIOPYTHON_AVAILABLE", False):
            assert compute_biopython_properties("ACDEF") is None

    @pytest.mark.skipif(not BIOPYTHON_AVAILABLE, reason="BioPython not installed")
    def test_short_sequence_still_computes(self):
        props = compute_biopython_properties("ACDEF")
        assert props is not None
        assert isinstance(props["isoelectric_point"], float)


class TestComputeAllProperties:
    """Test combined property computation."""

    def test_none_when_both_fail(self):
        with patch("dagster_pipelines.assets.property_calculators.compute_rdkit_properties", return_value=None), \
             patch("dagster_pipelines.assets.property_calculators.compute_biopython_properties", return_value=None):
            assert compute_all_properties("INVALID") is None

    def test_merges_both_results(self):
        rdkit = {"molecular_weight": 1000.0, "logp": -1.5}
        bio = {"isoelectric_point": 8.0, "hydrophobicity": -0.5}
        with patch("dagster_pipelines.assets.property_calculators.compute_rdkit_properties", return_value=rdkit), \
             patch("dagster_pipelines.assets.property_calculators.compute_biopython_properties", return_value=bio):
            props = compute_all_properties("ACDEF")
        assert props["molecular_weight"] == 1000.0
        assert props["isoelectric_point"] == 8.0

    def test_rdkit_only(self):
        rdkit = {"logp": -1.5}
        with patch("dagster_pipelines.assets.property_calculators.compute_rdkit_properties", return_value=rdkit), \
             patch("dagster_pipelines.assets.property_calculators.compute_biopython_properties", return_value=None):
            props = compute_all_properties("ACDEF")
        assert props == {"logp": -1.5}

    def test_biopython_only(self):
        bio = {"isoelectric_point": 8.0}
        with patch("dagster_pipelines.assets.property_calculators.compute_rdkit_properties", return_value=None), \
             patch("dagster_pipelines.assets.property_calculators.compute_biopython_properties", return_value=bio):
            props = compute_all_properties("ACDEF")
        assert props == {"isoelectric_point": 8.0}


class TestComputePropertiesWithFallbacks:
    """Test the fallback strategy chain."""

    def test_empty_sequence_returns_basic(self):
        props = compute_properties_with_fallbacks("")
        assert props["calculation_method"] == "Empty-Sequence"
        assert "molecular_weight" in props

    @pytest.mark.skipif(not BIOPYTHON_AVAILABLE, reason="BioPython not installed")
    def test_standard_sequence_uses_biopython(self):
        # RDKit not available in test env, but BioPython is
        props = compute_properties_with_fallbacks("ACDEFGHIKLMNPQRSTVWY")
        assert props is not None
        assert "BioPython" in props["calculation_method"]
        assert "isoelectric_point" in props

    @pytest.mark.skipif(not BIOPYTHON_AVAILABLE, reason="BioPython not installed")
    def test_non_standard_sequence_sanitized(self):
        props = compute_properties_with_fallbacks("ACXEFGHIK")
        assert props is not None
        # Should still have BioPython results
        assert "calculation_method" in props

    def test_all_fail_returns_basic_estimated(self):
        with patch("dagster_pipelines.assets.property_calculators.compute_rdkit_properties", return_value=None), \
             patch("dagster_pipelines.assets.property_calculators.compute_biopython_properties", return_value=None):
            props = compute_properties_with_fallbacks("ACDEF")
        assert props["calculation_method"] == "Basic-Estimated"
        assert "molecular_weight" in props
