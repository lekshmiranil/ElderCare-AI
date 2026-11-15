"""Daily wellness check-in for the elderly user."""
from datetime import datetime

import pandas as pd
import streamlit as st

from src.services import wellness_service as ws
from src.services.medication_service import ValidationError

QUESTIONS = {"mood": "How is your mood today?",
             "wellbeing": "How do you feel in general today?",
             "activity": "How active have you been today?"}


def trend_frame(checkins):
    df = pd.DataFrame(checkins)
    df = df.set_index("checkin_date")[list(ws.METRICS)]
    df.columns = [c.capitalize() for c in df.columns]
    return df


def render(db_path, elder) -> None:
    st.title("Daily check-in")
    st.write("Tell us how you are today. This takes less than a minute.")
    if msg := st.session_state.pop("flash_ok", None):
        st.success(msg)

    today = ws.get_today(db_path, elder["id"])
    if today:
        st.info("You already checked in today. You can change your answers below.")

    with st.container(key="card_checkin"):
        with st.form("checkin"):
            values = {}
            for m in ws.METRICS:
                default = (today[m] - 1) if today else 2
                values[m] = st.radio(QUESTIONS[m], range(1, 6), index=default, horizontal=True,
                                     format_func=lambda v, m=m: f"{v}  {ws.SCALES[m][v-1]}", key=f"ci_{m}")
            notes = st.text_area("Anything else you would like to note? (optional)",
                                 value=today["notes"] if today else "", max_chars=500)
            if st.form_submit_button("Save my check-in"):
                try:
                    ws.save_checkin(db_path, elder["id"], values["mood"], values["wellbeing"],
                                    values["activity"], notes)
                    st.session_state["flash_ok"] = "Thank you. Your check-in is saved."
                    st.rerun()
                except ValidationError as e:
                    st.error(str(e))

    st.subheader("Your last two weeks")
    checkins = ws.list_checkins(db_path, elder["id"], 14)
    if len(checkins) >= 2:
        st.line_chart(trend_frame(checkins), color=["#0E7C86", "#0B3C5D", "#E0A030"])
        st.caption("1 is the lowest answer and 5 is the highest. These are your own answers, "
                   "not a medical measurement.")
    else:
        st.write("Your chart appears after two check-ins.")
