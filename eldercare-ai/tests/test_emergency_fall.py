import sqlite3
from datetime import datetime
from pathlib import Path

import numpy as np
import pytest
from streamlit.testing.v1 import AppTest

from src.database.queries import get_person
from src.database.schema import init_db
from src.database.seed import reset_demo_data
from src.notifications.channel import Delivery, NotificationChannel, SimulatedChannel
from src.safety.sensor_sim import SCENARIOS, simulate
from src.services import fall_service as fs
from src.services.emergency_service import trigger_emergency
from src.services.medication_service import ValidationError
from src.services.notification_service import list_notifications

NOW = datetime(2030, 6, 15, 12, 0)


@pytest.fixture
def ctx(tmp_path):
    db = tmp_path / "t.db"
    init_db(db)
    reset_demo_data(db)
    return db, get_person(db, "elder"), get_person(db, "caregiver")


class SuccessChannel(NotificationChannel):
    name = "test"

    def send(self, recipient, message):
        return Delivery(True, "Delivered by test channel")


def test_simulated_channel_never_claims_delivery(ctx):
    db, elder, cg = ctx
    r = trigger_emergency(db, elder, cg, SimulatedChannel(), NOW)
    assert r["sent"] is False and "nothing was sent" in r["note"]
    row = sqlite3.connect(db).execute("SELECT alert_sent, delivery_note FROM emergency_events ORDER BY id DESC").fetchone()
    assert row[0] == 0 and "nothing was sent" in row[1]
    note = list_notifications(db)[0]
    assert note["category"] == "emergency" and note["simulated"] == 1


def test_sent_is_recorded_only_if_a_channel_reports_it(ctx):
    db, elder, cg = ctx
    assert trigger_emergency(db, elder, cg, SuccessChannel(), NOW)["sent"] is True
    assert sqlite3.connect(db).execute("SELECT alert_sent FROM emergency_events ORDER BY id DESC").fetchone()[0] == 1


def test_emergency_button_needs_confirmation(tmp_path, monkeypatch):
    db = tmp_path / "ui.db"
    monkeypatch.setenv("DB_PATH", str(db))
    at = AppTest.from_file(str(Path(__file__).resolve().parent.parent / "app.py"), default_timeout=60).run()

    def events():
        return sqlite3.connect(db).execute("SELECT COUNT(*) FROM emergency_events").fetchone()[0]
    before = events()
    next(b for b in at.button if b.label == "I need help").click().run()
    assert events() == before and any("Do you want to send" in w.value for w in at.warning)   # asked, nothing logged yet
    next(b for b in at.button if b.label == "No, cancel").click().run()
    assert events() == before
    next(b for b in at.button if b.label == "I need help").click().run()
    next(b for b in at.button if b.label == "Yes, send the alert").click().run()
    assert events() == before + 1
    text = " ".join(w.value for w in at.warning) + " " + " ".join(e.value for e in at.error)
    assert "nothing was sent" in text and "112" in text


# ---- fall detection ------------------------------------------------------------------------------------
def test_simulation_is_repeatable_and_shaped():
    a, b = simulate("fall", 1), simulate("fall", 1)
    assert np.array_equal(a, b) and len(a) == 200 and not np.array_equal(a, simulate("fall", 2))
    for sc in SCENARIOS:
        assert simulate(sc, 3).shape == (200,)


def test_falls_detected_and_normal_activity_mostly_ignored():
    falls = [fs.assess(simulate("fall", s), 2.5)["outcome"] for s in range(9000, 9050)]
    assert falls.count("fall") == 50
    for sc in ("standing", "sitting", "walking", "sit_hard"):
        outs = [fs.assess(simulate(sc, s), 2.5)["outcome"] for s in range(9000, 9050)]
        assert outs.count("none") >= 48, sc


def test_threshold_changes_the_rule_but_ml_still_flags_unusual():
    w = simulate("fall_soft", 11)
    low, high = fs.assess(w, 2.0), fs.assess(w, 4.0)
    assert low["triggered"] and low["outcome"] == "fall"
    assert not high["triggered"] and high["outcome"] == "unusual"


def test_stumble_is_not_a_fall():
    r = fs.assess(simulate("stumble", 5), 2.5)
    assert not r["triggered"] and r["outcome"] in ("unusual", "none")


def test_threshold_validation_and_storage(ctx):
    db = ctx[0]
    assert fs.get_threshold(db) == 2.5
    fs.set_threshold(db, 3.2)
    assert fs.get_threshold(db) == 3.2
    for bad in (0.5, 9):
        with pytest.raises(ValidationError):
            fs.set_threshold(db, bad)


def test_events_recorded_with_simulated_notification_and_none_is_ignored(ctx):
    db, elder, _ = ctx
    n_events = sqlite3.connect(db).execute("SELECT COUNT(*) FROM fall_events").fetchone()[0]
    fs.record_event(db, elder["id"], fs.assess(simulate("walking", 1), 2.5), "walking", NOW)
    assert sqlite3.connect(db).execute("SELECT COUNT(*) FROM fall_events").fetchone()[0] == n_events
    fs.record_event(db, elder["id"], fs.assess(simulate("fall", 1), 2.5), "fall", NOW)
    row = sqlite3.connect(db).execute("SELECT kind, scenario, simulated FROM fall_events ORDER BY id DESC").fetchone()
    assert row == ("fall", "fall", 1)
    assert list_notifications(db)[0]["category"] == "fall" and "simulated" in list_notifications(db)[0]["message"].lower()


def test_old_database_is_upgraded(tmp_path):
    db = tmp_path / "old.db"
    conn = sqlite3.connect(db)
    conn.execute("CREATE TABLE fall_events (id INTEGER PRIMARY KEY, elder_id INTEGER, detected_at TEXT, peak_g REAL, threshold_g REAL, simulated INTEGER)")
    conn.commit(); conn.close()
    init_db(db)
    cols = {r[1] for r in sqlite3.connect(db).execute("PRAGMA table_info(fall_events)")}
    assert {"kind", "ml_score", "scenario"} <= cols
