from flask import Blueprint, request, jsonify, session
from utils.db import get_db_connection
from functools import wraps
from datetime import datetime, timedelta, timezone
import bcrypt

admin_bp = Blueprint('admin', __name__)


def admin_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if session.get('role') != 'admin':
            return jsonify({"error": "Nicht autorisiert"}), 403
        return f(*args, **kwargs)
    return decorated


@admin_bp.route('/admin/users', methods=['GET'])
@admin_required
def list_users():
    conn = get_db_connection()
    with conn.cursor() as cur:
        cur.execute("SELECT username, role, expires_at FROM users ORDER BY username")
        rows = cur.fetchall()
    conn.close()
    return jsonify({"users": [
        {
            "username": r["username"],
            "role": r["role"],
            "expires_at": r["expires_at"].isoformat() if r["expires_at"] else None,
        }
        for r in rows
    ]})


@admin_bp.route('/admin/users/create', methods=['POST'])
@admin_required
def create_user():
    data = request.get_json()
    username = (data.get('username') or '').strip()
    password = data.get('password', '')
    role = data.get('role', 'user')
    temp_minutes = data.get('temp_minutes')

    if not username or not password:
        return jsonify({"error": "Username und Passwort erforderlich"}), 400
    if role not in ('admin', 'user'):
        return jsonify({"error": "Ungültige Rolle"}), 400

    pw_hash = bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()
    expires_at = None
    if temp_minutes:
        try:
            expires_at = datetime.now(timezone.utc) + timedelta(minutes=int(temp_minutes))
        except ValueError:
            return jsonify({"error": "Ungültige Minutenanzahl"}), 400

    try:
        conn = get_db_connection()
        with conn.cursor() as cur:
            cur.execute(
                "INSERT INTO users (username, password, role, expires_at) VALUES (%s, %s, %s, %s)",
                (username, pw_hash, role, expires_at)
            )
        conn.commit()
        conn.close()
        msg = f"Benutzer '{username}' erstellt"
        if expires_at:
            msg += f" (läuft ab: {expires_at.strftime('%H:%M Uhr')})"
        return jsonify({"message": msg})
    except Exception as e:
        if 'duplicate' in str(e).lower() or 'unique' in str(e).lower():
            return jsonify({"error": f"Benutzername '{username}' existiert bereits"}), 409
        return jsonify({"error": str(e)}), 500


@admin_bp.route('/admin/users/delete', methods=['POST'])
@admin_required
def delete_user():
    data = request.get_json()
    username = (data.get('username') or '').strip()
    if not username:
        return jsonify({"error": "Username erforderlich"}), 400
    if username == session.get('user'):
        return jsonify({"error": "Eigenen Account kann nicht gelöscht werden"}), 400
    try:
        conn = get_db_connection()
        with conn.cursor() as cur:
            cur.execute("DELETE FROM users WHERE username = %s", (username,))
            deleted = cur.rowcount
        conn.commit()
        conn.close()
        if not deleted:
            return jsonify({"error": "Benutzer nicht gefunden"}), 404
        return jsonify({"message": f"Benutzer '{username}' gelöscht"})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@admin_bp.route('/admin/settings', methods=['GET'])
@admin_required
def get_settings():
    try:
        conn = get_db_connection()
        with conn.cursor() as cur:
            cur.execute("SELECT key, value FROM settings")
            rows = cur.fetchall()
        conn.close()
        return jsonify({r["key"]: r["value"] for r in rows})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@admin_bp.route('/admin/settings', methods=['POST'])
@admin_required
def save_settings():
    data = request.get_json()
    allowed_keys = {'adguard_url', 'grafana_url', 'dashboard_title'}
    try:
        conn = get_db_connection()
        with conn.cursor() as cur:
            for key, value in data.items():
                if key not in allowed_keys:
                    continue
                cur.execute(
                    "INSERT INTO settings (key, value) VALUES (%s, %s) "
                    "ON CONFLICT (key) DO UPDATE SET value = EXCLUDED.value",
                    (key, str(value))
                )
        conn.commit()
        conn.close()
        return jsonify({"message": "Einstellungen gespeichert"})
    except Exception as e:
        return jsonify({"error": str(e)}), 500
