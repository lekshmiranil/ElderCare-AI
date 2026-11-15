"""Small read helpers used by the UI in Phase 1. Business logic arrives in later phases."""
from .connection import get_connection


def get_person(db_path, role: str):
    with get_connection(db_path) as conn:
        return conn.execute("SELECT * FROM people WHERE role = ? LIMIT 1", (role,)).fetchone()


def count_rows(db_path, table: str) -> int:
    from .schema import TABLES
    if table not in TABLES:  # guards the f-string below against injection
        raise ValueError("Unknown table")
    with get_connection(db_path) as conn:
        return conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]


def list_active_medications(db_path):
    with get_connection(db_path) as conn:
        return conn.execute("SELECT * FROM medications WHERE active = 1 "
                            "ORDER BY reminder_time").fetchall()


def list_upcoming_appointments(db_path, elder_id: int, now_iso: str):
    with get_connection(db_path) as conn:
        return conn.execute("SELECT * FROM appointments WHERE elder_id = ? AND appt_datetime >= ? "
                            "ORDER BY appt_datetime", (elder_id, now_iso)).fetchall()
