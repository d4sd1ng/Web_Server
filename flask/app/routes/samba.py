from flask import Blueprint, render_template, request, redirect, url_for, flash
import os
import subprocess

samba_bp = Blueprint('samba_bp', __name__, template_folder='templates')

@samba_bp.route('/samba')
def samba():
    return render_template('samba.html')

@samba_bp.route('/samba/setup', methods=['POST'])
def setup_samba():
    # Hier führen Sie die Samba-Setup-Befehle aus
    try:
        # Beispielbefehl zum Einrichten von Samba
        subprocess.run(["sudo", "samba-tool", "domain", "provision", "--use-rfc2307", "--interactive"], check=True)
        flash("Samba erfolgreich eingerichtet.")
    except subprocess.CalledProcessError as e:
        flash(f"Fehler bei der Samba-Einrichtung: {e}")
    return redirect(url_for('samba_bp.samba'))
