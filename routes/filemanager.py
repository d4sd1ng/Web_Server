import os
import io
import shutil
import stat
from flask import Blueprint, jsonify, request, session, send_file
from functools import wraps

filemanager_bp = Blueprint('filemanager', __name__)

IO_TIMEOUT = 10

HOSTS = {
    "pi": {
        "label": "Pi",
        "protocol": "local",
        "root": "/host",
    },
    "nas": {
        "label": "NAS",
        "protocol": "smb",
        "host": os.environ.get("NAS_HOST", "192.168.178.100"),
        "user": os.environ.get("NAS_USER", "d4sd1ng"),
        "password": os.environ.get("NAS_PASSWORD", ""),
    },
}

_SMB_SKIP = {"IPC$", "print$", "netlogon", "sysvol"}


def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if 'user' not in session:
            return jsonify({"error": "Nicht eingeloggt"}), 401
        return f(*args, **kwargs)
    return decorated


def _fmt_size(n):
    for unit in ('B', 'KiB', 'MiB', 'GiB'):
        if n < 1024:
            return f"{n} {unit}" if unit == 'B' else f"{n:.1f} {unit}"
        n /= 1024
    return f"{n:.1f} TiB"


# ── Local (Pi) ────────────────────────────────────────────────────────────────

def _local_resolve(info, path):
    root = info["root"]
    real_root = os.path.realpath(root)
    if not path or path == '/':
        return real_root, None
    full = os.path.normpath(path)
    if not full.startswith(real_root):
        full = os.path.normpath(os.path.join(real_root, full.lstrip('/')))
    try:
        real_full = os.path.realpath(full)
    except Exception:
        return None, "Ungültiger Pfad"
    if not (real_full == real_root or real_full.startswith(real_root + os.sep)):
        return None, "Zugriff verweigert"
    return real_full, None


def _local_display(info, real_path):
    real_root = os.path.realpath(info["root"])
    return real_path[len(real_root):] or '/'


def _local_list(info, path):
    real, err = _local_resolve(info, path)
    if err:
        return None, err, None
    try:
        entries = []
        for name in os.listdir(real):
            try:
                full = os.path.join(real, name)
                st = os.lstat(full)
                is_dir = stat.S_ISDIR(st.st_mode)
                entries.append({
                    "name": name,
                    "is_dir": is_dir,
                    "is_link": stat.S_ISLNK(st.st_mode),
                    "size": None if is_dir else st.st_size,
                    "size_fmt": "" if is_dir else _fmt_size(st.st_size),
                    "mtime": int(st.st_mtime),
                })
            except Exception:
                pass
        entries.sort(key=lambda e: (0 if e['is_dir'] else 1, e['name'].lower()))
        return entries, None, _local_display(info, real)
    except PermissionError:
        return None, "Zugriff verweigert", None
    except FileNotFoundError:
        return None, "Pfad nicht gefunden", None
    except Exception as e:
        return None, str(e), None


def _local_delete(info, path, names):
    real, err = _local_resolve(info, path)
    if err:
        return [err]
    real_root = os.path.realpath(info["root"])
    errors = []
    for name in names:
        target = os.path.join(real, name)
        if not os.path.realpath(target).startswith(real_root):
            errors.append(f"{name}: verweigert")
            continue
        try:
            if os.path.isdir(target) and not os.path.islink(target):
                shutil.rmtree(target)
            else:
                os.remove(target)
        except Exception as e:
            errors.append(f"{name}: {e}")
    return errors


# ── SMB (NAS) — multi-share ───────────────────────────────────────────────────
# Virtual path format: /share-name/sub/path
# Root path "/" lists all available shares as folders.

def _smb_connect(info):
    from smb.SMBConnection import SMBConnection
    conn = SMBConnection(
        info["user"], info["password"],
        'dashboard', info["host"],
        use_ntlm_v2=True, is_direct_tcp=True,
    )
    if not conn.connect(info["host"], 445, timeout=IO_TIMEOUT):
        raise ConnectionError("SMB-Verbindung fehlgeschlagen")
    return conn


def _smb_parse(path):
    """Split /share/rest/of/path into (share, smb_path).
    Returns ('', '') for root."""
    parts = path.strip('/').split('/', 1)
    if not parts or parts[0] == '':
        return '', '/'
    share = parts[0]
    sub = '/' + parts[1] if len(parts) > 1 else '/'
    return share, sub


def _smb_list(info, path):
    try:
        conn = _smb_connect(info)
    except Exception as e:
        return None, str(e), None

    try:
        share, smb_path = _smb_parse(path)

        # Root: list shares
        if not share:
            shares = conn.listShares()
            entries = [
                {"name": s.name, "is_dir": True, "is_link": False,
                 "size": None, "size_fmt": "", "mtime": 0}
                for s in shares
                if s.type == 0 and s.name not in _SMB_SKIP
            ]
            entries.sort(key=lambda e: e['name'].lower())
            return entries, None, '/'

        # Inside a share
        items = conn.listPath(share, smb_path)
        entries = []
        for f in items:
            if f.filename in ('.', '..'):
                continue
            is_dir = f.isDirectory
            entries.append({
                "name": f.filename,
                "is_dir": is_dir,
                "is_link": False,
                "size": None if is_dir else f.file_size,
                "size_fmt": "" if is_dir else _fmt_size(f.file_size),
                "mtime": int(f.last_write_time),
            })
        entries.sort(key=lambda e: (0 if e['is_dir'] else 1, e['name'].lower()))
        display = '/' + share + ('' if smb_path == '/' else smb_path)
        return entries, None, display

    except Exception as e:
        return None, str(e), None
    finally:
        conn.close()


def _smb_rmtree(conn, share, path):
    for f in conn.listPath(share, path):
        if f.filename in ('.', '..'):
            continue
        child = path.rstrip('/') + '/' + f.filename
        if f.isDirectory:
            _smb_rmtree(conn, share, child)
        else:
            conn.deleteFiles(share, child)
    conn.deleteDirectory(share, path)


def _smb_delete(info, path, names):
    share, smb_path = _smb_parse(path)
    if not share:
        return ["Löschen im Root nicht möglich"]
    try:
        conn = _smb_connect(info)
    except Exception as e:
        return [str(e)]
    errors = []
    try:
        for name in names:
            target = smb_path.rstrip('/') + '/' + name
            try:
                attrs = conn.getAttributes(share, target)
                if attrs.isDirectory:
                    _smb_rmtree(conn, share, target)
                else:
                    conn.deleteFiles(share, target)
            except Exception as e:
                errors.append(f"{name}: {e}")
    finally:
        conn.close()
    return errors


def _smb_read(info, path, name):
    share, smb_path = _smb_parse(path)
    if not share:
        return None, "Kein Share angegeben"
    try:
        conn = _smb_connect(info)
    except Exception as e:
        return None, str(e)
    try:
        target = smb_path.rstrip('/') + '/' + name
        buf = io.BytesIO()
        conn.retrieveFile(share, target, buf)
        buf.seek(0)
        return buf, None
    except Exception as e:
        return None, str(e)
    finally:
        conn.close()


def _smb_write(info, path, name, stream):
    share, smb_path = _smb_parse(path)
    if not share:
        return "Kein Share angegeben"
    try:
        conn = _smb_connect(info)
    except Exception as e:
        return str(e)
    try:
        target = smb_path.rstrip('/') + '/' + name
        conn.storeFile(share, target, stream)
        return None
    except Exception as e:
        return str(e)
    finally:
        conn.close()


# ── Routes ────────────────────────────────────────────────────────────────────

@filemanager_bp.route('/api/fm/list')
@login_required
def fm_list():
    host = request.args.get('host', 'pi')
    path = request.args.get('path', '/')
    info = HOSTS.get(host)
    if not info:
        return jsonify({"error": "Unbekannter Host"}), 400

    if info["protocol"] == "local":
        entries, err, display = _local_list(info, path)
    else:
        entries, err, display = _smb_list(info, path)

    if err:
        code = 403 if "verweigert" in err else 404 if "nicht gefunden" in err.lower() else 503 if "Verbindung" in err else 500
        return jsonify({"error": err}), code
    return jsonify({"path": display, "host": host, "entries": entries})


@filemanager_bp.route('/api/fm/mkdir', methods=['POST'])
@login_required
def fm_mkdir():
    data = request.json or {}
    host = data.get('host', '')
    info = HOSTS.get(host)
    if not info:
        return jsonify({"error": "Unbekannter Host"}), 400
    name = data.get('name', '').strip()
    if not name or '/' in name or name in ('.', '..'):
        return jsonify({"error": "Ungültiger Name"}), 400
    path = data.get('path', '/')
    try:
        if info["protocol"] == "local":
            real, err = _local_resolve(info, path)
            if err:
                return jsonify({"error": err}), 400
            os.makedirs(os.path.join(real, name), exist_ok=False)
        else:
            share, smb_path = _smb_parse(path)
            if not share:
                return jsonify({"error": "Share wählen"}), 400
            conn = _smb_connect(info)
            try:
                conn.createDirectory(share, smb_path.rstrip('/') + '/' + name)
            finally:
                conn.close()
    except FileExistsError:
        return jsonify({"error": "Bereits vorhanden"}), 409
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    return jsonify({"message": f"'{name}' erstellt"})


@filemanager_bp.route('/api/fm/delete', methods=['POST'])
@login_required
def fm_delete():
    data = request.json or {}
    host = data.get('host', '')
    info = HOSTS.get(host)
    if not info:
        return jsonify({"error": "Unbekannter Host"}), 400
    names = data.get('names', [])
    for name in names:
        if '/' in name or name in ('.', '..'):
            return jsonify({"error": f"{name}: ungültig"}), 400
    path = data.get('path', '/')
    if info["protocol"] == "local":
        errors = _local_delete(info, path, names)
    else:
        errors = _smb_delete(info, path, names)
    if errors:
        return jsonify({"error": '; '.join(errors)}), 500
    return jsonify({"message": f"{len(names)} Element(e) gelöscht"})


@filemanager_bp.route('/api/fm/rename', methods=['POST'])
@login_required
def fm_rename():
    data = request.json or {}
    host = data.get('host', '')
    info = HOSTS.get(host)
    if not info:
        return jsonify({"error": "Unbekannter Host"}), 400
    old = data.get('old_name', '').strip()
    new = data.get('new_name', '').strip()
    if not old or not new or '/' in old or '/' in new or old in ('.', '..') or new in ('.', '..'):
        return jsonify({"error": "Ungültiger Name"}), 400
    path = data.get('path', '/')
    try:
        if info["protocol"] == "local":
            real, err = _local_resolve(info, path)
            if err:
                return jsonify({"error": err}), 400
            os.rename(os.path.join(real, old), os.path.join(real, new))
        else:
            share, smb_path = _smb_parse(path)
            if not share:
                return jsonify({"error": "Share wählen"}), 400
            conn = _smb_connect(info)
            try:
                base = smb_path.rstrip('/')
                conn.rename(share, base + '/' + old, base + '/' + new)
            finally:
                conn.close()
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    return jsonify({"message": f"{old} → {new}"})


@filemanager_bp.route('/api/fm/transfer', methods=['POST'])
@login_required
def fm_transfer():
    data = request.json or {}
    op = data.get('op')
    if op not in ('copy', 'move'):
        return jsonify({"error": "Ungültige Operation"}), 400
    src_host = data.get('src_host', '')
    dst_host = data.get('dst_host', '')
    src_info = HOSTS.get(src_host)
    dst_info = HOSTS.get(dst_host)
    if not src_info or not dst_info:
        return jsonify({"error": "Unbekannter Host"}), 400
    src_path = data.get('src_path', '/')
    dst_path = data.get('dst_path', '/')
    names = data.get('names', [])
    errors = []

    for name in names:
        if '/' in name or name in ('.', '..'):
            errors.append(f"{name}: ungültig")
            continue
        try:
            if src_info["protocol"] == "local" and dst_info["protocol"] == "local":
                src_real, err = _local_resolve(src_info, src_path)
                dst_real, err2 = _local_resolve(dst_info, dst_path)
                if err or err2:
                    errors.append(f"{name}: {err or err2}")
                    continue
                src = os.path.join(src_real, name)
                dst = os.path.join(dst_real, name)
                if op == 'copy':
                    shutil.copytree(src, dst) if os.path.isdir(src) and not os.path.islink(src) else shutil.copy2(src, dst)
                else:
                    shutil.move(src, dst)

            elif src_info["protocol"] == "local":
                src_real, err = _local_resolve(src_info, src_path)
                if err:
                    errors.append(f"{name}: {err}")
                    continue
                src_file = os.path.join(src_real, name)
                if not os.path.isfile(src_file):
                    errors.append(f"{name}: Ordner cross-host nicht unterstützt")
                    continue
                with open(src_file, 'rb') as f:
                    write_err = _smb_write(dst_info, dst_path, name, f)
                if write_err:
                    errors.append(f"{name}: {write_err}")
                    continue
                if op == 'move':
                    os.remove(src_file)

            elif dst_info["protocol"] == "local":
                buf, err = _smb_read(src_info, src_path, name)
                if err:
                    errors.append(f"{name}: {err}")
                    continue
                dst_real, err = _local_resolve(dst_info, dst_path)
                if err:
                    errors.append(f"{name}: {err}")
                    continue
                with open(os.path.join(dst_real, name), 'wb') as f:
                    shutil.copyfileobj(buf, f)
                if op == 'move':
                    errors.extend(_smb_delete(src_info, src_path, [name]))

            else:
                buf, err = _smb_read(src_info, src_path, name)
                if err:
                    errors.append(f"{name}: {err}")
                    continue
                write_err = _smb_write(dst_info, dst_path, name, buf)
                if write_err:
                    errors.append(f"{name}: {write_err}")
                    continue
                if op == 'move':
                    errors.extend(_smb_delete(src_info, src_path, [name]))

        except Exception as e:
            errors.append(f"{name}: {e}")

    if errors:
        return jsonify({"error": '; '.join(errors)}), 500
    verb = "Kopiert" if op == 'copy' else "Verschoben"
    return jsonify({"message": f"{len(names)} Element(e) {verb}"})


@filemanager_bp.route('/api/fm/download')
@login_required
def fm_download():
    host = request.args.get('host', '')
    path = request.args.get('path', '/')
    name = request.args.get('name', '')
    if not name or '/' in name or name in ('.', '..'):
        return jsonify({"error": "Ungültig"}), 400
    info = HOSTS.get(host)
    if not info:
        return jsonify({"error": "Unbekannter Host"}), 400
    if info["protocol"] == "local":
        real, err = _local_resolve(info, path)
        if err:
            return jsonify({"error": err}), 400
        filepath = os.path.join(real, name)
        if not os.path.isfile(filepath):
            return jsonify({"error": "Keine Datei"}), 404
        return send_file(filepath, as_attachment=True, download_name=name)
    else:
        buf, err = _smb_read(info, path, name)
        if err:
            return jsonify({"error": err}), 404
        return send_file(buf, as_attachment=True, download_name=name)
