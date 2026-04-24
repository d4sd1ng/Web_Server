#!/usr/bin/env python3
from flask import Flask, redirect, url_for
from dotenv import load_dotenv
import os
import logging

load_dotenv()

logging.basicConfig(level=logging.INFO)

app = Flask(__name__)
app.secret_key = os.getenv('SECRET_KEY', os.urandom(24))

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

for bp in [
    auth_bp, dashboard_bp, adguard_bp, admin_bp, backup_bp,
    databases_bp, downloader_bp, fail2ban_bp, grow_controller_bp,
    mounts_bp, printer_bp, samba_bp, settings_bp, trading_bp, wireguard_bp,
]:
    app.register_blueprint(bp)


@app.route('/')
def index():
    return redirect(url_for('auth.login'))


if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
