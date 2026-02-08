.PHONY: help build up down restart logs ps clean init-db shell-db shell-dagster-daemon shell-dagster-webserver test test-cov backup-db restore-db dev-setup health

# Default target
help:
	@echo "VenomFlow - Docker Management"
	@echo ""
	@echo "Available commands:"
	@echo ""
	@echo "Service Management:"
	@echo "  make build           - Build all Docker images"
	@echo "  make up              - Start all services"
	@echo "  make down            - Stop all services"
	@echo "  make restart         - Restart all services"
	@echo "  make ps              - Show service status"
	@echo "  make clean           - Stop and remove volumes"
	@echo "  make health          - Check health of all services"
	@echo ""
	@echo "Logs:"
	@echo "  make logs                    - View logs (all services)"
	@echo "  make logs-postgres           - View PostgreSQL logs"
	@echo "  make logs-redis              - View Redis logs"
	@echo "  make logs-elasticsearch      - View Elasticsearch logs"
	@echo "  make logs-prometheus         - View Prometheus logs"
	@echo "  make logs-grafana            - View Grafana logs"
	@echo "  make logs-dagster-webserver  - View Dagster webserver logs"
	@echo "  make logs-dagster-daemon     - View Dagster daemon logs"
	@echo ""
	@echo "Database:"
	@echo "  make init-db         - Initialize database"
	@echo "  make shell-db        - Open PostgreSQL shell"
	@echo "  make backup-db       - Backup database"
	@echo "  make restore-db      - Restore database from backup (FILE=path/to/backup.sql)"
	@echo ""
	@echo "Dagster:"
	@echo "  make shell-dagster-daemon     - Open Dagster daemon container shell"
	@echo "  make shell-dagster-webserver  - Open Dagster webserver container shell"
	@echo "  make test                     - Run tests in Dagster daemon"
	@echo "  make test-cov                 - Run tests with coverage"
	@echo ""
	@echo "Development:"
	@echo "  make dev-setup       - Setup development environment"
	@echo ""
	@echo "Services available at:"
	@echo "  Dagster:         http://localhost:3000"
	@echo "  Grafana:         http://localhost:3001"
	@echo "  Prometheus:      http://localhost:9090"
	@echo "  Elasticsearch:   http://localhost:9200"

# Build Docker images
build:
	docker-compose build

# Start all services
up:
	docker-compose up -d
	@echo "Services starting..."
	@echo "Waiting for health checks..."
	@sleep 10
	@docker-compose ps
	@echo ""
	@echo "Services available at:"
	@echo "  Dagster:         http://localhost:3000"
	@echo "  Grafana:         http://localhost:3001"
	@echo "  Prometheus:      http://localhost:9090"
	@echo "  Elasticsearch:   http://localhost:9200"

# Stop all services
down:
	docker-compose down

# Restart all services
restart:
	docker-compose restart

# View logs
logs:
	docker-compose logs -f

# View logs for specific service
logs-postgres:
	docker-compose logs -f postgres

logs-redis:
	docker-compose logs -f redis

logs-elasticsearch:
	docker-compose logs -f elasticsearch

logs-prometheus:
	docker-compose logs -f prometheus

logs-grafana:
	docker-compose logs -f grafana

logs-dagster-webserver:
	docker-compose logs -f dagster-webserver

logs-dagster-daemon:
	docker-compose logs -f dagster-daemon

# Show service status
ps:
	docker-compose ps -a

# Clean everything (including volumes)
clean:
	@echo "WARNING: This will remove all volumes and data!"
	@echo "Press Ctrl+C to cancel, or wait 5 seconds to continue..."
	@sleep 5
	docker-compose down -v
	@echo "Clean complete!"

# Initialize database
init-db:
	@echo "Initializing database..."
	docker-compose exec postgres psql -U venomflow_user -d venomflow -f /docker-entrypoint-initdb.d/01-schema.sql
	@echo "Database initialized!"

# Database shell
shell-db:
	docker-compose exec postgres psql -U venomflow_user -d venomflow

# Dagster daemon container shell
shell-dagster-daemon:
	docker-compose exec dagster-daemon bash

# Dagster webserver container shell
shell-dagster-webserver:
	docker-compose exec dagster-webserver bash

# Run tests
test:
	docker-compose exec dagster-daemon pytest tests/ -v

# Run tests with coverage
test-cov:
	docker-compose exec dagster-daemon pytest tests/ -v --cov=src --cov-report=html


# Backup database
backup-db:
	@mkdir -p ./backups
	@echo "Creating database backup..."
	docker-compose exec -T postgres pg_dump -U venomflow_user venomflow > ./backups/venomflow_$$(date +%Y%m%d_%H%M%S).sql
	@echo "Backup created in ./backups/"

# Restore database (specify file with FILE=backup.sql)
restore-db:
	@if [ -z "$(FILE)" ]; then \
		echo "Error: Please specify backup file with FILE=path/to/backup.sql"; \
		exit 1; \
	fi
	@echo "Restoring database from $(FILE)..."
	docker-compose exec -T postgres psql -U venomflow_user venomflow < $(FILE)
	@echo "Database restored!"

# Health check all services
health:
	@echo "Checking service health..."
	@echo ""
	@echo "=== Service Status ==="
	@docker-compose ps
	@echo ""
	@echo "=== Health Checks ==="
	@echo -n "PostgreSQL: "
	@docker-compose exec -T postgres pg_isready -U venomflow_user -d venomflow 2>/dev/null && echo "✓ Healthy" || echo "✗ Unhealthy"
	@echo -n "Redis: "
	@docker-compose exec -T redis redis-cli --raw incr ping >/dev/null 2>&1 && echo "✓ Healthy" || echo "✗ Unhealthy"
	@echo -n "Elasticsearch: "
	@curl -s -u elastic:changeme_elastic_password http://localhost:9200/_cluster/health 2>/dev/null | grep -q "green\|yellow" && echo "✓ Healthy" || echo "✗ Unhealthy"
	@echo -n "Prometheus: "
	@curl -sf http://localhost:9090/-/healthy >/dev/null 2>&1 && echo "✓ Healthy" || echo "✗ Unhealthy"
	@echo -n "Grafana: "
	@curl -sf http://localhost:3001/api/health >/dev/null 2>&1 && echo "✓ Healthy" || echo "✗ Unhealthy"
	@echo -n "Dagster Webserver: "
	@curl -sf http://localhost:3000/server_info >/dev/null 2>&1 && echo "✓ Healthy" || echo "✗ Unhealthy"

# Install development dependencies
dev-setup:
	@echo "Setting up development environment..."
	@if [ ! -f .env ]; then \
		if [ -f .env.example ]; then \
			cp .env.example .env; \
			echo "✓ Environment file created from .env.example"; \
		else \
			echo "✗ Warning: .env.example not found"; \
		fi \
	else \
		echo "✓ .env file already exists"; \
	fi
	@mkdir -p ./backups
	@echo "✓ Created backups directory"
	@echo ""
	@echo "Development environment ready!"
	@echo "Next steps:"
	@echo "  1. Review and update .env file with your settings"
	@echo "  2. Run 'make build' to build Docker images"
	@echo "  3. Run 'make up' to start all services"