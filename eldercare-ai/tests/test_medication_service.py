from datetime import datetime

import pytest

from src.database.schema import init_db
from src.database.seed import reset_demo_data
from src.services import medication_service as ms
from src.services.notification_service import list_notifications

NOON = datetime(2030, 6, 15, 12, 0)


@pytest.fixture
def db(tmp_path):
    path = tmp_path / "t.db"
    init_db(path)
    reset_demo_data(path)
    return path


@pytest.mark.parametrize("name,sched,time", [
    ("", "daily", "08:00"), ("X", "", "08:00"), ("X", "daily", "8am"),
    ("X", "daily", "25:00"), ("A" * 81, "daily", "08:00"), ("X", "s" * 121, "08:00")])
def test_validation_rejects_bad_input(name, sched, time):
    with pytest.raises(ms.ValidationError):
        ms.validate_medication(name, sched, time)


def test_add_edit_delete(db):
    mid = ms.add_medication(db, 1, "  TestMed  ", "Once daily", "07:30")
    assert any(m["name"] == "TestMed" for m in ms.list_medications(db, 1))
    ms.update_medication(db, mid, "TestMed2", "Twice daily", "07:45")
    updated = [m for m in ms.list_medications(db, 1) if m["id"] == mid][0]
    assert (updated["name"], updated["reminder_time"]) == ("TestMed2", "07:45")
    ms.delete_medication(db, mid)
    assert all(m["id"] != mid for m in ms.list_medications(db, 1))


def test_update_missing_medication(db):
    with pytest.raises(ms.ValidationError):
        ms.update_medication(db, 9999, "X", "daily", "08:00")


def test_status_upcoming_overdue_and_recorded(db):
    by_name = lambda: {m["name"]: m["status"] for m in ms.todays_schedule(db, 1, NOON)}
    s = by_name()
    assert s["Metformin (sample)"] == "overdue"        # 08:00 < 12:00, nothing recorded
    assert s["Atorvastatin (sample)"] == "upcoming"    # 21:00 > 12:00
    ms.record_status(db, 1, "taken", NOON)
    assert by_name()["Metformin (sample)"] == "taken"


def test_recording_again_replaces_status(db):
    ms.record_status(db, 1, "skipped", NOON)
    ms.record_status(db, 1, "taken", NOON)
    today = [r for r in ms.history(db, 1, 1, NOON) if r["medication"].startswith("Metformin")]
    assert [r["status"] for r in today] == ["taken"]


def test_missed_creates_simulated_notification(db):
    before = len(list_notifications(db))
    ms.record_status(db, 1, "missed", NOON)
    notes = list_notifications(db)
    assert len(notes) == before + 1 and notes[0]["simulated"] == 1
    ms.record_status(db, 2, "taken", NOON)  # taken must not notify
    assert len(list_notifications(db)) == before + 1


def test_invalid_status_rejected(db):
    with pytest.raises(ms.ValidationError):
        ms.record_status(db, 1, "banana", NOON)


def test_history_window(db):
    ms.record_status(db, 1, "taken", NOON)
    assert all(r["date"] >= "2030-06-09" for r in ms.history(db, 1, 7, NOON))
