from flask import Blueprint, render_template, jsonify, request
import subprocess
import os

fail2ban_bp = Blueprint('fail2ban', __name__)

# Pfad zum Fail2Ban-Log
FAIL2BAN_LOG = "/opt/server/logs/fail2ban.log"

@fail2ban_bp.route('/fail2ban', methods=['GET'])
def fail2ban_page():
    """Fail2Ban-Seite anzeigen."""
    return render_template('fail2ban.html')

@fail2ban_bp.route('/fail2ban/ips', methods=['GET'])
def get_banned_ips():
    """Liste der gesperrten IPs abrufen."""
    try:
        result = subprocess.run(["fail2ban-client", "status"], capture_output=True, text=True)
        lines = result.stdout.splitlines()
        jails = [
            jail.strip() for line in lines if "Jail list" in line
            for jail in line.split(":")[1].split(",")
        ]

        banned_ips = {}
        for jail in jails:
            result = subprocess.run(["fail2ban-client", "status", jail], capture_output=True, text=True)
            for line in result.stdout.splitlines():
                if "Banned IP list:" in line:
                    ips = line.split(":")[1].strip().split()
                    banned_ips[jail] = ips
        return jsonify({"banned_ips": banned_ips})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@fail2ban_bp.route('/fail2ban/unban', methods=['POST'])
def unban_ip():
    """Eine IP-Adresse entsperren."""
    ip = request.form.get('ip')
    jail = request.form.get('jail')
    if not ip or not jail:
        return jsonify({"error": "IP und Jail sind erforderlich"}), 400
    try:
        subprocess.run(["fail2ban-client", "set", jail, "unbanip", ip], check=True)
        return jsonify({"message": f"IP {ip} erfolgreich entsperrt"})
    except subprocess.CalledProcessError as e:
        return jsonify({"error": str(e)}), 500

@fail2ban_bp.route('/fail2ban/logs', methods=['GET'])
def get_logs():
    """Logdatei von Fail2Ban abrufen."""
    if not os.path.exists(FAIL2BAN_LOG):
        return jsonify({"error": "Fail2Ban-Logdatei nicht gefunden"}), 404
    try:
        with open(FAIL2BAN_LOG, "r") as log_file:
            logs = log_file.readlines()[-50:]  # Zeigt die letzten 50 Zeilen
        return jsonify({"logs": logs})
    except Exception as e:
        return jsonify({"error": str(e)}), 500
