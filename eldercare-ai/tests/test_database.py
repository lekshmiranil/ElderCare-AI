import sqlite3

import pytest

from config.settings import load_settings
from src.database.queries import count_rows, get_person
from src.database.schema import TABLES, init_db
from src.database.seed import reset_demo_data


@pytest.fixture
def db(tmp_path):
    path = tmp_path / "test.db"
    init_db(path)
    return path


def test_init_creates_all_tables(db):
    conn = sqlite3.connect(db)
    names = {r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}
    assert set(TABLES) <= names


def test_seed_is_repeatable(db):
    reset_demo_data(db)
    reset_demo_data(db)  # resetting twice must not duplicate rows
    assert count_rows(db, "people") == 2
    assert count_rows(db, "medications") == 4
    assert get_person(db, "elder")["role"] == "elder"


def test_invalid_status_rejected(db):
    reset_demo_data(db)
    conn = sqlite3.connect(db)
    with pytest.raises(sqlite3.IntegrityError):
        conn.execute("INSERT INTO medication_logs (medication_id,log_date,status,logged_at) "
                     "VALUES (1,'2030-01-01','invalid','x')")


def test_count_rows_rejects_unknown_table(db):
    with pytest.raises(ValueError):
        count_rows(db, "people; DROP TABLE people")


def test_settings_default_to_safe_values(monkeypatch):
    for k in ("AI_PROVIDER", "GEMINI_API_KEY", "DEMO_MODE"):
        monkeypatch.delenv(k, raising=False)
    s = load_settings()
    assert s.demo_mode is True and s.ai_provider == "local" and not s.has_gemini_key


def test_settings_repr_hides_key(monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "SECRET123")
    assert "SECRET123" not in repr(load_settings())
