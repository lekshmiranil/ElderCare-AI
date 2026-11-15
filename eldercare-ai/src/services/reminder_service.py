"""Personal reminders (for example 'drink water at 17:00'). Medicines are NOT handled here."""
from datetime import datetime

from src.database.connection import get_connection
from src.services.medication_service import ValidationError, _TIME_RE


def add_reminder(db_path, elder_id: int, task: str, remind_time: str) -> int:
    task = (task or "").strip()
    if not task:
        raise ValidationError("Please say what the reminder is for.")
    if len(task) > 100:
        raise ValidationError("The reminder is too long (100 characters maximum).")
    if not _TIME_RE.match(remind_time or ""):
        raise ValidationError("Please choose a valid time.")
    with get_connection(db_path) as c:
        return c.execute("INSERT INTO reminders (elder_id,task,remind_time) VALUES (?,?,?)",
                         (elder_id, task, remind_time)).lastrowid


def list_reminders(db_path, elder_id: int, now=None):
    now = now or datetime.now()
    hhmm = now.strftime("%H:%M")
    with get_connection(db_path) as c:
        rows = c.execute("SELECT * FROM reminders WHERE elder_id=? ORDER BY remind_time", (elder_id,)).fetchall()
    return [{**dict(r), "status": "past" if r["remind_time"] < hhmm else "upcoming"} for r in rows]


def delete_reminder(db_path, reminder_id: int) -> None:
    with get_connection(db_path) as c:
        c.execute("DELETE FROM reminders WHERE id=?", (reminder_id,))
