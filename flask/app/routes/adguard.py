from flask import Blueprint, redirect

adguard_bp = Blueprint('adguard', __name__)

@adguard_bp.route('/adguard', methods=['GET'])
def adguard_page():
    """Leitet zur AdGuard-Weboberfläche weiter."""
    adguard_url = "http://192.168.1.6:8888"  # Ersetze durch die URL deiner AdGuard-Weboberfläche
    return redirect(adguard_url)
