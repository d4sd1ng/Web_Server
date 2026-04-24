#!/bin/bash
set -euo pipefail

JOB="vps-config"
VPS="d4sd1ng@77.42.74.250"
VPS_KEY="/home/d4sd1ng/.ssh/vps_wg"
NAS="/mnt/nas-backup"
DEST="$NAS/vps/$JOB"
LOG="$NAS/vps/backup.log"
DATE=$(date '+%Y-%m-%d_%H-%M-%S')
SSH="ssh -i $VPS_KEY -o IdentitiesOnly=yes -o IdentityAgent=none -o StrictHostKeyChecking=no"

mkdir -p "$DEST"
echo "==== $(date '+%Y-%m-%d %H:%M:%S') start $JOB ====" >> "$LOG"

$SSH "$VPS" "tar czf - ~/wg-clients ~/reset_wireguard_vps.sh 2>/dev/null" \
    > "$DEST/${JOB}_${DATE}.tar.gz"

ls -t "$DEST"/${JOB}_*.tar.gz 2>/dev/null | tail -n +6 | xargs rm -f

echo "==== $(date '+%Y-%m-%d %H:%M:%S') done $JOB ====" >> "$LOG"
