-- VenomFlow Database Schema
-- PostgreSQL schema for venom peptide data

-- Create UUID extension
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Organisms table
CREATE TABLE IF NOT EXISTS organisms (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name VARCHAR(255) NOT NULL,
    common_name VARCHAR(255),
    taxonomy_id INTEGER NOT NULL UNIQUE,
    lineage TEXT,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_organisms_taxonomy_id ON organisms(taxonomy_id);
CREATE INDEX idx_organisms_name ON organisms(name);

-- Peptides table
CREATE TABLE IF NOT EXISTS peptides (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    uniprot_id VARCHAR(50) NOT NULL UNIQUE,
    sequence TEXT NOT NULL,
    name VARCHAR(255),
    description TEXT,
    length INTEGER NOT NULL,
    organism_id UUID NOT NULL REFERENCES organisms(id) ON DELETE CASCADE,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_peptides_uniprot_id ON peptides(uniprot_id);
CREATE INDEX idx_peptides_organism_id ON peptides(organism_id);
CREATE INDEX idx_peptides_length ON peptides(length);

-- Peptide properties table
CREATE TABLE IF NOT EXISTS peptide_properties (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    peptide_id UUID NOT NULL UNIQUE REFERENCES peptides(id) ON DELETE CASCADE,
    molecular_weight NUMERIC(10, 4),
    isoelectric_point NUMERIC(5, 2),
    hydrophobicity NUMERIC(6, 3),
    net_charge NUMERIC(6, 2),
    instability_index NUMERIC(6, 2),
    aliphatic_index NUMERIC(6, 2),
    helix_fraction NUMERIC(5, 4),
    turn_fraction NUMERIC(5, 4),
    sheet_fraction NUMERIC(5, 4),
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_peptide_properties_peptide_id ON peptide_properties(peptide_id);

-- Bioactivity types enum
CREATE TYPE activity_type AS ENUM (
    'cytotoxic',
    'antimicrobial',
    'neurotoxic',
    'hemolytic',
    'anticoagulant',
    'enzyme_inhibitor',
    'other'
);

-- Bioactivities table
CREATE TABLE IF NOT EXISTS bioactivities (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    peptide_id UUID NOT NULL REFERENCES peptides(id) ON DELETE CASCADE,
    activity_type activity_type NOT NULL,
    target VARCHAR(255),
    potency NUMERIC(12, 6),
    unit VARCHAR(50),
    assay_type VARCHAR(255),
    reference TEXT,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_bioactivities_peptide_id ON bioactivities(peptide_id);
CREATE INDEX idx_bioactivities_activity_type ON bioactivities(activity_type);

-- BLAST results table
CREATE TABLE IF NOT EXISTS blast_results (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    query_peptide_id UUID NOT NULL REFERENCES peptides(id) ON DELETE CASCADE,
    subject_peptide_id UUID NOT NULL REFERENCES peptides(id) ON DELETE CASCADE,
    identity_percentage NUMERIC(5, 2) NOT NULL,
    alignment_length INTEGER NOT NULL,
    e_value NUMERIC(20, 10) NOT NULL,
    bit_score NUMERIC(10, 2) NOT NULL,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_blast_results_query_peptide_id ON blast_results(query_peptide_id);
CREATE INDEX idx_blast_results_subject_peptide_id ON blast_results(subject_peptide_id);
CREATE INDEX idx_blast_results_identity ON blast_results(identity_percentage);

-- Pipeline runs tracking table
CREATE TABLE IF NOT EXISTS pipeline_runs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    pipeline_name VARCHAR(255) NOT NULL,
    run_id VARCHAR(255) NOT NULL,
    status VARCHAR(50) NOT NULL,
    started_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    completed_at TIMESTAMP,
    error_message TEXT,
    records_processed INTEGER DEFAULT 0
);

CREATE INDEX idx_pipeline_runs_pipeline_name ON pipeline_runs(pipeline_name);
CREATE INDEX idx_pipeline_runs_status ON pipeline_runs(status);
CREATE INDEX idx_pipeline_runs_started_at ON pipeline_runs(started_at);

-- Function to update updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Create triggers for updated_at columns
CREATE TRIGGER update_organisms_updated_at BEFORE UPDATE ON organisms
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_peptides_updated_at BEFORE UPDATE ON peptides
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_peptide_properties_updated_at BEFORE UPDATE ON peptide_properties
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_bioactivities_updated_at BEFORE UPDATE ON bioactivities
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- Create full-text search index on peptide descriptions
CREATE INDEX idx_peptides_description_fts ON peptides 
    USING gin(to_tsvector('english', COALESCE(description, '')));

-- Comments
COMMENT ON TABLE organisms IS 'Organism taxonomy information';
COMMENT ON TABLE peptides IS 'Venom peptide sequences and metadata';
COMMENT ON TABLE peptide_properties IS 'Calculated biochemical properties';
COMMENT ON TABLE bioactivities IS 'Biological activity data';
COMMENT ON TABLE blast_results IS 'Sequence similarity search results';
COMMENT ON TABLE pipeline_runs IS 'Data pipeline execution tracking';
