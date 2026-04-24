import os
import shutil
import stat
from flask import Blueprint, jsonify, request, session, send_file
from functools import wraps
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FutTimeout

filemanager_bp = Blueprint('filemanager', __name__)

HOSTS = {
    "pi":  {"label": "Pi",  "root": "/host"},
    "nas": {"label": "NAS", "root": "/mnt/nas-backup"},
}
IO_TIMEOUT = 5


def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if 'user' not in session:
            return jsonify({"error": "Nicht eingeloggt"}), 401
        return f(*args, **kwargs)
    return decorated


def _resolve(host, path):
    info = HOSTS.get(host)
    if not info:
        return None, "Unbekannter Host"
    root = info["root"]
    if not path:
        path = root
    full = os.path.normpath(path)
    real_root = os.path.realpath(root)
    try:
        real_full = os.path.realpath(full)
    except Exception:
        return None, "Ungültiger Pfad"
    if not (real_full == real_root or real_full.startswith(real_root + os.sep)):
        return None, "Zugriff verweigert"
    return real_full, None


def _io(fn, *args):
    with ThreadPoolExecutor(max_workers=1) as ex:
        try:
            return ex.submit(fn, *args).result(timeout=IO_TIMEOUT)
        except FutTimeout:
            raise TimeoutError("IO Timeout")


def _fmt_size(n):
    for unit in ('B', 'KiB', 'MiB', 'GiB'):
        if n < 1024:
            return f"{n} {unit}" if unit == 'B' else f"{n:.1f} {unit}"
        n /= 1024
    return f"{n:.1f} TiB"


@filemanager_bp.route('/api/fm/list')
@login_required
def fm_list():
    host = request.args.get('host', 'pi')
    path = request.args.get('path', '')
    real, err = _resolve(host, path)
    if err:
        return jsonify({"error": err}), 400

    def _do():
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
        return entries

    try:
        entries = _io(_do)
        return jsonify({"path": real, "host": host, "entries": entries})
    except TimeoutError:
        return jsonify({"error": "Timeout — NAS erreichbar?"}), 504
    except PermissionError:
        return jsonify({"error": "Zugriff verweigert"}), 403
    except FileNotFoundError:
        return jsonify({"error": "Pfad nicht gefunden"}), 404
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@filemanager_bp.route('/api/fm/mkdir', methods=['POST'])
@login_required
def fm_mkdir():
    data = request.json or {}
    real, err = _resolve(data.get('host', ''), data.get('path', ''))
    if err:
        return jsonify({"error": err}), 400
    name = data.get('name', '').strip()
    if not name or '/' in name or name in ('.', '..'):
        return jsonify({"error": "Ungültiger Name"}), 400
    try:
        os.makedirs(os.path.join(real, name), exist_ok=False)
        return jsonify({"message": f"'{name}' erstellt"})
    except FileExistsError:
        return jsonify({"error": "Bereits vorhanden"}), 409
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@filemanager_bp.route('/api/fm/delete', methods=['POST'])
@login_required
def fm_delete():
    data = request.json or {}
    host = data.get('host', '')
    real, err = _resolve(host, data.get('path', ''))
    if err:
        return jsonify({"error": err}), 400
    names = data.get('names', [])
    real_root = os.path.realpath(HOSTS[host]['root'])
    errors = []
    for name in names:
        if '/' in name or name in ('.', '..'):
            errors.append(f"{name}: ungültig")
            continue
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
    if errors:
        return jsonify({"error": '; '.join(errors)}), 500
    return jsonify({"message": f"{len(names)} Element(e) gelöscht"})


@filemanager_bp.route('/api/fm/rename', methods=['POST'])
@login_required
def fm_rename():
    data = request.json or {}
    real, err = _resolve(data.get('host', ''), data.get('path', ''))
    if err:
        return jsonify({"error": err}), 400
    old = data.get('old_name', '').strip()
    new = data.get('new_name', '').strip()
    if not old or not new or '/' in old or '/' in new or old in ('.', '..') or new in ('.', '..'):
        return jsonify({"error": "Ungültiger Name"}), 400
    try:
        os.rename(os.path.join(real, old), os.path.join(real, new))
        return jsonify({"message": f"{old} → {new}"})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@filemanager_bp.route('/api/fm/transfer', methods=['POST'])
@login_required
def fm_transfer():
    data = request.json or {}
    op = data.get('op')
    if op not in ('copy', 'move'):
        return jsonify({"error": "Ungültige Operation"}), 400
    src_real, err = _resolve(data.get('src_host', ''), data.get('src_path', ''))
    if err:
        return jsonify({"error": f"Quelle: {err}"}), 400
    dst_real, err = _resolve(data.get('dst_host', ''), data.get('dst_path', ''))
    if err:
        return jsonify({"error": f"Ziel: {err}"}), 400
    names = data.get('names', [])
    errors = []
    for name in names:
        if '/' in name or name in ('.', '..'):
            errors.append(f"{name}: ungültig")
            continue
        src = os.path.join(src_real, name)
        dst = os.path.join(dst_real, name)
        try:
            if op == 'copy':
                if os.path.isdir(src) and not os.path.islink(src):
                    shutil.copytree(src, dst)
                else:
                    shutil.copy2(src, dst)
            else:
                shutil.move(src, dst)
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
    path = request.args.get('path', '')
    name = request.args.get('name', '')
    if not name or '/' in name or name in ('.', '..'):
        return jsonify({"error": "Ungültig"}), 400
    real, err = _resolve(host, path)
    if err:
        return jsonify({"error": err}), 400
    filepath = os.path.join(real, name)
    if not os.path.isfile(filepath):
        return jsonify({"error": "Keine Datei"}), 404
    return send_file(filepath, as_attachment=True, download_name=name)
