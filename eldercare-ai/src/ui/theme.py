"""Shared styling: calm blue/teal healthcare look with large, high-contrast text."""
import streamlit as st

CSS = """
<style>
html, body, [class*="css"] { font-size: 19px; }
h1 { color:#0B3C5D; font-weight:700; }
h2, h3 { color:#0B3C5D; }
/* Cards: containers created with key="card_..." */
[class*="st-key-card"] { background:#FFFFFF; border:1px solid #D5E2EA; border-radius:14px;
    padding:1.1rem 1.3rem; box-shadow:0 1px 3px rgba(11,60,93,.06); }
.ec-badge { display:inline-block; padding:.25rem .8rem; border-radius:999px;
            font-size:.85rem; font-weight:600; }
.ec-demo { background:#FFF3CD; color:#7A5B00; border:1px solid #F0D98C; }
.ec-ai-off { background:#E3EEF4; color:#0B3C5D; }
.ec-ai-on { background:#D8F3EE; color:#0A5C55; }
.ec-taken { background:#D8F3EE; color:#0A5C55; }
.ec-skipped { background:#E3EEF4; color:#0B3C5D; }
.ec-missed, .ec-overdue { background:#FDE2E2; color:#8A1C1C; }
.ec-attention { background:#FDE2E2; color:#8A1C1C; }
.ec-ok { background:#D8F3EE; color:#0A5C55; }
.ec-upcoming { background:#EEF2F5; color:#3A4F63; }
.st-key-emergency_open button { background:#B3261E; color:#FFFFFF; border:3px solid #7A130E; min-height:5.5rem;
    font-size:1.7rem; font-weight:700; border-radius:16px; }
.st-key-emergency_open button:hover { background:#8F1D17; color:#FFFFFF; }
.stButton > button { min-height:3rem; font-size:1.05rem; border-radius:10px; }
.stButton > button:focus-visible { outline:3px solid #0E7C86; outline-offset:2px; }
</style>
"""

STATUS_LABELS = {"taken": "Taken", "skipped": "Skipped", "missed": "Missed",
                 "overdue": "Overdue", "upcoming": "Upcoming"}


def apply_theme() -> None:
    st.markdown(CSS, unsafe_allow_html=True)


def badge(text: str, kind: str) -> str:
    return f'<span class="ec-badge ec-{kind}">{text}</span>'


def status_badge(status: str) -> str:
    return badge(STATUS_LABELS.get(status, status), status)
