from flask import Blueprint, render_template, request, jsonify
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FutTimeout
import subprocess
import socket
import json
import os

backup_bp = Blueprint('backup', __name__)

BACKUP_DIR = "/opt/server/backups"
NAS_MOUNT = "/mnt/nas-backup"
NAS_MAC = "00:08:9b:bd:2b:e6"
NAS_IP  = "192.168.178.100"
IO_TIMEOUT = 2
LOG_CACHE = "/tmp/backup_log_cache.json"

JOBS = [
    {"name": "pi-config-core",         "category": "pi",      "script": f"{BACKUP_DIR}/pi-config-core.sh"},
    {"name": "pi-services-data",        "category": "pi",      "script": f"{BACKUP_DIR}/pi-services-data.sh"},
    {"name": "pi-monitoring-optional",  "category": "pi",      "script": f"{BACKUP_DIR}/pi-monitoring-optional.sh"},
    {"name": "vps-config",              "category": "vps",     "script": f"{BACKUP_DIR}/vps-config.sh"},
    {"name": "vps-docker-data",         "category": "vps",     "script": f"{BACKUP_DIR}/vps-docker-data.sh"},
    {"name": "win-selective-data",      "category": "windows", "script": None},
]

JOBS_BY_NAME = {j["name"]: j for j in JOBS}


def _io(fn, *args):
    with ThreadPoolExecutor(max_workers=1) as ex:
        return ex.submit(fn, *args).result(timeout=IO_TIMEOUT)


def _nas_reachable():
    for port in (445, 139, 80, 8080):
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.settimeout(1)
            result = s.connect_ex((NAS_IP, port))
            s.close()
            if result == 0:
                return True
        except Exception:
            pass
    return False


def mount_ok():
    if not _nas_reachable():
        return False
    # NAS is up — ensure mount is fresh
    subprocess.run(["sudo", "/bin/umount", "-l", NAS_MOUNT],
                   capture_output=True, timeout=3)
    remount_nas()
    try:
        _io(os.listdir, NAS_MOUNT)
        return True
    except Exception:
        return False


def remount_nas():
    try:
        subprocess.run(["sudo", "/bin/mount", NAS_MOUNT],
                       timeout=5, capture_output=True)
    except Exception:
        pass


def load_log_cache():
    try:
        with open(LOG_CACHE) as f:
            return json.load(f)
    except Exception:
        return {}


def save_log_cache(cache):
    try:
        with open(LOG_CACHE, "w") as f:
            json.dump(cache, f)
    except Exception:
        pass


def get_last_log(job_name, category, nas_ok=True):
    cache = load_log_cache()

    if not nas_ok:
        cached = cache.get(job_name)
        return (cached + " ⟳") if cached else "—"

    subdir = {"pi": "pi", "vps": "vps", "windows": "windows"}.get(category, "pi")
    log_path = os.path.join(NAS_MOUNT, subdir, "backup.log")

    def _read():
        if not os.path.exists(log_path):
            return None
        with open(log_path) as f:
            lines = [l for l in f if job_name in l]
        return lines[-1].strip() if lines else None

    try:
        result = _io(_read)
        if result:
            cache[job_name] = result
            save_log_cache(cache)
            return result
        return cache.get(job_name, "Noch kein Eintrag")
    except Exception:
        cached = cache.get(job_name)
        return (cached + " ⟳") if cached else "—"


def build_job_list(nas_ok):
    def _entry(j):
        return {
            "name": j["name"],
            "category": j["category"],
            "exists": bool(j["script"] and os.path.exists(j["script"])),
            "configured": j["script"] is not None,
            "last_log": get_last_log(j["name"], j["category"], nas_ok),
        }
    with ThreadPoolExecutor(max_workers=len(JOBS)) as ex:
        return list(ex.map(_entry, JOBS))


def send_wol(mac: str):
    mac_bytes = bytes.fromhex(mac.replace(":", "").replace("-", ""))
    magic = b'\xff' * 6 + mac_bytes * 16
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
        s.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        s.sendto(magic, ('<broadcast>', 9))


@backup_bp.route('/api/backup/wake-nas', methods=['POST'])
def wake_nas():
    try:
        send_wol(NAS_MAC)
        # Also attempt remount in background
        import threading
        threading.Thread(target=lambda: (
            __import__('time').sleep(60), remount_nas()
        ), daemon=True).start()
        return jsonify({"message": "Magic Packet gesendet — NAS sollte in ~60s erreichbar sein"})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@backup_bp.route('/api/backup/remount', methods=['POST'])
def remount():
    remount_nas()
    ok = mount_ok()
    if ok:
        return jsonify({"message": "NAS erfolgreich gemountet"})
    return jsonify({"error": "NAS nicht erreichbar"}), 503


@backup_bp.route('/api/backup/status', methods=['GET'])
def backup_status():
    nas = mount_ok()
    return jsonify({"mount_ok": nas, "jobs": build_job_list(nas)})


@backup_bp.route('/backup', methods=['GET'])
def backup_page():
    nas = mount_ok()
    return render_template('backup.html', jobs=build_job_list(nas), mount_ok=nas)


@backup_bp.route('/backup/run/<job_name>', methods=['POST'])
def run_backup(job_name):
    if job_name not in JOBS_BY_NAME:
        return jsonify({"error": "Unbekannter Job"}), 400
    job = JOBS_BY_NAME[job_name]
    if not job["script"]:
        return jsonify({"error": "Job noch nicht konfiguriert"}), 400
    if not mount_ok():
        return jsonify({"error": "NAS nicht gemountet"}), 503
    try:
        result = subprocess.run(
            ["sudo", "bash", job["script"]],
            capture_output=True, text=True, timeout=300
        )
        return jsonify({
            "stdout": result.stdout,
            "stderr": result.stderr,
            "returncode": result.returncode
        })
    except subprocess.TimeoutExpired:
        return jsonify({"error": "Timeout nach 5 Minuten"}), 504
    except Exception as e:
        return jsonify({"error": str(e)}), 500
