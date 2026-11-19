# VenomFlow AGENTS.md

> Guide for AI agents working on the VenomFlow project - understand the codebase structure, conventions, and key workflows.

## Project Overview

**VenomFlow** is a microservices-based data pipeline platform for computational toxinology research. It ingests venom peptide data from UniProt, enriches it with physicochemical properties and structural data, and provides:
- Dagster asset-based pipelines for orchestration
- GraphQL API via FastAPI for computational chemists
- Elasticsearch for similarity search
- PostgreSQL for structured data
- Redis for caching and job queues
- Prometheus + Grafana for monitoring

**Primary Goal:** Enable virtual screening and drug discovery research on venom peptides.

## Technology Stack

| Component | Technology | Purpose | Key Details |
|-----------|-----------|---------|-------------|
| **Orchestration** | Dagster 1.5+ | Asset-based data pipelines | Assets organized in `dagster_pipelines/assets/` by function |
| **API** | FastAPI 0.109+ + Strawberry | GraphQL endpoint (queries only) | Resolvers in `api/schema/queries.py`, types in `api/schema/types.py` |
| **Database** | PostgreSQL 16 | Primary data store | Schema: `shared/database/01-schema.sql` |
| **Cache** | Redis 7 | Job queues, caching | Stream-based event processing |
| **Search** | Elasticsearch 8.11 | Full-text and k-mer search | Sequence similarity indexing |
| **Processing** | RDKit, BioPython | Cheminformatics, bioinformatics | Computed properties stored in DB |
| **Monitoring** | Prometheus, Grafana | Metrics and dashboards | Configs in `monitoring/` |
| **Containerization** | Docker, Docker Compose | Microservices deployment | 8 core services |

## Directory Structure

```
venomflow/
├── docker-compose.yml          # All service definitions (8 services)
├── Makefile                    # Common commands (use `make help`)
├── pyproject.toml              # Metadata, dependency extras, pytest/ruff/coverage config
├── requirements-dev.txt        # Dev/test tooling (Dagster runtime + pytest/ruff)
├── requirements-dev.lock       # Hash-pinned lockfile used by CI
├── LICENSE                     # MIT
├── .env.example                # Environment variables template
│
├── dagster_pipelines/          # Dagster orchestration
│   ├── Dockerfile              # Dagster container image
│   ├── .dockerignore
│   ├── requirements.txt        # Dagster runtime dependencies
│   ├── requirements.lock       # Hash-pinned lockfile used by the image
│   ├── workspace.yaml          # Dagster workspace config
│   ├── dagster.yaml            # Dagster settings
│   ├── __init__.py             # Dagster definitions entry point
│   ├── assets/                 # Data assets (computations)
│   │   ├── ingestion.py        # UniProt ingestion
│   │   ├── enrichment.py       # Property enrichment asset
│   │   ├── property_calculators.py  # RDKit/BioPython helpers
│   │   ├── blast_similarity.py # Sequence similarity asset
│   │   └── elasticsearch_indexer.py # Bulk indexing asset
│   ├── jobs/                   # venom_flow_pipeline + daily schedule
│   └── resources/              # External service clients
│       ├── database.py         # PostgreSQL connection
│       ├── redis.py            # Redis client
│       └── elasticsearch.py    # Elasticsearch client
│
├── api/                        # FastAPI GraphQL API
│   ├── Dockerfile              # API container image
│   ├── .dockerignore
│   ├── requirements.txt        # API dependencies
│   ├── requirements.lock       # Hash-pinned lockfile used by the image
│   ├── main.py                 # API entry point
│   └── schema/                 # GraphQL schema definitions
│       ├── queries.py          # Query resolvers
│       └── types.py            # Strawberry types and input filters
│
├── shared/                     # Shared code across services
│   ├── config/                 # Configuration management
│   │   └── settings.py         # Pydantic BaseSettings (load env vars)
│   ├── models/                 # Pydantic data models
│   │   ├── organism.py         # Organism model
│   │   ├── peptide.py          # Peptide model (sequence validation)
│   │   ├── bioactivity.py      # Bioactivity model
│   │   └── properties.py       # Physicochemical properties
│   └── database/               # Database utilities
│       ├── connection.py       # Connection pool management
│       ├── 01-schema.sql       # Full database schema (8 tables)
│       └── 02-dagster-init.sql # Dagster metadata database
│
├── scripts/                    # Utility scripts
│   ├── init_database.sh        # Apply 01-schema.sql to the running database
│   ├── verify_infrastructure.py  # Check all services health
│   ├── verify_schema.py        # Validate database schema
│   ├── analyze_schema.py       # Schema analysis tool
│   └── test_database.py        # Database testing
│
├── monitoring/                 # Monitoring configuration
│   ├── prometheus/
│   │   └── prometheus.yml      # Prometheus scrape config
│   └── grafana/
│       ├── dashboards/         # Dashboard definitions
│       └── datasources/        # Data source configs
│
├── tests/                      # Test suite
│   ├── conftest.py             # Shared fixtures
│   ├── api/                    # GraphQL type and resolver tests
│   └── unit/                   # Asset, resource, settings and model tests
│
└── .github/workflows/ci.yml    # Ruff, pytest, docker compose config
```

## Key Patterns & Conventions

### Configuration Management
- **Environment variables**: All config via `.env` file (copy from `.env.example`)
- **Settings module**: Use `shared/config/settings.py` for type-safe config
  ```python
  from shared.config.settings import settings
  postgres_url = settings.postgres_url
  redis_url = settings.redis_url
  elastic_url = settings.elastic_url
  ```
- **Validation**: Settings have Pydantic validators for critical fields

### Database Schema
- **Location**: `shared/database/01-schema.sql`
- **8 Core Tables**: `organisms`, `peptides`, `bioactivity`, `structures`, `properties`, `peptide_similarities`, `pipeline_runs`, `screening_jobs`
- **Primary Keys**: All use UUID (generated via `uuid_generate_v4()`)
- **Sequences**: Validated via regex `^[ACDEFGHIKLMNPQRSTVWYXBZUO]+$` (accepts standard 20 amino acids plus non-standard codes XBZUO used in protein databases)
- **Deduplication**: `sequence_hash` (SHA256) for identifying duplicate sequences
- **Quality Scoring**: `calculate_peptide_quality()` function returns 0.00-1.00 completeness score
- **Views**: `peptides_enriched` - pre-aggregated view for API queries
- **Auto-updates**: Trigger function `update_updated_at_column()` on all tables

### Pydantic Models Convention
- **Base Models**: Inherit from `BaseModel` with `ConfigDict(from_attributes=True)`
- **Validators**: Use `@field_validator` decorator
- **Computed Fields**: Use `@computed_field` decorator with `@property`
- **Naming pattern**: `{Model}Create`, `{Model}Update`, `{ModelWithRelations}` for variants
- **Example data**: Include `json_schema_extra` with examples
- **Location**: All models in `shared/models/`

### Dagster Assets Convention
- **Grouping**: Assets live in `dagster_pipelines/assets/`; the job and daily schedule are in `dagster_pipelines/jobs/`
- **Return type**: Always return `MaterializeResult` with metadata
- **Context**: Use `AssetExecutionContext` for logging
- **Dependencies**: Specify deps as function parameters
- **Metadata**: Return row counts, timestamps, quality scores
- **Location**: `dagster_pipelines/assets/`

### GraphQL Schema Convention (FastAPI + Strawberry)
- **Schema files**: `api/schema/queries.py` (resolvers) and `api/schema/types.py` (types/filters)
- **Scope**: Query-only — there are no mutations or subscriptions
- **Strawberry decorators**: Use `@strawberry.type` for types, `@strawberry.field` for resolvers

### Docker Development
- **Build images**: `make build`
- **Start services**: `make up`  
- **Stop services**: `make down`
- **Check health**: `make health` OR `make ps`
- **View logs**: `make logs` (all services) or `make logs-<service>`
- **Database init**: `make init-db`
- **Test**: `make test` or `make test-cov`

## Common Workflows

### 1. Starting Development Environment
```bash
# Copy env file
cp .env.example .env
# Edit .env with your settings

# Start all services
make up

# Wait for services to be healthy (30-60s)
make health

# Verify infrastructure
python3 scripts/verify_infrastructure.py
```

### 2. Running Dagster Pipelines
```bash
# Via Dagster UI
# Navigate to http://localhost:3000

# Via CLI
docker exec venomflow-dagster-daemon dagster job execute -m dagster_pipelines -j <job_name>

# Run tests
make test
```

### 3. Database Workflows
```bash
# Initialize database
make init-db

# Connect to database
make shell-db

# Backup database
make backup-db

# Restore database
make restore-db FILE=backup_YYYYMMDD_HHMMSS.sql
```

### 4. Testing Changes
```bash
# Run tests
make test

# Run with coverage
make test-cov

# Check logs
make logs-dagster-daemon | grep ERROR
```

### 5. Code Quality
Packages accessible via virtual environment `.venv`. Activate via `source .venv/bin/activate` from root directory.
```bash
# Format code
black .

# Sort imports
isort .

# Lint
flake8 .

# Type check
mypy .
```

## Important Files

| File | Purpose | Key Points |
|------|---------|-------------|
| `docker-compose.yml` | Service definitions | 8 services: postgres, redis, elasticsearch, prometheus, grafana, dagster-webserver, dagster-daemon, api |
| `shared/database/01-schema.sql` | Database schema | 8 tables, UUID PKs, triggers, views, quality function |
| `shared/config/settings.py` | Config management | Pydantic BaseSettings, all env vars defined |
| `dagster_pipelines/__init__.py` | Dagster definitions | Main entry point for assets |
| `dagster_pipelines/assets/` | Data pipeline logic | Ingestion, enrichment, similarity, indexing |
| `api/main.py` | FastAPI entry point | GraphQL server setup |
| `shared/models/` | Data models | Pydantic models with validation |
| `scripts/verify_infrastructure.py` | Health check script | Tests all service connectivity |

## Database Schema Highlights

### Key Tables

**peptides**: Core table with sequence data
- `sequence_hash`: SHA256 for deduplication
- `quality_score`: 0.00-1.00 completeness
- Validation: Only valid amino acids allowed

**peptide_similarities**: Sequence relationships for screening
- `similarity_score`: 0.0000-1.0000
- `alignment_method`: 'blast', 'smith-waterman', etc.
- Unique constraint on ordered pairs to prevent duplicates

**screening_jobs**: Virtual screening operations
- `parameters`: JSON configuration
- `results`: JSON output
- Tracks status and timing

### Useful Database Functions

```sql
-- Calculate quality score for a peptide
SELECT calculate_peptide_quality(peptide_uuid);

-- Get enriched peptide data for API
SELECT * FROM peptides_enriched WHERE quality_score > 0.8 LIMIT 10;
```

## Service Ports & URLs

| Service | Port | URL | Credentials |
|---------|------|-----|-------------|
| Dagster UI | 3000 | http://localhost:3000 | See env file |
| Grafana | 3001 | http://localhost:3001 | admin/.env password |
| API | 8000 | http://localhost:8000 | (future implementation) |
| Prometheus | 9090 | http://localhost:9090 | None |
| Elasticsearch | 9200 | http://localhost:9200 | elastic/.env password |
| PostgreSQL | 5432 | localhost:5432 | venomflow_user/.env password |
| Redis | 6379 | localhost:6379 | .env password |

## Common Tasks & Where to Look

| Task | Where to Start | Notes |
|------|---------------|-------|
| **Fetch UniProt data** | `dagster_pipelines/assets/ingestion.py` | Implements rate limiting, pagination |
| **Validate sequences** | `shared/models/peptide.py` | Pydantic `@field_validator` regex for amino acids |
| **Compute properties** | `dagster_pipelines/assets/property_calculators.py` | RDKit/BioPython helpers |
| **Sequence similarity** | `dagster_pipelines/assets/blast_similarity.py` | BioPython alignment |
| **GraphQL query** | `api/schema/queries.py` | Resolvers and row mapping |
| **Database query** | `shared/database/connection.py` | Connection pooling |
| **Elasticsearch search** | `api/schema/queries.py` (`search_peptides`) | Full-text search |
| **Add new API endpoint** | `api/schema/queries.py`, `api/schema/types.py` | Schema + resolver pattern |
| **Add new Dagster asset** | `dagster_pipelines/assets/` | Create asset, add to `dagster_pipelines/__init__.py` defs |
| **Configure logging** | `.env` file | `app_log_level` variable |

## Testing Approach

- **Unit tests**: Test individual functions in `tests/unit/`
- **Dagster tests**: Test assets in `dagster_pipelines/tests/`
- **Run command**: `make test` or `make test-cov`
- **Coverage**: HTML reports in `htmlcov/`

## Data Flow Overview

```
UniProt API
    ↓ (Dagster Ingestion)
PostgreSQL (raw data)
    ↓ (Dagster Validation & Enrichment)
  ├──→ Properties calculated (RDKit)
  ├──→ Sequence similarity computed
  └──→ Elasticsearch indexed
    ↓ (GraphQL API)
  Computational chemists
    ↓ ( Screening jobs)
  Results storage (PostgreSQL)
```

## Architecture Principles

1. **Separation of Concerns**: Each service has single responsibility
2. **Loose Coupling**: Services communicate via defined interfaces
3. **Asset-Based**: Dagster orchestrates via data assets
4. **Data Quality**: Built-in validation at multiple stages
5. **Observability**: Comprehensive logging, metrics, tracing
6. **Extensibility**: Plugin-style architecture for data sources, enrichers

## Environment Variables (Critical)

All required variables defined in `.env.example`. Must customize these:

- `POSTGRES_PASSWORD`, `REDIS_PASSWORD`, `ELASTIC_PASSWORD`
- `GRAFANA_ADMIN_PASSWORD`
- `API_SECRET_KEY` (32+ characters)
- `DAGSTER_POSTGRES_PASSWORD`

Always check `make health` after changes.

## Quick Reference

### Make Commands
```bash
make help          # Show all commands
make build         # Build images
make up            # Start services
make down          # Stop services
make ps            # Check status
make logs          # View all logs
make logs-<service># View specific service logs
make health        # Health check
make test          # Run tests
make init-db       # Initialize database
make clean         # Remove all (volumes)
```

### Docker Commands
```bash
docker-compose ps              # Service status
docker-compose logs <service>  # Service logs
docker-compose restart <service>  # Restart service
```

### Database Commands
```bash
make shell-db        # PostgreSQL shell
make backup-db       # Backup
make restore-db FILE=file.sql  # Restore
```

### Validation Script
```bash
python3 scripts/verify_infrastructure.py
# Tests: postgres, redis, elasticsearch, prometheus, grafana
# Exits 0 if all pass, 1 if any fail
```

## Known Limitations & TODO

- GraphQL API is query-only (no mutations or subscriptions, no authentication)
- No dedicated data-validation asset; validation is model-level (Pydantic)
- Similarity is pre-computed and stored; there is no live BLAST runner
- Screening jobs framework is a database table only, not functional
- Grafana dashboard is provisioned but alerting is not configured

## Development Workflow

1. **Before coding**: `make health` to ensure services running
2. **Make changes**: Edit relevant files
3. **Test changes**: `make test` or `make test-cov`
4. **Restart services**: `make restart` (if needed)
5. **Check logs**: `make logs-dagster-daemon` for errors
6. **Commit changes**: Use `make clean` only if starting fresh (removes volumes!)

## Important Notes

- Do NOT commit `.env` file (contains secrets)
- Use `.env.example` as template
- Sequence validation is strict (only 20 amino acids)
- UUIDs required for all primary keys
- All services have health checks
- Elasticsearch requires 512MB+ JVM memory
- Use `make logs-<service>` not `docker logs` for consistent formatting
- Virtual environment accessible via `.venv` on root folder of the project

---

This guide should help AI agents quickly understand the project structure and effectively work on the VenomFlow codebase. For project development plans, see `venomflow_agent_optimized_plan.md`.