import os
import time
import threading
import subprocess
from flask import Blueprint, jsonify, session
from functools import wraps

metrics_bp = Blueprint('metrics', __name__)

# Background CPU sampler — avoids blocking the request with a 1s sleep
_cpu_cache = {'pct': None, 'ts': 0}
_cpu_lock = threading.Lock()


def _read_cpu_stat():
    with open('/proc/stat') as f:
        line = f.readline()
    vals = list(map(int, line.split()[1:]))
    idle = vals[3] + vals[4]  # idle + iowait
    total = sum(vals)
    return total, idle


def _cpu_sampler():
    while True:
        try:
            t1, i1 = _read_cpu_stat()
            time.sleep(2)
            t2, i2 = _read_cpu_stat()
            dt, di = t2 - t1, i2 - i1
            pct = round(100.0 * (dt - di) / dt, 1) if dt else 0.0
            with _cpu_lock:
                _cpu_cache['pct'] = pct
                _cpu_cache['ts'] = time.time()
        except Exception:
            time.sleep(5)


threading.Thread(target=_cpu_sampler, daemon=True).start()


def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if 'user' not in session:
            return jsonify({"error": "Nicht eingeloggt"}), 401
        return f(*args, **kwargs)
    return decorated


def _mem():
    info = {}
    try:
        with open('/proc/meminfo') as f:
            raw = {l.split(':')[0]: int(l.split()[1]) for l in f if ':' in l}
        total  = raw.get('MemTotal', 0)
        avail  = raw.get('MemAvailable', 0)
        used   = total - avail
        swap_t = raw.get('SwapTotal', 0)
        swap_f = raw.get('SwapFree', 0)
        info['mem_total_mb']  = total // 1024
        info['mem_used_mb']   = used  // 1024
        info['mem_pct']       = round(used / total * 100, 1) if total else 0
        info['swap_total_mb'] = swap_t // 1024
        info['swap_used_mb']  = (swap_t - swap_f) // 1024
        info['swap_pct']      = round((swap_t - swap_f) / swap_t * 100, 1) if swap_t else 0
    except Exception:
        pass
    return info


def _disks():
    disks = []
    try:
        out = subprocess.getoutput("df -h --output=target,size,used,avail,pcent,fstype | tail -n +2")
        skip = ('tmpfs', 'devtmpfs', 'udev', 'overlay', 'squashfs')
        for line in out.splitlines():
            parts = line.split()
            if len(parts) < 6:
                continue
            mnt, size, used, avail, pct, fstype = parts[0], parts[1], parts[2], parts[3], parts[4], parts[5]
            if fstype in skip or any(mnt.startswith(p) for p in ('/sys', '/proc', '/dev', '/run')):
                continue
            disks.append({'mount': mnt, 'size': size, 'used': used, 'avail': avail,
                          'pct': int(pct.rstrip('%')), 'fstype': fstype})
    except Exception:
        pass
    return disks


def _load():
    try:
        vals = open('/proc/loadavg').read().split()
        return {'load1': float(vals[0]), 'load5': float(vals[1]), 'load15': float(vals[2])}
    except Exception:
        return {}


def _temp():
    try:
        with open('/sys/class/thermal/thermal_zone0/temp') as f:
            return round(int(f.read().strip()) / 1000, 1)
    except Exception:
        try:
            out = subprocess.getoutput('vcgencmd measure_temp')
            return float(out.replace("temp=", "").replace("'C", ""))
        except Exception:
            return None


def _net():
    interfaces = []
    try:
        with open('/proc/net/dev') as f:
            lines = f.readlines()[2:]
        for line in lines:
            parts = line.split()
            iface = parts[0].rstrip(':')
            if iface in ('lo',) or iface.startswith('br-') or iface.startswith('veth'):
                continue
            rx_bytes = int(parts[1])
            tx_bytes = int(parts[9])

            def _fmt(b):
                if b >= 1073741824: return f"{b/1073741824:.1f} GiB"
                if b >= 1048576:    return f"{b/1048576:.1f} MiB"
                if b >= 1024:       return f"{b/1024:.1f} KiB"
                return f"{b} B"

            interfaces.append({'iface': iface, 'rx': _fmt(rx_bytes), 'tx': _fmt(tx_bytes),
                                'rx_bytes': rx_bytes, 'tx_bytes': tx_bytes})
    except Exception:
        pass
    return interfaces


def _cpu_cores():
    try:
        out = subprocess.getoutput("nproc")
        return int(out.strip())
    except Exception:
        return None


@metrics_bp.route('/api/metrics/system')
@login_required
def system_metrics():
    with _cpu_lock:
        cpu_pct = _cpu_cache['pct']
    return jsonify({
        'cpu_pct':  cpu_pct,
        'cpu_cores': _cpu_cores(),
        'temp':     _temp(),
        'load':     _load(),
        'mem':      _mem(),
        'disks':    _disks(),
        'net':      _net(),
    })


@metrics_bp.route('/api/metrics/containers')
@login_required
def container_metrics():
    try:
        cores = _cpu_cores() or 1
        out = subprocess.getoutput(
            "docker stats --no-stream --format "
            "'{{.Name}}|{{.CPUPerc}}|{{.MemUsage}}|{{.MemPerc}}|{{.NetIO}}'"
        )
        containers = []
        for line in out.splitlines():
            parts = line.split('|')
            if len(parts) < 5:
                continue
            cpu_str = parts[1].strip().rstrip('%')
            mem_str = parts[3].strip().rstrip('%')
            try:
                cpu = round(float(cpu_str) / cores, 1)
                mem = float(mem_str)
            except ValueError:
                cpu = mem = 0.0
            containers.append({
                'name':    parts[0].strip(),
                'cpu_pct': cpu,
                'mem':     parts[2].strip(),
                'mem_pct': mem,
                'net_io':  parts[4].strip(),
            })
        containers.sort(key=lambda c: c['cpu_pct'], reverse=True)
        return jsonify({"containers": containers})
    except Exception as e:
        return jsonify({"error": str(e)}), 500
