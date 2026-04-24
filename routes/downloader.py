import os
import threading
import uuid
from flask import Blueprint, jsonify, request, session
from functools import wraps

downloader_bp = Blueprint('downloader', __name__)

DOWNLOAD_DIRS = {
    "pi":  "/home/d4sd1ng/downloads",
    "nas": "/mnt/nas-backup/downloads",
}

JOBS = {}
JOBS_LOCK = threading.Lock()

HISTORY = []          # last 10 completed downloads
HISTORY_FILE = '/tmp/dl_history.json'
HISTORY_LOCK = threading.Lock()


def _load_history():
    global HISTORY
    try:
        import json
        with open(HISTORY_FILE) as f:
            HISTORY = json.load(f)
    except Exception:
        HISTORY = []


def _save_history():
    try:
        import json
        with open(HISTORY_FILE, 'w') as f:
            json.dump(HISTORY[-10:], f)
    except Exception:
        pass


def _add_history(job, moved_files, subdir):
    import time
    with HISTORY_LOCK:
        HISTORY.append({
            'title':    job.get('title', '?'),
            'url':      job.get('url', ''),
            'format':   job.get('format', ''),
            'dest':     job.get('dest', ''),
            'subdir':   subdir,
            'files':    [os.path.basename(f) for f in moved_files],
            'paths':    moved_files,
            'ts':       int(time.time()),
        })
        if len(HISTORY) > 10:
            del HISTORY[:-10]
        _save_history()


_load_history()


def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if 'user' not in session:
            return jsonify({"error": "Nicht eingeloggt"}), 401
        return f(*args, **kwargs)
    return decorated


def _base_opts():
    return {
        'quiet':           True,
        'no_warnings':     True,
        'age_limit':       99,
        'ignoreerrors':    False,
        'nocheckcertificate': True,
        'http_headers': {
            'User-Agent': (
                'Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
                'AppleWebKit/537.36 (KHTML, like Gecko) '
                'Chrome/124.0.0.0 Safari/537.36'
            )
        },
    }


def _sanitize(name):
    import re
    name = re.sub(r'[<>:"/\\|?*\x00-\x1f]', '_', name)
    name = re.sub(r'_+', '_', name).strip('_. ')
    return name[:120] or 'download'


def _move_to_subdir(dest_dir, fmt, downloaded_files):
    """Move downloaded files into video/ or music/ subfolder with clean names."""
    subdir = 'music' if fmt == 'audio' else 'video'
    target_dir = os.path.join(dest_dir, subdir)
    os.makedirs(target_dir, exist_ok=True)
    moved = []
    for src in downloaded_files:
        if not os.path.exists(src):
            continue
        base = os.path.basename(src)
        stem, ext = os.path.splitext(base)
        clean = _sanitize(stem) + ext.lower()
        dst = os.path.join(target_dir, clean)
        # avoid overwrite
        if os.path.exists(dst):
            i = 1
            while os.path.exists(dst):
                dst = os.path.join(target_dir, f"{_sanitize(stem)}_{i}{ext.lower()}")
                i += 1
        try:
            os.rename(src, dst)
            moved.append(dst)
        except Exception:
            moved.append(src)
    return moved, subdir


def _run_download(job_id, url, dest_dir, fmt):
    try:
        from yt_dlp import YoutubeDL
    except ImportError:
        with JOBS_LOCK:
            JOBS[job_id]['status'] = 'error'
            JOBS[job_id]['error'] = 'yt-dlp nicht installiert'
        return

    job = JOBS[job_id]
    tmp_dir = os.path.join(dest_dir, '.tmp_dl')
    os.makedirs(tmp_dir, exist_ok=True)

    downloaded_files = []

    def progress_hook(d):
        if d['status'] == 'downloading':
            job['status']   = 'downloading'
            job['progress'] = d.get('_percent_str', '?').strip()
            job['speed']    = d.get('_speed_str', '').strip()
            job['eta']      = d.get('_eta_str', '').strip()
            job['size']     = d.get('_total_bytes_str') or d.get('_total_bytes_estimate_str', '')
            if job['size']:
                job['size'] = job['size'].strip()
        elif d['status'] == 'finished':
            job['status']   = 'processing'
            job['progress'] = '100%'
            fname = d.get('filename', '')
            if fname and os.path.exists(fname):
                downloaded_files.append(fname)

    opts = _base_opts()
    opts['outtmpl'] = os.path.join(tmp_dir, '%(title)s.%(ext)s')
    opts['progress_hooks'] = [progress_hook]

    if fmt == 'audio':
        opts['format'] = 'bestaudio/best'
        opts['postprocessors'] = [{
            'key': 'FFmpegExtractAudio',
            'preferredcodec': 'mp3',
            'preferredquality': '192',
        }]
    elif fmt == '720':
        opts['format'] = 'bestvideo[height<=720][ext=mp4]+bestaudio[ext=m4a]/bestvideo[height<=720]+bestaudio/best[height<=720]/best'
    elif fmt == '1080':
        opts['format'] = 'bestvideo[height<=1080][ext=mp4]+bestaudio[ext=m4a]/bestvideo[height<=1080]+bestaudio/best'
    else:
        opts['format'] = 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/bestvideo+bestaudio/best'

    try:
        with YoutubeDL(opts) as ydl:
            info = ydl.extract_info(url, download=True)
            job['title'] = (info.get('title') or url)[:80]

        # collect any remaining files in tmp_dir not yet captured by hook
        for f in os.listdir(tmp_dir):
            fp = os.path.join(tmp_dir, f)
            if fp not in downloaded_files and os.path.isfile(fp):
                downloaded_files.append(fp)

        moved, subdir = _move_to_subdir(dest_dir, fmt, downloaded_files)
        job['status']   = 'done'
        job['progress'] = '100%'
        job['filename'] = ', '.join(os.path.basename(f) for f in moved)
        job['subdir']   = subdir
        _add_history(job, moved, subdir)

        # clean up tmp dir if empty
        try:
            os.rmdir(tmp_dir)
        except Exception:
            pass

    except Exception as e:
        job['status'] = 'error'
        job['error']  = str(e)[:300]


@downloader_bp.route('/api/dl/info', methods=['POST'])
@login_required
def dl_info():
    data = request.json or {}
    url = data.get('url', '').strip()
    if not url:
        return jsonify({"error": "Keine URL"}), 400
    try:
        from yt_dlp import YoutubeDL
    except ImportError:
        return jsonify({"error": "yt-dlp nicht installiert"}), 500

    opts = _base_opts()
    opts['skip_download'] = True
    try:
        with YoutubeDL(opts) as ydl:
            info = ydl.extract_info(url, download=False)
            return jsonify({
                "title":     info.get('title', '?'),
                "duration":  info.get('duration'),
                "uploader":  info.get('uploader', ''),
                "thumbnail": info.get('thumbnail', ''),
                "extractor": info.get('extractor_key', ''),
            })
    except Exception as e:
        return jsonify({"error": str(e)[:200]}), 500


@downloader_bp.route('/api/dl/add', methods=['POST'])
@login_required
def dl_add():
    data = request.json or {}
    urls = [u.strip() for u in data.get('urls', '').splitlines() if u.strip()]
    if not urls:
        return jsonify({"error": "Keine URLs"}), 400
    dest_key = data.get('dest', 'pi')
    if dest_key not in DOWNLOAD_DIRS:
        return jsonify({"error": "Ungültiges Ziel"}), 400
    fmt = data.get('format', 'best')
    if fmt not in ('best', '720', '1080', 'audio'):
        fmt = 'best'

    dest_dir = DOWNLOAD_DIRS[dest_key]
    added = []
    for url in urls:
        job_id = str(uuid.uuid4())[:8]
        job = {
            'id':       job_id,
            'url':      url,
            'title':    url,
            'dest':     dest_dir,
            'format':   fmt,
            'status':   'queued',
            'progress': '0%',
            'speed':    '',
            'eta':      '',
            'size':     '',
            'filename': '',
            'subdir':   '',
            'error':    '',
        }
        with JOBS_LOCK:
            JOBS[job_id] = job
        threading.Thread(
            target=_run_download,
            args=(job_id, url, dest_dir, fmt),
            daemon=True
        ).start()
        added.append(job_id)

    return jsonify({"added": added, "message": f"{len(added)} Download(s) gestartet"})


@downloader_bp.route('/api/dl/status')
@login_required
def dl_status():
    with JOBS_LOCK:
        jobs = list(JOBS.values())
    jobs.sort(key=lambda j: j['id'], reverse=True)
    return jsonify({"jobs": jobs})


@downloader_bp.route('/api/dl/clear', methods=['POST'])
@login_required
def dl_clear():
    with JOBS_LOCK:
        done = [k for k, v in JOBS.items() if v['status'] in ('done', 'error')]
        for k in done:
            del JOBS[k]
    return jsonify({"message": f"{len(done)} abgeschlossene Jobs entfernt"})


@downloader_bp.route('/api/dl/history')
@login_required
def dl_history():
    with HISTORY_LOCK:
        h = list(reversed(HISTORY))
    return jsonify({"history": h})


@downloader_bp.route('/api/dl/check')
@login_required
def dl_check():
    import shutil
    ytdlp = shutil.which('yt-dlp') is not None
    ffmpeg = shutil.which('ffmpeg') is not None
    try:
        from yt_dlp import YoutubeDL
        ytdlp_lib = True
    except ImportError:
        ytdlp_lib = False
    return jsonify({"yt_dlp": ytdlp or ytdlp_lib, "ffmpeg": ffmpeg})
