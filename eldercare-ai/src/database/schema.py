"""Database schema. All tables for later phases are defined now to avoid migrations."""
from .connection import get_connection

SCHEMA = """
CREATE TABLE IF NOT EXISTS people (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    role TEXT NOT NULL CHECK (role IN ('elder', 'caregiver')),
    name TEXT NOT NULL,
    age INTEGER,
    phone TEXT,
    relationship TEXT,
    notes TEXT
);

CREATE TABLE IF NOT EXISTS medications (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    elder_id INTEGER NOT NULL REFERENCES people(id) ON DELETE CASCADE,
    name TEXT NOT NULL,
    schedule_text TEXT NOT NULL,          -- as prescribed, entered by a person
    reminder_time TEXT NOT NULL,          -- HH:MM
    active INTEGER NOT NULL DEFAULT 1
);

CREATE TABLE IF NOT EXISTS medication_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    medication_id INTEGER NOT NULL REFERENCES medications(id) ON DELETE CASCADE,
    log_date TEXT NOT NULL,               -- YYYY-MM-DD
    status TEXT NOT NULL CHECK (status IN ('taken', 'skipped', 'missed')),
    logged_at TEXT NOT NULL,
    UNIQUE (medication_id, log_date)
);

CREATE TABLE IF NOT EXISTS appointments (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    elder_id INTEGER NOT NULL REFERENCES people(id) ON DELETE CASCADE,
    title TEXT NOT NULL,
    appt_datetime TEXT NOT NULL,
    location TEXT
);

CREATE TABLE IF NOT EXISTS wellness_checkins (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    elder_id INTEGER NOT NULL REFERENCES people(id) ON DELETE CASCADE,
    checkin_date TEXT NOT NULL,
    mood INTEGER NOT NULL CHECK (mood BETWEEN 1 AND 5),
    wellbeing INTEGER NOT NULL CHECK (wellbeing BETWEEN 1 AND 5),
    activity INTEGER NOT NULL CHECK (activity BETWEEN 1 AND 5),
    notes TEXT
);

CREATE TABLE IF NOT EXISTS emergency_events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    elder_id INTEGER NOT NULL REFERENCES people(id) ON DELETE CASCADE,
    triggered_at TEXT NOT NULL,
    alert_sent INTEGER NOT NULL DEFAULT 0,   -- 1 only if a real alert left the app
    delivery_note TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS fall_events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    elder_id INTEGER NOT NULL REFERENCES people(id) ON DELETE CASCADE,
    detected_at TEXT NOT NULL,
    peak_g REAL NOT NULL,
    threshold_g REAL NOT NULL,
    simulated INTEGER NOT NULL DEFAULT 1
);

CREATE TABLE IF NOT EXISTS notifications (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    created_at TEXT NOT NULL,
    category TEXT NOT NULL,                -- medication, emergency, fall, wellness
    message TEXT NOT NULL,
    simulated INTEGER NOT NULL DEFAULT 1,
    read INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS reminders (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    elder_id INTEGER NOT NULL REFERENCES people(id) ON DELETE CASCADE,
    task TEXT NOT NULL,
    remind_time TEXT NOT NULL              -- HH:MM, saved only after the person confirms
);

CREATE TABLE IF NOT EXISTS ai_usage (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    ts TEXT NOT NULL,
    provider TEXT NOT NULL,
    model TEXT NOT NULL,
    feature TEXT NOT NULL,
    outcome TEXT NOT NULL              -- ok, cache, quota, auth, model_not_found, network, blocked, ...
);

CREATE TABLE IF NOT EXISTS ai_cache (
    cache_key TEXT PRIMARY KEY,        -- hash only; the question text is never stored here
    created_at TEXT NOT NULL,
    response TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS app_settings (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL
);
"""

TABLES = ["people", "medications", "medication_logs", "appointments",
          "wellness_checkins", "emergency_events", "fall_events",
          "notifications", "reminders", "ai_usage", "ai_cache", "app_settings"]


# Columns added after the first release. Existing databases are upgraded in place.
NEW_COLUMNS = {"fall_events": {"kind": "TEXT NOT NULL DEFAULT 'fall'", "ml_score": "REAL", "scenario": "TEXT"}}


def init_db(db_path) -> None:
    with get_connection(db_path) as conn:
        conn.executescript(SCHEMA)
        for table, cols in NEW_COLUMNS.items():
            have = {r["name"] for r in conn.execute(f"PRAGMA table_info({table})")}
            for name, ddl in cols.items():
                if name not in have:
                    conn.execute(f"ALTER TABLE {table} ADD COLUMN {name} {ddl}")
