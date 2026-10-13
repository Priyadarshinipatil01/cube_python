import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).resolve().parent / "cubes.db"

def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_connection()
    conn.execute("""
        CREATE TABLE IF NOT EXISTS cubes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL UNIQUE,
            description TEXT DEFAULT '',
            metric TEXT NOT NULL,
            dimension TEXT NOT NULL,
            chart_type TEXT NOT NULL,
            enabled INTEGER NOT NULL DEFAULT 1
        )
    """)
    conn.commit()
    conn.close()
