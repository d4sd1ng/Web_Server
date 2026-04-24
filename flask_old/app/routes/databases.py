from flask import Blueprint, render_template, jsonify
import psycopg2
import os

databases_bp = Blueprint('databases', __name__)

def get_databases():
    conn = psycopg2.connect(
        dbname="postgres",
        user=os.getenv('DB_USER'),       # Verwende Umgebungsvariablen für die Anmeldeinformationen
        password=os.getenv('DB_PASSWORD'),
        host="localhost"
    )
    cur = conn.cursor()
    cur.execute("SELECT datname FROM pg_database WHERE datistemplate = false;")
    databases = cur.fetchall()
    cur.close()
    conn.close()
    return [db[0] for db in databases]

@databases_bp.route('/', methods=['GET'])
def databases_page():
    databases = get_databases()
    return render_template('databases.html', databases=databases)

@databases_bp.route('/list', methods=['GET'])
def list_databases():
    databases = get_databases()
    return jsonify(databases)
