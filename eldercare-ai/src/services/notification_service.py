"""Notification records. In demo mode these are simulated: stored, never sent anywhere."""
from datetime import datetime

from src.database.connection import get_connection


def add_notification(db_path, category: str, message: str, simulated: bool = True, now=None) -> None:
    now = now or datetime.now()
    with get_connection(db_path) as conn:
        conn.execute("INSERT INTO notifications (created_at,category,message,simulated) VALUES (?,?,?,?)",
                     (now.isoformat(timespec="seconds"), category, message, int(simulated)))


def list_notifications(db_path, limit: int = 20):
    with get_connection(db_path) as conn:
        return conn.execute("SELECT * FROM notifications ORDER BY created_at DESC LIMIT ?",
                            (limit,)).fetchall()


def unread_count(db_path) -> int:
    with get_connection(db_path) as conn:
        return conn.execute("SELECT COUNT(*) FROM notifications WHERE read = 0").fetchone()[0]


def mark_all_read(db_path) -> None:
    with get_connection(db_path) as conn:
        conn.execute("UPDATE notifications SET read = 1 WHERE read = 0")
