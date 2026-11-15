"""ElderCare AI: entry point. Sets up config, database and navigation; pages live in src/ui."""
import streamlit as st

from config.settings import load_settings
from src.ai.factory import build_manager
from src.database.queries import count_rows, get_person
from src.database.schema import init_db
from src.database.seed import reset_demo_data
from src.notifications.channel import SimulatedChannel
from src.ui import (ai_panel, caregiver_dashboard, checkin_page, companion_page, elderly_dashboard, emergency_panel,
                    fall_page, medication_page, profile_page, scan_page)
from src.ui.theme import apply_theme, badge
from src.utils.logger import get_logger

st.set_page_config(page_title="ElderCare AI", page_icon="🩺", layout="wide")
apply_theme()

settings = load_settings()
log = get_logger("eldercare", settings.log_level)


@st.cache_resource
def bootstrap(db_path: str) -> bool:
    """Create or upgrade tables once per server run; seed demo data only if the database is empty."""
    init_db(db_path)
    if count_rows(db_path, "people") == 0:
        reset_demo_data(db_path)
    return True


bootstrap(str(settings.db_path))
manager = build_manager(settings)   # builds objects only; makes no API call
channel = SimulatedChannel()        # no real alert channel exists, so nothing is ever really sent

PAGES = ["Elderly dashboard", "Care Companion", "Medications", "Scan prescription", "Daily check-in",
         "Emergency help", "My profile", "Caregiver dashboard", "Fall detection (simulation)"]

with st.sidebar:
    st.header("ElderCare AI")
    view = st.radio("Menu", PAGES, label_visibility="collapsed")
    st.markdown(badge("DEMO MODE", "demo") if settings.demo_mode else "", unsafe_allow_html=True)
    ai_panel.render(manager)
    st.caption("Sample data is fictional. Nothing is sent to anyone in demo mode.")
    with st.expander("Demo data"):
        st.caption("Resetting replaces all data, including your edits, with the sample data.")
        if st.button("Reset demo data"):
            reset_demo_data(settings.db_path)
            st.session_state.clear()
            st.rerun()

elder = get_person(settings.db_path, "elder")
caregiver = get_person(settings.db_path, "caregiver")
db = settings.db_path

try:
    if view == "Elderly dashboard":
        elderly_dashboard.render(db, elder, caregiver, channel, settings.demo_mode)
    elif view == "Care Companion":
        companion_page.render(db, elder, caregiver, manager)
    elif view == "Medications":
        medication_page.render(db, elder)
    elif view == "Scan prescription":
        scan_page.render(db, elder)
    elif view == "Daily check-in":
        checkin_page.render(db, elder)
    elif view == "Emergency help":
        emergency_panel.render_page(db, elder, caregiver, channel, settings.demo_mode)
    elif view == "My profile":
        profile_page.render(db, elder, caregiver)
    elif view == "Caregiver dashboard":
        caregiver_dashboard.render(db, elder, caregiver, manager)
    else:
        fall_page.render(db, elder)
except Exception as exc:   # never show a stack trace to an older user; log only the error type, never personal data
    log.error("Page %r failed: %s", view, type(exc).__name__)
    st.error("Sorry, something went wrong on this page. Please try again, or choose another page from the menu.")
