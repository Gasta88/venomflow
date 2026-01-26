#!/bin/bash

###############################################################################
# VenomFlow Database Initialization Script
# 
# Applies the schema.sql to the PostgreSQL database via Docker.
# This script should be run after starting the Docker containers.
#
# Usage:
#   ./scripts/init_database.sh
#
# Exit Codes:
#   0 - Success
#   1 - Failure
###############################################################################

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

echo ""
echo "============================================================"
echo "🐘 VenomFlow Database Initialization"
echo "============================================================"
echo ""

# Check if Docker is available
if ! command -v docker &> /dev/null; then
    echo -e "${RED}❌ Docker is not installed or not in PATH${NC}"
    exit 1
fi

# Check if schema.sql exists
SCHEMA_FILE="$PROJECT_ROOT/shared/database/schema.sql"
if [ ! -f "$SCHEMA_FILE" ]; then
    echo -e "${RED}❌ Schema file not found: $SCHEMA_FILE${NC}"
    exit 1
fi

echo -e "${BLUE}📁 Schema file: $SCHEMA_FILE${NC}"
echo ""

# Load environment variables if .env exists
if [ -f "$PROJECT_ROOT/.env" ]; then
    echo -e "${BLUE}📋 Loading environment variables from .env${NC}"
    set -a
    source "$PROJECT_ROOT/.env"
    set +a
else
    echo -e "${YELLOW}⚠️  No .env file found, using default values${NC}"
fi

# Set default values
POSTGRES_CONTAINER="${POSTGRES_CONTAINER:-venomflow-postgres}"
POSTGRES_USER="${POSTGRES_USER:-venomflow_user}"
POSTGRES_DB="${POSTGRES_DB:-venomflow}"

echo -e "${BLUE}🐳 Container: $POSTGRES_CONTAINER${NC}"
echo -e "${BLUE}👤 User: $POSTGRES_USER${NC}"
echo -e "${BLUE}🗄️  Database: $POSTGRES_DB${NC}"
echo ""

# Check if container is running
echo -e "${BLUE}🔍 Checking if PostgreSQL container is running...${NC}"
if ! docker ps --format '{{.Names}}' | grep -q "^${POSTGRES_CONTAINER}$"; then
    echo -e "${RED}❌ PostgreSQL container '$POSTGRES_CONTAINER' is not running${NC}"
    echo -e "${YELLOW}💡 Start the container with: docker compose up -d postgres${NC}"
    exit 1
fi

echo -e "${GREEN}✅ Container is running${NC}"
echo ""

# Wait for PostgreSQL to be ready
echo -e "${BLUE}⏳ Waiting for PostgreSQL to be ready...${NC}"
MAX_RETRIES=30
RETRY_COUNT=0

while [ $RETRY_COUNT -lt $MAX_RETRIES ]; do
    if docker exec "$POSTGRES_CONTAINER" pg_isready -U "$POSTGRES_USER" -d "$POSTGRES_DB" > /dev/null 2>&1; then
        echo -e "${GREEN}✅ PostgreSQL is ready${NC}"
        break
    fi
    
    RETRY_COUNT=$((RETRY_COUNT + 1))
    if [ $RETRY_COUNT -eq $MAX_RETRIES ]; then
        echo -e "${RED}❌ PostgreSQL did not become ready in time${NC}"
        exit 1
    fi
    
    echo -e "${YELLOW}⏳ Waiting... (attempt $RETRY_COUNT/$MAX_RETRIES)${NC}"
    sleep 1
done

echo ""

# Apply schema
echo -e "${BLUE}🔧 Applying database schema...${NC}"
if docker exec -i "$POSTGRES_CONTAINER" psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" < "$SCHEMA_FILE" > /dev/null 2>&1; then
    echo -e "${GREEN}✅ Schema applied successfully${NC}"
else
    echo -e "${RED}❌ Failed to apply schema${NC}"
    echo -e "${YELLOW}💡 Check the schema.sql file for syntax errors${NC}"
    exit 1
fi

echo ""

# Verify schema installation
echo -e "${BLUE}🔍 Verifying schema installation...${NC}"

# Count tables
TABLE_COUNT=$(docker exec "$POSTGRES_CONTAINER" psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -t -c \
    "SELECT COUNT(*) FROM information_schema.tables WHERE table_schema = 'public' AND table_type = 'BASE TABLE';" \
    2>/dev/null | tr -d '[:space:]')

if [ -z "$TABLE_COUNT" ] || [ "$TABLE_COUNT" -eq 0 ]; then
    echo -e "${RED}❌ No tables found after schema application${NC}"
    exit 1
fi

echo -e "${GREEN}✅ Found $TABLE_COUNT tables${NC}"

# Count indexes
INDEX_COUNT=$(docker exec "$POSTGRES_CONTAINER" psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -t -c \
    "SELECT COUNT(*) FROM pg_indexes WHERE schemaname = 'public';" \
    2>/dev/null | tr -d '[:space:]')

echo -e "${GREEN}✅ Found $INDEX_COUNT indexes${NC}"

# Count triggers
TRIGGER_COUNT=$(docker exec "$POSTGRES_CONTAINER" psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -t -c \
    "SELECT COUNT(*) FROM information_schema.triggers WHERE trigger_schema = 'public';" \
    2>/dev/null | tr -d '[:space:]')

echo -e "${GREEN}✅ Found $TRIGGER_COUNT triggers${NC}"

# Check for views
VIEW_COUNT=$(docker exec "$POSTGRES_CONTAINER" psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -t -c \
    "SELECT COUNT(*) FROM information_schema.views WHERE table_schema = 'public';" \
    2>/dev/null | tr -d '[:space:]')

echo -e "${GREEN}✅ Found $VIEW_COUNT views${NC}"

# Check for functions
FUNCTION_COUNT=$(docker exec "$POSTGRES_CONTAINER" psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -t -c \
    "SELECT COUNT(*) FROM information_schema.routines WHERE routine_schema = 'public';" \
    2>/dev/null | tr -d '[:space:]')

echo -e "${GREEN}✅ Found $FUNCTION_COUNT functions${NC}"

echo ""
echo "============================================================"
echo -e "${GREEN}🎉 Database initialization complete!${NC}"
echo "============================================================"
echo ""
echo "Summary:"
echo "  📊 Tables:    $TABLE_COUNT"
echo "  🔍 Indexes:   $INDEX_COUNT"
echo "  ⚡ Triggers:  $TRIGGER_COUNT"
echo "  👁️  Views:     $VIEW_COUNT"
echo "  🔧 Functions: $FUNCTION_COUNT"
echo ""
echo "Next steps:"
echo "  1. Run tests: python3 scripts/test_database.py"
echo "  2. Start API: docker compose up -d api"
echo "  3. Start Dagster: docker compose up -d dagster-webserver"
echo ""

exit 0
