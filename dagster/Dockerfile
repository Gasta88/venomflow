FROM python:3.11-slim

WORKDIR /opt/dagster/app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    postgresql-client \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Set environment variables
ENV DAGSTER_HOME=/opt/dagster/app

# Expose Dagster webserver port
EXPOSE 3000

# Default command (can be overridden in docker-compose)
CMD ["dagster-webserver", "-h", "0.0.0.0", "-p", "3000"]
