#!/usr/bin/env bash
# 备份 PostgreSQL 到 gzip 文件，并清理超过保留天数的旧备份。
set -euo pipefail

cd "$(dirname "$0")/.."

BACKUP_DIR="${BACKUP_DIR:-/var/backups/tallywise}"
KEEP_DAYS="${KEEP_DAYS:-14}"

mkdir -p "$BACKUP_DIR"
file="$BACKUP_DIR/tallywise-$(date +%Y%m%d-%H%M%S).sql.gz"

docker compose exec -T db pg_dump -U tallywise -d tallywise | gzip > "$file"
find "$BACKUP_DIR" -name 'tallywise-*.sql.gz' -mtime +"$KEEP_DAYS" -delete

echo "backup written: $file"
