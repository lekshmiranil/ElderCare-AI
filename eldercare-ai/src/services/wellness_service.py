"""Daily wellness check-ins and simple, transparent trend rules.

Everything here is self-reported. The rules compare numbers; they do not
interpret health and never produce a diagnosis.
"""
from datetime import date, datetime, timedelta

from src.database.connection import get_connection
from src.services.medication_service import ValidationError

METRICS = ("mood", "wellbeing", "activity")
SCALES = {
    "mood": ["Very low", "Low", "Okay", "Good", "Very good"],
    "wellbeing": ["Very poor", "Poor", "Okay", "Good", "Very good"],
    "activity": ["Very little", "Little", "Some", "Quite active", "Very active"],
}
LOW_VALUE = 2            # rule 1: a score at or below this is flagged
DROP_THRESHOLD = 1.5     # rule 2: points below the recent average
BASELINE_MAX, BASELINE_MIN = 5, 3
MISSING_DAYS = 2         # rule 3: days without a check-in


def _score(value, name):
    if not isinstance(value, int) or isinstance(value, bool) or not 1 <= value <= 5:
        raise ValidationError(f"Please choose a value for {name}.")
    return value


def save_checkin(db_path, elder_id, mood, wellbeing, activity, notes="", now=None) -> None:
    """One check-in per day; saving again the same day replaces it."""
    _score(mood, "mood"), _score(wellbeing, "wellbeing"), _score(activity, "activity")
    notes = (notes or "").strip()
    if len(notes) > 500:
        raise ValidationError("Notes are too long (500 characters maximum).")
    today = (now or datetime.now()).date().isoformat()
    with get_connection(db_path) as conn:
        existing = conn.execute("SELECT id FROM wellness_checkins WHERE elder_id=? AND checkin_date=?",
                                (elder_id, today)).fetchone()
        if existing:
            conn.execute("UPDATE wellness_checkins SET mood=?, wellbeing=?, activity=?, notes=? WHERE id=?",
                         (mood, wellbeing, activity, notes, existing["id"]))
        else:
            conn.execute("INSERT INTO wellness_checkins (elder_id,checkin_date,mood,wellbeing,activity,notes) "
                         "VALUES (?,?,?,?,?,?)", (elder_id, today, mood, wellbeing, activity, notes))


def list_checkins(db_path, elder_id, days=14, now=None):
    """Check-ins from the last `days` days, oldest first."""
    start = ((now or datetime.now()).date() - timedelta(days=days - 1)).isoformat()
    with get_connection(db_path) as conn:
        rows = conn.execute("SELECT * FROM wellness_checkins WHERE elder_id=? AND checkin_date>=? "
                            "ORDER BY checkin_date", (elder_id, start)).fetchall()
    return [dict(r) for r in rows]


def get_today(db_path, elder_id, now=None):
    today = (now or datetime.now()).date().isoformat()
    with get_connection(db_path) as conn:
        row = conn.execute("SELECT * FROM wellness_checkins WHERE elder_id=? AND checkin_date=?",
                           (elder_id, today)).fetchone()
    return dict(row) if row else None


def analyze(checkins, today: date):
    """Apply three fixed rules to check-ins (oldest first). Returns a list of flags.

    1. low_value: the latest score for mood, wellbeing or activity is 2 or lower.
    2. drop: the latest score is 1.5 or more below the average of up to 5 earlier
       check-ins (needs at least 3 earlier check-ins).
    3. missing: no check-in for 2 or more days.
    """
    flags = []
    if not checkins:
        return [{"rule": "missing", "metric": None, "severity": "info",
                 "message": "No check-ins have been recorded yet."}]
    latest, earlier = checkins[-1], checkins[:-1][-BASELINE_MAX:]
    gap = (today - date.fromisoformat(latest["checkin_date"])).days
    if gap >= MISSING_DAYS:
        flags.append({"rule": "missing", "metric": None, "severity": "warn",
                      "message": f"No check-in recorded for {gap} days."})
    for m in METRICS:
        v = latest[m]
        if v <= LOW_VALUE:
            flags.append({"rule": "low_value", "metric": m, "severity": "warn",
                          "message": f"Latest self-reported {m} is low ({SCALES[m][v-1]})."})
        if len(earlier) >= BASELINE_MIN:
            avg = sum(e[m] for e in earlier) / len(earlier)
            if v <= avg - DROP_THRESHOLD:
                flags.append({"rule": "drop", "metric": m, "severity": "warn",
                              "message": f"Self-reported {m} dropped to {v} from a recent average of {avg:.1f}."})
    return flags
