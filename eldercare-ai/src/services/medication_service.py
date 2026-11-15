"""Medication business logic. No UI code and no AI: schedules come only from people.

The schedule text is stored exactly as entered. The app never creates or changes
a schedule or dosage on its own.
"""
import re
from datetime import datetime

from src.database.connection import get_connection
from src.services.notification_service import add_notification

STATUSES = ("taken", "skipped", "missed")
_TIME_RE = re.compile(r"^([01]\d|2[0-3]):[0-5]\d$")


class ValidationError(ValueError):
    """Raised with a message that is safe to show to the user."""


def validate_medication(name: str, schedule_text: str, reminder_time: str):
    name, schedule_text = (name or "").strip(), (schedule_text or "").strip()
    if not name:
        raise ValidationError("Please enter the medicine name.")
    if len(name) > 80:
        raise ValidationError("The medicine name is too long (80 characters maximum).")
    if not schedule_text:
        raise ValidationError("Please enter the prescribed schedule, for example 'Once daily, after breakfast'.")
    if len(schedule_text) > 120:
        raise ValidationError("The schedule is too long (120 characters maximum).")
    if not _TIME_RE.match(reminder_time or ""):
        raise ValidationError("Please choose a valid reminder time.")
    return name, schedule_text, reminder_time


def add_medication(db_path, elder_id: int, name: str, schedule_text: str, reminder_time: str) -> int:
    name, schedule_text, reminder_time = validate_medication(name, schedule_text, reminder_time)
    with get_connection(db_path) as conn:
        cur = conn.execute("INSERT INTO medications (elder_id,name,schedule_text,reminder_time) "
                           "VALUES (?,?,?,?)", (elder_id, name, schedule_text, reminder_time))
        return cur.lastrowid


def update_medication(db_path, med_id: int, name: str, schedule_text: str, reminder_time: str) -> None:
    name, schedule_text, reminder_time = validate_medication(name, schedule_text, reminder_time)
    with get_connection(db_path) as conn:
        cur = conn.execute("UPDATE medications SET name=?, schedule_text=?, reminder_time=? WHERE id=?",
                           (name, schedule_text, reminder_time, med_id))
        if cur.rowcount == 0:
            raise ValidationError("That medication no longer exists.")


def delete_medication(db_path, med_id: int) -> None:
    """Hard delete. Its history is removed too (ON DELETE CASCADE)."""
    with get_connection(db_path) as conn:
        conn.execute("DELETE FROM medications WHERE id = ?", (med_id,))


def list_medications(db_path, elder_id: int):
    with get_connection(db_path) as conn:
        return conn.execute("SELECT * FROM medications WHERE elder_id=? AND active=1 "
                            "ORDER BY reminder_time, name", (elder_id,)).fetchall()


def record_status(db_path, med_id: int, status: str, now=None) -> None:
    """Record today's status for a medication. Recording again replaces the earlier entry."""
    if status not in STATUSES:
        raise ValidationError("Unknown status.")
    now = now or datetime.now()
    with get_connection(db_path) as conn:
        med = conn.execute("SELECT name, reminder_time FROM medications WHERE id=?", (med_id,)).fetchone()
        if med is None:
            raise ValidationError("That medication no longer exists.")
        conn.execute(
            "INSERT INTO medication_logs (medication_id,log_date,status,logged_at) VALUES (?,?,?,?) "
            "ON CONFLICT(medication_id, log_date) DO UPDATE SET status=excluded.status, "
            "logged_at=excluded.logged_at",
            (med_id, now.date().isoformat(), status, now.isoformat(timespec="seconds")))
    if status == "missed":
        add_notification(db_path, "medication",
                         f"{med['name']} (due {med['reminder_time']}) was marked as missed.", now=now)


def todays_schedule(db_path, elder_id: int, now=None):
    """Each active medication with a display status.

    Status is the recorded one (taken/skipped/missed) or, if nothing is recorded,
    'overdue' (reminder time has passed) or 'upcoming'. Plain time comparison, no AI.
    """
    now = now or datetime.now()
    today, hhmm = now.date().isoformat(), now.strftime("%H:%M")
    with get_connection(db_path) as conn:
        rows = conn.execute(
            "SELECT m.id, m.name, m.schedule_text, m.reminder_time, l.status AS logged "
            "FROM medications m LEFT JOIN medication_logs l "
            "ON l.medication_id = m.id AND l.log_date = ? "
            "WHERE m.elder_id = ? AND m.active = 1 ORDER BY m.reminder_time, m.name",
            (today, elder_id)).fetchall()
    result = []
    for r in rows:
        status = r["logged"] or ("overdue" if r["reminder_time"] < hhmm else "upcoming")
        result.append({"id": r["id"], "name": r["name"], "schedule_text": r["schedule_text"],
                       "reminder_time": r["reminder_time"], "status": status})
    return result


def history(db_path, elder_id: int, days: int = 7, now=None):
    """Recorded entries for the last `days` days including today, newest first."""
    from datetime import timedelta
    now = now or datetime.now()
    start = (now.date() - timedelta(days=days - 1)).isoformat()
    with get_connection(db_path) as conn:
        rows = conn.execute(
            "SELECT l.log_date AS date, m.name AS medication, m.reminder_time AS time, l.status "
            "FROM medication_logs l JOIN medications m ON m.id = l.medication_id "
            "WHERE m.elder_id = ? AND l.log_date >= ? ORDER BY l.log_date DESC, m.reminder_time",
            (elder_id, start)).fetchall()
    return [dict(r) for r in rows]
