#!/bin/bash
# Backup VenomFlow database

set -e

BACKUP_DIR="/home/user/webapp/backups"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_FILE="$BACKUP_DIR/venomflow_backup_$TIMESTAMP.sql"

# Create backup directory if it doesn't exist
mkdir -p "$BACKUP_DIR"

echo "Creating database backup..."

# Perform backup
PGPASSWORD=$POSTGRES_PASSWORD pg_dump \
    -h "$POSTGRES_HOST" \
    -U "$POSTGRES_USER" \
    -d "$POSTGRES_DB" \
    -F c \
    -f "$BACKUP_FILE"

echo "Backup created: $BACKUP_FILE"

# Compress backup
gzip "$BACKUP_FILE"

echo "Backup compressed: ${BACKUP_FILE}.gz"

# Clean up old backups (keep last 7 days)
find "$BACKUP_DIR" -name "venomflow_backup_*.sql.gz" -mtime +7 -delete

echo "Backup complete!"
