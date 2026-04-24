from flask import Blueprint, request, jsonify, session
from functools import wraps
import subprocess
import re

wireguard_bp = Blueprint('wireguard', __name__)

WG_INTERFACE = "wg0"
VPS_ENDPOINT = "avataryx.de:51820"
VPS_PUBLIC_KEY = "GGYUfZu5TY2GXAtYyQE67XgiyPWCCKn+NrE5DweuN3w="
VPS_HOST = "77.42.74.250"
VPS_USER = "d4sd1ng"
VPS_SSH_KEY = "/home/d4sd1ng/.ssh/vps_wg"
DNS = "10.0.0.1"
BASE_IP = "10.0.0."


def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if 'user' not in session:
            return jsonify({"error": "Nicht eingeloggt"}), 401
        return f(*args, **kwargs)
    return decorated


def admin_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if 'user' not in session:
            return jsonify({"error": "Nicht eingeloggt"}), 401
        if session.get('role') != 'admin':
            return jsonify({"error": "Nur Admins"}), 403
        return f(*args, **kwargs)
    return decorated


def _run(cmd, timeout=15):
    try:
        r = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=timeout)
        return r.stdout.strip(), r.stderr.strip(), r.returncode
    except subprocess.TimeoutExpired:
        return "", "Timeout", -1
    except Exception as e:
        return "", str(e), -1


def _parse_wg_show():
    import time as _time

    # WireGuard server runs on VPS — SSH there to get peer data
    ssh_cmd = (f"ssh -i {VPS_SSH_KEY} -o StrictHostKeyChecking=no "
               f"-o IdentitiesOnly=yes -o IdentityAgent=none "
               f"{VPS_USER}@{VPS_HOST} sudo wg show {WG_INTERFACE} dump")
    out, err, code = _run(ssh_cmd, timeout=20)
    if code != 0:
        return {"up": False, "peers": [], "interface": {}, "error": err}

    lines = [l for l in out.splitlines() if l.strip()]
    if not lines:
        return {"up": False, "peers": [], "interface": {}, "error": "no output"}

    # First line: interface — pubkey, privkey, listen_port, fwmark
    iface_parts = lines[0].split("\t")
    interface = {}
    if len(iface_parts) >= 3:
        interface["public key"] = iface_parts[0]
        interface["listening port"] = iface_parts[2]

    now = int(_time.time())
    peers = []
    for line in lines[1:]:
        parts = line.split("\t")
        # pubkey, preshared, endpoint, allowed_ips, last_handshake, rx, tx, keepalive
        if len(parts) < 8:
            continue
        pubkey, _, endpoint, allowed_ips, last_hs_str, rx, tx, _ = parts[:8]
        try:
            last_hs = int(last_hs_str)
        except ValueError:
            last_hs = 0

        age = now - last_hs if last_hs > 0 else None
        active = age is not None and age < 180  # active if handshake < 3 min ago

        if age is None:
            handshake_label = "Noch nie"
        elif age < 60:
            handshake_label = f"{age}s ago"
        elif age < 3600:
            handshake_label = f"{age // 60}m {age % 60}s ago"
        else:
            handshake_label = f"{age // 3600}h {(age % 3600) // 60}m ago"

        peers.append({
            "pubkey": pubkey,
            "endpoint": endpoint if endpoint != "(none)" else None,
            "allowed_ips": allowed_ips,
            "handshake": handshake_label,
            "active": active,
            "rx": rx,
            "tx": tx,
        })

    return {"up": True, "peers": peers, "interface": interface}


def _make_qr_base64(text):
    try:
        import qrcode, io, base64
        qr = qrcode.make(text)
        buf = io.BytesIO()
        qr.save(buf, format="PNG")
        return base64.b64encode(buf.getvalue()).decode()
    except Exception:
        return None


def _add_peer_to_vps(pubkey, ip):
    ssh_base = ["ssh", "-i", VPS_SSH_KEY,
                "-o", "StrictHostKeyChecking=no",
                "-o", "IdentitiesOnly=yes",
                "-o", "IdentityAgent=none",
                f"{VPS_USER}@{VPS_HOST}"]
    try:
        # Add peer to running interface
        subprocess.run(
            ssh_base + ["sudo", "wg", "set", WG_INTERFACE, "peer", pubkey,
                        "allowed-ips", f"{ip}/32"],
            check=True, timeout=20
        )
        # Save running config back to wg0.conf (atomic, no duplicates)
        subprocess.run(
            ssh_base + ["sudo", "wg-quick", "save", WG_INTERFACE],
            check=True, timeout=20
        )
        return None
    except Exception as e:
        return str(e)


@wireguard_bp.route('/api/wireguard/status')
@login_required
def wg_status():
    data = _parse_wg_show()
    data["installed"] = True
    return jsonify(data)


@wireguard_bp.route('/api/wireguard/new-client', methods=['POST'])
@admin_required
def new_client():
    data = request.json or {}
    name = re.sub(r'[^\w\-]', '', data.get('name', 'client'))[:32] or 'client'
    ip_last = str(data.get('ip_last', '')).strip()
    if not ip_last.isdigit() or not (2 <= int(ip_last) <= 254):
        return jsonify({"error": "Ungültige IP (2–254)"}), 400
    ip = BASE_IP + ip_last

    privkey, _, _ = _run("wg genkey")
    if not privkey:
        return jsonify({"error": "wg genkey fehlgeschlagen"}), 500
    pubkey, _, _ = _run(f"echo '{privkey}' | wg pubkey")
    if not pubkey:
        return jsonify({"error": "wg pubkey fehlgeschlagen"}), 500

    config = f"""[Interface]
PrivateKey = {privkey}
Address = {ip}/32
DNS = {DNS}

[Peer]
PublicKey = {VPS_PUBLIC_KEY}
Endpoint = {VPS_ENDPOINT}
AllowedIPs = 0.0.0.0/0
PersistentKeepalive = 25
"""
    vps_err = _add_peer_to_vps(pubkey, ip)
    result = {
        "name": name,
        "ip": ip,
        "config": config,
        "pubkey": pubkey,
        "qr": _make_qr_base64(config),
    }
    if vps_err:
        result["vps_warning"] = f"Peer nicht automatisch eingetragen: {vps_err}"
    else:
        result["vps_ok"] = True
    return jsonify(result)


@wireguard_bp.route('/api/wireguard/remove-peer', methods=['POST'])
@admin_required
def remove_peer():
    data = request.json or {}
    pubkey = data.get('pubkey', '').strip()
    if not re.match(r'^[A-Za-z0-9+/=]{40,50}$', pubkey):
        return jsonify({"error": "Ungültiger Public Key"}), 400

    ssh_base = ["ssh", "-i", VPS_SSH_KEY,
                "-o", "StrictHostKeyChecking=no",
                "-o", "IdentitiesOnly=yes",
                "-o", "IdentityAgent=none",
                f"{VPS_USER}@{VPS_HOST}"]
    try:
        subprocess.run(
            ssh_base + ["sudo", "wg", "set", WG_INTERFACE, "peer", pubkey, "remove"],
            check=True, timeout=20
        )
        subprocess.run(
            ssh_base + ["sudo", "wg-quick", "save", WG_INTERFACE],
            check=True, timeout=20
        )
        return jsonify({"message": "Peer entfernt und wg0.conf gespeichert."})
    except Exception as e:
        return jsonify({"error": str(e)}), 500
