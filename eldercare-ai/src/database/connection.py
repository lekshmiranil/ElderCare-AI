"""SQLite connection helper."""
import sqlite3
from contextlib import contextmanager
from pathlib import Path


@contextmanager
def get_connection(db_path):
    """Yield a connection with foreign keys on; commit on success, roll back on error."""
    Path(db_path).parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()
