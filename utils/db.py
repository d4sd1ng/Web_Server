import os
import psycopg2
import psycopg2.extras


def get_db_connection():
    conn = psycopg2.connect(
        host=os.getenv('POSTGRES_HOST', 'localhost'),
        port=int(os.getenv('POSTGRES_PORT', 5432)),
        dbname=os.getenv('POSTGRES_DB', 'homeserver'),
        user=os.getenv('POSTGRES_USER'),
        password=os.getenv('POSTGRES_PASSWORD'),
    )
    conn.cursor_factory = psycopg2.extras.RealDictCursor
    return conn
