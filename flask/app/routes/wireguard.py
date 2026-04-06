from flask import Blueprint, render_template, jsonify
import subprocess

# Blueprint für WireGuard
wireguard_bp = Blueprint('wireguard', __name__)

@wireguard_bp.route('/wireguard', methods=['GET'])
def wireguard_page():
    """WireGuard-Seite anzeigen."""
    try:
        # Status von WireGuard abrufen
        status = subprocess.getoutput("wg show")
    except Exception as e:
        status = f"Fehler beim Abrufen des WireGuard-Status: {e}"
    return render_template('wireguard.html', status=status)
