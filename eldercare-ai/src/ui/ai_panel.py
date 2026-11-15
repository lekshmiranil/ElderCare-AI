"""Sidebar AI status, manual switch and usage indicator. Rendering this never calls an API."""
import streamlit as st

from src.ai.manager import AIManager
from src.ui.theme import badge

KINDS = {"local": "ai-off", "off": "ai-off", "ready": "ai-on", "paused": "attention", "limit": "attention"}


def _flip(manager: AIManager) -> None:
    manager.set_enabled(bool(st.session_state.get("ai_toggle")))


def render(manager: AIManager) -> None:
    status = manager.status()
    st.markdown(badge(status.label, KINDS[status.state]), unsafe_allow_html=True)
    if manager.configured:
        st.session_state["ai_toggle"] = manager.is_enabled()
        st.toggle("Use Gemini AI for open chat", key="ai_toggle", on_change=_flip, args=(manager,))
        st.caption(f"Gemini calls today: {status.used_today} of {status.daily_limit}")
        if manager.is_enabled():
            st.caption("Open-ended messages are sent to Google Gemini. Medicine, appointment, safety and "
                       "emergency messages never are.")
        if status.state in ("paused", "limit"):
            st.caption(status.detail)
            if status.state == "paused":
                st.button("Retry Gemini now", on_click=manager.clear_pause)
    else:
        st.caption("Local ML mode. To add Gemini, set AI_PROVIDER=gemini and GEMINI_API_KEY in .env. "
                   "Everything works without it.")
