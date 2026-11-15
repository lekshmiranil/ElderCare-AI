from datetime import datetime, timedelta

import pytest

from src.ai.manager import AIManager, Limits
from src.ai.wellness_insights import analyze_patterns
from src.database.queries import get_person
from src.database.schema import init_db
from src.database.seed import reset_demo_data
from src.services import summary_service as sm
from tests.fakes import FakeProvider

NOW = datetime(2030, 6, 15, 12, 0)


def series(moods, wells=None, acts=None):
    wells, acts = wells or moods, acts or moods
    return [{"checkin_date": (NOW.date() - timedelta(days=len(moods) - 1 - i)).isoformat(),
             "mood": m, "wellbeing": w, "activity": a} for i, (m, w, a) in enumerate(zip(moods, wells, acts))]


def test_needs_enough_data():
    assert analyze_patterns(series([3, 3, 3, 3])) == []


def test_steady_scores_produce_no_findings():
    assert analyze_patterns(series([4, 4, 3, 4, 4, 4, 3, 4])) == []


def test_downward_trend_found_with_evidence():
    f = analyze_patterns(series([5, 5, 4, 4, 3, 3, 2, 2]))
    trend = [x for x in f if x.kind == "trend" and x.metric == "mood"][0]
    assert "downward" in trend.text and trend.evidence["slope_per_week"] < -0.5 and trend.evidence["r2"] >= 0.3


def test_association_is_not_called_causal():
    f = analyze_patterns(series([2, 3, 4, 2, 4, 3, 5, 2], acts=[2, 3, 4, 2, 4, 3, 5, 2]))
    assoc = [x for x in f if x.kind == "association"]
    assert assoc and "not proof of cause" in assoc[0].text


@pytest.fixture
def env(tmp_path):
    db = tmp_path / "t.db"
    init_db(db)
    reset_demo_data(db)
    return db, get_person(db, "elder")


def mgr(db, provider):
    m = AIManager(db, provider, Limits(min_interval_s=0))
    m.set_enabled(True)
    return m


def test_facts_contain_counts_not_identities(env):
    import json
    db, elder = env
    facts = sm.collect_facts(db, elder, datetime.now())
    blob = json.dumps(facts)
    assert facts["period_days"] == 7 and facts["taken"] + facts["missed"] + facts["skipped"] == facts["medicine_entries_recorded"]
    for secret in ("Lekshmi", "Metformin", "+91", "Daniel"):
        assert secret not in blob


def test_local_summary_uses_only_the_facts(env):
    db, elder = env
    facts = sm.collect_facts(db, elder, datetime.now())
    assert sm.numbers_supported(sm.local_summary(facts, "Lekshmi"), facts)


def test_faithful_gemini_summary_is_accepted_and_private(env):
    db, elder = env
    facts = sm.collect_facts(db, elder, datetime.now())
    ok = f"Over the last 7 days, {facts['taken']} entries were marked taken and {facts['missed']} missed."
    p = FakeProvider([ok])
    text, source, notice = sm.gemini_summary(mgr(db, p), facts, "Lekshmi", datetime.now())
    assert source == "gemini" and text == ok and notice is None
    sent = p.requests[0].system + p.requests[0].user
    assert "Lekshmi" not in sent and "Metformin" not in sent


def test_invented_numbers_are_rejected(env):
    db, elder = env
    facts = sm.collect_facts(db, elder, datetime.now())
    text, source, notice = sm.gemini_summary(mgr(db, FakeProvider(["She took 99 medicines and had 42 falls."])), facts, "Lekshmi")
    assert source == "local" and "not in your data" in notice and "99" not in text


def test_summary_falls_back_when_gemini_is_off(env):
    db, elder = env
    facts = sm.collect_facts(db, elder, datetime.now())
    p = FakeProvider()
    off = AIManager(db, p)   # switch left off
    assert sm.gemini_summary(off, facts, "Lekshmi")[1] == "local" and p.calls == 0
