from flask import Blueprint, render_template

# Blueprint für den Grow Controller
grow_controller_bp = Blueprint('grow_controller', __name__)

@grow_controller_bp.route('/grow_controller', methods=['GET'])
def grow_controller_page():
    """Grow Controller-Seite anzeigen."""
    # Platzhalter für spätere Sensordaten
    sensors = {
        "temperature": 25.0,  # Beispielwert
        "humidity": 60.0,    # Beispielwert
        "light_status": "Aus"
    }
    return render_template('grow_controller.html', sensors=sensors)
