from datetime import datetime, timedelta

import pytest

from src.ai.manager import AIManager, Limits
from src.ai.providers.base import AIRequest
from src.database.schema import init_db
from src.database.seed import reset_demo_data
from tests.fakes import FakeProvider

T0 = datetime(2030, 6, 15, 12, 0, 0)


def req(text="tell me a story"):
    return AIRequest("companion_chat", "sys", text)


@pytest.fixture
def db(tmp_path):
    path = tmp_path / "t.db"
    init_db(path)
    reset_demo_data(path)
    return path


def mgr(db, provider, **limits):
    base = dict(daily_limit=20, min_interval_s=0, cache_ttl_h=24, quota_cooldown_min=30)
    base.update(limits)
    return AIManager(db, provider, Limits(**base))


def test_switch_is_off_by_default_and_blocks_calls(db):
    p = FakeProvider()
    m = mgr(db, p)
    out = m.complete(req(), T0)
    assert out.source == "local" and out.text is None and p.calls == 0
    assert m.status(T0).state == "off"


def test_cannot_enable_without_provider(db):
    m = mgr(db, None)
    m.set_enabled(True)
    assert not m.is_enabled() and m.status(T0).state == "local"
    assert m.complete(req(), T0).source == "local"


def test_success_then_cache(db):
    p = FakeProvider(["Story one"])
    m = mgr(db, p)
    m.set_enabled(True)
    a = m.complete(req("Tell me a   STORY"), T0)
    b = m.complete(req("tell me a story"), T0 + timedelta(minutes=1))      # same after normalising
    assert (a.source, a.text) == ("gemini", "Story one")
    assert (b.source, b.text) == ("gemini_cache", "Story one") and p.calls == 1
    assert m.status(T0).used_today == 1                                     # cache hits do not count


def test_cache_expires(db):
    p = FakeProvider(["A", "B"])
    m = mgr(db, p, cache_ttl_h=1)
    m.set_enabled(True)
    m.complete(req(), T0)
    out = m.complete(req(), T0 + timedelta(hours=2))
    assert out.source == "gemini" and out.text == "B" and p.calls == 2


def test_quota_error_pauses_and_never_retries(db):
    p = FakeProvider(error_kind="quota")
    m = mgr(db, p)
    m.set_enabled(True)
    first = m.complete(req("one"), T0)
    assert first.source == "local" and "limit" in first.notice.lower() and p.calls == 1
    for i in range(5):                                                      # many more questions, no more calls
        assert m.complete(req(f"other question {i}"), T0 + timedelta(minutes=5)).source == "local"
    assert p.calls == 1
    assert m.status(T0 + timedelta(minutes=5)).state == "paused"
    assert m.status(T0 + timedelta(minutes=31)).state == "ready"            # pause expires by itself, but...
    p.error_kind = None
    assert m.complete(req("later"), T0 + timedelta(minutes=31)).source == "gemini"


def test_manual_retry_clears_pause(db):
    p = FakeProvider(error_kind="quota")
    m = mgr(db, p)
    m.set_enabled(True)
    m.complete(req(), T0)
    m.clear_pause()
    p.error_kind = None
    assert m.complete(req("again"), T0 + timedelta(minutes=1)).source == "gemini"


@pytest.mark.parametrize("kind", ["auth", "model_not_found"])
def test_config_errors_pause_for_a_day(db, kind):
    p = FakeProvider(error_kind=kind)
    m = mgr(db, p)
    m.set_enabled(True)
    m.complete(req(), T0)
    assert m.status(T0 + timedelta(hours=23)).state == "paused"


def test_blocked_prompt_does_not_pause(db):
    p = FakeProvider(error_kind="blocked")
    m = mgr(db, p)
    m.set_enabled(True)
    assert m.complete(req("x"), T0).source == "local"
    assert m.status(T0).state == "ready"


def test_daily_limit(db):
    p = FakeProvider()
    m = mgr(db, p, daily_limit=2)
    m.set_enabled(True)
    outs = [m.complete(req(f"q{i}"), T0 + timedelta(minutes=i)).source for i in range(4)]
    assert outs == ["gemini", "gemini", "local", "local"] and p.calls == 2
    assert m.status(T0 + timedelta(minutes=5)).state == "limit"
    assert m.complete(req("q9"), T0 + timedelta(days=1)).source == "gemini"   # resets next day


def test_minimum_spacing(db):
    p = FakeProvider()
    m = mgr(db, p, min_interval_s=5)
    m.set_enabled(True)
    assert m.complete(req("a"), T0).source == "gemini"
    assert m.complete(req("b"), T0 + timedelta(seconds=2)).source == "local"
    assert m.complete(req("c"), T0 + timedelta(seconds=6)).source == "gemini"
    assert p.calls == 2


def test_long_input_is_truncated_before_sending(db):
    p = FakeProvider()
    m = mgr(db, p)
    m.set_enabled(True)
    m.complete(req("x" * 5000), T0)
    assert len(p.requests[0].user) == 400


def test_cache_stores_no_question_text(db):
    import sqlite3
    m = mgr(db, FakeProvider())
    m.set_enabled(True)
    m.complete(req("my secret question"), T0)
    dump = " ".join(str(r) for r in sqlite3.connect(db).execute("SELECT * FROM ai_cache"))
    assert "secret" not in dump


def test_app_built_prompts_are_not_truncated_but_chat_is(db):
    p = FakeProvider()
    m = mgr(db, p)
    m.set_enabled(True)
    m.complete(AIRequest("knowledge_rag", "sys", "p" * 3000 + " QUESTION-END", 100, 4000), T0)
    assert p.requests[0].user.endswith("QUESTION-END")
    m.complete(AIRequest("companion_chat", "sys", "x" * 5000), T0 + timedelta(minutes=1))
    assert len(p.requests[1].user) == 400
