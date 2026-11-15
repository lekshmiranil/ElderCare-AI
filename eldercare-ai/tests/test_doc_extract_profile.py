import io
import sqlite3
from pathlib import Path

import pytest
from streamlit.testing.v1 import AppTest

from src.ai import doc_extract as de
from src.ai.assistant import answer
from src.ai.data.eval_sets import DOC_EVAL
from src.ai.manager import AIManager, Limits
from src.database.queries import get_person
from src.database.schema import init_db
from src.database.seed import reset_demo_data
from src.services import medication_service as ms
from src.services import profile_service as ps
from tests.fakes import FakeProvider

RX = DOC_EVAL[0][0]


@pytest.fixture
def env(tmp_path):
    db = tmp_path / "t.db"
    init_db(db)
    reset_demo_data(db)
    return db, get_person(db, "elder"), get_person(db, "caregiver")


def test_parser_finds_medicines_and_ignores_headers():
    got = {c.name for c in de.parse_medications(RX)}
    assert got == {"Metformin", "Amlodipine", "Omeprazole", "Atorvastatin"}      # no doctor, patient or follow-up lines
    metformin = [c for c in de.parse_medications(RX) if c.name == "Metformin"][0]
    assert metformin.strength == "500 mg" and metformin.schedule_text == "1-0-1 after food" and metformin.confidence == "good"
    assert de.parse_medications(DOC_EVAL[2][0]) == []


def test_missing_schedule_is_flagged_for_checking():
    c = de.parse_medications("Tab. Paracetamol 650 mg")[0]
    assert c.schedule_text == "" and c.confidence == "check"


def test_nothing_saved_without_confirmation_and_invalid_items_block_everything(env):
    db, elder, _ = env
    good = {"name": "Metformin", "strength": "500 mg", "schedule_text": "1-0-1 after food", "reminder_time": "08:00"}
    bad = {"name": "Other", "strength": "", "schedule_text": "", "reminder_time": "09:00"}
    before = len(ms.list_medications(db, elder["id"]))
    with pytest.raises(ms.ValidationError):
        de.save_confirmed(db, elder["id"], [good], confirmed=False)
    with pytest.raises(ms.ValidationError):
        de.save_confirmed(db, elder["id"], [good, bad], confirmed=True)       # one bad line saves none
    assert len(ms.list_medications(db, elder["id"])) == before
    assert de.save_confirmed(db, elder["id"], [good], True) == 1
    assert "Metformin 500 mg" in [m["name"] for m in ms.list_medications(db, elder["id"])]


@pytest.mark.skipif(not de.ocr_available(), reason="optional OCR add-on not installed")
def test_ocr_round_trip_on_a_generated_prescription():
    from PIL import Image, ImageDraw, ImageFont
    img = Image.new("RGB", (900, 200), "white")
    d = ImageDraw.Draw(img)
    try:
        font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 30)
    except OSError:
        pytest.skip("no TrueType font available")
    d.text((30, 40), "1. Tab. Metformin 500 mg  1-0-1 after food", fill="black", font=font)
    buf = io.BytesIO()
    img.save(buf, "PNG")
    assert [c.name for c in de.parse_medications(de.ocr_image(buf.getvalue()))] == ["Metformin"]


def test_ocr_unavailable_is_reported_cleanly(monkeypatch):
    monkeypatch.setattr(de, "ocr_available", lambda: False)
    with pytest.raises(de.OCRUnavailable):
        de.ocr_image(b"x")


def test_scan_page_saves_only_after_confirmation(tmp_path, monkeypatch):
    db = tmp_path / "ui.db"
    monkeypatch.setenv("DB_PATH", str(db))
    count = lambda: sqlite3.connect(db).execute("SELECT COUNT(*) FROM medications").fetchone()[0]
    at = AppTest.from_file(str(Path(__file__).resolve().parent.parent / "app.py"), default_timeout=60).run()
    at.sidebar.radio[0].set_value("Scan prescription").run()
    at.text_area[0].set_value("1. Tab. Metformin 500 mg  1-0-1 after food\n2. Tab. Amlodipine 5 mg once daily morning").run()
    next(b for b in at.button if b.label == "Find medicines in this text").click().run()
    before = count()
    save = next(b for b in at.button if b.label == "Save the selected medicines")
    assert save.disabled and count() == before                                   # disabled until confirmed
    next(c for c in at.checkbox if c.label.startswith("I have checked")).check().run()
    next(b for b in at.button if b.label == "Save the selected medicines").click().run()
    assert count() == before + 2


# ---- profile and personalization ------------------------------------------------------------------------------
def test_demo_person_is_lekshmi(env):
    assert env[1]["name"] == "Lekshmi"


def test_profile_validation_and_update(env):
    db, elder, cg = env
    with pytest.raises(ms.ValidationError):
        ps.update_person(db, elder["id"], "  ", 70, "1")
    with pytest.raises(ms.ValidationError):
        ps.update_person(db, elder["id"], "A", 0, "1")
    ps.update_person(db, elder["id"], "Lekshmi Devi", 72, "+91 90000 11111")
    assert get_person(db, "elder")["name"] == "Lekshmi Devi"
    ps.update_person(db, cg["id"], "Arun", 40, "+91 90000 22222", "Brother")
    assert get_person(db, "caregiver")["relationship"] == "Brother"


def test_preferences_roundtrip_and_validation(env):
    db, elder, _ = env
    ps.save_preferences(db, "Lekshmi Amma", "gardening, music", "06:30", "21:30")
    prefs = ps.get_preferences(db)
    assert prefs["interests"] == "gardening, music" and ps.display_name(elder, prefs) == "Lekshmi Amma"
    with pytest.raises(ms.ValidationError):
        ps.save_preferences(db, "x", "", "7am", "")


def test_preferences_personalise_replies_and_gemini_context(env):
    db, elder, cg = env
    ps.save_preferences(db, "Lekshmi Amma", "gardening", "06:30", "21:30")
    p = FakeProvider(["Gardens are lovely in the evening."])
    m = AIManager(db, p, Limits(min_interval_s=0))
    m.set_enabled(True)
    assert "Lekshmi Amma" in answer(db, elder, cg, "hello", m).text
    answer(db, elder, cg, "tell me a story", m)
    sent = p.requests[0].user
    assert "gardening" in sent and "Lekshmi Amma" in sent and "Metformin" not in sent


def test_ocr_digit_confusions_in_dose_patterns_are_repaired():
    assert de.fix_dose_digits("Tab. Metformin 500 mg 1-0-l after food") == "Tab. Metformin 500 mg 1-0-1 after food"
    assert de.fix_dose_digits("l-O-l") == "1-0-1"
    assert de.fix_dose_digits("Hello-world") == "Hello-world"          # ordinary words are left alone
    assert de.parse_medications("1. Tab. Metformin 500 mg 1-0-l after food")[0].schedule_text == "1-0-1 after food"
