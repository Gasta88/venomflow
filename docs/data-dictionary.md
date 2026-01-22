# VenomFlow Data Dictionary

## Database Schema Reference

This document describes the structure and relationships of data stored in VenomFlow.

## Tables

### organisms

Stores taxonomy information for venom-producing organisms.

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| id | UUID | PRIMARY KEY | Unique identifier |
| name | VARCHAR(255) | NOT NULL | Scientific name |
| common_name | VARCHAR(255) | NULL | Common name |
| taxonomy_id | INTEGER | NOT NULL, UNIQUE | NCBI taxonomy ID |
| lineage | TEXT | NULL | Full taxonomic lineage |
| created_at | TIMESTAMP | NOT NULL | Record creation time |
| updated_at | TIMESTAMP | NOT NULL | Last update time |

**Indexes**:
- `idx_organisms_taxonomy_id` on `taxonomy_id`
- `idx_organisms_name` on `name`

**Example**:
```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "name": "Bungarus multicinctus",
  "common_name": "Many-banded krait",
  "taxonomy_id": 8616,
  "lineage": "Eukaryota;Metazoa;Chordata;Reptilia;Squamata;Serpentes;Elapidae"
}
```

---

### peptides

Stores venom peptide sequences and basic metadata.

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| id | UUID | PRIMARY KEY | Unique identifier |
| uniprot_id | VARCHAR(50) | NOT NULL, UNIQUE | UniProt accession ID |
| sequence | TEXT | NOT NULL | Amino acid sequence |
| name | VARCHAR(255) | NULL | Peptide name |
| description | TEXT | NULL | Peptide description |
| length | INTEGER | NOT NULL | Sequence length |
| organism_id | UUID | NOT NULL, FK | Reference to organisms |
| created_at | TIMESTAMP | NOT NULL | Record creation time |
| updated_at | TIMESTAMP | NOT NULL | Last update time |

**Indexes**:
- `idx_peptides_uniprot_id` on `uniprot_id`
- `idx_peptides_organism_id` on `organism_id`
- `idx_peptides_length` on `length`
- `idx_peptides_description_fts` full-text search on `description`

**Relationships**:
- `organism_id` → `organisms.id` (MANY-TO-ONE)

**Example**:
```json
{
  "id": "650e8400-e29b-41d4-a716-446655440001",
  "uniprot_id": "P01399",
  "sequence": "KFKPHVTLHTSSRLTVKNLKTKHNNCMHRHSKIPPHFRHKDTIPQRKYACDDCKTPNCKQRK",
  "name": "Alpha-bungarotoxin",
  "description": "Neurotoxin from B. multicinctus",
  "length": 66,
  "organism_id": "550e8400-e29b-41d4-a716-446655440000"
}
```

---

### peptide_properties

Stores calculated biochemical properties for peptides.

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| id | UUID | PRIMARY KEY | Unique identifier |
| peptide_id | UUID | NOT NULL, UNIQUE, FK | Reference to peptides |
| molecular_weight | NUMERIC(10,4) | NULL | Molecular weight (Da) |
| isoelectric_point | NUMERIC(5,2) | NULL | Isoelectric point (pI) |
| hydrophobicity | NUMERIC(6,3) | NULL | GRAVY score |
| net_charge | NUMERIC(6,2) | NULL | Net charge at pH 7 |
| instability_index | NUMERIC(6,2) | NULL | Instability index |
| aliphatic_index | NUMERIC(6,2) | NULL | Aliphatic index |
| helix_fraction | NUMERIC(5,4) | NULL | Predicted helix fraction |
| turn_fraction | NUMERIC(5,4) | NULL | Predicted turn fraction |
| sheet_fraction | NUMERIC(5,4) | NULL | Predicted sheet fraction |
| created_at | TIMESTAMP | NOT NULL | Record creation time |
| updated_at | TIMESTAMP | NOT NULL | Last update time |

**Indexes**:
- `idx_peptide_properties_peptide_id` on `peptide_id`

**Relationships**:
- `peptide_id` → `peptides.id` (ONE-TO-ONE)

**Example**:
```json
{
  "id": "750e8400-e29b-41d4-a716-446655440002",
  "peptide_id": "650e8400-e29b-41d4-a716-446655440001",
  "molecular_weight": 7834.2156,
  "isoelectric_point": 9.25,
  "hydrophobicity": -0.156,
  "net_charge": 7.5,
  "instability_index": 45.23,
  "aliphatic_index": 78.45
}
```

---

### bioactivities

Stores biological activity data for peptides.

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| id | UUID | PRIMARY KEY | Unique identifier |
| peptide_id | UUID | NOT NULL, FK | Reference to peptides |
| activity_type | activity_type | NOT NULL | Type of activity (enum) |
| target | VARCHAR(255) | NULL | Target organism/molecule |
| potency | NUMERIC(12,6) | NULL | Potency value |
| unit | VARCHAR(50) | NULL | Unit of measurement |
| assay_type | VARCHAR(255) | NULL | Type of assay used |
| reference | TEXT | NULL | Literature reference |
| created_at | TIMESTAMP | NOT NULL | Record creation time |
| updated_at | TIMESTAMP | NOT NULL | Last update time |

**Indexes**:
- `idx_bioactivities_peptide_id` on `peptide_id`
- `idx_bioactivities_activity_type` on `activity_type`

**Relationships**:
- `peptide_id` → `peptides.id` (MANY-TO-ONE)

**Activity Types** (Enum):
- `cytotoxic`
- `antimicrobial`
- `neurotoxic`
- `hemolytic`
- `anticoagulant`
- `enzyme_inhibitor`
- `other`

**Example**:
```json
{
  "id": "850e8400-e29b-41d4-a716-446655440003",
  "peptide_id": "650e8400-e29b-41d4-a716-446655440001",
  "activity_type": "neurotoxic",
  "target": "Nicotinic acetylcholine receptor",
  "potency": 0.000125,
  "unit": "nM",
  "assay_type": "Receptor binding assay",
  "reference": "PMID:12345678"
}
```

---

### blast_results

Stores sequence similarity search results.

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| id | UUID | PRIMARY KEY | Unique identifier |
| query_peptide_id | UUID | NOT NULL, FK | Query peptide reference |
| subject_peptide_id | UUID | NOT NULL, FK | Subject peptide reference |
| identity_percentage | NUMERIC(5,2) | NOT NULL | Sequence identity (%) |
| alignment_length | INTEGER | NOT NULL | Length of alignment |
| e_value | NUMERIC(20,10) | NOT NULL | Expect value |
| bit_score | NUMERIC(10,2) | NOT NULL | Bit score |
| created_at | TIMESTAMP | NOT NULL | Record creation time |

**Indexes**:
- `idx_blast_results_query_peptide_id` on `query_peptide_id`
- `idx_blast_results_subject_peptide_id` on `subject_peptide_id`
- `idx_blast_results_identity` on `identity_percentage`

**Relationships**:
- `query_peptide_id` → `peptides.id` (MANY-TO-ONE)
- `subject_peptide_id` → `peptides.id` (MANY-TO-ONE)

**Example**:
```json
{
  "id": "950e8400-e29b-41d4-a716-446655440004",
  "query_peptide_id": "650e8400-e29b-41d4-a716-446655440001",
  "subject_peptide_id": "750e8400-e29b-41d4-a716-446655440005",
  "identity_percentage": 95.5,
  "alignment_length": 150,
  "e_value": 1.5e-50,
  "bit_score": 280.5
}
```

---

### pipeline_runs

Tracks Dagster pipeline executions.

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| id | UUID | PRIMARY KEY | Unique identifier |
| pipeline_name | VARCHAR(255) | NOT NULL | Name of pipeline |
| run_id | VARCHAR(255) | NOT NULL | Dagster run ID |
| status | VARCHAR(50) | NOT NULL | Execution status |
| started_at | TIMESTAMP | NOT NULL | Start timestamp |
| completed_at | TIMESTAMP | NULL | Completion timestamp |
| error_message | TEXT | NULL | Error details if failed |
| records_processed | INTEGER | DEFAULT 0 | Number of records processed |

**Indexes**:
- `idx_pipeline_runs_pipeline_name` on `pipeline_name`
- `idx_pipeline_runs_status` on `status`
- `idx_pipeline_runs_started_at` on `started_at`

**Status Values**:
- `pending`
- `running`
- `completed`
- `failed`
- `cancelled`

**Example**:
```json
{
  "id": "a50e8400-e29b-41d4-a716-446655440006",
  "pipeline_name": "venom_ingestion_pipeline",
  "run_id": "dagster_run_abc123",
  "status": "completed",
  "started_at": "2024-01-15T10:30:00Z",
  "completed_at": "2024-01-15T10:45:30Z",
  "records_processed": 1250
}
```

---

## Entity Relationships

```
organisms (1) ──< (M) peptides
                        │
                        ├──< (M) bioactivities
                        │
                        ├──> (1) peptide_properties
                        │
                        └──< (M) blast_results (as query)
                                 │
                                 └──< (M) blast_results (as subject)
```

## Data Types Reference

### UUID
- Format: `550e8400-e29b-41d4-a716-446655440000`
- Generated by PostgreSQL `uuid_generate_v4()`

### NUMERIC
- Precision varies by column
- Used for decimal values (molecular weight, scores, etc.)

### TIMESTAMP
- Format: `2024-01-15T10:30:00Z`
- Stored in UTC
- Automatically updated via triggers for `updated_at` columns

## Common Queries

### Get peptide with all related data
```sql
SELECT p.*, o.name as organism_name, pp.*, b.*
FROM peptides p
JOIN organisms o ON p.organism_id = o.id
LEFT JOIN peptide_properties pp ON p.id = pp.peptide_id
LEFT JOIN bioactivities b ON p.id = b.peptide_id
WHERE p.uniprot_id = 'P01399';
```

### Find similar peptides via BLAST
```sql
SELECT p2.*, br.identity_percentage, br.e_value
FROM blast_results br
JOIN peptides p2 ON br.subject_peptide_id = p2.id
WHERE br.query_peptide_id = '650e8400-e29b-41d4-a716-446655440001'
  AND br.identity_percentage >= 90.0
ORDER BY br.identity_percentage DESC;
```

### Search peptides by organism
```sql
SELECT p.*
FROM peptides p
JOIN organisms o ON p.organism_id = o.id
WHERE o.taxonomy_id = 8616;
```
