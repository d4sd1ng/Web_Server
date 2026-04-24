from flask import Blueprint, render_template, request, jsonify
from flask import Blueprint, render_template, request, jsonify
import os
import json
import subprocess

mounts_bp = Blueprint('mounts', __name__)

MOUNTS_FILE = "/opt/server/config/mounts.json"

@mounts_bp.route('/mounts', methods=['GET'])
def mounts_page():
    """Mounts-Seite anzeigen."""
    mounts = []
    if os.path.exists(MOUNTS_FILE):
        try:
            with open(MOUNTS_FILE, "r", encoding='utf-8') as f:
                mounts = json.load(f)
        except UnicodeDecodeError as e:
            print(f"Fehler beim Lesen der Datei: {e}")
    return render_template('mounts.html', mounts=mounts)

@mounts_bp.route('/mounts/add', methods=['POST'])
def add_mount():
    """Neuen Mount-Punkt hinzufügen."""
    platform = request.form.get('platform')  # Windows oder Linux
    device = request.form.get('device')
    mount_point = request.form.get('mount_point')

    if not platform or not device or not mount_point:
        return jsonify({"error": "Plattform, Gerät und Mount-Punkt sind erforderlich"}), 400

    # Mount-Punkt in der Konfigurationsdatei speichern
    mount_entry = {"platform": platform, "device": device, "mount_point": mount_point}

    mounts = []
    if os.path.exists(MOUNTS_FILE):
        try:
            with open(MOUNTS_FILE, "r", encoding='utf-8') as f:
                mounts = json.load(f)
        except UnicodeDecodeError as e:
            print(f"Fehler beim Lesen der Datei: {e}")

    mounts.append(mount_entry)

    with open(MOUNTS_FILE, "w", encoding='utf-8') as f:
        json.dump(mounts, f, indent=4, ensure_ascii=False)

    return jsonify({"message": "Mount hinzugefügt", "entry": mount_entry})

@mounts_bp.route('/mounts/check', methods=['POST'])
def check_mount():
    """Prüft, ob der Mount-Punkt funktioniert."""
    platform = request.form.get('platform')
    mount_point = request.form.get('mount_point')

    try:
        if platform == "windows":
            result = subprocess.run(["net", "use", mount_point], capture_output=True, text=True)
        elif platform == "linux":
            result = subprocess.run(["ls", mount_point], capture_output=True, text=True)
        else:
            return jsonify({"error": "Ungültige Plattform"}), 400

        if result.returncode == 0:
            return jsonify({"message": f"Mount {mount_point} ist erreichbar"})
        else:
            return jsonify({"error": f"Mount {mount_point} ist nicht erreichbar: {result.stderr}"}), 400
    except Exception as e:
        return jsonify({"error": str(e)}), 500
