"""
Enrichment Worker for VenomFlow

Background worker for enriching peptide data with calculated properties.
"""

import os
import time
from typing import Dict, List
from Bio.SeqUtils.ProtParam import ProteinAnalysis
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class EnrichmentWorker:
    """Worker for calculating peptide biochemical properties."""
    
    def __init__(self):
        """Initialize enrichment worker."""
        logger.info("Enrichment worker initialized")
    
    def calculate_properties(self, sequence: str) -> Dict:
        """
        Calculate biochemical properties for a peptide sequence.
        
        Args:
            sequence: Amino acid sequence
            
        Returns:
            Dictionary of calculated properties
        """
        try:
            analyzer = ProteinAnalysis(sequence)
            
            properties = {
                "molecular_weight": round(analyzer.molecular_weight(), 4),
                "isoelectric_point": round(analyzer.isoelectric_point(), 2),
                "hydrophobicity": round(analyzer.gravy(), 3),
                "instability_index": round(analyzer.instability_index(), 2),
                "aliphatic_index": round(analyzer.aliphatic_index(), 2),
                "aromaticity": round(analyzer.aromaticity(), 4),
            }
            
            # Secondary structure predictions
            helix, turn, sheet = analyzer.secondary_structure_fraction()
            properties.update({
                "helix_fraction": round(helix, 4),
                "turn_fraction": round(turn, 4),
                "sheet_fraction": round(sheet, 4),
            })
            
            return properties
            
        except Exception as e:
            logger.error(f"Error calculating properties for sequence: {e}")
            return {}
    
    def process_batch(self, peptides: List[Dict]) -> List[Dict]:
        """
        Process a batch of peptides and enrich with properties.
        
        Args:
            peptides: List of peptide records
            
        Returns:
            List of enriched peptide records
        """
        logger.info(f"Processing batch of {len(peptides)} peptides")
        
        enriched = []
        for peptide in peptides:
            if "sequence" not in peptide:
                logger.warning(f"Peptide {peptide.get('id')} missing sequence")
                continue
            
            properties = self.calculate_properties(peptide["sequence"])
            peptide["properties"] = properties
            enriched.append(peptide)
        
        logger.info(f"Enriched {len(enriched)} peptides")
        return enriched
    
    def run(self):
        """
        Run the worker in continuous mode.
        
        TODO: Implement actual job queue integration (e.g., Redis, RabbitMQ)
        """
        logger.info("Starting enrichment worker...")
        
        while True:
            try:
                # TODO: Poll job queue for peptides to enrich
                time.sleep(10)
                
            except KeyboardInterrupt:
                logger.info("Worker shutdown requested")
                break
            except Exception as e:
                logger.error(f"Worker error: {e}")
                time.sleep(5)


if __name__ == "__main__":
    worker = EnrichmentWorker()
    worker.run()
