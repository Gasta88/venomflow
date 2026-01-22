#!/usr/bin/env python3
"""
Seed test data into VenomFlow database

Populates the database with sample venom peptide data for testing.
"""

import sys
import os
import psycopg2
from psycopg2.extras import execute_values
from datetime import datetime


SAMPLE_ORGANISMS = [
    ("Bungarus multicinctus", "Many-banded krait", 8616, "Eukaryota;Metazoa;Chordata;Reptilia;Squamata;Serpentes;Elapidae"),
    ("Conus geographus", "Geography cone", 6492, "Eukaryota;Metazoa;Mollusca;Gastropoda;Caenogastropoda;Conidae"),
    ("Androctonus australis", "Yellow fat-tailed scorpion", 6858, "Eukaryota;Metazoa;Arthropoda;Arachnida;Scorpiones;Buthidae"),
]

SAMPLE_PEPTIDES = [
    ("P01399", "KFKPHVTLHTSSRLTVKNLKTKHNNCMHRHSKIPPHFRHKDTIPQRKYACDDCKTPNCKQRK", "Alpha-bungarotoxin", "Neurotoxin from B. multicinctus"),
    ("P01400", "IRPRGCSWDPYQPQQGCNSSCSSKRQCKOHRCCAYKRQQVKCVGRGCTKKPSCKDRRK", "Kappa-bungarotoxin", "Neurotoxin from B. multicinctus"),
    ("P01519", "GCCSHPACAGNNQHICEKSKACGADSCDEGKTCCGKQKCMNGKCKCYPNRPGNM", "Conotoxin GI", "Neurotoxin from C. geographus"),
]


def get_connection():
    """Get database connection."""
    return psycopg2.connect(
        host=os.getenv("POSTGRES_HOST", "localhost"),
        port=os.getenv("POSTGRES_PORT", "5432"),
        database=os.getenv("POSTGRES_DB", "venomflow"),
        user=os.getenv("POSTGRES_USER", "venomflow_user"),
        password=os.getenv("POSTGRES_PASSWORD", "password")
    )


def seed_organisms(conn):
    """Seed organism data."""
    print("Seeding organisms...")
    
    with conn.cursor() as cur:
        execute_values(
            cur,
            """
            INSERT INTO organisms (name, common_name, taxonomy_id, lineage)
            VALUES %s
            ON CONFLICT (taxonomy_id) DO NOTHING
            """,
            SAMPLE_ORGANISMS
        )
    
    conn.commit()
    print(f"✓ Seeded {len(SAMPLE_ORGANISMS)} organisms")


def seed_peptides(conn):
    """Seed peptide data."""
    print("Seeding peptides...")
    
    with conn.cursor() as cur:
        # Get organism IDs
        cur.execute("SELECT id, taxonomy_id FROM organisms")
        organism_map = {tax_id: org_id for org_id, tax_id in cur.fetchall()}
        
        # Insert peptides
        for uniprot_id, sequence, name, description in SAMPLE_PEPTIDES:
            # Use first organism for simplicity
            organism_id = list(organism_map.values())[0]
            
            cur.execute(
                """
                INSERT INTO peptides (uniprot_id, sequence, name, description, length, organism_id)
                VALUES (%s, %s, %s, %s, %s, %s)
                ON CONFLICT (uniprot_id) DO NOTHING
                """,
                (uniprot_id, sequence, name, description, len(sequence), organism_id)
            )
    
    conn.commit()
    print(f"✓ Seeded {len(SAMPLE_PEPTIDES)} peptides")


def main():
    """Main seeding function."""
    print("Seeding VenomFlow test data...\n")
    
    try:
        conn = get_connection()
        
        seed_organisms(conn)
        seed_peptides(conn)
        
        conn.close()
        
        print("\n✓ Test data seeding complete!")
        return 0
        
    except Exception as e:
        print(f"\n✗ Error seeding data: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
