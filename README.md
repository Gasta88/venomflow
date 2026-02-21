# VenomFlow

**VenomFlow** is a microservices-based data pipeline platform for comprehensive venom peptide research. It provides automated data ingestion, validation, enrichment, and analysis of venom peptides from multiple biological databases, enabling researchers to discover novel bioactive compounds and therapeutic candidates.

---

## Table of Contents

- [Overview](#-overview)
- [Key Features](#-key-features)
- [Use Cases](#-use-cases)
- [Quick Start](#-quick-start)
- [Architecture](#-architecture)
- [Technology Stack](#-technology-stack)
- [Project Structure](#-project-structure)
- [Development Workflow](#-development-workflow)
- [Configuration](#-configuration)
- [API Documentation](#-api-documentation)
- [Data Pipeline](#-data-pipeline)
- [Monitoring & Observability](#-monitoring--observability)
- [Testing](#-testing)
- [Deployment](#-deployment)

---

## Overview

VenomFlow is designed for collecting, processing, and analyzing venom peptide data from UniProt. The platform leverages data engineering practices and tools to provide a scalable, maintainable, and extensible solution for venom research.

### Why VenomFlow?

- **Automated Data Pipelines**: Schedule and orchestrate data workflows with Dagster
- **Scalable Architecture**: Microservices design allows independent scaling of components
- **Rich Search Capabilities**: Full-text search with Elasticsearch
- **GraphQL API**: Flexible data queries with FastAPI and Strawberry
- **Real-time Monitoring**: Track pipeline health and performance with Prometheus & Grafana
- **Research-Ready**: Clean, validated, and enriched data ready for analysis

---

## Key Features

### Data Ingestion & Processing
- **UniProt Integration**: Fetch data from UniProt with rate limiting and pagination
- **Automated Validation**: Ensure data quality with comprehensive validation rules
- **Sequence Analysis**: Sequence similarity analysis for homology searches
- **Property Enrichment**: Automatic calculation of physicochemical properties
- **Batch Processing**: Efficient handling of large datasets

### Search & Discovery
- **Full-text Search**: Fast, relevant search across all peptide data
- **Advanced Filtering**: Filter by organism, bioactivity, properties, and more
- **Faceted Search**: Aggregate and explore data by multiple dimensions
- **Relationship Mapping**: Discover connections between peptides, organisms, and bioactivities

### API & Integration
- **GraphQL API**: Flexible queries with precise data fetching
- **RESTful Endpoints**: Standard HTTP interfaces for common operations
- **Authentication**: Secure access with JWT tokens
- **Interactive Documentation**: Auto-generated API docs with Swagger/GraphQL Playground

### Monitoring & Analytics
- **Real-time Dashboards**: Monitor pipeline execution and system health
- **Alert System**: Get notified of pipeline failures or anomalies
- **Metrics Collection**: Track throughput, latency, and resource usage
- **Historical Analysis**: Visualize trends over time

---

## Use Cases

### Drug Discovery
- Identify novel peptides with specific bioactivities
- Screen potential therapeutic candidates
- Analyze structure-activity relationships

### Comparative Biology
- Study venom peptide evolution across species
- Identify conserved sequences and motifs
- Map bioactivity distribution across taxa

### Toxinology Research
- Catalog venom components from diverse organisms
- Track toxin variants and isoforms
- Link peptides to clinical effects

### Chemical Biology
- Analyze physicochemical properties
- Predict peptide stability and solubility
- Design peptide modifications

---

## Quick Start

Get VenomFlow running locally in under 5 minutes!

### Prerequisites

- **Docker** 24.0+ and **Docker Compose** v2.0+
- **Git** for cloning the repository
- At least **8GB RAM** and **20GB disk space**

### Installation

1. **Clone the repository**
   ```bash
   git clone https://github.com/Gasta88/venomflow.git
   cd venomflow
   ```

2. **Configure environment variables**
   ```bash
   cp .env.example .env
   # Edit .env with your preferred settings (optional for quick start)
   nano .env
   ```

3. **Start all services**
   ```bash
   make up
   ```

4. **Wait for services to be healthy** (30-60 seconds)
   ```bash
   make ps
   ```

5. **Access the services**
   - **Dagster UI**: http://localhost:3000
   - **Grafana**: http://localhost:3001
   - **Prometheus**: http://localhost:9090
   - **Elasticsearch**: http://localhost:9200
   - **PostgreSQL**: localhost:5432

### Verify Installation

```bash
# Check all services are running
make ps

# View all logs
make logs

# Run a test query
curl -X POST http://localhost:8000/graphql \
  -H "Content-Type: application/json" \
  -d '{"query": "{ health }"}'
```

### Stop Services

```bash
# Stop all services
make down

# Stop and remove volumes (WARNING: deletes all data)
make clean
```

---

## Architecture

VenomFlow follows a microservices architecture with a separation of concerns.

```
┌─────────────────────────────────────────────────────────────────┐
│                         VenomFlow Platform                      │
└─────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│                      API Layer (FastAPI)                        │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │   GraphQL API                  REST API                   │  │
│  │   - Queries                    - Health checks            │  │
│  │   - Mutations                  - Batch operations         │  │
│  │   - Subscriptions              - File uploads             │  │
│  └──────────────────────────────────────────────────────────┘   │
└───────────────────────────┬─────────────────────────────────────┘
                            │
┌───────────────────────────┴─────────────────────────────────────┐
│              Orchestration Layer (Dagster)                      │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │  Dagster Web Server    │    Dagster Daemon               │   │
│  │  - Pipeline UI         │    - Scheduler                  │   │
│  │  - Job monitoring      │    - Sensors                    │   │
│  │  - Asset lineage       │    - Run coordinator            │   │
│  └──────────────────────────────────────────────────────────┘   │
└───────────────────────────┬─────────────────────────────────────┘
                            │
┌───────────────────────────┴─────────────────────────────────────┐
│                     Processing Layer                            │
│  ┌────────────────┬────────────────┬────────────────────────┐   │
│  │  Ingestion     │  Validation    │  Enrichment            │   │
│  │  - UniProt     │  - Schema      │  - Properties          │   │
│  │                │  - Quality     │  - Similarity          │   │
│  │                │  - Dedup       │  - Cross-reference     │   │
│  └────────────────┴────────────────┴────────────────────────┘   │
└───────────────────────────┬─────────────────────────────────────┘
                            │
┌───────────────────────────┴─────────────────────────────────────┐
│                      Storage Layer                              │
│  ┌──────────────┬──────────────┬──────────────┐                 │
│  │ PostgreSQL   │ Elasticsearch│    Redis     │                 │
│  │ - Structured │ - Full-text  │ - Cache      │                 │
│  │ - Relations  │ - Search     │ - Sessions   │                 │
│  │ - Metadata   │ - Analytics  │ - Queue      │                 │
│  └──────────────┴──────────────┴──────────────┘                 │
└───────────────────────────┬─────────────────────────────────────┘
                            │
┌───────────────────────────┴─────────────────────────────────────┐
│              Monitoring Layer (Prometheus/Grafana)              │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │  Metrics Collection    │    Visualization                │   │
│  │  - Service health      │    - Dashboards                 │   │
│  │  - Pipeline metrics    │    - Alerts                     │   │
│  │  - Resource usage      │    - Historical data            │   │
│  └──────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────┘
```

### Architecture Principles

1. **Separation of Concerns**: Each service has a single and defined responsibility
2. **Loose Coupling**: Services communicate via defined interfaces
3. **High Cohesion**: Related functionality is grouped together
4. **Scalability**: Services can be scaled independently based on load
5. **Resilience**: Failure in one service doesn't cascade to others
6. **Observability**: Comprehensive logging, metrics, and tracing

---

## Project Structure

```
venomflow/
├── README.md                        # This file
├── .env.example                     # Environment variables template
├── .gitignore                       # Git ignore rules
├── docker-compose.yml               # Docker orchestration
│
├── api/                             # FastAPI GraphQL API
│   ├── Dockerfile                      # API container definition
│   ├── requirements.txt                # API dependencies
│   ├── main.py                         # API entry point
│   ├── schema/                         # GraphQL schema definitions
│   │   ├── queries.py                  # Query resolvers
│   │   ├── mutations.py                # Mutation resolvers
│   │   └── subscriptions.py            # Subscription resolvers
│   ├── resolvers/                      # Business logic
│   │   └── peptide.py                  # Peptide resolvers
│   ├── services/                       # Service layer
│   │   └── search.py                   # Search services
│   └── tests/                          # API tests
│
├── dagster_pipelines/               # Dagster orchestration
│   ├── Dockerfile                      # Dagster container definition
│   ├── requirements.txt                # Dagster dependencies
│   ├── dagster.yaml                    # Dagster configuration
│   ├── workspace.yaml                  # Workspace definition
│   ├── assets/                         # Data assets (tables/files)
│   │   ├── ingestion.py                # Data ingestion assets
│   │   ├── validation.py               # Validation assets
│   │   └── enrichment.py               # Enrichment assets
│   ├── resources/                      # External resources
│   │   └── database.py                 # Database connections
│   ├── jobs/                           # Job definitions
│   ├── sensors/                        # Event sensors
│   └── tests/                          # Pipeline tests
│
├── shared/                          # Shared code across services
│   ├── config/                         # Configuration management
│   │   └── settings.py                 # Pydantic settings
│   ├── models/                         # Data models
│   │   ├── organism.py                 # Organism model
│   │   ├── peptide.py                  # Peptide model
│   │   ├── bioactivity.py              # Bioactivity model
│   │   └── properties.py               # Properties model
│   ├── database/                       # Database utilities
│   │   ├── connection.py               # Connection management
│   │   ├── schema.sql                  # Database schema
│   │   └── migrations/                 # Schema migrations
│   └── utils/                          # Utility functions
│       └── validators.py               # Data validators
│
├── workers/                         # Background workers
│   ├── enrichment_worker.py            # Enrichment processor
│   └── blast_runner.py                 # BLAST execution
│
├── scripts/                         # Utility scripts
│   ├── init_database.sh                # Database initialization
│   ├── verify_infrastructure.py        # Infrastructure check
│   ├── seed_test_data.py               # Test data seeding
│   └── backup.sh                       # Backup automation
│
├── monitoring/                      # Monitoring configuration
│   ├── prometheus/                     # Prometheus config
│   │   └── prometheus.yml              # Scrape targets
│   └── grafana/                        # Grafana config
│       ├── dashboards/                 # Dashboard definitions
│       └── datasources/                # Data source config
│
├── tests/                           # Test suite
│   └── unit/                        # Unit fixtures
```

---

##  Configuration

VenomFlow uses environment variables for configuration. Copy `.env.example` to `.env` and customize:

### Critical Settings

```bash
# Application
APP_ENV=development          # development, staging, production
APP_DEBUG=true               # Enable debug mode

# Database
POSTGRES_HOST=postgres
POSTGRES_PORT=5432
POSTGRES_DB=venomflow
POSTGRES_USER=venomflow_user
POSTGRES_PASSWORD=your_secure_password_here

# Cache
REDIS_HOST=redis
REDIS_PORT=6379
REDIS_PASSWORD=your_redis_password_here

# Search
ELASTIC_HOST=elasticsearch
ELASTIC_PORT=9200
ELASTIC_PASSWORD=your_elastic_password_here

# Storage
REDIS_HOST=redis
REDIS_PORT=6379
REDIS_PASSWORD=your_redis_password_here

# API
API_PORT=8000
API_SECRET_KEY=your_32_character_secret_key_here
```

---

## API Documentation

### GraphQL Playground

Access the interactive GraphQL playground at http://localhost:8000/graphql

### Example Queries

**Get peptides with pagination**
```graphql
query GetPeptides {
  searchPeptides(page: 1, pageSize: 10) {
    items {
      id
      sequence
      name
      organism {
        name
        taxonomyId
      }
      bioactivities {
        activityType
        value
      }
    }
    pageInfo {
      total
      page
      pageSize
      totalPages
      hasNext
      hasPrevious
    }
  }
}
```

**Search peptides**
```graphql
query SearchPeptides {
  searchPeptides(query: "neurotoxin", page: 1, pageSize: 5) {
    items {
      id
      sequence
      name
      qualityScore
    }
    pageInfo {
      total
      page
    }
  }
}
```

**Get peptide by UniProt accession**
```graphql
query GetPeptide {
  peptide(accession: "P00974") {
    id
    uniprotId
    name
    sequence
    organism {
      name
      venomType
    }
    properties {
      isoelectricPoint
      hydrophobicity
    }
  }
}
```

**Find similar peptides**
```graphql
query SimilarPeptides {
  similarPeptides(accession: "P00974", threshold: 0.7, limit: 10) {
    queryAccession
    threshold
    items {
      peptide {
        id
        name
        sequence
      }
      similarityScore
      alignmentMethod
    }
    total
  }
}
```

---

## Data Pipeline

### Pipeline Architecture

VenomFlow uses Dagster for orchestrating data pipelines with the following stages:

1. **Ingestion**: Fetch raw data from external sources
2. **Validation**: Verify data quality and completeness
3. **Enrichment**: Add computed properties and cross-references
4. **Indexing**: Update Elasticsearch for fast search

### Running Pipelines

```bash
# Via Dagster UI
# Navigate to http://localhost:3000 and click "Launchpad"

# Via CLI
dagster job execute -m dagster_pipelines -j venomflow_pipeline

# Schedule-based execution
# Pipelines run automatically based on configured schedules
```

### Pipeline Monitoring

- **Real-time**: Watch pipeline execution in Dagster UI
- **Metrics**: View throughput and latency in Grafana
- **Logs**: Access detailed logs in Dagster or via `docker compose logs`
- **Alerts**: Get notified of failures via configured channels

---

## Monitoring & Observability

VenomFlow ships with a fully provisioned **Prometheus + Grafana** monitoring stack.
When you run `make up`, both services start automatically, the Prometheus datasource
is registered in Grafana, and the *VenomFlow Overview* dashboard is loaded — no
manual configuration needed.

### Architecture

```
FastAPI (/metrics)  ──▶  Prometheus (scrape)  ──▶  Grafana (visualise)
```

- **Prometheus** scrapes the FastAPI `/metrics` endpoint every 15 s and stores the
  time-series data.
- **Grafana** reads from Prometheus through a pre-provisioned datasource and displays
  the *VenomFlow Overview* dashboard.

### Accessing the Services

| Service    | URL                        | Credentials                                       |
|------------|----------------------------|----------------------------------------------------|
| Grafana    | http://localhost:3001      | `admin` / value of `GRAFANA_ADMIN_PASSWORD` in `.env` |
| Prometheus | http://localhost:9090      | No authentication                                  |

### Grafana Setup & Dashboard

Grafana is **auto-provisioned** on first start via configuration files mounted into the
container:

| File | Purpose |
|------|---------|
| `monitoring/grafana/datasources/datasource.yml` | Registers Prometheus as the default datasource |
| `monitoring/grafana/dashboards/dashboards.yml` | Tells Grafana where to find dashboard JSON files |
| `monitoring/grafana/dashboards/venomflow-overview.json` | The *VenomFlow Overview* dashboard |

**To inspect the dashboard:**

1. Start all services: `make up`
2. Open Grafana at http://localhost:3001
3. Log in with `admin` / your `GRAFANA_ADMIN_PASSWORD`
4. Navigate to **Dashboards → VenomFlow Overview**

The dashboard contains the following panels:

| Panel | Description |
|-------|-------------|
| API Status | `up` / `down` indicator for the FastAPI service |
| Prometheus Status | `up` / `down` indicator for Prometheus self-monitoring |
| API Request Rate | Requests per second broken down by method, handler, and status |
| API Response Latency | p50 / p95 / p99 response time percentiles |
| HTTP Responses by Status Code | Rate of 2xx, 4xx, 5xx responses |
| Requests In Progress | Number of currently in-flight requests |

### Prometheus Configuration

Prometheus configuration lives at `monitoring/prometheus/prometheus.yml`.
The API scrape target (`api:8000`) is pre-configured; additional exporters
(PostgreSQL, Redis, Elasticsearch) can be enabled by uncommenting or adding
their targets.

### API Metrics Endpoint

The FastAPI application exposes Prometheus-format metrics at
`http://localhost:8000/metrics` using
[`prometheus-fastapi-instrumentator`](https://github.com/trallnag/prometheus-fastapi-instrumentator).
Key metrics include:

- `http_requests_total` — total request count by method, handler, and status
- `http_request_duration_seconds` — request latency histogram
- `http_requests_in_progress` — gauge of in-flight requests

### Logging

Logs are collected in JSON format and available via:

```bash
# All services
make logs

# Specific service
make logs-dagster-webserver

# With grep
make logs | grep ERROR
```

---

## Testing

The project uses **pytest** for unit testing. Tests cover all Dagster pipeline assets, helper functions, resources, job definitions, and shared configuration. No external services (database, Elasticsearch, Redis) are needed to run the test suite — all dependencies are mocked.

### Running Tests

```bash
# Run the full test suite locally (no Docker required)
make test

# Run tests with coverage report
make test-cov

# Run tests inside the Dagster daemon container
make test-docker
```

### Test Structure

```
tests/
├── conftest.py                         # Shared fixtures (mock_context, mock_database_resource, mock_session)
├── unit/
│   ├── assets/
│   │   ├── test_blast_similarity.py    # Sequence alignment, helpers, asset
│   │   ├── test_elasticsearch_indexer.py # Index creation, mapping, bulk indexing
│   │   ├── test_enrichment.py          # Property enrichment asset, batch helpers
│   │   └── test_ingestion.py           # UniProt ingestion, hashing, batch insert
│   ├── test_property_calculators.py    # RDKit/BioPython property computation
│   ├── test_resources.py               # Database, Elasticsearch, Redis resources
│   ├── test_jobs.py                    # Dagster job definitions
│   └── test_settings.py               # Pydantic settings and validators
└── integration/                        # (reserved for future integration tests)
```

---

## Deployment

### Production Deployment

**Quick production setup:**

```bash
# 1. Set production environment
export APP_ENV=production
export APP_DEBUG=false

# 2. Update .env with production values
# - Strong passwords
# - External database hosts
# - Production API keys

# 3. Build production images
make build

# 4. Start services
make up

# 5. Run migrations
docker compose exec dagster-webserver python scripts/migrate.py

# 6. Verify deployment
make ps
curl http://your-domain/health
```

### Infrastructure Requirements

**Minimum (Development)**
- 4 CPU cores
- 8 GB RAM
- 50 GB disk space

**Recommended (Production)**
- 8 CPU cores
- 16 GB RAM
- 200 GB SSD storage
- Load balancer
- Backup storage

