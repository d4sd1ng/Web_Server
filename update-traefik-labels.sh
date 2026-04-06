#!/usr/bin/env bash
set -euo pipefail

COMPOSE_FILE="${1:-/opt/server/docker-compose.yml}"
BACKUP_FILE="${COMPOSE_FILE}.bak.$(date +%Y%m%d_%H%M%S)"

if [[ ! -f "$COMPOSE_FILE" ]]; then
  echo "Fehler: Datei nicht gefunden: $COMPOSE_FILE"
  exit 1
fi

cp "$COMPOSE_FILE" "$BACKUP_FILE"
echo "Backup erstellt: $BACKUP_FILE"

sed -i \
  -e 's/home\.vpn\.local/home.internal.avataryx.de/g' \
  -e 's/vault\.vpn\.local/vault.internal.avataryx.de/g' \
  -e 's/portainer\.vpn\.local/portainer.internal.avataryx.de/g' \
  -e 's/traefik\.vpn\.local/traefik.internal.avataryx.de/g' \
  -e 's/adguard\.vpn\.local/adguard.internal.avataryx.de/g' \
  "$COMPOSE_FILE"

echo "Domains in Labels ersetzt."

echo
echo "Geänderte Host-Regeln:"
grep -n 'traefik\.http\.routers\..*\.rule=Host' "$COMPOSE_FILE" || true

echo
echo "Fertig."
echo "Zum Anwenden:"
echo "docker compose up -d"
