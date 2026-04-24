from flask import Blueprint, render_template

# Blueprint für Backup & Restore
backup_bp = Blueprint('backup', __name__)

@backup_bp.route('/backup', methods=['GET'])
def backup_page():
    """Backup & Restore-Seite anzeigen."""
    return render_template('backup.html')
