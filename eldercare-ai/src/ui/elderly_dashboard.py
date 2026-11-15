"""Elderly dashboard: large, simple, one clear action per item."""
from datetime import datetime

import streamlit as st

from src.database.queries import list_upcoming_appointments
from src.services import medication_service as meds
from src.services import profile_service, reminder_service
from src.services import wellness_service as wellness
from src.ui import emergency_panel
from src.ui.theme import status_badge


def _greeting(now: datetime) -> str:
    return "Good morning" if now.hour < 12 else "Good afternoon" if now.hour < 17 else "Good evening"


def _record(db_path, med_id, status):
    try:
        meds.record_status(db_path, med_id, status)
    except meds.ValidationError as e:
        st.session_state["flash_error"] = str(e)


def render(db_path, elder, caregiver, channel=None, demo_mode=True) -> None:
    now = datetime.now()
    st.title(f"{_greeting(now)}, {profile_service.display_name(elder, profile_service.get_preferences(db_path))}")
    st.caption(now.strftime("%A, %d %B %Y"))

    if err := st.session_state.pop("flash_error", None):
        st.error(err)

    if channel is not None:
        emergency_panel.render(db_path, elder, caregiver, channel, demo_mode)

    schedule = meds.todays_schedule(db_path, elder["id"], now)

    overdue = [m for m in schedule if m["status"] == "overdue"]
    for m in overdue:
        st.warning(f"{m['name']} was due at {m['reminder_time']}. Please check it and tell the app "
                   f"whether you took it or skipped it.")

    left, right = st.columns([3, 2])
    with left:
        with st.container(key="card_meds"):
            st.subheader("Your medicines today")
            if not schedule:
                st.write("No medicines are set up yet. Open **Medications** in the menu to add one.")
            for m in schedule:
                c1, c2 = st.columns([3, 1])
                c1.markdown(f"**{m['reminder_time']}  {m['name']}**")
                c1.caption(m["schedule_text"])
                c2.markdown(status_badge(m["status"]), unsafe_allow_html=True)
                b1, b2, b3 = st.columns(3)
                b1.button("Taken", key=f"t{m['id']}", on_click=_record,
                          args=(db_path, m["id"], "taken"), width="stretch")
                b2.button("Skip", key=f"s{m['id']}", on_click=_record,
                          args=(db_path, m["id"], "skipped"), width="stretch")
                b3.button("Missed", key=f"m{m['id']}", on_click=_record,
                          args=(db_path, m["id"], "missed"), width="stretch")
                st.divider()
    with right:
        with st.container(key="card_profile"):
            st.subheader("About you")
            st.write(f"**{elder['name']}**, age {elder['age']}")
        with st.container(key="card_reminders"):
            st.subheader("My reminders")
            rems = reminder_service.list_reminders(db_path, elder["id"], now)
            if not rems:
                st.write("None yet. Ask the Care Companion to set one.")
            for r in rems:
                st.markdown(f"**{r['remind_time']}**  {r['task']}" + ("  (done for today)" if r["status"] == "past" else ""))
        with st.container(key="card_checkin_status"):
            st.subheader("Today's check-in")
            if wellness.get_today(db_path, elder["id"], now):
                st.write("Done. Thank you.")
            else:
                st.write("Not done yet. Open **Daily check-in** in the menu.")
        with st.container(key="card_caregiver"):
            st.subheader("Your caregiver")
            st.write(f"**{caregiver['name']}** ({caregiver['relationship']})")
            st.write(caregiver["phone"])
        with st.container(key="card_appts"):
            st.subheader("Upcoming appointments")
            appts = list_upcoming_appointments(db_path, elder["id"], now.isoformat(timespec="minutes"))
            if not appts:
                st.write("No appointments coming up.")
            for a in appts:
                when = datetime.fromisoformat(a["appt_datetime"]).strftime("%a %d %b, %H:%M")
                st.markdown(f"**{a['title']}**  \n{when}  \n{a['location'] or ''}")
