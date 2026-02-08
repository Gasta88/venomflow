-- Dagster PostgreSQL Database Initialization Script
-- This script initializes the Dagster database and user for VenomFlow's pipeline orchestration

-- ============================================================================
-- DAGSTER DATABASE AND USER SETUP
-- ============================================================================
-- Note: This script runs during PostgreSQL container initialization
-- It's executed by the default PostgreSQL user (venomflow_user)

-- Create Dagster user (if not exists)
-- DO NOT replace if exists to preserve existing credentials
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_user WHERE usename = 'dagster_user') THEN
        CREATE ROLE dagster_user WITH LOGIN PASSWORD 'dagster_password';
        RAISE NOTICE 'Dagster user dagster_user created';
    ELSE
        RAISE NOTICE 'Dagster user dagster_user already exists, skipping creation';
    END IF;
END $$;

-- Create Dagster database (if not exists)
-- DO NOT replace if exists to prevent data loss on container restart
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_database WHERE datname = 'dagster') THEN
        CREATE DATABASE dagster
            OWNER = dagster_user
            ENCODING = 'UTF8'
            LC_COLLATE = 'en_US.UTF-8'
            LC_CTYPE = 'en_US.UTF-8'
            TEMPLATE = template0;
        RAISE NOTICE 'Dagster database dagster created';
    ELSE
        RAISE NOTICE 'Dagster database dagster already exists, skipping creation';
    END IF;
END $$;

-- Grant all privileges on dagster database to dagster_user
-- Database-level privileges can be granted from any database connection
GRANT ALL PRIVILEGES ON DATABASE dagster TO dagster_user;

-- The schema-level privileges will be set up by Dagster itself on first launch
-- when it creates its tables. The owner (dagster_user) already has full access
-- to the database and can create schema objects.

RAISE NOTICE 'Dagster database initialization completed successfully';