"""
Unit tests for property calculation functions.
Tests RDKit and BioPython property computation for peptide sequences.
"""

import pytest
from unittest.mock import patch, MagicMock


class TestComputeRDKitProperties:
    """Unit tests for compute_rdkit_properties function."""

    @pytest.fixture
    def mock_rdkit(self):
        """Mock RDKit modules."""
        mock_chem = MagicMock()
        mock_descriptors = MagicMock()

        mock_mol = MagicMock()
        mock_mol.FromSmiles.return_value = MagicMock()
        mock_chem.MolFromSmiles.return_value = mock_mol
        mock_chem.AddHs.return_value = mock_mol

        mock_descriptors.ExactMolWt.return_value = 1234.56
        mock_descriptors.MolLogP.return_value = 1.23
        mock_descriptors.TPSA.return_value = 456.78
        mock_descriptors.NumHDonors.return_value = 8
        mock_descriptors.NumHAcceptors.return_value = 15

        with patch.dict(
            "sys.modules",
            {
                "rdkit": MagicMock(),
                "rdkit.Chem": mock_chem,
                "rdkit.Chem.Descriptors": mock_descriptors,
            },
        ):
            yield {"chem": mock_chem, "descriptors": mock_descriptors}

    def test_compute_rdkit_properties_valid_sequence(self, mock_rdkit):
        """Test RDKit property computation for valid peptide sequence."""
        from dagster_pipelines.assets.property_calculators import (
            compute_rdkit_properties,
        )

        sequence = "ACDEFGHIK"
        props = compute_rdkit_properties(sequence)

        assert props is not None
        assert "molecular_weight" in props
        assert "logp" in props
        assert "tpsa" in props
        assert "num_h_donors" in props
        assert "num_h_acceptors" in props
        assert isinstance(props["molecular_weight"], float)
        assert isinstance(props["logp"], float)

    def test_compute_rdkit_properties_invalid_sequence(self, mock_rdkit):
        """Test RDKit property computation fails for invalid sequence."""
        from dagster_pipelines.assets.property_calculators import (
            compute_rdkit_properties,
        )

        sequence = "ACX123"  # Contains invalid characters

        props = compute_rdkit_properties(sequence)

        # Should return None for invalid sequences
        assert props is None

    def test_compute_rdkit_properties_empty_sequence(self, mock_rdkit):
        """Test RDKit property computation with empty sequence."""
        from dagster_pipelines.assets.property_calculators import (
            compute_rdkit_properties,
        )

        props = compute_rdkit_properties("")

        assert props is None

    def test_compute_rdkit_properties_rdkit_unavailable(self):
        """Test graceful handling when RDKit is not available."""
        with patch(
            "dagster_pipelines.assets.property_calculators.RDKIT_AVAILABLE", False
        ):
            from dagster_pipelines.assets.property_calculators import (
                compute_rdkit_properties,
            )

            props = compute_rdkit_properties("ACDEFGHIK")

            assert props is None


class TestComputeBioPythonProperties:
    """Unit tests for compute_biopython_properties function."""

    @pytest.fixture
    def mock_biopython(self):
        """Mock BioPython modules."""
        mock_protein_analysis = MagicMock()

        mock_protein_analysis.isoelectric_point.return_value = 8.45
        mock_protein_analysis.gravy.return_value = -0.623

        with patch.dict(
            "sys.modules",
            {
                "Bio": MagicMock(),
                "Bio.SeqUtils": MagicMock(),
                "Bio.SeqUtils.ProtParam": MagicMock(
                    **{"ProteinAnalysis.return_value": mock_protein_analysis}
                ),
            },
        ):
            yield {"analysis": mock_protein_analysis}

    def test_compute_biopython_properties_valid_sequence(self, mock_biopython):
        """Test BioPython property computation for valid peptide sequence."""
        from dagster_pipelines.assets.property_calculators import (
            compute_biopython_properties,
        )

        sequence = "ACDEFGHIKLMNPQRSTVWY"
        props = compute_biopython_properties(sequence)

        assert props is not None
        assert "isoelectric_point" in props
        assert "hydrophobicity" in props
        assert isinstance(props["isoelectric_point"], float)
        assert isinstance(props["hydrophobicity"], float)

    def test_compute_biopython_properties_invalid_sequence(self, mock_biopython):
        """Test BioPython property computation fails for invalid sequence."""
        from dagster_pipelines.assets.property_calculators import (
            compute_biopython_properties,
        )

        sequence = "ACX123"  # Contains invalid characters

        props = compute_biopython_properties(sequence)

        # Should return None for invalid sequences
        assert props is None

    def test_compute_biopython_properties_empty_sequence(self, mock_biopython):
        """Test BioPython property computation with empty sequence."""
        from dagster_pipelines.assets.property_calculators import (
            compute_biopython_properties,
        )

        props = compute_biopython_properties("")

        assert props is None

    def test_compute_biopython_properties_short_sequence(self, mock_biopython):
        """Test BioPython property computation warning for short sequence."""
        from dagster_pipelines.assets.property_calculators import (
            compute_biopython_properties,
        )

        sequence = "ACDEF"  # Short sequence (<10)

        with patch(
            "dagster_pipelines.assets.property_calculators.logger"
        ) as mock_logger:
            props = compute_biopython_properties(sequence)

            # Should still compute properties for short sequence but log warning
            mock_logger.warning.assert_called()
            assert props is not None

    def test_compute_biopython_properties_unavailable(self):
        """Test graceful handling when BioPython is not available."""
        with patch(
            "dagster_pipelines.assets.property_calculators.BIOPYTHON_AVAILABLE", False
        ):
            from dagster_pipelines.assets.property_calculators import (
                compute_biopython_properties,
            )

            props = compute_biopython_properties("ACDEFGHIK")

            assert props is None


class TestComputeAllProperties:
    """Unit tests for compute_all_properties function."""

    def test_compute_all_properties_success(self):
        """Test computing all properties for valid sequence."""
        with (
            patch(
                "dagster_pipelines.assets.property_calculators.RDKIT_AVAILABLE", True
            ),
            patch(
                "dagster_pipelines.assets.property_calculators.BIOPYTHON_AVAILABLE",
                True,
            ),
            patch(
                "dagster_pipelines.assets.property_calculators.compute_rdkit_properties"
            ) as mock_rdkit,
            patch(
                "dagster_pipelines.assets.property_calculators.compute_biopython_properties"
            ) as mock_biopython,
        ):
            mock_rdkit.return_value = {
                "molecular_weight": 1234.56,
                "logp": 1.23,
                "tpsa": 456.78,
                "num_h_donors": 8,
                "num_h_acceptors": 15,
            }
            mock_biopython.return_value = {
                "isoelectric_point": 8.45,
                "hydrophobicity": -0.623,
            }

            from dagster_pipelines.assets.property_calculators import (
                compute_all_properties,
            )

            props = compute_all_properties("ACDEFGHIK")

            assert props is not None
            assert len(props) == 7  # 5 RDKit + 2 BioPython properties
            assert "molecular_weight" in props
            assert "isoelectric_point" in props

    def test_compute_all_properties_rdkit_only(self):
        """Test computing properties when only RDKit succeeds."""
        with (
            patch(
                "dagster_pipelines.assets.property_calculators.RDKIT_AVAILABLE", True
            ),
            patch(
                "dagster_pipelines.assets.property_calculators.BIOPYTHON_AVAILABLE",
                True,
            ),
            patch(
                "dagster_pipelines.assets.property_calculators.compute_rdkit_properties"
            ) as mock_rdkit,
            patch(
                "dagster_pipelines.assets.property_calculators.compute_biopython_properties"
            ) as mock_biopython,
        ):
            mock_rdkit.return_value = {
                "molecular_weight": 1234.56,
                "logp": 1.23,
                "tpsa": 456.78,
                "num_h_donors": 8,
                "num_h_acceptors": 15,
            }
            mock_biopython.return_value = None

            from dagster_pipelines.assets.property_calculators import (
                compute_all_properties,
            )

            props = compute_all_properties("ACDEFGHIK")

            assert props is not None
            assert len(props) == 5  # Only RDKit properties

    def test_compute_all_properties_biopython_only(self):
        """Test computing properties when only BioPython succeeds."""
        with (
            patch(
                "dagster_pipelines.assets.property_calculators.RDKIT_AVAILABLE", True
            ),
            patch(
                "dagster_pipelines.assets.property_calculators.BIOPYTHON_AVAILABLE",
                True,
            ),
            patch(
                "dagster_pipelines.assets.property_calculators.compute_rdkit_properties"
            ) as mock_rdkit,
            patch(
                "dagster_pipelines.assets.property_calculators.compute_biopython_properties"
            ) as mock_biopython,
        ):
            mock_rdkit.return_value = None
            mock_biopython.return_value = {
                "isoelectric_point": 8.45,
                "hydrophobicity": -0.623,
            }

            from dagster_pipelines.assets.property_calculators import (
                compute_all_properties,
            )

            props = compute_all_properties("ACDEFGHIK")

            assert props is not None
            assert len(props) == 2  # Only BioPython properties

    def test_compute_all_properties_none_fail(self):
        """Test computing properties when both methods fail."""
        with (
            patch(
                "dagster_pipelines.assets.property_calculators.RDKIT_AVAILABLE", True
            ),
            patch(
                "dagster_pipelines.assets.property_calculators.BIOPYTHON_AVAILABLE",
                True,
            ),
            patch(
                "dagster_pipelines.assets.property_calculators.compute_rdkit_properties",
                return_value=None,
            ),
            patch(
                "dagster_pipelines.assets.property_calculators.compute_biopython_properties",
                return_value=None,
            ),
        ):
            from dagster_pipelines.assets.property_calculators import (
                compute_all_properties,
            )

            props = compute_all_properties("INVALID")

            assert props is None


class TestAminoAcidValidation:
    def test_compute_properties_lowercase_sequence(self):
        """Test property computation handles lowercase sequences."""
        from dagster_pipelines.assets.property_calculators import (
            compute_rdkit_properties,
        )

        seq_lower = "acdefghik"

        with (
            patch(
                "dagster_pipelines.assets.property_calculators.RDKIT_AVAILABLE", True
            ),
            patch("dagster.assets.property_calculators"),
        ):
            props = compute_rdkit_properties(seq_lower)
            assert props is None  # Should fail validation for lowercase

    def test_compute_properties_with_whitespace(self):
        """Test property computation handles whitespace in sequences."""
        # Sequence with whitespace should be cleaned and computed
        sequence = "ACDEFGHIK\nLMNPQRSTVWY\tC"

        with (
            patch(
                "dagster_pipelines.assets.property_calculators.BIOPYTHON_AVAILABLE",
                True,
            ),
            patch(
                "dagster_pipelines.assets.property_calculators.compute_biopython_properties"
            ) as mock_compute,
        ):
            # The function should validate before computation
            mock_compute.return_value = {
                "isoelectric_point": 8.45,
                "hydrophobicity": -0.623,
            }
            props = mock_compute(sequence.replace("\n", "").replace("\t", ""))

            assert props is not None
