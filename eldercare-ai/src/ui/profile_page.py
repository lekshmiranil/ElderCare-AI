"""Profile, caregiver details, personal preferences and reminders. The sidebar and chat use these straight away."""
from datetime import datetime

import streamlit as st

from src.services import profile_service as ps
from src.services import reminder_service as rs
from src.services.medication_service import ValidationError


def _t(hhmm):
    return datetime.strptime(hhmm, "%H:%M").time() if hhmm else None


def render(db_path, elder, caregiver) -> None:
    st.title("My profile")
    if msg := st.session_state.pop("flash_ok", None):
        st.success(msg)

    with st.container(key="card_profile_edit"):
        st.subheader("About me")
        with st.form("edit_elder"):
            name = st.text_input("My name", value=elder["name"])
            age = st.number_input("My age", 1, 120, int(elder["age"] or 70))
            phone = st.text_input("My phone number", value=elder["phone"] or "")
            if st.form_submit_button("Save my details"):
                try:
                    ps.update_person(db_path, elder["id"], name, int(age), phone)
                    st.session_state["flash_ok"] = "Your details are saved."
                    st.rerun()
                except ValidationError as e:
                    st.error(str(e))

    with st.container(key="card_cg_edit"):
        st.subheader("My caregiver")
        with st.form("edit_caregiver"):
            cname = st.text_input("Caregiver name", value=caregiver["name"])
            rel = st.text_input("Relationship", value=caregiver["relationship"] or "")
            cphone = st.text_input("Caregiver phone number", value=caregiver["phone"] or "")
            if st.form_submit_button("Save caregiver details"):
                try:
                    ps.update_person(db_path, caregiver["id"], cname, caregiver["age"], cphone, rel)
                    st.session_state["flash_ok"] = "Caregiver details are saved."
                    st.rerun()
                except ValidationError as e:
                    st.error(str(e))

    prefs = ps.get_preferences(db_path)
    with st.container(key="card_prefs"):
        st.subheader("My preferences")
        st.caption("The companion uses these to be more personal. If Gemini is switched on, your name, interests "
                   "and usual times are included in open-chat messages sent to it. Medicines are never included.")
        with st.form("prefs"):
            pn = st.text_input("What should I call you?", value=prefs["preferred_name"])
            interests = st.text_input("Things I enjoy (for example gardening, music)", value=prefs["interests"])
            wake = st.time_input("I usually wake up at", value=_t(prefs["wake_time"]) or _t("07:00"), step=900)
            bed = st.time_input("I usually go to bed at", value=_t(prefs["bedtime"]) or _t("22:00"), step=900)
            if st.form_submit_button("Save preferences"):
                try:
                    ps.save_preferences(db_path, pn, interests, wake.strftime("%H:%M"), bed.strftime("%H:%M"))
                    st.session_state["flash_ok"] = "Preferences saved."
                    st.rerun()
                except ValidationError as e:
                    st.error(str(e))

    st.subheader("My reminders")
    reminders = rs.list_reminders(db_path, elder["id"])
    if not reminders:
        st.write("No reminders yet. Ask the Care Companion, for example: remind me to drink water at 5 pm.")
    for r in reminders:
        c1, c2 = st.columns([4, 1])
        c1.write(f"**{r['remind_time']}**  {r['task']}  (every day)")
        c2.button("Delete", key=f"delrem{r['id']}", on_click=rs.delete_reminder, args=(db_path, r["id"]))
