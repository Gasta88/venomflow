# VenomFlow 🐍

A comprehensive bioinformatics platform for venom peptide analysis, combining data orchestration, enrichment pipelines, and modern API access.

## 🏗️ Architecture

VenomFlow follows a microservices architecture with the following components:

- **Dagster**: Data orchestration and pipeline management
- **FastAPI + GraphQL**: Modern API layer for data access
- **PostgreSQL**: Primary data storage
- **Redis**: Caching and job queuing
- **Prometheus + Grafana**: Monitoring and observability

## 📁 Project Structure

```
venomflow/
├── dagster/          # Orchestration pipelines and assets
├── api/              # GraphQL API service
├── shared/           # Shared models, config, and utilities
├── workers/          # Background workers for compute tasks
├── scripts/          # Utility scripts for setup and maintenance
├── monitoring/       # Prometheus and Grafana configurations
├── tests/            # Test suite
└── docs/             # Documentation
```

## 🚀 Quick Start

### Prerequisites

- Docker and Docker Compose
- Python 3.11+
- Git

### Setup

1. Clone the repository:
```bash
git clone https://github.com/Gasta88/venomflow.git
cd venomflow
```

2. Copy environment configuration:
```bash
cp .env.example .env
# Edit .env with your configuration
```

3. Start all services:
```bash
docker-compose up -d
```

4. Initialize the database:
```bash
./scripts/init_database.sh
```

### Access Points

- **Dagster UI**: http://localhost:3001
- **GraphQL API**: http://localhost:8000/graphql
- **Grafana**: http://localhost:3000 (admin/admin)
- **Prometheus**: http://localhost:9090

## 🧪 Development

### Running Tests

```bash
# Unit tests
pytest tests/unit/

# Integration tests
pytest tests/integration/

# All tests with coverage
pytest --cov=. tests/
```

### Local Development

Each service can be run locally for development:

```bash
# Dagster development
cd dagster
pip install -r requirements.txt
dagster dev

# API development
cd api
pip install -r requirements.txt
uvicorn main:app --reload
```

## 📊 Data Pipeline

VenomFlow processes venom peptide data through multiple stages:

1. **Ingestion**: Fetch data from UniProt and other sources
2. **Validation**: Ensure data quality and consistency
3. **Enrichment**: Add biological properties, BLAST results, and annotations
4. **Storage**: Persist to PostgreSQL with full lineage tracking

## 🔍 API Usage

Access data through the GraphQL API:

```graphql
query GetPeptide {
  peptide(id: "P12345") {
    id
    sequence
    organism {
      name
      taxonomy
    }
    bioactivities {
      type
      target
      potency
    }
  }
}
```

## 📚 Documentation

- [Architecture Overview](docs/architecture.md)
- [API Reference](docs/api-reference.md)
- [Data Dictionary](docs/data-dictionary.md)
- [Deployment Guide](docs/deployment-guide.md)

## 🤝 Contributing

1. Create a feature branch: `git checkout -b feature/my-feature`
2. Make changes and test thoroughly
3. Commit: `git commit -am 'Add new feature'`
4. Push: `git push origin feature/my-feature`
5. Open a Pull Request

## 📝 License

This project is licensed under the MIT License.

## 🙏 Acknowledgments

- UniProt for peptide data
- NCBI for BLAST services
- The bioinformatics community

---

**VenomFlow** - Turning venom data into biological insights 🧬
