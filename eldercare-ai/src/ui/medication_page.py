"""Medication management: add, edit, delete, and view history."""
from datetime import datetime

import pandas as pd
import streamlit as st

from src.services import medication_service as meds
from src.ui.theme import STATUS_LABELS


def _parse_time(hhmm: str):
    return datetime.strptime(hhmm, "%H:%M").time()


def render(db_path, elder) -> None:
    st.title("Medications")
    st.info("Enter each schedule exactly as your doctor prescribed it. This app only stores and "
            "reminds. It never suggests medicines or doses.")

    if msg := st.session_state.pop("flash_ok", None):
        st.success(msg)

    with st.container(key="card_add"):
        st.subheader("Add a medicine")
        with st.form("add_med", clear_on_submit=True):
            name = st.text_input("Medicine name")
            schedule = st.text_input("Prescribed schedule", placeholder="e.g. Once daily, after breakfast")
            t = st.time_input("Reminder time", value=_parse_time("08:00"), step=300)
            if st.form_submit_button("Add medicine"):
                try:
                    meds.add_medication(db_path, elder["id"], name, schedule, t.strftime("%H:%M"))
                    st.session_state["flash_ok"] = "Medicine added."
                    st.rerun()
                except meds.ValidationError as e:
                    st.error(str(e))

    st.subheader("Your medicines")
    current = meds.list_medications(db_path, elder["id"])
    if not current:
        st.write("No medicines yet.")
    for m in current:
        with st.expander(f"{m['reminder_time']}  {m['name']}"):
            with st.form(f"edit_{m['id']}"):
                n = st.text_input("Medicine name", value=m["name"], key=f"n{m['id']}")
                s = st.text_input("Prescribed schedule", value=m["schedule_text"], key=f"s{m['id']}")
                tt = st.time_input("Reminder time", value=_parse_time(m["reminder_time"]),
                                   step=300, key=f"t{m['id']}")
                if st.form_submit_button("Save changes"):
                    try:
                        meds.update_medication(db_path, m["id"], n, s, tt.strftime("%H:%M"))
                        st.session_state["flash_ok"] = "Changes saved."
                        st.rerun()
                    except meds.ValidationError as e:
                        st.error(str(e))
            confirm = st.checkbox("I want to delete this medicine and its history", key=f"c{m['id']}")
            if st.button("Delete medicine", key=f"d{m['id']}", disabled=not confirm):
                meds.delete_medication(db_path, m["id"])
                st.session_state["flash_ok"] = "Medicine deleted."
                st.rerun()

    st.subheader("Last 7 days")
    rows = meds.history(db_path, elder["id"], days=7)
    if rows:
        df = pd.DataFrame(rows)
        df["status"] = df["status"].map(lambda s: STATUS_LABELS.get(s, s))
        df.columns = ["Date", "Medicine", "Time", "Status"]
        st.dataframe(df, hide_index=True, width="stretch")
    else:
        st.write("Nothing recorded yet.")
