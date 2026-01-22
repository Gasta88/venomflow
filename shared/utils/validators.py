"""
Data validators for VenomFlow

Validation utilities for peptide sequences, taxonomy data, etc.
"""

import re
from typing import Optional


def is_valid_amino_acid_sequence(sequence: str) -> bool:
    """
    Validate that a sequence contains only valid amino acid codes.
    
    Args:
        sequence: Amino acid sequence to validate
        
    Returns:
        True if valid, False otherwise
    """
    valid_aa = set('ACDEFGHIKLMNPQRSTVWY')
    return all(c in valid_aa for c in sequence.upper())


def is_valid_uniprot_id(uniprot_id: str) -> bool:
    """
    Validate UniProt accession ID format.
    
    Args:
        uniprot_id: UniProt ID to validate
        
    Returns:
        True if valid format, False otherwise
    """
    # UniProt ID pattern: [A-Z0-9]{6,10}
    pattern = r'^[A-Z0-9]{6,10}$'
    return bool(re.match(pattern, uniprot_id.upper()))


def is_valid_taxonomy_id(taxonomy_id: int) -> bool:
    """
    Validate NCBI taxonomy ID.
    
    Args:
        taxonomy_id: Taxonomy ID to validate
        
    Returns:
        True if valid, False otherwise
    """
    return taxonomy_id > 0


def sanitize_sequence(sequence: str) -> str:
    """
    Sanitize a peptide sequence by removing whitespace and converting to uppercase.
    
    Args:
        sequence: Raw sequence string
        
    Returns:
        Sanitized sequence
    """
    return ''.join(sequence.split()).upper()


def calculate_sequence_length(sequence: str) -> int:
    """
    Calculate the length of a peptide sequence.
    
    Args:
        sequence: Amino acid sequence
        
    Returns:
        Sequence length
    """
    return len(sanitize_sequence(sequence))


def validate_email(email: str) -> bool:
    """
    Validate email address format.
    
    Args:
        email: Email address to validate
        
    Returns:
        True if valid format, False otherwise
    """
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return bool(re.match(pattern, email))


def validate_doi(doi: str) -> bool:
    """
    Validate DOI (Digital Object Identifier) format.
    
    Args:
        doi: DOI to validate
        
    Returns:
        True if valid format, False otherwise
    """
    pattern = r'^10\.\d{4,}\/[-._;()\/:a-zA-Z0-9]+$'
    return bool(re.match(pattern, doi))
