"""
Utility functions for computing physicochemical properties of peptides.
Uses RDKit and BioPython to calculate molecular and protein-specific properties.

Note: While the database accepts non-standard amino acids (X, B, Z, U, O),
RDKit property calculations only work with the 20 standard amino acids since RDKit
lacks SMILES structures for non-standard codes. Sequences with XBZUO will be
skipped for RDKit calculations but can still be processed by BioPython.
"""

import logging
from typing import Any, Dict, Optional

try:
    from rdkit import Chem
    from rdkit.Chem import Descriptors

    RDKIT_AVAILABLE = True
except ImportError:
    RDKIT_AVAILABLE = False

try:
    from Bio.SeqUtils.ProtParam import ProteinAnalysis

    BIOPYTHON_AVAILABLE = True
except ImportError:
    BIOPYTHON_AVAILABLE = False


logger = logging.getLogger(__name__)


def compute_rdkit_properties(sequence: str) -> Optional[Dict[str, Any]]:
    """Compute RDKit molecular properties for a peptide sequence.

    Converts the peptide sequence to an RDKit molecule and computes:
    - molecular_weight: Exact molecular mass
    - logp: Octanol-water partition coefficient
    - tpsa: Topological polar surface area (Å²)
    - num_h_donors: Number of hydrogen bond donors
    - num_h_acceptors: Number of hydrogen bond acceptors

    Args:
        sequence: Peptide sequence string (amino acids only).

    Returns:
        Dictionary with computed properties, or None if conversion fails.

    Example:
        >>> props = compute_rdkit_properties("ACDEFGHIK")
        >>> print(props['molecular_weight'])
    """
    if not RDKIT_AVAILABLE:
        logger.warning("RDKit not available, skipping RDKit property computation")
        return None

    try:
        amino_acids = {
            "A": "C1C(=O)NC(C)=C1N",  # Alanine
            "R": "NC(=N)NCCC(N)C(N)=O",  # Arginine
            "N": "C(C(=O)N)N",  # Asparagine
            "D": "C(C(=O)O)N",  # Aspartic acid
            "C": "C(C(=O)N)S",  # Cysteine
            "Q": "C(CC(=O)N)C(=O)N",  # Glutamine
            "E": "C(CC(=O)O)C(=O)N",  # Glutamic acid
            "G": "C(C(=O)N)N",  # Glycine
            "H": "C(CC1=CN=CN1)C(=O)N",  # Histidine
            "I": "C(C)C(C(=O)N)N",  # Isoleucine
            "L": "CC(C)C(=O)N",  # Leucine
            "K": "C(CCN)C(=O)N",  # Lysine
            "M": "CSCC(=O)N",  # Methionine
            "F": "NC(=O)C(C)C1=CC=CC=C1",  # Phenylalanine
            "P": "C(C(=O)N)C1CCC1",  # Proline
            "S": "C(C(=O)N)O",  # Serine
            "T": "CC(C(=O)N)O",  # Threonine
            "W": "C(C(=O)N)C1=CN=C2C=C(C=C2)C(=C1)",  # Tryptophan
            "Y": "C(C(=O)N)C1=CC=C(C=C1)O",  # Tyrosine
            "V": "CC(C)C(=O)N",  # Valine
        }

        if not sequence:
            logger.warning("Empty sequence provided for RDKit computation")
            return None

        if not all(aa in amino_acids for aa in sequence):
            invalid_chars = set(sequence) - set(amino_acids.keys())
            # Log warning about non-standard amino acids (X, B, Z, U, O) which are not supported by RDKit
            logger.warning(
                f"Non-standard amino acids in sequence (RDKit cannot compute properties): {invalid_chars}. "
                "These amino acids (X=unknown, B=Asn/Asp, Z=Gln/Glu, U=selenocysteine, O=pyrrolysine) "
                "are valid in the database but not supported for RDKit calculations."
            )
            return None

        smiles = "".join(amino_acids[aa] for aa in sequence)
        mol = Chem.MolFromSmiles(smiles)

        if mol is None:
            logger.warning(f"RDKit failed to parse sequence: {sequence}")
            return None

        mol = Chem.AddHs(mol)

        properties = {
            "molecular_weight": Descriptors.ExactMolWt(mol),
            "logp": Descriptors.MolLogP(mol),
            "tpsa": Descriptors.TPSA(mol),
            "num_h_donors": Descriptors.NumHDonors(mol),
            "num_h_acceptors": Descriptors.NumHAcceptors(mol),
        }

        logger.debug(f"Computed RDKit properties for sequence length {len(sequence)}")
        return properties

    except Exception as e:
        logger.error(f"Error computing RDKit properties: {e}")
        return None


def compute_biopython_properties(sequence: str) -> Optional[Dict[str, Any]]:
    """Compute BioPython protein properties for a peptide sequence.

    Uses BioPython's ProtParam ProteinAnalysis to compute:
    - isoelectric_point: pH at which net charge is zero
    - hydrophobicity: Grand average of hydropathicity (GRAVY)

    Args:
        sequence: Peptide sequence string.

    Returns:
        Dictionary with computed properties, or None if computation fails.

    Example:
        >>> props = compute_biopython_properties("ACDEFGHIK")
        >>> print(props['isoelectric_point'])
    """
    if not BIOPYTHON_AVAILABLE:
        logger.warning(
            "BioPython not available, skipping BioPython property computation"
        )
        return None

    try:
        if not sequence:
            logger.warning("Empty sequence provided for BioPython computation")
            return None

        valid_amino_acids = set("ACDEFGHIKLMNPQRSTVWY")
        if not all(aa in valid_amino_acids for aa in sequence):
            invalid_chars = set(sequence) - valid_amino_acids
            logger.warning(f"Invalid amino acids in sequence: {invalid_chars}")
            return None

        if len(sequence) < 10:
            logger.warning(
                f"Sequence length {len(sequence)} may be too short for reliable pI calculation"
            )

        prot_analysis = ProteinAnalysis(sequence)

        isoelectric_point = prot_analysis.isoelectric_point()
        hydrophobicity = prot_analysis.gravy()

        properties = {
            "isoelectric_point": round(isoelectric_point, 2),
            "hydrophobicity": round(hydrophobicity, 3),
        }

        logger.debug(
            f"Computed BioPython properties for sequence length {len(sequence)}"
        )
        return properties

    except Exception as e:
        logger.error(f"Error computing BioPython properties: {e}")
        return None


def compute_all_properties(sequence: str) -> Optional[Dict[str, Any]]:
    """Compute all available physicochemical properties for a peptide sequence.

    Combines RDKit and BioPython property calculations into a single dict.

    Args:
        sequence: Peptide sequence string.

    Returns:
        Dictionary with all computed properties, or None if all fail.
    """
    rdkit_props = compute_rdkit_properties(sequence)
    biopython_props = compute_biopython_properties(sequence)

    all_props = {}

    if rdkit_props:
        all_props.update(rdkit_props)
    if biopython_props:
        all_props.update(biopython_props)

    if not all_props:
        logger.warning("Failed to compute any properties for sequence")
        return None

    return all_props
