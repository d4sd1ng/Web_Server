from flask import Blueprint, render_template

# Blueprint für die 3D-Drucker-Seite
printer_bp = Blueprint('printer', __name__)

@printer_bp.route('/3d_printer', methods=['GET'])
def printer_page():
    """3D-Drucker-Seite anzeigen."""
    # Platzhalter für spätere Integration mit Klipper oder anderen Tools
    printer_status = {
        "status": "Bereit",
        "current_job": "Kein aktiver Job",
        "progress": 0
    }
    return render_template('printer.html', status=printer_status)
