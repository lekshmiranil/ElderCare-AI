"""Quota protection: visiting pages, with Gemini configured and switched ON, must never make an HTTP call."""
from pathlib import Path

import requests
from streamlit.testing.v1 import AppTest

from src.ai.manager import AIManager
from src.ai.providers.gemini import GeminiProvider


def test_rendering_every_page_makes_no_http_request(tmp_path, monkeypatch):
    db = tmp_path / "load.db"
    monkeypatch.setenv("DB_PATH", str(db))
    monkeypatch.setenv("AI_PROVIDER", "gemini")
    monkeypatch.setenv("GEMINI_API_KEY", "test-key-not-real")
    posts = []
    monkeypatch.setattr(requests, "post", lambda *a, **k: posts.append(1) or (_ for _ in ()).throw(AssertionError("network call")))

    at = AppTest.from_file(str(Path(__file__).resolve().parent.parent / "app.py"), default_timeout=60).run()
    AIManager(db, GeminiProvider("test-key-not-real", "m")).set_enabled(True)   # switch ON in the database
    at.run()
    for page in ["Elderly dashboard", "Medications", "Daily check-in", "Care Companion", "Caregiver dashboard"]:
        at.sidebar.radio[0].set_value(page).run()
        assert not at.exception, page
    # data and safety questions must not call the API even with the switch on
    at.sidebar.radio[0].set_value("Care Companion").run()
    for q in ["what medicines do i take today", "i have chest pain", "what dose should i take"]:
        at.chat_input[0].set_value(q).run()
        assert not at.exception
    assert posts == []


def test_secret_never_appears_in_settings_repr(monkeypatch):
    from config.settings import load_settings
    monkeypatch.setenv("GEMINI_API_KEY", "TOPSECRET")
    assert "TOPSECRET" not in repr(load_settings())


def test_only_the_gemini_provider_touches_the_network():
    from pathlib import Path
    root = Path(__file__).resolve().parent.parent / "src"
    offenders = [str(f.relative_to(root)) for f in root.rglob("*.py")
                 if f.name != "gemini.py" and ("generativelanguage" in f.read_text().lower() or "import requests" in f.read_text())]
    assert offenders == []
