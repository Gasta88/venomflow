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
    from rdkit.Chem import AllChem, Descriptors

    RDKIT_AVAILABLE = True
except ImportError:
    RDKIT_AVAILABLE = False

try:
    from Bio.SeqUtils.ProtParam import ProteinAnalysis

    BIOPYTHON_AVAILABLE = True
except ImportError:
    BIOPYTHON_AVAILABLE = False


logger = logging.getLogger(__name__)

AMINO_ACID_MAPPING = {
    "X": "G",
    "B": "D",
    "Z": "E",
    "U": "C",
    "O": "K",
}

STANDARD_AMINO_ACIDS = set("ACDEFGHIKLMNPQRSTVWY")

BIOPYTHON_VALID_AAS = set("ACDEFGHIKLMNPQRSTVWY")

AMINO_ACID_MW = {
    "A": 89.09,
    "R": 174.20,
    "N": 132.12,
    "D": 133.10,
    "C": 121.16,
    "Q": 146.15,
    "E": 147.13,
    "G": 75.07,
    "H": 155.16,
    "I": 131.17,
    "L": 131.17,
    "K": 146.19,
    "M": 149.21,
    "F": 165.19,
    "P": 115.13,
    "S": 105.09,
    "T": 119.12,
    "W": 204.23,
    "Y": 181.19,
    "V": 117.15,
    "X": 110.00,
    "B": 132.61,
    "Z": 146.64,
    "U": 150.41,
    "O": 255.35,
}


def sanitize_sequence(sequence: str) -> str:
    """Sanitize sequence by mapping non-standard amino acids to similar standards.

    Args:
        sequence: Peptide sequence that may contain non-standard amino acids.

    Returns:
        Sanitized sequence with non-standard AAs replaced.
    """
    return "".join(AMINO_ACID_MAPPING.get(c, c) for c in sequence)


def calculate_molecular_weight_from_sequence(sequence: str) -> float:
    """Calculate molecular weight from amino acid composition.

    Args:
        sequence: Peptide sequence string.

    Returns:
        Estimated molecular weight.
    """
    if not sequence:
        return 0.0
    return (
        sum(AMINO_ACID_MW.get(aa, 110.0) for aa in sequence)
        - (len(sequence) - 1) * 18.015
    )


def calculate_basic_properties(sequence: str) -> Dict[str, Any]:
    """Calculate basic properties that can be computed for any sequence.

    Args:
        sequence: Peptide sequence string.

    Returns:
        Dictionary with basic molecular properties.
    """
    return {
        "molecular_weight": calculate_molecular_weight_from_sequence(sequence),
        "sequence_length": len(sequence),
        "calculation_method": "Basic-Estimated",
    }


def compute_rdkit_properties(sequence: str) -> Optional[Dict[str, Any]]:
    """Compute RDKit molecular properties for a peptide sequence.

    Uses RDKit's native MolFromSequence() to properly create peptide bonds and
    computes molecular properties including:
    - molecular_weight: Exact molecular mass
    - logp: Octanol-water partition coefficient
    - tpsa: Topological polar surface area (Å²)
    - num_h_donors: Number of hydrogen bond donors
    - num_h_acceptors: Number of hydrogen bond acceptors

    Args:
        sequence: Peptide sequence string (20 standard amino acids only).

    Returns:
        Dictionary with computed properties, or None if conversion fails.

    Example:
        >>> props = compute_rdkit_properties("ACDEFGHIK")
        >>> print(props['molecular_weight'])

    Note:
        - Only 20 standard amino acids (ACDEFGHIKLMNPQRSTVWY) are supported
        - Non-standard amino acids (X, B, Z, U, O) should be sanitized before calling
    """
    if not RDKIT_AVAILABLE:
        logger.warning("RDKit not available, skipping RDKit property computation")
        return None

    try:
        standard_aas = set("ACDEFGHIKLMNPQRSTVWY")

        if not sequence:
            logger.warning("Empty sequence provided for RDKit computation")
            return None

        if not all(aa in standard_aas for aa in sequence):
            invalid_chars = set(sequence) - standard_aas
            logger.warning(
                f"Non-standard amino acids in sequence: {invalid_chars}. "
                "RDKit MolFromSequence() only supports 20 standard amino acids."
            )
            return None

        mol = Chem.MolFromSequence(sequence)

        if mol is None:
            logger.warning(
                f"RDKit MolFromSequence failed to parse sequence: {sequence}"
            )
            return None

        mol = Chem.AddHs(mol)

        properties = {
            "molecular_weight": Descriptors.ExactMolWt(mol),
            "logp": Descriptors.MolLogP(mol),
            "tpsa": Descriptors.TPSA(mol),
            "num_h_donors": Descriptors.NumHDonors(mol),
            "num_h_acceptors": Descriptors.NumHAcceptors(mol),
            "calculation_method": "RDKit",
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

    Note:
        Sequences with non-standard amino acids are now accepted but will use
        approximate molecular weight estimation.
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

        if not all(aa in BIOPYTHON_VALID_AAS for aa in sequence):
            invalid_chars = set(sequence) - BIOPYTHON_VALID_AAS
            logger.debug(
                f"Sequence contains non-standard amino acids: {invalid_chars}. "
                "Using BioPython for pI and GRAVY, but results may be approximate."
            )

        if len(sequence) < 10:
            logger.debug(
                f"Sequence length {len(sequence)} may be too short for reliable pI calculation"
            )

        prot_analysis = ProteinAnalysis(sequence)

        isoelectric_point = prot_analysis.isoelectric_point()
        hydrophobicity = prot_analysis.gravy()
        instability_index = prot_analysis.instability_index()
        aromaticity = prot_analysis.aromaticity()

        properties = {
            "isoelectric_point": round(isoelectric_point, 2),
            "hydrophobicity": round(hydrophobicity, 3),
            "instability_index": round(instability_index, 2),
            "aromaticity": round(aromaticity, 4),
        }

        net_charge_at_ph7 = prot_analysis.charge_at_pH(7.0)
        properties["charge_at_ph7"] = (
            round(net_charge_at_ph7, 3) if net_charge_at_ph7 is not None else None
        )

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


def compute_properties_with_fallbacks(sequence: str) -> Dict[str, Any]:
    """Compute peptide properties using fallback strategies for maximum compatibility.

    Tries multiple computation strategies in order:
    1. RDKit MolFromSequence (best) + BioPython for protein properties
    2. Sanitized RDKit + BioPython for non-standard AAs
    3. BioPython only for protein biochemical properties

    Args:
        sequence: Peptide sequence string (may contain non-standard amino acids).

    Returns:
        Dictionary with computed properties including calculation_method and molecular_weight.

    Example:
        >>> props = compute_properties_with_fallbacks("ACDEFGHIK")
        >>> print(props['calculation_method'])
    """
    if not sequence:
        logger.warning("Empty sequence provided")
        result = {
            "molecular_weight": calculate_molecular_weight_from_sequence(sequence),
            "calculation_method": "Empty-Sequence",
        }
        return result

    all_props: Dict[str, Any] = {}
    method_parts = []

    # Strategy 1: Try RDKit with standard amino acids only
    if set(sequence).issubset(STANDARD_AMINO_ACIDS):
        rdkit_result = compute_rdkit_properties(sequence)
        if rdkit_result:
            all_props.update(rdkit_result)
            method_parts.append("RDKit")

    # Strategy 2: Sanitized non-standard amino acids and retry RDKit
    sanitized = sanitize_sequence(sequence)
    if set(sanitized).issubset(STANDARD_AMINO_ACIDS) and not all_props:
        rdkit_result = compute_rdkit_properties(sanitized)
        if rdkit_result:
            all_props.update(rdkit_result)
            method_parts.append("RDKit-Estimated")

    # Strategy 3: Add BioPython protein biochemical properties
    biopython_result = compute_biopython_properties(sequence)
    if biopython_result:
        all_props.update(biopython_result)
        method_parts.append("BioPython")

    if not all_props:
        logger.warning("Failed to compute any properties for sequence")
        return {
            "molecular_weight": calculate_molecular_weight_from_sequence(sequence),
            "calculation_method": "Basic-Estimated",
        }

    all_props["calculation_method"] = (
        "+".join(method_parts) if len(method_parts) > 1 else method_parts[0]
    )

    return all_props
