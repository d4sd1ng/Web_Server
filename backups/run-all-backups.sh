#!/bin/bash
set -euo pipefail

NAS="/mnt/nas-backup"
LOG="/tmp/backup-master.log"
CACHE="/tmp/backup_log_cache.json"
BACKUP_DIR="/opt/server/backups"
MAX_WAIT=3300
INTERVAL=60

echo "==== $(date '+%Y-%m-%d %H:%M:%S') backup master start ====" >> "$LOG"

# Wait for NAS: try remount each cycle
waited=0
until sudo /bin/umount -l "$NAS" 2>/dev/null; sudo /bin/mount "$NAS" 2>/dev/null && touch "$NAS/.probe" 2>/dev/null && rm -f "$NAS/.probe"; do
    if [ $waited -ge $MAX_WAIT ]; then
        echo "$(date '+%Y-%m-%d %H:%M:%S') ERROR: NAS not reachable after ${MAX_WAIT}s, aborting" >> "$LOG"
        exit 1
    fi
    echo "$(date '+%Y-%m-%d %H:%M:%S') waiting for NAS... (${waited}s elapsed)" >> "$LOG"
    sleep $INTERVAL
    waited=$((waited + INTERVAL))
done

echo "$(date '+%Y-%m-%d %H:%M:%S') NAS is online, starting jobs" >> "$LOG"

update_cache() {
    local name="$1"
    local status="$2"
    local ts
    ts=$(date '+%Y-%m-%d %H:%M:%S')
    local entry="==== $ts $status $name ===="
    # Read existing cache or start fresh
    local current="{}"
    [ -f "$CACHE" ] && current=$(cat "$CACHE")
    python3 -c "
import json, sys
data = json.loads(sys.argv[1])
data[sys.argv[2]] = sys.argv[3]
print(json.dumps(data))
" "$current" "$name" "$entry" > "${CACHE}.tmp" && mv "${CACHE}.tmp" "$CACHE"
}

run_job() {
    local script="$1"
    local name
    name=$(basename "$script" .sh)
    echo "$(date '+%Y-%m-%d %H:%M:%S') --- starting $name ---" >> "$LOG"
    if bash "$script" >> "$LOG" 2>&1; then
        echo "$(date '+%Y-%m-%d %H:%M:%S') --- $name OK ---" >> "$LOG"
        update_cache "$name" "done"
    else
        echo "$(date '+%Y-%m-%d %H:%M:%S') --- $name FAILED ---" >> "$LOG"
        update_cache "$name" "FAILED"
    fi
}

run_job "$BACKUP_DIR/pi-config-core.sh"
run_job "$BACKUP_DIR/pi-services-data.sh"
run_job "$BACKUP_DIR/pi-monitoring-optional.sh"
run_job "$BACKUP_DIR/vps-config.sh"
run_job "$BACKUP_DIR/vps-docker-data.sh"

echo "==== $(date '+%Y-%m-%d %H:%M:%S') backup master done ====" >> "$LOG"
