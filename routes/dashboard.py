from flask import Blueprint, render_template, session, redirect, url_for

dashboard_bp = Blueprint('dashboard', __name__)

@dashboard_bp.route('/dashboard', methods=['GET'])
def dashboard():
    """Dashboard-Seite."""
    if 'user' not in session:
        return redirect(url_for('auth.login'))

    user = session['user']
    role = session['role']

    # Unterschiedliche Inhalte basierend auf der Rolle
    return render_template('dashboard.html', user=user, role=role)
