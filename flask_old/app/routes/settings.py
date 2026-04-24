from flask import Blueprint, render_template, request, jsonify

settings_bp = Blueprint('settings', __name__)

@settings_bp.route('/settings', methods=['GET'])
def settings_page():
    """Server-Einstellungen-Seite anzeigen."""
    settings = {
        "hostname": "homeserver",
        "ip_address": "192.168.1.6",
        "dns_server": "192.168.1.6"
    }
    return render_template('settings.html', settings=settings)

@settings_bp.route('/settings/update', methods=['POST'])
def update_settings():
    """Server-Einstellungen aktualisieren."""
    hostname = request.form.get('hostname')
    ip_address = request.form.get('ip_address')
    dns_server = request.form.get('dns_server')

    # Platzhalter: Speichern der Einstellungen
    print(f"Einstellungen aktualisiert: {hostname}, {ip_address}, {dns_server}")
    return jsonify({"message": "Einstellungen erfolgreich aktualisiert"})
