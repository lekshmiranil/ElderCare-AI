"""Fall detection demonstration on simulated sensor data."""
import time

import pandas as pd
import streamlit as st

from src.safety.sensor_sim import SCENARIOS, T, simulate
from src.services import caregiver_service as cs
from src.services import fall_service as fs
from src.services.medication_service import ValidationError


def render(db_path, elder) -> None:
    st.title("Fall detection (simulation)")
    st.info("This page uses simulated sensor data to show how detection could work. It is not connected to any "
            "real device, and no real-world accuracy is claimed.")
    threshold = st.slider("Impact threshold (g)", fs.MIN_T, fs.MAX_T, fs.get_threshold(db_path), 0.1,
                          help="A fall is flagged when the peak reaches this value and the person then stays almost still.")
    if threshold != fs.get_threshold(db_path):
        try:
            fs.set_threshold(db_path, threshold)
        except ValidationError as e:
            st.error(str(e))
    scenario = st.selectbox("Simulated activity", list(SCENARIOS), format_func=SCENARIOS.get, index=len(SCENARIOS) - 1)
    if st.button("Run simulation"):
        window = simulate(scenario, int(time.time() * 1000) % 100000)
        result = fs.assess(window, threshold)
        fs.record_event(db_path, elder["id"], result, scenario)
        st.session_state["fall_last"] = (scenario, window, result)

    if last := st.session_state.get("fall_last"):
        scenario, window, r = last
        st.line_chart(pd.DataFrame({"Acceleration (g)": window, "Threshold (g)": r["threshold_g"]}, index=T.round(2)),
                      color=["#0E7C86", "#B3261E"])
        c = st.columns(3)
        c[0].metric("Peak", f"{r['peak_g']:.2f} g")
        c[1].metric("Rule: impact + stillness", "Triggered" if r["triggered"] else "Not triggered")
        c[2].metric("ML unusual-movement score", f"{r['ml_score']:.2f}", "flagged" if r["ml_unusual"] else "normal range",
                    delta_color="inverse" if r["ml_unusual"] else "off")
        if r["outcome"] == "fall":
            st.error("Simulated fall detected. A caregiver notification was recorded. In demo mode nothing was sent.")
        elif r["outcome"] == "unusual":
            st.warning("Unusual movement detected, but it does not match the fall rule. Recorded, and the caregiver "
                       "notification is simulated.")
        else:
            st.success("Normal movement. Nothing recorded.")

    with st.expander("How this works, and how a real wearable could connect"):
        st.markdown(
            "- **Rule (deterministic):** peak acceleration at or above the threshold, followed by about 1.5 seconds of stillness.\n"
            "- **ML (local):** an Isolation Forest trained only on simulated normal movement flags windows that look unusual. "
            "It does not know what a fall is, so it reports unusual movement.\n"
            "- **Real device:** a wearable's accelerometer would stream readings over Bluetooth to a phone app, which would "
            "send windows to this logic (or run it on the device). Real use needs validation on real people, tuning for "
            "false alarms, battery and connection handling, and a real notification channel.\n"
            "- **Not claimed:** any real-world detection accuracy. The data here is synthetic.")

    st.subheader("Event history")
    events = cs.list_fall_events(db_path, elder["id"])
    if events:
        st.dataframe(pd.DataFrame([{"When": e["detected_at"].replace("T", " "),
                                    "Type": "Fall" if e.get("kind", "fall") == "fall" else "Unusual movement",
                                    "Peak (g)": round(e["peak_g"], 2), "Threshold (g)": e["threshold_g"],
                                    "Source": "Simulated"} for e in events]), hide_index=True, width="stretch")
    else:
        st.write("No events yet.")
