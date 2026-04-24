#!/usr/bin/env bash
set -euo pipefail

REMOTE_BASE="/mnt/nas-backup/pi-config-core"
LOG_FILE="/opt/server/logs/backup/pi-config-core.log"
DAY="$(date +%u)"
DOM="$(date +%d)"

SOURCES=(
/opt/server/docker-compose.yml
/opt/server/project_overview.md
/opt/server/architecture_rules.md
/opt/server/current_state.md
/opt/server/decision_log.md
/opt/server/task_contract.md
/opt/server/traefik/config
/opt/server/traefik/letsencrypt
/opt/server/traefik/traefik.yml
/opt/server/logs/traefik/logs
/opt/server/authelia/config
/opt/server/authelia/redis
/opt/server/adguard/work
/opt/server/adguard/conf
/opt/server/homer/assets
)

mkdir -p /opt/server/logs/backup
mkdir -p "${REMOTE_BASE}/current" "${REMOTE_BASE}/daily" "${REMOTE_BASE}/weekly" "${REMOTE_BASE}/monthly"

{
echo "==== $(date '+%F %T') start pi-config-core ===="

rsync -a --delete "${SOURCES[@]}" "${REMOTE_BASE}/current/"

rm -rf "${REMOTE_BASE}/daily/d3"
[ -d "${REMOTE_BASE}/daily/d2" ] && mv "${REMOTE_BASE}/daily/d2" "${REMOTE_BASE}/daily/d3" || true
[ -d "${REMOTE_BASE}/daily/d1" ] && mv "${REMOTE_BASE}/daily/d1" "${REMOTE_BASE}/daily/d2" || true
cp -a "${REMOTE_BASE}/current" "${REMOTE_BASE}/daily/d1"

if [ "${DAY}" = "7" ]; then
rm -rf "${REMOTE_BASE}/weekly/w2"
[ -d "${REMOTE_BASE}/weekly/w1" ] && mv "${REMOTE_BASE}/weekly/w1" "${REMOTE_BASE}/weekly/w2" || true
cp -a "${REMOTE_BASE}/current" "${REMOTE_BASE}/weekly/w1"
fi

if [ "${DOM}" = "01" ]; then
rm -rf "${REMOTE_BASE}/monthly/m1"
cp -a "${REMOTE_BASE}/current" "${REMOTE_BASE}/monthly/m1"
fi

echo "==== $(date '+%F %T') done pi-config-core ===="
} >> "$LOG_FILE" 2>&1
