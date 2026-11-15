"""Read-only summaries for the caregiver dashboard. Plain arithmetic, no AI."""
from datetime import datetime

from src.database.connection import get_connection
from src.services import medication_service as meds
from src.services import wellness_service as wellness


def adherence(history_rows):
    """Share of recorded entries marked taken. Unrecorded doses are not counted."""
    counts = {s: sum(1 for r in history_rows if r["status"] == s) for s in meds.STATUSES}
    recorded = sum(counts.values())
    rate = round(100 * counts["taken"] / recorded) if recorded else None
    return {**counts, "recorded": recorded, "rate": rate}


def list_emergency_events(db_path, elder_id, limit=20):
    with get_connection(db_path) as conn:
        return [dict(r) for r in conn.execute(
            "SELECT * FROM emergency_events WHERE elder_id=? ORDER BY triggered_at DESC LIMIT ?",
            (elder_id, limit))]


def list_fall_events(db_path, elder_id, limit=20):
    with get_connection(db_path) as conn:
        return [dict(r) for r in conn.execute(
            "SELECT * FROM fall_events WHERE elder_id=? ORDER BY detected_at DESC LIMIT ?",
            (elder_id, limit))]


def recent_activity(db_path, elder_id, limit=10):
    """Merged feed of medication entries, check-ins, emergency and fall events."""
    items = []
    with get_connection(db_path) as conn:
        for r in conn.execute("SELECT l.logged_at ts, m.name, l.status FROM medication_logs l "
                              "JOIN medications m ON m.id=l.medication_id WHERE m.elder_id=? "
                              "ORDER BY l.logged_at DESC LIMIT ?", (elder_id, limit)):
            items.append({"ts": r["ts"], "kind": "Medication", "text": f"{r['name']}: {r['status']}"})
        for r in conn.execute("SELECT checkin_date d, mood, wellbeing, activity FROM wellness_checkins "
                              "WHERE elder_id=? ORDER BY checkin_date DESC LIMIT ?", (elder_id, limit)):
            items.append({"ts": f"{r['d']}T12:00:00", "kind": "Check-in", "date_only": True,
                          "text": f"Mood {r['mood']}/5, wellbeing {r['wellbeing']}/5, activity {r['activity']}/5"})
        for r in conn.execute("SELECT triggered_at ts, alert_sent FROM emergency_events WHERE elder_id=? "
                              "ORDER BY triggered_at DESC LIMIT ?", (elder_id, limit)):
            items.append({"ts": r["ts"], "kind": "Emergency",
                          "text": "Emergency button pressed. " +
                                  ("Alert sent." if r["alert_sent"] else "Alert was simulated, nothing was sent.")})
        for r in conn.execute("SELECT detected_at ts, peak_g FROM fall_events WHERE elder_id=? "
                              "ORDER BY detected_at DESC LIMIT ?", (elder_id, limit)):
            items.append({"ts": r["ts"], "kind": "Fall (simulated)", "text": f"Simulated fall event, peak {r['peak_g']} g"})
    items.sort(key=lambda i: i["ts"], reverse=True)
    return items[:limit]


def attention_items(db_path, elder_id, now=None):
    """Things the fixed rules flag right now. Each is {'severity', 'text'}."""
    now = now or datetime.now()
    out = []
    for m in meds.todays_schedule(db_path, elder_id, now):
        if m["status"] == "overdue":
            out.append({"severity": "warn", "text": f"{m['name']} was due at {m['reminder_time']} and is not recorded."})
        elif m["status"] == "missed":
            out.append({"severity": "warn", "text": f"{m['name']} (due {m['reminder_time']}) was marked missed today."})
    for f in wellness.analyze(wellness.list_checkins(db_path, elder_id, 14, now), now.date()):
        out.append({"severity": f["severity"], "text": f["message"]})
    today_str = now.date().isoformat()
    with get_connection(db_path) as conn:
        for table, col, label in (("emergency_events", "triggered_at", "Emergency button pressed"),
                                  ("fall_events", "detected_at", "Simulated fall event")):
            n = conn.execute(f"SELECT COUNT(*) FROM {table} WHERE elder_id=? AND substr({col},1,10)=?",
                             (elder_id, today_str)).fetchone()[0]
            if n:
                out.append({"severity": "warn", "text": f"{label} today ({n})."})
    return out
