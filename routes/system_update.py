from flask import Blueprint, jsonify, session
from functools import wraps
import subprocess

system_update_bp = Blueprint('system_update', __name__)


def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if 'user' not in session:
            return jsonify({"error": "Nicht eingeloggt"}), 401
        return f(*args, **kwargs)
    return decorated


def run(cmd, timeout=60):
    try:
        r = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=timeout)
        return r.stdout.strip(), r.stderr.strip(), r.returncode
    except subprocess.TimeoutExpired:
        return "", "Timeout", -1
    except Exception as e:
        return "", str(e), -1


@system_update_bp.route('/api/system/apt-check')
@login_required
def apt_check():
    out, _, _ = run("sudo apt update -qq 2>/dev/null; apt list --upgradable 2>/dev/null | grep -v 'Listing'")
    packages = [l.strip() for l in out.splitlines() if l.strip()]
    return jsonify({"count": len(packages), "packages": packages})


@system_update_bp.route('/api/system/apt-upgrade', methods=['POST'])
@login_required
def apt_upgrade():
    if session.get('role') != 'admin':
        return jsonify({"error": "Nur Admins"}), 403
    out, err, code = run(
        "sudo apt update -qq 2>&1 && sudo DEBIAN_FRONTEND=noninteractive apt upgrade -y 2>&1",
        timeout=300
    )
    return jsonify({"output": out or err, "returncode": code})


@system_update_bp.route('/api/system/containers')
@login_required
def containers():
    out, _, _ = run("docker ps -a --format '{{.Names}}|{{.Image}}|{{.Status}}|{{.RunningFor}}'")
    rows = []
    for line in out.splitlines():
        parts = line.split('|')
        if len(parts) == 4:
            rows.append({
                "name": parts[0],
                "image": parts[1],
                "status": parts[2],
                "running_for": parts[3],
                "up": parts[2].startswith("Up"),
            })
    return jsonify({"containers": rows})


@system_update_bp.route('/api/system/watchtower-run', methods=['POST'])
@login_required
def watchtower_run():
    if session.get('role') != 'admin':
        return jsonify({"error": "Nur Admins"}), 403
    out, err, code = run("docker exec watchtower /watchtower --run-once 2>&1", timeout=120)
    return jsonify({"output": out or err, "returncode": code})


@system_update_bp.route('/api/system/container-restart/<name>', methods=['POST'])
@login_required
def container_restart(name):
    if session.get('role') != 'admin':
        return jsonify({"error": "Nur Admins"}), 403
    allowed = [c.strip() for c in
               subprocess.run("docker ps -a --format '{{.Names}}'", shell=True,
                              capture_output=True, text=True).stdout.splitlines()]
    if name not in allowed:
        return jsonify({"error": "Unbekannter Container"}), 400
    out, err, code = run(f"docker restart {name}", timeout=30)
    return jsonify({"output": out or err, "returncode": code})
