#!/bin/bash
# Odoo PostgreSQL Backup Script
# Runs via cron (daily at 2 AM)

set -e

BACKUP_DIR="$HOME/backups/odoo"
CONTAINER_NAME="employee_postgres"
DB_NAME="odoo"
DB_USER="odoo"
KEEP_DAYS=7

# Create backup directory
mkdir -p "$BACKUP_DIR"

# Timestamp
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_FILE="$BACKUP_DIR/odoo_backup_${TIMESTAMP}.sql.gz"

echo "[$(date)] Starting Odoo backup..."

# Dump database
docker exec "$CONTAINER_NAME" pg_dump -U "$DB_USER" "$DB_NAME" | gzip > "$BACKUP_FILE"

if [ $? -eq 0 ]; then
    SIZE=$(du -h "$BACKUP_FILE" | cut -f1)
    echo "[$(date)] Backup successful: $BACKUP_FILE ($SIZE)"
else
    echo "[$(date)] ERROR: Backup failed!"
    exit 1
fi

# Clean up old backups
echo "[$(date)] Cleaning up backups older than $KEEP_DAYS days..."
find "$BACKUP_DIR" -name "odoo_backup_*.sql.gz" -mtime +$KEEP_DAYS -delete

# Count remaining backups
COUNT=$(ls -1 "$BACKUP_DIR"/odoo_backup_*.sql.gz 2>/dev/null | wc -l)
echo "[$(date)] Backup complete. $COUNT backup(s) retained."
