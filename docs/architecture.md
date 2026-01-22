# VenomFlow Architecture

## Overview

VenomFlow is a microservices-based bioinformatics platform designed for comprehensive venom peptide analysis. The architecture emphasizes scalability, maintainability, and data integrity.

## System Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                         Users / Clients                      │
└──────────────────┬──────────────────────────────────────────┘
                   │
                   ▼
          ┌────────────────┐
          │   GraphQL API   │ ◄──── FastAPI + Strawberry
          │   (Port 8000)   │
          └────────┬────────┘
                   │
        ┌──────────┴──────────┐
        ▼                     ▼
┌──────────────┐      ┌──────────────┐
│  PostgreSQL  │      │    Redis     │
│  (Primary    │      │  (Caching &  │
│   Storage)   │      │   Queuing)   │
└──────┬───────┘      └──────┬───────┘
       │                     │
       │   ┌─────────────────┴─────────┐
       │   │                           │
       ▼   ▼                           ▼
┌──────────────────┐           ┌──────────────┐
│     Dagster      │           │   Workers    │
│  (Orchestration) │──────────▶│  Background  │
│   (Port 3001)    │           │  Processing  │
└──────────────────┘           └──────────────┘
       │
       ▼
┌──────────────────┐
│   Monitoring     │
│  Prometheus +    │
│    Grafana       │
└──────────────────┘
```

## Core Components

### 1. GraphQL API (FastAPI + Strawberry)

**Purpose**: Provides a modern, flexible API for querying venom peptide data.

**Key Features**:
- Type-safe GraphQL schema
- Real-time subscriptions for pipeline updates
- Efficient data fetching with field selection
- Built-in API documentation

**Technology Stack**:
- FastAPI for HTTP server
- Strawberry for GraphQL
- SQLAlchemy for ORM
- Redis for caching

### 2. Dagster (Data Orchestration)

**Purpose**: Manages data pipelines for ingestion, validation, and enrichment.

**Key Features**:
- Asset-based data modeling
- Automatic lineage tracking
- Incremental processing
- Built-in observability

**Pipeline Stages**:
1. **Ingestion**: Fetch data from UniProt, NCBI
2. **Validation**: Ensure data quality
3. **Enrichment**: Calculate properties, run BLAST
4. **Storage**: Persist to PostgreSQL

### 3. PostgreSQL Database

**Purpose**: Primary data store for all venom peptide information.

**Schema Design**:
- **organisms**: Taxonomy information
- **peptides**: Sequence and metadata
- **peptide_properties**: Calculated biochemical properties
- **bioactivities**: Biological activity data
- **blast_results**: Sequence similarity results
- **pipeline_runs**: Pipeline execution tracking

### 4. Background Workers

**Purpose**: Handle computationally intensive tasks asynchronously.

**Worker Types**:
- **Enrichment Worker**: Calculate peptide properties
- **BLAST Runner**: Sequence similarity searches

### 5. Redis

**Purpose**: Caching and job queue management.

**Use Cases**:
- API response caching
- Job queue for workers
- Session storage
- Real-time pubsub

### 6. Monitoring (Prometheus + Grafana)

**Purpose**: Observability and performance monitoring.

**Metrics Tracked**:
- API response times
- Pipeline execution duration
- Database query performance
- Worker processing rates
- System resource usage

## Data Flow

### Ingestion Pipeline

```
External Sources → Dagster Ingestion → Validation → Enrichment → PostgreSQL
     ↓                                                    ↑
 (UniProt, NCBI)                                   Background Workers
```

### Query Flow

```
Client → GraphQL API → Redis Cache → PostgreSQL → Response
                           ↓
                      Cache Hit ──────────────────┘
```

## Scalability Considerations

### Horizontal Scaling

- **API**: Multiple FastAPI instances behind load balancer
- **Workers**: Scale worker count based on queue depth
- **Dagster**: Distributed execution with Docker

### Vertical Scaling

- **Database**: PostgreSQL read replicas
- **Redis**: Redis Cluster for distributed caching

### Performance Optimization

- Database indexing on frequently queried fields
- Connection pooling for database connections
- Redis caching for hot data
- Batch processing in workers
- GraphQL field selection to minimize data transfer

## Security

### Data Protection

- Environment variable-based configuration
- Secrets management (not hardcoded)
- Database connection encryption
- API authentication (JWT tokens - to be implemented)

### Access Control

- Row-level security in PostgreSQL
- API rate limiting
- CORS configuration
- Input validation and sanitization

## Deployment

### Docker Compose (Development)

All services run in Docker containers with docker-compose.yml orchestration.

### Production Deployment

Recommended stack:
- **Container Orchestration**: Kubernetes
- **Database**: Managed PostgreSQL (AWS RDS, Google Cloud SQL)
- **Caching**: Managed Redis (ElastiCache, MemoryStore)
- **Monitoring**: Prometheus + Grafana on separate instances
- **Load Balancing**: Cloud load balancers (ALB, Cloud Load Balancing)

## Technology Stack Summary

| Component | Technology | Purpose |
|-----------|------------|---------|
| API | FastAPI + Strawberry | GraphQL API server |
| Orchestration | Dagster | Data pipeline management |
| Database | PostgreSQL 15 | Primary data storage |
| Cache/Queue | Redis 7 | Caching and job queuing |
| Monitoring | Prometheus + Grafana | Observability |
| Workers | Python | Background processing |
| Containerization | Docker | Service isolation |

## Future Enhancements

1. **Machine Learning Integration**: Peptide activity prediction models
2. **Advanced Search**: Full-text search with Elasticsearch
3. **Real-time Processing**: Stream processing with Apache Kafka
4. **API Gateway**: Kong or Traefik for advanced routing
5. **Microservices Split**: Separate services for different organism families
