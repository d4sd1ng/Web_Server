from flask import Blueprint, jsonify
import os
import json
import time
import requests
import subprocess

api_bp = Blueprint('api', __name__)

NEWS_CACHE_FILE = "/tmp/news_cache.json"
CACHE_TTL = 7200  # 2 Stunden → max 24 Calls/Tag pro Topic

NEWSDATA_KEY = os.getenv("NEWSDATA_API_KEY")
NEWSDATA_URL = os.getenv("NEWSDATA_BASE_URL", "https://newsdata.io/api/1")


def get_cpu_temp():
    try:
        with open("/sys/class/thermal/thermal_zone0/temp") as f:
            return round(int(f.read().strip()) / 1000, 1)
    except Exception:
        try:
            out = subprocess.getoutput("vcgencmd measure_temp")
            return float(out.replace("temp=", "").replace("'C", ""))
        except Exception:
            return None


def load_cache():
    try:
        if os.path.exists(NEWS_CACHE_FILE):
            with open(NEWS_CACHE_FILE) as f:
                return json.load(f)
    except Exception:
        pass
    return {}


def save_cache(cache):
    try:
        with open(NEWS_CACHE_FILE, "w") as f:
            json.dump(cache, f)
    except Exception:
        pass


def fetch_news(topic):
    cache = load_cache()
    now = time.time()
    entry = cache.get(topic)
    if entry and now - entry["ts"] < CACHE_TTL:
        return entry["articles"], None
    try:
        params = {
            "apikey": NEWSDATA_KEY,
            "language": "de,en",
            "q": topic,
            "size": 5,
        }
        res = requests.get(f"{NEWSDATA_URL}/news", params=params, timeout=10)
        data = res.json()
        if data.get("status") != "success":
            return [], data.get("message", "API-Fehler")
        articles = [
            {
                "title": a.get("title", ""),
                "link": a.get("link", ""),
                "source": a.get("source_id", ""),
                "pubDate": a.get("pubDate", ""),
            }
            for a in data.get("results", [])
        ]
        cache[topic] = {"ts": now, "articles": articles}
        save_cache(cache)
        return articles, None
    except Exception as e:
        return [], str(e)


def get_alerts():
    alerts = []
    # Docker Container
    try:
        out = subprocess.getoutput(
            "docker ps -a --format '{{.Names}} {{.Status}}'"
        )
        for line in out.splitlines():
            parts = line.split(" ", 1)
            if len(parts) == 2 and "Up" not in parts[1]:
                alerts.append({"level": "warning", "msg": f"Container '{parts[0]}' nicht aktiv: {parts[1]}"})
    except Exception:
        pass

    # Disk
    try:
        import shutil
        total, used, free = shutil.disk_usage("/")
        pct = used / total * 100
        if pct > 85:
            alerts.append({"level": "danger", "msg": f"Festplatte {pct:.0f}% belegt"})
    except Exception:
        pass

    # NAS Mount
    if not os.path.ismount("/mnt/nas-backup"):
        alerts.append({"level": "warning", "msg": "NAS nicht gemountet (/mnt/nas-backup)"})

    return alerts


@api_bp.route('/api/temperature')
def temperature():
    temp = get_cpu_temp()
    return jsonify({"temp": temp})


@api_bp.route('/api/news/<topic>')
def news(topic):
    if topic not in ("crypto", "ai"):
        return jsonify({"error": "Ungültiges Topic"}), 400
    query = "cryptocurrency bitcoin" if topic == "crypto" else "artificial intelligence"
    articles, error = fetch_news(query)
    if error:
        return jsonify({"error": error}), 500
    return jsonify({"articles": articles})


@api_bp.route('/api/alerts')
def alerts():
    return jsonify({"alerts": get_alerts()})


@api_bp.route('/api/settings')
def public_settings():
    try:
        from utils.db import get_db_connection
        conn = get_db_connection()
        with conn.cursor() as cur:
            cur.execute("SELECT key, value FROM settings")
            rows = cur.fetchall()
        conn.close()
        return jsonify({r["key"]: r["value"] for r in rows})
    except Exception:
        return jsonify({
            "adguard_url": "http://192.168.178.10:8081",
            "grafana_url": "http://192.168.178.10:3000",
            "dashboard_title": "Homeserver"
        })


@api_bp.route('/api/sysinfo')
def sysinfo():
    import shutil, socket, platform
    info = {}
    try:
        info["hostname"] = socket.gethostname()
    except Exception:
        info["hostname"] = "—"
    try:
        info["ip"] = subprocess.getoutput("hostname -I").split()[0]
    except Exception:
        info["ip"] = "—"
    try:
        uptime_sec = float(open("/proc/uptime").read().split()[0])
        days = int(uptime_sec // 86400)
        hours = int((uptime_sec % 86400) // 3600)
        minutes = int((uptime_sec % 3600) // 60)
        info["uptime"] = f"{days}d {hours}h {minutes}m"
    except Exception:
        info["uptime"] = "—"
    try:
        total, used, free = shutil.disk_usage("/")
        info["disk_total"] = round(total / 1e9, 1)
        info["disk_used"] = round(used / 1e9, 1)
        info["disk_pct"] = round(used / total * 100, 1)
    except Exception:
        info["disk_total"] = info["disk_used"] = info["disk_pct"] = None
    try:
        info["cpu_temp"] = get_cpu_temp()
    except Exception:
        info["cpu_temp"] = None
    try:
        mem = open("/proc/meminfo").read()
        mem_total = int([l for l in mem.splitlines() if "MemTotal" in l][0].split()[1]) // 1024
        mem_free = int([l for l in mem.splitlines() if "MemAvailable" in l][0].split()[1]) // 1024
        info["mem_total"] = mem_total
        info["mem_used"] = mem_total - mem_free
    except Exception:
        info["mem_total"] = info["mem_used"] = None
    try:
        info["os"] = platform.platform()
    except Exception:
        info["os"] = "—"
    return jsonify(info)
