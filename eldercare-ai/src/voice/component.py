"""Bridge to the browser's speech features (see frontend/index.html).

Streamlit custom component with no build step. It returns {"id", "text"} when the
person finishes speaking, and speaks text aloud when asked. All speech work happens
in the browser; nothing here calls an AI service or any other API.
"""
from pathlib import Path

import streamlit.components.v1 as components

_voice = components.declare_component("eldercare_voice", path=str(Path(__file__).parent / "frontend"))


def voice_widget(last_text: str, speak, auto_speak: bool, key: str = "voice"):
    """Render the speak/listen buttons. Returns the newest spoken message or None."""
    return _voice(last_text=last_text, speak=speak, auto_speak=auto_speak, key=key, default=None)
