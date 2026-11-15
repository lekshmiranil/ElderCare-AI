from pathlib import Path

from src.ai.local_responder import has_emergency, has_medical_advice, has_self_harm


def test_rule_vocabulary_basics():
    assert has_emergency("I have chest pain") and has_emergency("i passed out")
    assert has_self_harm("i want to die") and has_medical_advice("what dose should i take")
    assert not has_emergency("what medicines do i take today")
    # "should i take my medicine now" is a schedule question, not a dose question
    assert not has_medical_advice("which tablets should i take today")


def test_voice_and_local_code_makes_no_network_calls():
    """Quota protection: voice, rules and local ML code must not reach any API."""
    banned = ["fetch(", "XMLHttpRequest", "WebSocket", "generativelanguage", "requests.", "urllib",
              "http://", "https://", "import requests"]
    root = Path(__file__).resolve().parent.parent
    voice = [root / "src/voice/frontend/index.html", root / "src/voice/component.py"]
    local = [root / "src/ai/local_responder.py", root / "src/ai/classifiers.py"]
    for f in voice + local:
        text = f.read_text().lower()
        for b in banned:
            assert b.lower() not in text, f"{b} found in {f.name}"
    for f in voice:                                   # voice code must not even mention Gemini
        assert "gemini" not in f.read_text().lower(), f.name
