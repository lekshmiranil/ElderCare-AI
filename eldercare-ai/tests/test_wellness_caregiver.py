from datetime import date, datetime

import pytest

from src.database.schema import init_db
from src.database.seed import reset_demo_data
from src.services import caregiver_service as cs
from src.services import medication_service as ms
from src.services import notification_service as ns
from src.services import wellness_service as ws

NOON = datetime(2030, 6, 15, 12, 0)
TODAY = NOON.date()


def ci(d, mood=4, well=4, act=4):
    return {"checkin_date": d, "mood": mood, "wellbeing": well, "activity": act}


@pytest.fixture
def db(tmp_path):
    path = tmp_path / "t.db"
    init_db(path)
    reset_demo_data(path)
    return path


@pytest.mark.parametrize("bad", [0, 6, None, "3", True])
def test_checkin_rejects_bad_scores(db, bad):
    with pytest.raises(ms.ValidationError):
        ws.save_checkin(db, 1, bad, 3, 3)


def test_checkin_notes_limit(db):
    with pytest.raises(ms.ValidationError):
        ws.save_checkin(db, 1, 3, 3, 3, "x" * 501)


def test_checkin_saved_once_per_day(db):
    ws.save_checkin(db, 1, 3, 3, 3, "a", NOON)
    ws.save_checkin(db, 1, 5, 4, 3, "b", NOON)
    rows = [r for r in ws.list_checkins(db, 1, 1, NOON)]
    assert len(rows) == 1 and rows[0]["mood"] == 5 and rows[0]["notes"] == "b"
    assert ws.get_today(db, 1, NOON)["wellbeing"] == 4


def test_rule_low_value():
    flags = ws.analyze([ci("2030-06-15", mood=2)], TODAY)
    assert any(f["rule"] == "low_value" and f["metric"] == "mood" for f in flags)


def test_rule_drop_needs_baseline_and_threshold():
    base = [ci(f"2030-06-{d}", mood=5) for d in (10, 11, 12, 13)]
    flags = ws.analyze(base + [ci("2030-06-15", mood=3)], TODAY)   # 5 -> 3 = 2 points
    assert any(f["rule"] == "drop" and f["metric"] == "mood" for f in flags)
    small = ws.analyze(base + [ci("2030-06-15", mood=4)], TODAY)   # 1 point only
    assert not any(f["rule"] == "drop" for f in small)
    few = ws.analyze([ci("2030-06-14", mood=5), ci("2030-06-15", mood=3)], TODAY)  # too little history
    assert not any(f["rule"] == "drop" for f in few)


def test_rule_missing():
    assert any(f["rule"] == "missing" for f in ws.analyze([ci("2030-06-12")], TODAY))
    assert not any(f["rule"] == "missing" for f in ws.analyze([ci("2030-06-14")], TODAY))
    assert ws.analyze([], TODAY)[0]["rule"] == "missing"


def test_no_flags_for_steady_good_scores():
    steady = [ci(f"2030-06-{d}") for d in (11, 12, 13, 14, 15)]
    assert ws.analyze(steady, TODAY) == []


def test_adherence_math():
    rows = [{"status": s} for s in ["taken"] * 3 + ["missed", "skipped"]]
    a = cs.adherence(rows)
    assert a["rate"] == 60 and a["recorded"] == 5
    assert cs.adherence([])["rate"] is None


def test_attention_items_flag_overdue_and_recorded_missed(db):
    texts = " ".join(i["text"] for i in cs.attention_items(db, 1, NOON))
    assert "Metformin" in texts and "not recorded" in texts
    ms.record_status(db, 1, "missed", NOON)
    assert "marked missed" in " ".join(i["text"] for i in cs.attention_items(db, 1, NOON))


def test_recent_activity_sorted_and_limited(db):
    feed = cs.recent_activity(db, 1, 5)
    assert len(feed) <= 5 and [a["ts"] for a in feed] == sorted((a["ts"] for a in feed), reverse=True)


def test_notifications_read_state(db):
    assert ns.unread_count(db) == 1
    ns.mark_all_read(db)
    assert ns.unread_count(db) == 0
