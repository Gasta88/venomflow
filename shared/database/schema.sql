-- VenomFlow PostgreSQL Database Schema
-- Comprehensive schema for venom peptide research platform
-- Supports multi-source data ingestion, virtual screening, and quality tracking

-- ============================================================================
-- EXTENSIONS
-- ============================================================================

-- UUID generation for primary keys
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Trigram indexing for fuzzy text search (sequence similarity)
CREATE EXTENSION IF NOT EXISTS "pg_trgm";

-- ============================================================================
-- CORE TABLES
-- ============================================================================

-- ----------------------------------------------------------------------------
-- 1. ORGANISMS TABLE
-- Stores organism taxonomy and classification data
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS organisms (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name VARCHAR(255) NOT NULL,
    common_name VARCHAR(255),
    taxonomy_id INTEGER UNIQUE,  -- NCBI Taxonomy ID
    taxonomy JSONB,  -- Full taxonomic lineage
    venom_type VARCHAR(100),  -- e.g., 'snake', 'spider', 'scorpion', 'cone_snail'
    description TEXT,
    source VARCHAR(100),  -- Data source: 'uniprot', 'ncbi', 'manual'
    external_ids JSONB,  -- External database identifiers
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    
    -- Constraints
    CONSTRAINT organisms_name_check CHECK (name <> ''),
    CONSTRAINT organisms_venom_type_check CHECK (
        venom_type IN ('snake', 'spider', 'scorpion', 'cone_snail', 'jellyfish', 
                       'bee', 'wasp', 'ant', 'frog', 'lizard', 'fish', 'other')
    )
);

-- Indexes for organisms
CREATE INDEX idx_organisms_name ON organisms(name);
CREATE INDEX idx_organisms_taxonomy_id ON organisms(taxonomy_id);
CREATE INDEX idx_organisms_venom_type ON organisms(venom_type);
CREATE INDEX idx_organisms_taxonomy_gin ON organisms USING gin(taxonomy);

-- ----------------------------------------------------------------------------
-- 2. PEPTIDES TABLE
-- Core peptide data with sequences and metadata
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS peptides (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    uniprot_id VARCHAR(20) UNIQUE,
    name VARCHAR(255) NOT NULL,
    sequence TEXT NOT NULL,
    sequence_hash VARCHAR(64) UNIQUE NOT NULL,  -- SHA256 hash for deduplication
    sequence_length INTEGER NOT NULL,
    molecular_weight DECIMAL(10, 2),
    organism_id UUID REFERENCES organisms(id) ON DELETE SET NULL,
    function_description TEXT,
    family VARCHAR(100),  -- Protein family classification
    source VARCHAR(100) NOT NULL,  -- Data source
    quality_score DECIMAL(3, 2),  -- 0.00 to 1.00 data completeness score
    metadata JSONB,  -- Flexible metadata storage
    external_ids JSONB,  -- Cross-references to other databases
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    
    -- Constraints
    CONSTRAINT peptides_sequence_check CHECK (sequence ~ '^[ACDEFGHIKLMNPQRSTVWY]+$'),
    CONSTRAINT peptides_sequence_length_check CHECK (sequence_length = length(sequence)),
    CONSTRAINT peptides_quality_score_check CHECK (quality_score >= 0 AND quality_score <= 1)
);

-- Indexes for peptides
CREATE INDEX idx_peptides_organism_id ON peptides(organism_id);
CREATE INDEX idx_peptides_sequence_hash ON peptides(sequence_hash);
CREATE INDEX idx_peptides_uniprot_id ON peptides(uniprot_id);
CREATE INDEX idx_peptides_name ON peptides(name);
CREATE INDEX idx_peptides_family ON peptides(family);
CREATE INDEX idx_peptides_source ON peptides(source);
CREATE INDEX idx_peptides_quality_score ON peptides(quality_score);
CREATE INDEX idx_peptides_sequence_trgm ON peptides USING gin(sequence gin_trgm_ops);
CREATE INDEX idx_peptides_metadata_gin ON peptides USING gin(metadata);

-- ----------------------------------------------------------------------------
-- 3. BIOACTIVITY TABLE
-- Stores biological activity data for peptides
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS bioactivity (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    peptide_id UUID NOT NULL REFERENCES peptides(id) ON DELETE CASCADE,
    activity_type VARCHAR(100) NOT NULL,  -- e.g., 'neurotoxic', 'antimicrobial', 'cytotoxic'
    target VARCHAR(255),  -- Biological target (receptor, ion channel, etc.)
    value DECIMAL(15, 6),  -- Numeric activity value (IC50, EC50, etc.)
    unit VARCHAR(50),  -- Unit of measurement
    assay_type VARCHAR(100),  -- Type of assay used
    organism_tested VARCHAR(255),  -- Organism tested on
    confidence_level VARCHAR(50),  -- 'high', 'medium', 'low'
    reference TEXT,  -- Citation or reference
    pubmed_id INTEGER,
    source VARCHAR(100) NOT NULL,
    metadata JSONB,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    
    -- Constraints
    CONSTRAINT bioactivity_confidence_check CHECK (
        confidence_level IN ('high', 'medium', 'low', 'unknown')
    ),
    CONSTRAINT bioactivity_value_check CHECK (value IS NULL OR value >= 0)
);

-- Indexes for bioactivity
CREATE INDEX idx_bioactivity_peptide_id ON bioactivity(peptide_id);
CREATE INDEX idx_bioactivity_type ON bioactivity(activity_type);
CREATE INDEX idx_bioactivity_target ON bioactivity(target);
CREATE INDEX idx_bioactivity_pubmed_id ON bioactivity(pubmed_id);
CREATE INDEX idx_bioactivity_confidence ON bioactivity(confidence_level);

-- ----------------------------------------------------------------------------
-- 4. STRUCTURES TABLE
-- 3D structure data and predictions
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS structures (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    peptide_id UUID NOT NULL REFERENCES peptides(id) ON DELETE CASCADE,
    structure_type VARCHAR(50) NOT NULL,  -- 'experimental', 'predicted', 'homology_model'
    pdb_id VARCHAR(10),  -- PDB identifier if available
    structure_data TEXT,  -- PDB format or other structure representation
    secondary_structure VARCHAR(255),  -- e.g., 'alpha-helix', 'beta-sheet'
    method VARCHAR(100),  -- Determination method: 'X-ray', 'NMR', 'AlphaFold', etc.
    resolution DECIMAL(4, 2),  -- Resolution in Angstroms (for experimental)
    confidence_score DECIMAL(3, 2),  -- Confidence for predictions (0.00-1.00)
    file_url TEXT,  -- URL to structure file in object storage
    source VARCHAR(100) NOT NULL,
    metadata JSONB,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    
    -- Constraints
    CONSTRAINT structures_type_check CHECK (
        structure_type IN ('experimental', 'predicted', 'homology_model')
    ),
    CONSTRAINT structures_confidence_check CHECK (
        confidence_score IS NULL OR (confidence_score >= 0 AND confidence_score <= 1)
    )
);

-- Indexes for structures
CREATE INDEX idx_structures_peptide_id ON structures(peptide_id);
CREATE INDEX idx_structures_pdb_id ON structures(pdb_id);
CREATE INDEX idx_structures_type ON structures(structure_type);
CREATE INDEX idx_structures_method ON structures(method);

-- ----------------------------------------------------------------------------
-- 5. PROPERTIES TABLE
-- Physicochemical properties of peptides
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS properties (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    peptide_id UUID NOT NULL UNIQUE REFERENCES peptides(id) ON DELETE CASCADE,
    molecular_formula VARCHAR(255),
    isoelectric_point DECIMAL(4, 2),
    hydrophobicity DECIMAL(6, 3),  -- Grand average of hydropathicity (GRAVY)
    charge_at_ph7 DECIMAL(6, 3),
    instability_index DECIMAL(6, 2),
    aliphatic_index DECIMAL(6, 2),
    aromaticity DECIMAL(5, 4),
    molar_extinction DECIMAL(10, 2),  -- at 280nm
    half_life_mammalian INTEGER,  -- seconds
    amino_acid_composition JSONB,  -- Composition by residue
    calculated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    calculation_method VARCHAR(100),  -- Tool/method used for calculation
    metadata JSONB,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Indexes for properties
CREATE INDEX idx_properties_peptide_id ON properties(peptide_id);
CREATE INDEX idx_properties_isoelectric_point ON properties(isoelectric_point);
CREATE INDEX idx_properties_hydrophobicity ON properties(hydrophobicity);
CREATE INDEX idx_properties_instability_index ON properties(instability_index);

-- ----------------------------------------------------------------------------
-- 6. PEPTIDE_SIMILARITIES TABLE
-- Sequence similarity relationships for virtual screening
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS peptide_similarities (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    peptide_id_1 UUID NOT NULL REFERENCES peptides(id) ON DELETE CASCADE,
    peptide_id_2 UUID NOT NULL REFERENCES peptides(id) ON DELETE CASCADE,
    similarity_score DECIMAL(5, 4) NOT NULL,  -- 0.0000 to 1.0000
    alignment_method VARCHAR(50) NOT NULL,  -- 'blast', 'smith-waterman', 'needleman-wunsch'
    alignment_length INTEGER,
    identities INTEGER,
    gaps INTEGER,
    e_value DECIMAL(10, 4),  -- BLAST e-value
    bit_score DECIMAL(8, 2),  -- BLAST bit score
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    
    -- Constraints
    CONSTRAINT peptide_similarities_unique_pair UNIQUE(peptide_id_1, peptide_id_2),
    CONSTRAINT peptide_similarities_no_self CHECK (peptide_id_1 <> peptide_id_2),
    CONSTRAINT peptide_similarities_score_check CHECK (
        similarity_score >= 0 AND similarity_score <= 1
    ),
    CONSTRAINT peptide_similarities_ordered CHECK (peptide_id_1 < peptide_id_2)
);

-- Indexes for peptide_similarities
CREATE INDEX idx_peptide_similarities_peptide_1 ON peptide_similarities(peptide_id_1);
CREATE INDEX idx_peptide_similarities_peptide_2 ON peptide_similarities(peptide_id_2);
CREATE INDEX idx_peptide_similarities_score ON peptide_similarities(similarity_score DESC);
CREATE INDEX idx_peptide_similarities_method ON peptide_similarities(alignment_method);
CREATE INDEX idx_peptide_similarities_e_value ON peptide_similarities(e_value);

-- ----------------------------------------------------------------------------
-- 7. PIPELINE_RUNS TABLE
-- Track data pipeline execution for lineage
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS pipeline_runs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    run_id VARCHAR(100) UNIQUE NOT NULL,  -- Dagster run ID
    pipeline_name VARCHAR(100) NOT NULL,
    status VARCHAR(50) NOT NULL,  -- 'started', 'running', 'success', 'failed'
    started_at TIMESTAMP WITH TIME ZONE NOT NULL,
    completed_at TIMESTAMP WITH TIME ZONE,
    duration_seconds INTEGER,
    records_processed INTEGER DEFAULT 0,
    records_failed INTEGER DEFAULT 0,
    error_message TEXT,
    config JSONB,  -- Pipeline configuration used
    metadata JSONB,  -- Additional run metadata
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    
    -- Constraints
    CONSTRAINT pipeline_runs_status_check CHECK (
        status IN ('started', 'running', 'success', 'failed', 'cancelled')
    ),
    CONSTRAINT pipeline_runs_duration_check CHECK (
        duration_seconds IS NULL OR duration_seconds >= 0
    )
);

-- Indexes for pipeline_runs
CREATE INDEX idx_pipeline_runs_run_id ON pipeline_runs(run_id);
CREATE INDEX idx_pipeline_runs_pipeline_name ON pipeline_runs(pipeline_name);
CREATE INDEX idx_pipeline_runs_status ON pipeline_runs(status);
CREATE INDEX idx_pipeline_runs_started_at ON pipeline_runs(started_at DESC);

-- ----------------------------------------------------------------------------
-- 8. SCREENING_JOBS TABLE
-- Virtual screening batch operations
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS screening_jobs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    job_name VARCHAR(255) NOT NULL,
    job_type VARCHAR(50) NOT NULL,  -- 'similarity_search', 'bioactivity_prediction', 'docking'
    status VARCHAR(50) NOT NULL,  -- 'queued', 'running', 'completed', 'failed'
    query_sequence TEXT,  -- Query peptide sequence
    query_peptide_id UUID REFERENCES peptides(id) ON DELETE SET NULL,
    parameters JSONB NOT NULL,  -- Screening parameters
    results JSONB,  -- Screening results
    num_candidates INTEGER DEFAULT 0,
    num_hits INTEGER DEFAULT 0,
    started_at TIMESTAMP WITH TIME ZONE,
    completed_at TIMESTAMP WITH TIME ZONE,
    duration_seconds INTEGER,
    error_message TEXT,
    created_by VARCHAR(100),  -- User or system that created the job
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    
    -- Constraints
    CONSTRAINT screening_jobs_status_check CHECK (
        status IN ('queued', 'running', 'completed', 'failed', 'cancelled')
    ),
    CONSTRAINT screening_jobs_type_check CHECK (
        job_type IN ('similarity_search', 'bioactivity_prediction', 'docking', 
                     'property_filter', 'blast_search')
    )
);

-- Indexes for screening_jobs
CREATE INDEX idx_screening_jobs_status ON screening_jobs(status);
CREATE INDEX idx_screening_jobs_type ON screening_jobs(job_type);
CREATE INDEX idx_screening_jobs_peptide_id ON screening_jobs(query_peptide_id);
CREATE INDEX idx_screening_jobs_created_at ON screening_jobs(created_at DESC);
CREATE INDEX idx_screening_jobs_created_by ON screening_jobs(created_by);

-- ============================================================================
-- TRIGGERS
-- ============================================================================

-- Trigger function to automatically update updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Apply trigger to tables with updated_at column
CREATE TRIGGER update_organisms_updated_at
    BEFORE UPDATE ON organisms
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_peptides_updated_at
    BEFORE UPDATE ON peptides
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_bioactivity_updated_at
    BEFORE UPDATE ON bioactivity
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_structures_updated_at
    BEFORE UPDATE ON structures
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_properties_updated_at
    BEFORE UPDATE ON properties
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_screening_jobs_updated_at
    BEFORE UPDATE ON screening_jobs
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- ============================================================================
-- VIEWS
-- ============================================================================

-- Enriched peptides view for API queries
-- Joins peptide data with organism, bioactivity, and properties
CREATE OR REPLACE VIEW peptides_enriched AS
SELECT 
    p.id,
    p.uniprot_id,
    p.name,
    p.sequence,
    p.sequence_length,
    p.molecular_weight,
    p.family,
    p.function_description,
    p.quality_score,
    p.source as peptide_source,
    p.external_ids as peptide_external_ids,
    p.created_at,
    p.updated_at,
    -- Organism data
    o.id as organism_id,
    o.name as organism_name,
    o.common_name as organism_common_name,
    o.taxonomy_id,
    o.venom_type,
    -- Aggregated bioactivity data
    COUNT(DISTINCT b.id) as bioactivity_count,
    jsonb_agg(DISTINCT jsonb_build_object(
        'id', b.id,
        'type', b.activity_type,
        'target', b.target,
        'value', b.value,
        'unit', b.unit,
        'confidence', b.confidence_level
    )) FILTER (WHERE b.id IS NOT NULL) as bioactivities,
    -- Properties data
    pr.isoelectric_point,
    pr.hydrophobicity,
    pr.charge_at_ph7,
    pr.instability_index,
    pr.aliphatic_index,
    pr.aromaticity,
    -- Structure availability
    COUNT(DISTINCT s.id) as structure_count,
    bool_or(s.structure_type = 'experimental') as has_experimental_structure
FROM peptides p
LEFT JOIN organisms o ON p.organism_id = o.id
LEFT JOIN bioactivity b ON p.id = b.peptide_id
LEFT JOIN properties pr ON p.id = pr.peptide_id
LEFT JOIN structures s ON p.id = s.peptide_id
GROUP BY 
    p.id, p.uniprot_id, p.name, p.sequence, p.sequence_length, 
    p.molecular_weight, p.family, p.function_description, p.quality_score,
    p.source, p.external_ids, p.created_at, p.updated_at,
    o.id, o.name, o.common_name, o.taxonomy_id, o.venom_type,
    pr.isoelectric_point, pr.hydrophobicity, pr.charge_at_ph7,
    pr.instability_index, pr.aliphatic_index, pr.aromaticity;

-- ============================================================================
-- FUNCTIONS
-- ============================================================================

-- Function to calculate peptide data quality score
-- Scores based on completeness of critical fields
CREATE OR REPLACE FUNCTION calculate_peptide_quality(peptide_uuid UUID)
RETURNS DECIMAL(3, 2) AS $$
DECLARE
    quality_score DECIMAL(3, 2) := 0;
    has_organism BOOLEAN;
    has_bioactivity BOOLEAN;
    has_properties BOOLEAN;
    has_structure BOOLEAN;
    has_function BOOLEAN;
    has_family BOOLEAN;
BEGIN
    -- Check for organism (20 points)
    SELECT (organism_id IS NOT NULL) INTO has_organism
    FROM peptides WHERE id = peptide_uuid;
    IF has_organism THEN quality_score := quality_score + 0.20; END IF;
    
    -- Check for bioactivity data (25 points)
    SELECT EXISTS(SELECT 1 FROM bioactivity WHERE peptide_id = peptide_uuid)
    INTO has_bioactivity;
    IF has_bioactivity THEN quality_score := quality_score + 0.25; END IF;
    
    -- Check for properties (20 points)
    SELECT EXISTS(SELECT 1 FROM properties WHERE peptide_id = peptide_uuid)
    INTO has_properties;
    IF has_properties THEN quality_score := quality_score + 0.20; END IF;
    
    -- Check for structure (15 points)
    SELECT EXISTS(SELECT 1 FROM structures WHERE peptide_id = peptide_uuid)
    INTO has_structure;
    IF has_structure THEN quality_score := quality_score + 0.15; END IF;
    
    -- Check for function description (10 points)
    SELECT (function_description IS NOT NULL AND function_description <> '')
    INTO has_function
    FROM peptides WHERE id = peptide_uuid;
    IF has_function THEN quality_score := quality_score + 0.10; END IF;
    
    -- Check for family classification (10 points)
    SELECT (family IS NOT NULL AND family <> '')
    INTO has_family
    FROM peptides WHERE id = peptide_uuid;
    IF has_family THEN quality_score := quality_score + 0.10; END IF;
    
    RETURN quality_score;
END;
$$ LANGUAGE plpgsql;

-- ============================================================================
-- COMMENTS
-- ============================================================================

-- Table comments
COMMENT ON TABLE organisms IS 'Stores organism taxonomy and venom classification data';
COMMENT ON TABLE peptides IS 'Core peptide sequences with metadata and quality scores';
COMMENT ON TABLE bioactivity IS 'Biological activity measurements and assay results';
COMMENT ON TABLE structures IS '3D structural data (experimental and predicted)';
COMMENT ON TABLE properties IS 'Calculated physicochemical properties';
COMMENT ON TABLE peptide_similarities IS 'Sequence similarity relationships for screening';
COMMENT ON TABLE pipeline_runs IS 'Data pipeline execution tracking for lineage';
COMMENT ON TABLE screening_jobs IS 'Virtual screening batch job management';

-- Column comments (selected important ones)
COMMENT ON COLUMN peptides.sequence_hash IS 'SHA256 hash for sequence deduplication';
COMMENT ON COLUMN peptides.quality_score IS 'Data completeness score (0.00-1.00)';
COMMENT ON COLUMN bioactivity.confidence_level IS 'Reliability of bioactivity data';
COMMENT ON COLUMN peptide_similarities.similarity_score IS 'Normalized similarity score for screening';
COMMENT ON COLUMN screening_jobs.parameters IS 'JSON parameters for screening job execution';

-- View comments
COMMENT ON VIEW peptides_enriched IS 'Denormalized view joining peptides with related data for API queries';

-- Function comments
COMMENT ON FUNCTION calculate_peptide_quality(UUID) IS 'Calculate quality score based on data completeness (0.00-1.00)';
COMMENT ON FUNCTION update_updated_at_column() IS 'Trigger function to auto-update updated_at timestamps';

-- ============================================================================
-- GRANTS (Optional - adjust based on your security model)
-- ============================================================================

-- Example grants for application user
-- GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO venomflow_user;
-- GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO venomflow_user;
-- GRANT EXECUTE ON ALL FUNCTIONS IN SCHEMA public TO venomflow_user;
