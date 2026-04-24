#!/usr/bin/env python3
from flask import Flask, redirect, url_for
from dotenv import load_dotenv
import os
import logging

load_dotenv()

logging.basicConfig(level=logging.INFO)

app = Flask(__name__)


def init_db():
    from utils.db import get_db_connection
    try:
        conn = get_db_connection()
        with conn.cursor() as cur:
            cur.execute("""
                ALTER TABLE users ADD COLUMN IF NOT EXISTS expires_at TIMESTAMPTZ DEFAULT NULL
            """)
            cur.execute("""
                CREATE TABLE IF NOT EXISTS settings (
                    key VARCHAR(100) PRIMARY KEY,
                    value TEXT NOT NULL
                )
            """)
            cur.execute("""
                INSERT INTO settings (key, value) VALUES
                    ('adguard_url', 'http://192.168.178.10:8081'),
                    ('grafana_url', 'http://192.168.178.10:3000'),
                    ('dashboard_title', 'Homeserver')
                ON CONFLICT (key) DO NOTHING
            """)
        conn.commit()
        conn.close()
        logging.info("DB init OK")
    except Exception as e:
        logging.warning(f"DB init: {e}")
app.secret_key = os.getenv('SECRET_KEY', os.urandom(24))

from routes.api import api_bp
from routes.auth import auth_bp
from routes.dashboard import dashboard_bp
from routes.adguard import adguard_bp
from routes.admin import admin_bp
from routes.backup import backup_bp
from routes.databases import databases_bp
from routes.downloader import downloader_bp
from routes.fail2ban import fail2ban_bp
from routes.grow_controller import grow_controller_bp
from routes.mounts import mounts_bp
from routes.printer import printer_bp
from routes.samba import samba_bp
from routes.settings import settings_bp
from routes.trading import trading_bp
from routes.wireguard import wireguard_bp
from routes.system_update import system_update_bp
from routes.filemanager import filemanager_bp
from routes.metrics import metrics_bp

init_db()

for bp in [
    api_bp, auth_bp, dashboard_bp, adguard_bp, admin_bp, backup_bp,
    databases_bp, downloader_bp, fail2ban_bp, grow_controller_bp,
    mounts_bp, printer_bp, samba_bp, settings_bp, trading_bp, wireguard_bp,
    system_update_bp, filemanager_bp, metrics_bp,
]:
    app.register_blueprint(bp)


@app.before_request
def check_session_expiry():
    from flask import request as req, session
    from utils.db import get_db_connection
    from datetime import datetime, timezone
    if 'user' not in session:
        return
    if req.endpoint in ('auth.login', 'auth.logout', 'static'):
        return
    try:
        conn = get_db_connection()
        with conn.cursor() as cur:
            cur.execute("SELECT expires_at FROM users WHERE username = %s", (session['user'],))
            row = cur.fetchone()
        conn.close()
        if row and row['expires_at'] and row['expires_at'] < datetime.now(timezone.utc):
            session.clear()
            return redirect(url_for('auth.login'))
    except Exception:
        pass


@app.route('/')
def index():
    return redirect(url_for('auth.login'))


if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
