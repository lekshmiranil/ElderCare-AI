"""Profile, caregiver details and personal preferences. Plain data, no AI."""
import re

from src.database.connection import get_connection
from src.services.medication_service import ValidationError

PREF_KEYS = ("preferred_name", "interests", "wake_time", "bedtime")
_TIME = re.compile(r"^([01]\d|2[0-3]):[0-5]\d$")


def _text(value, label, maxlen, required=False):
    value = (value or "").strip()
    if required and not value:
        raise ValidationError(f"Please enter {label}.")
    if len(value) > maxlen:
        raise ValidationError(f"{label.capitalize()} is too long ({maxlen} characters maximum).")
    return value


def update_person(db_path, person_id: int, name: str, age, phone: str, relationship: str = None) -> None:
    name, phone = _text(name, "a name", 60, True), _text(phone, "a phone number", 30)
    if age is not None and not (1 <= int(age) <= 120):
        raise ValidationError("Please enter an age between 1 and 120.")
    rel = _text(relationship, "the relationship", 40) if relationship is not None else None
    with get_connection(db_path) as c:
        cur = c.execute("UPDATE people SET name=?, age=?, phone=?, relationship=COALESCE(?, relationship) WHERE id=?",
                        (name, age, phone, rel, person_id))
        if cur.rowcount == 0:
            raise ValidationError("That person no longer exists.")


def get_preferences(db_path) -> dict:
    with get_connection(db_path) as c:
        rows = {r["key"]: r["value"] for r in c.execute("SELECT key,value FROM app_settings WHERE key LIKE 'pref_%'")}
    return {k: rows.get(f"pref_{k}", "") for k in PREF_KEYS}


def save_preferences(db_path, preferred_name="", interests="", wake_time="", bedtime="") -> None:
    values = {"preferred_name": _text(preferred_name, "the preferred name", 30),
              "interests": _text(interests, "interests", 150), "wake_time": wake_time or "", "bedtime": bedtime or ""}
    for k in ("wake_time", "bedtime"):
        if values[k] and not _TIME.match(values[k]):
            raise ValidationError("Please choose a valid time.")
    with get_connection(db_path) as c:
        for k, v in values.items():
            c.execute("INSERT INTO app_settings (key,value) VALUES (?,?) ON CONFLICT(key) DO UPDATE SET value=excluded.value",
                      (f"pref_{k}", v))


def display_name(elder, prefs: dict) -> str:
    """What the app calls the person: preferred name if set, otherwise the first name."""
    return prefs.get("preferred_name") or elder["name"].split()[0]
