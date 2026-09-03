#!/usr/bin/env bash
# Ежедневный бэкап БД ПЛС (cron)
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

if [[ -f .env ]]; then
  set -a
  # shellcheck disable=SC1091
  source .env
  set +a
fi

LOG_DIR="${PLS_BACKUP_DIR:-backups}"
mkdir -p "$LOG_DIR"
LOG_FILE="$LOG_DIR/backup.log"

log() {
  echo "$(date '+%Y-%m-%d %H:%M:%S') $*" | tee -a "$LOG_FILE"
}

log "=== backup start ==="

ARGS=(pls backup)
if [[ -n "${PLS_BACKUP_RETENTION:-}" ]]; then
  ARGS+=(--retention "$PLS_BACKUP_RETENTION")
fi

if ! flask "${ARGS[@]}" >>"$LOG_FILE" 2>&1; then
  log "ERROR: flask pls backup failed"
  exit 1
fi

log "=== backup ok ==="
