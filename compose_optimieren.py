#!/usr/bin/env python3
from pathlib import Path
from datetime import datetime
import shutil
import sys

COMPOSE_PATH = Path("/opt/server/docker-compose.yml")

LIMITS = {
    "traefik": {"cpus": '"0.50"', "mem_limit": "200m"},
    "adguard": {"cpus": '"1.00"', "mem_limit": "512m"},
    "vaultwarden": {"cpus": '"0.50"', "mem_limit": "256m"},
    "portainer": {"cpus": '"0.30"', "mem_limit": "200m"},
    "homer": {"cpus": '"0.20"', "mem_limit": "100m"},
    "postgres": {"cpus": '"1.50"', "mem_limit": "1g"},
}

def get_indent(line: str) -> int:
    return len(line) - len(line.lstrip(" "))

def is_service_header(line: str) -> bool:
    stripped = line.strip()
    return (
        stripped.endswith(":")
        and not stripped.startswith("#")
        and get_indent(line) == 4
        and stripped[:-1] in LIMITS
    )

def find_service_block_end(lines, start_idx):
    start_indent = get_indent(lines[start_idx])
    i = start_idx + 1
    while i < len(lines):
        line = lines[i]
        stripped = line.strip()
        if stripped and not stripped.startswith("#"):
            indent = get_indent(line)
            if indent <= start_indent:
                break
        i += 1
    return i

def service_has_key(lines, start_idx, end_idx, key):
    key_prefix = f"{key}:"
    for i in range(start_idx + 1, end_idx):
        stripped = lines[i].strip()
        if stripped.startswith(key_prefix):
            return True
    return False

def find_insert_position(lines, start_idx, end_idx):
    preferred_keys = (
        "restart:",
        "mem_limit:",
        "cpus:",
        "pids_limit:",
        "container_name:",
        "image:",
    )
    last_match = None
    for i in range(start_idx + 1, end_idx):
        stripped = lines[i].strip()
        if any(stripped.startswith(k) for k in preferred_keys):
            last_match = i
    if last_match is not None:
        return last_match + 1
    return start_idx + 1

def main():
    if not COMPOSE_PATH.exists():
        print(f"Fehler: Datei nicht gefunden: {COMPOSE_PATH}")
        sys.exit(1)

    backup_path = COMPOSE_PATH.with_suffix(
        COMPOSE_PATH.suffix + "." + datetime.now().strftime("%Y%m%d_%H%M%S") + ".bak"
    )
    shutil.copy2(COMPOSE_PATH, backup_path)

    lines = COMPOSE_PATH.read_text(encoding="utf-8").splitlines(keepends=True)
    output = []
    i = 0
    changed = False

    while i < len(lines):
        line = lines[i]
        if is_service_header(line):
            service_name = line.strip()[:-1]
            start_idx = i
            end_idx = find_service_block_end(lines, start_idx)
            block = lines[start_idx:end_idx]

            has_cpus = service_has_key(lines, start_idx, end_idx, "cpus")
            has_mem = service_has_key(lines, start_idx, end_idx, "mem_limit")

            insert_lines = []
            base_indent = " " * 4
            field_indent = base_indent + " " * 2

            if not has_mem:
                insert_lines.append(f"{field_indent}mem_limit: {LIMITS[service_name]['mem_limit']}\n")
            if not has_cpus:
                insert_lines.append(f"{field_indent}cpus: {LIMITS[service_name]['cpus']}\n")

            if insert_lines:
                insert_pos = find_insert_position(lines, start_idx, end_idx) - start_idx
                block = block[:insert_pos] + insert_lines + block[insert_pos:]
                changed = True

            output.extend(block)
            i = end_idx
        else:
            output.append(line)
            i += 1

    COMPOSE_PATH.write_text("".join(output), encoding="utf-8")

    print(f"Backup erstellt: {backup_path}")
    if changed:
        print("Ressourcenlimits wurden ergänzt.")
    else:
        print("Keine Änderungen nötig. Limits waren bereits vorhanden.")
    print(f"Datei aktualisiert: {COMPOSE_PATH}")

if __name__ == "__main__":
    main()
