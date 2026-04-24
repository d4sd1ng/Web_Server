from flask import Blueprint, jsonify, request, session
from functools import wraps
import subprocess
import re

fail2ban_bp = Blueprint('fail2ban', __name__)


def admin_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if 'user' not in session:
            return jsonify({"error": "Nicht eingeloggt"}), 401
        if session.get('role') != 'admin':
            return jsonify({"error": "Nur Admins"}), 403
        return f(*args, **kwargs)
    return decorated


def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if 'user' not in session:
            return jsonify({"error": "Nicht eingeloggt"}), 401
        return f(*args, **kwargs)
    return decorated


def _run(cmd, timeout=60):
    try:
        r = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=timeout)
        return r.stdout.strip(), r.stderr.strip(), r.returncode
    except subprocess.TimeoutExpired:
        return "", "Timeout", -1
    except Exception as e:
        return "", str(e), -1


def _installed():
    out, _, code = _run("which fail2ban-client")
    return code == 0 and bool(out)


def _running():
    _, _, code = _run("systemctl is-active fail2ban")
    return code == 0


@fail2ban_bp.route('/api/fail2ban/status')
@login_required
def f2b_status():
    installed = _installed()
    running = _running() if installed else False

    jails = []
    if running:
        out, _, _ = _run("fail2ban-client status")
        for line in out.splitlines():
            if "Jail list" in line:
                parts = line.split(":", 1)
                if len(parts) == 2:
                    jails = [j.strip() for j in parts[1].split(",") if j.strip()]

    jail_data = []
    for jail in jails:
        out, _, _ = _run(f"fail2ban-client status {jail}")
        entry = {"name": jail, "total_banned": 0, "currently_banned": 0, "banned_ips": [], "total_failed": 0}
        for line in out.splitlines():
            line = line.strip()
            if "Currently banned:" in line:
                m = re.search(r'\d+', line)
                entry["currently_banned"] = int(m.group()) if m else 0
            elif "Total banned:" in line:
                m = re.search(r'\d+', line)
                entry["total_banned"] = int(m.group()) if m else 0
            elif "Banned IP list:" in line:
                ips_part = line.split(":", 1)[1].strip()
                entry["banned_ips"] = [ip for ip in ips_part.split() if ip]
            elif "Total failed:" in line:
                m = re.search(r'\d+', line)
                entry["total_failed"] = int(m.group()) if m else 0
        jail_data.append(entry)

    return jsonify({
        "installed": installed,
        "running": running,
        "jails": jail_data,
    })


@fail2ban_bp.route('/api/fail2ban/install', methods=['POST'])
@admin_required
def f2b_install():
    if _installed():
        return jsonify({"message": "Fail2Ban ist bereits installiert"})
    out, err, code = _run(
        "sudo DEBIAN_FRONTEND=noninteractive apt-get install -y fail2ban 2>&1",
        timeout=180
    )
    if code != 0:
        return jsonify({"error": err or out}), 500
    # enable + start
    _run("sudo systemctl enable fail2ban")
    _run("sudo systemctl start fail2ban")
    return jsonify({"message": "Fail2Ban installiert und gestartet", "output": out})


@fail2ban_bp.route('/api/fail2ban/service', methods=['POST'])
@admin_required
def f2b_service():
    action = request.json.get('action')
    if action not in ('start', 'stop', 'restart'):
        return jsonify({"error": "Ungültige Aktion"}), 400
    out, err, code = _run(f"sudo systemctl {action} fail2ban")
    return jsonify({"returncode": code, "output": out or err})


@fail2ban_bp.route('/api/fail2ban/unban', methods=['POST'])
@admin_required
def f2b_unban():
    data = request.json or {}
    ip = data.get('ip', '').strip()
    jail = data.get('jail', '').strip()
    if not ip or not jail:
        return jsonify({"error": "IP und Jail erforderlich"}), 400
    # basic validation
    if not re.match(r'^[\w.\-:]+$', ip) or not re.match(r'^[\w\-]+$', jail):
        return jsonify({"error": "Ungültige Parameter"}), 400
    out, err, code = _run(f"sudo fail2ban-client set {jail} unbanip {ip}")
    if code != 0:
        return jsonify({"error": err or out}), 500
    return jsonify({"message": f"{ip} aus {jail} entsperrt"})


@fail2ban_bp.route('/api/fail2ban/logs')
@login_required
def f2b_logs():
    out, err, code = _run("sudo journalctl -u fail2ban -n 60 --no-pager --output=short-iso 2>&1")
    if code != 0:
        return jsonify({"error": err or "Logs nicht verfügbar"}), 500
    return jsonify({"logs": out})
