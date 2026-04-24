from flask import Blueprint, jsonify, session
from functools import wraps
import psycopg2
import psycopg2.extras
import os

databases_bp = Blueprint('databases', __name__)

PGADMIN_URL = 'https://pgadmin.internal.avataryx.de'


def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if 'user' not in session:
            return jsonify({"error": "Nicht eingeloggt"}), 401
        return f(*args, **kwargs)
    return decorated


def _conn(dbname='postgres'):
    return psycopg2.connect(
        dbname=dbname,
        user=os.getenv('POSTGRES_USER'),
        password=os.getenv('POSTGRES_PASSWORD'),
        host=os.getenv('POSTGRES_HOST', 'localhost'),
        port=int(os.getenv('POSTGRES_PORT', 5432)),
        connect_timeout=5,
    )


@databases_bp.route('/api/db/list')
@login_required
def db_list():
    try:
        conn = _conn()
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute("""
                SELECT datname AS name,
                       pg_size_pretty(pg_database_size(datname)) AS size,
                       pg_database_size(datname) AS size_bytes
                FROM pg_database
                WHERE datistemplate = false
                ORDER BY datname
            """)
            dbs = [dict(r) for r in cur.fetchall()]
        conn.close()
        return jsonify({"databases": dbs, "pgadmin_url": PGADMIN_URL})
    except Exception as e:
        return jsonify({"error": str(e)}), 503


@databases_bp.route('/api/db/tables')
@login_required
def db_tables():
    dbname = (session.get('_db_sel') or 'postgres')
    dbname = dbname if dbname.isidentifier() else 'postgres'
    req_db = __import__('flask').request.args.get('db', 'postgres')
    if req_db.isidentifier():
        dbname = req_db
    try:
        conn = _conn(dbname)
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute("""
                SELECT
                    t.table_name                                        AS name,
                    t.table_schema                                      AS schema,
                    COALESCE(s.n_live_tup, 0)                          AS rows,
                    pg_size_pretty(pg_total_relation_size(
                        quote_ident(t.table_schema)||'.'||quote_ident(t.table_name)
                    ))                                                  AS size
                FROM information_schema.tables t
                LEFT JOIN pg_stat_user_tables s
                       ON s.schemaname = t.table_schema
                      AND s.relname    = t.table_name
                WHERE t.table_schema NOT IN ('pg_catalog','information_schema')
                  AND t.table_type = 'BASE TABLE'
                ORDER BY t.table_schema, t.table_name
            """)
            tables = [dict(r) for r in cur.fetchall()]
        conn.close()
        return jsonify({"database": dbname, "tables": tables})
    except Exception as e:
        return jsonify({"error": str(e)}), 503


@databases_bp.route('/api/db/preview')
@login_required
def db_preview():
    from flask import request
    db     = request.args.get('db', 'postgres')
    table  = request.args.get('table', '')
    schema = request.args.get('schema', 'public')
    if not db.isidentifier() or not table.isidentifier():
        return jsonify({"error": "Ungültige Parameter"}), 400
    try:
        conn = _conn(db)
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(
                f'SELECT * FROM {psycopg2.extensions.quote_ident(schema, conn)}'
                f'.{psycopg2.extensions.quote_ident(table, conn)} LIMIT 15'
            )
            rows = [dict(r) for r in cur.fetchall()]
            cols = [desc[0] for desc in cur.description] if cur.description else []
        conn.close()
        return jsonify({"columns": cols, "rows": rows})
    except Exception as e:
        return jsonify({"error": str(e)}), 503


@databases_bp.route('/api/db/columns')
@login_required
def db_columns():
    db    = __import__('flask').request.args.get('db', 'postgres')
    table = __import__('flask').request.args.get('table', '')
    schema = __import__('flask').request.args.get('schema', 'public')
    if not db.isidentifier() or not table.isidentifier():
        return jsonify({"error": "Ungültige Parameter"}), 400
    try:
        conn = _conn(db)
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute("""
                SELECT column_name AS name,
                       data_type   AS type,
                       is_nullable AS nullable,
                       column_default AS default
                FROM information_schema.columns
                WHERE table_schema = %s AND table_name = %s
                ORDER BY ordinal_position
            """, (schema, table))
            cols = [dict(r) for r in cur.fetchall()]
        conn.close()
        return jsonify({"columns": cols})
    except Exception as e:
        return jsonify({"error": str(e)}), 503
