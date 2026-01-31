# =============================================================================
# DAGSTER DOCKERFILE
# =============================================================================
# Multi-stage build for Dagster orchestration services

FROM python:3.11-slim as base

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    DAGSTER_HOME=/opt/dagster/dagster_home

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    postgresql-client \
    curl \
    ncbi-blast+ \
    && rm -rf /var/lib/apt/lists/*

# Create application directory
WORKDIR /opt/dagster/app

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt && \
    pip install --no-cache-dir rdkit biopython

# Copy application code
COPY . .

# Create dagster home directory
RUN mkdir -p ${DAGSTER_HOME}

# Expose Dagster webserver port
EXPOSE 3000

# Default command (can be overridden in docker-compose)
CMD ["dagster-webserver", "-h", "0.0.0.0", "-p", "3000"]
