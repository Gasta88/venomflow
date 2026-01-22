#!/bin/bash
# Initialize VenomFlow database

set -e

echo "Initializing VenomFlow database..."

# Wait for PostgreSQL to be ready
until PGPASSWORD=$POSTGRES_PASSWORD psql -h "$POSTGRES_HOST" -U "$POSTGRES_USER" -d "$POSTGRES_DB" -c '\q'; do
  echo "PostgreSQL is unavailable - sleeping"
  sleep 1
done

echo "PostgreSQL is up - executing schema..."

# Execute schema
PGPASSWORD=$POSTGRES_PASSWORD psql -h "$POSTGRES_HOST" -U "$POSTGRES_USER" -d "$POSTGRES_DB" -f /home/user/webapp/shared/database/schema.sql

echo "Database initialization complete!"
