from flask import Blueprint, render_template, request, redirect, url_for, session
from utils.db import get_db_connection
from datetime import datetime, timezone
import bcrypt
import logging

# Blueprint für die Authentifizierung
auth_bp = Blueprint('auth', __name__)

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    """Login-Seite."""
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')

        try:
            logging.debug("Verbindungsaufbau zur Datenbank gestartet.")
            conn = get_db_connection()
            logging.debug("Datenbankverbindung erfolgreich.")

            with conn.cursor() as cursor:
                cursor.execute("SELECT username, password, role FROM users WHERE username = %s", (username,))
                user = cursor.fetchone()

            if user:
                logging.debug(f"Benutzer gefunden: {username}")
                logging.debug(f"Datenbank-Hash: {user['password']}")

            # Benutzerprüfung
            if user and bcrypt.checkpw(password.encode('utf-8'), user['password'].encode('utf-8')):
                if user.get('expires_at') and user['expires_at'] < datetime.now(timezone.utc):
                    conn.close()
                    logging.warning(f"Temporärer Benutzer abgelaufen: {username}")
                    return render_template('login.html', error="Temporärer Zugang ist abgelaufen")
                session['user'] = user['username']
                session['role'] = user['role']
                conn.close()
                logging.info(f"Login erfolgreich: {session['user']}, Rolle: {session['role']}")
                return redirect(url_for('dashboard.dashboard'))

            conn.close()
            logging.warning(f"Ungültige Anmeldedaten für Benutzer: {username}")
            return render_template('login.html', error="Ungültige Anmeldedaten")

        except Exception as e:
            logging.error(f"Fehler beim Datenbankzugriff: {e}")
            return render_template('login.html', error=f"Fehler beim Datenbankzugriff: {e}")

    return render_template('login.html')

@auth_bp.route('/logout', methods=['GET'])
def logout():
    """Logout-Funktion."""
    session.clear()  # Löscht alle Daten aus der aktuellen Session
    logging.info("Benutzer erfolgreich ausgeloggt.")
    return redirect(url_for('auth.login'))  # Weiterleitung zur Login-Seite
