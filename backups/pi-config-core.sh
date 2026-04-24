#!/bin/bash
JOB="pi-config-core"
MOUNT="/mnt/nas-backup"
TARGET="$MOUNT/pi/config-core"
LOG="$MOUNT/pi/backup.log"
TIMESTAMP=$(date +%Y-%m-%d_%H-%M-%S)
DOW=$(date +%u)
DOM=$(date +%d)

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
)

log() { echo "==== $(date '+%Y-%m-%d %H:%M:%S') $1 $JOB ====" | tee -a "$LOG"; }

if ! mountpoint -q "$MOUNT"; then
    echo "$(date '+%Y-%m-%d %H:%M:%S') ERROR: $MOUNT not mounted, aborting $JOB" | tee -a /var/log/backup-error.log
    exit 1
fi

mkdir -p "$TARGET/daily" "$TARGET/weekly" "$TARGET/monthly"

if [ "$DOM" = "01" ]; then TYPE="monthly"
elif [ "$DOW" = "7" ]; then TYPE="weekly"
else TYPE="daily"
fi

ARCHIVE="$TARGET/$TYPE/${JOB}_${TIMESTAMP}.tar.gz"

log "start"

EXISTING=()
for src in "${SOURCES[@]}"; do [ -e "$src" ] && EXISTING+=("$src"); done

tar -czf "$ARCHIVE" "${EXISTING[@]}" 2>>"$LOG"
STATUS=$?
[ $STATUS -ne 0 ] && log "ERROR (tar exit $STATUS)" && exit $STATUS

log "done"

ls -t "$TARGET/daily"/*.tar.gz 2>/dev/null  | tail -n +4 | xargs -r rm --
ls -t "$TARGET/weekly"/*.tar.gz 2>/dev/null | tail -n +3 | xargs -r rm --
ls -t "$TARGET/monthly"/*.tar.gz 2>/dev/null| tail -n +2 | xargs -r rm --
