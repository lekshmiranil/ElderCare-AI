"""Emergency button with confirmation. The result always states whether anything was actually sent."""
import streamlit as st

from src.services import caregiver_service as cs
from src.services.emergency_service import trigger_emergency


def _ask():
    st.session_state["emergency_confirm"] = True
    st.session_state.pop("emergency_result", None)


def _cancel():
    st.session_state["emergency_confirm"] = False


def _send(db_path, elder, caregiver, channel):
    st.session_state["emergency_result"] = trigger_emergency(db_path, elder, caregiver, channel)
    st.session_state["emergency_confirm"] = False


def render(db_path, elder, caregiver, channel, demo_mode: bool) -> None:
    ss = st.session_state
    if ss.get("emergency_confirm"):
        st.warning(f"Do you want to send an emergency alert to {caregiver['name']}?")
        if demo_mode:
            st.caption("Demo mode: the alert will be recorded and shown to the caregiver dashboard, "
                       "but nothing will actually be sent.")
        c1, c2 = st.columns(2)
        c1.button("Yes, send the alert", key="emergency_yes", on_click=_send, args=(db_path, elder, caregiver, channel),
                  width="stretch")
        c2.button("No, cancel", key="emergency_no", on_click=_cancel, width="stretch")
    else:
        st.button("I need help", key="emergency_open", on_click=_ask, width="stretch")
    result = ss.get("emergency_result")
    if result:
        when = result["time"].strftime("%H:%M")
        (st.success if result["sent"] else st.warning)(
            f"Alert recorded at {when}. {result['note']}." if not result["sent"] else f"Alert sent at {when}.")
        st.error("This app cannot call emergency services. If you are in danger, call 112 now, "
                 f"or call {caregiver['name']} on {caregiver['phone']}.")
        st.button("Dismiss", key="emergency_dismiss", on_click=lambda: ss.pop("emergency_result", None))


def render_page(db_path, elder, caregiver, channel, demo_mode: bool) -> None:
    st.title("Emergency help")
    render(db_path, elder, caregiver, channel, demo_mode)
    with st.container(key="card_contacts"):
        st.subheader("Who to call")
        st.write(f"**Emergency services:** 112  \n**{caregiver['name']}** ({caregiver['relationship']}): {caregiver['phone']}")
    st.subheader("Emergency history")
    events = cs.list_emergency_events(db_path, elder["id"])
    if not events:
        st.write("No emergency alerts recorded.")
    for e in events:
        st.markdown(f"**{e['triggered_at'].replace('T', ' ')}**  {'Sent' if e['alert_sent'] else 'Simulated, nothing was sent'}")
