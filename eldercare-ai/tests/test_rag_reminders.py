from datetime import datetime
from pathlib import Path

import pytest
from streamlit.testing.v1 import AppTest

from src.ai import rag
from src.ai.assistant import answer
from src.ai.data.eval_sets import OUT_OF_KB, RAG_EVAL, REMINDER_EVAL
from src.ai.manager import AIManager, Limits
from src.ai.reminder_nlu import parse_reminder
from src.database.queries import get_person
from src.database.schema import init_db
from src.database.seed import reset_demo_data
from src.services import reminder_service as rs
from src.services.medication_service import ValidationError
from tests.fakes import FakeProvider

NOON = datetime(2030, 6, 15, 12, 0)


@pytest.fixture
def env(tmp_path):
    db = tmp_path / "t.db"
    init_db(db)
    reset_demo_data(db)
    return db, get_person(db, "elder"), get_person(db, "caregiver")


def ask(env, text, provider=None, enabled=False):
    db, elder, cg = env
    m = AIManager(db, provider, Limits(min_interval_s=0))
    if enabled:
        m.set_enabled(True)
    return answer(db, elder, cg, text, m, NOON)


# ---- retrieval ------------------------------------------------------------------------------------------
def test_retrieval_quality_on_evaluation_questions():
    hit1 = sum(bool(p := rag.retrieve(q)) and p[0].doc_id == d for q, d in RAG_EVAL) / len(RAG_EVAL)
    hit3 = sum(d in [x.doc_id for x in rag.retrieve(q)] for q, d in RAG_EVAL) / len(RAG_EVAL)
    assert hit1 >= 0.75 and hit3 >= 0.85


def test_most_off_topic_questions_retrieve_nothing():
    assert sum(not rag.retrieve(q) for q in OUT_OF_KB) >= 4


def test_knowledge_answer_without_ai_shows_passages_and_sources(env):
    r = ask(env, "how can i prevent falls at home")
    assert r.source == "knowledge" and "Fall prevention at home" in r.sources and "lighting" in r.text.lower()
    assert r.trace["retrieved"]


def test_gemini_rag_answer_is_cited_and_labelled(env):
    p = FakeProvider(["Keep walkways clear and use good lighting [1]."])
    r = ask(env, "how can i prevent falls at home", p, enabled=True)
    assert r.source == "gemini" and r.sources and "[1]" not in r.text
    assert "Passages:" in p.requests[0].user and "Question:" in p.requests[0].user   # grounded prompt


def test_uncited_gemini_answer_is_rejected(env):
    r = ask(env, "how can i prevent falls at home", FakeProvider(["Just be careful."]), enabled=True)
    assert r.source == "knowledge" and "cite" in (r.notice or "")


def test_unsafe_gemini_rag_answer_is_rejected(env):
    r = ask(env, "how can i prevent falls at home", FakeProvider(["Take 500 mg daily [1]."]), enabled=True)
    assert r.source == "knowledge"


def test_citation_validation():
    assert rag.valid_citations("yes [1] and [2]", 3) and not rag.valid_citations("none", 3) and not rag.valid_citations("[5]", 3)


# ---- reminders ------------------------------------------------------------------------------------------
@pytest.mark.parametrize("text,task,time,problem", REMINDER_EVAL)
def test_reminder_extraction(text, task, time, problem):
    d = parse_reminder(text)
    assert (d.task, d.time, d.problem) == (task, time, problem)


def test_reminder_reply_asks_for_confirmation_and_saves_nothing(env):
    db, elder, _ = env
    r = ask(env, "remind me to drink water at 5 pm")
    assert r.action == {"type": "confirm_reminder", "task": "Drink water", "time": "17:00"}
    assert rs.list_reminders(db, elder["id"]) == []


def test_medicine_and_unclear_reminders_are_not_saved(env):
    assert "Medications page" in ask(env, "remind me to take my tablets at 8 pm").text
    amb = ask(env, "remind me to take a walk at 4")
    assert amb.action is None and "am or pm" in amb.text


def test_reminder_service_validation(env):
    db, elder, _ = env
    with pytest.raises(ValidationError):
        rs.add_reminder(db, elder["id"], "", "10:00")
    with pytest.raises(ValidationError):
        rs.add_reminder(db, elder["id"], "x", "25:99")
    rid = rs.add_reminder(db, elder["id"], "Walk", "17:00")
    assert rs.list_reminders(db, elder["id"], NOON)[0]["status"] == "upcoming"
    rs.delete_reminder(db, rid)
    assert rs.list_reminders(db, elder["id"]) == []


def test_reminder_saved_only_after_clicking_yes(tmp_path, monkeypatch):
    import sqlite3
    db = tmp_path / "ui.db"
    monkeypatch.setenv("DB_PATH", str(db))
    at = AppTest.from_file(str(Path(__file__).resolve().parent.parent / "app.py"), default_timeout=60).run()
    at.sidebar.radio[0].set_value("Care Companion").run()
    at.chat_input[0].set_value("remind me to drink water at 5 pm").run()
    count = lambda: sqlite3.connect(db).execute("SELECT COUNT(*) FROM reminders").fetchone()[0]
    assert count() == 0
    next(b for b in at.button if b.label == "No, do not save").click().run()
    assert count() == 0
    at.chat_input[0].set_value("remind me to drink water at 5 pm").run()
    next(b for b in at.button if b.label == "Yes, save the reminder").click().run()
    assert count() == 1
