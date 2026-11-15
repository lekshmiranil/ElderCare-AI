"""Caregiver dashboard: a separate, read-focused view with clear status indicators."""
from datetime import datetime

import pandas as pd
import streamlit as st

from src.ai.wellness_insights import analyze_patterns
from src.services import caregiver_service as cs
from src.services import summary_service as sm
from src.services import medication_service as meds
from src.services import notification_service as notes
from src.services import wellness_service as ws
from src.ui.checkin_page import trend_frame
from src.ui.theme import STATUS_LABELS, badge

STATUS_COLORS = {"taken": "#0E7C86", "skipped": "#9DB4C0", "missed": "#C0392B"}


def _fmt(ts: str, date_only=False) -> str:
    d = datetime.fromisoformat(ts)
    return d.strftime("%d %b") if date_only else d.strftime("%d %b, %H:%M")


def _delivery(sent) -> str:
    return "Sent" if sent else "Simulated, nothing was sent"


def render(db_path, elder, caregiver, manager=None) -> None:
    now = datetime.now()
    hist = meds.history(db_path, elder["id"], 7, now)
    adh = cs.adherence(hist)
    schedule = meds.todays_schedule(db_path, elder["id"], now)
    checkins = ws.list_checkins(db_path, elder["id"], 14, now)
    flags = cs.attention_items(db_path, elder["id"], now)

    st.title("Caregiver dashboard")
    attention = any(f["severity"] == "warn" for f in flags)
    st.markdown(f"**{elder['name']}**, age {elder['age']}  &nbsp; " +
                (badge("Needs attention", "attention") if attention else badge("Nothing flagged", "ok")),
                unsafe_allow_html=True)

    tabs = st.tabs(["Overview", "Medications", "Wellness", "Alerts", "Notifications"])

    with tabs[0]:
        c = st.columns(4)
        c[0].metric("Adherence, 7 days", f"{adh['rate']}%" if adh["rate"] is not None else "No data")
        c[1].metric("Taken today", f"{sum(m['status']=='taken' for m in schedule)} of {len(schedule)}")
        c[2].metric("Latest mood", f"{checkins[-1]['mood']}/5" if checkins else "No data")
        c[3].metric("Unread notifications", notes.unread_count(db_path))
        st.subheader("Needs attention")
        if not flags:
            st.success("Nothing is flagged by the app's simple rules right now.")
        for f in flags:
            (st.warning if f["severity"] == "warn" else st.info)(f["text"])
        st.subheader("Weekly summary")
        facts = sm.collect_facts(db_path, elder, now)
        name = elder["name"].split()[0]
        b1, b2 = st.columns(2)
        if b1.button("Write summary (rule-based)"):
            st.session_state["summary"] = (sm.local_summary(facts, name), "local", None)
        if manager is not None and manager.is_enabled():
            if b2.button("Ask Gemini to write it"):
                st.session_state["summary"] = sm.gemini_summary(manager, facts, name, now)
        if summ := st.session_state.get("summary"):
            text, source, notice = summ
            st.markdown(badge("AI-written by Gemini" if source != "local" else "Rule-based summary (no AI text)",
                              "ai-on" if source != "local" else "ai-off"), unsafe_allow_html=True)
            st.write(text)
            if notice:
                st.caption(notice)
        st.subheader("Recent activity")
        for a in cs.recent_activity(db_path, elder["id"]):
            st.markdown(f"**{_fmt(a['ts'], a.get('date_only', False))}**  {a['kind']}: {a['text']}")

    with tabs[1]:
        st.caption("Adherence is the share of recorded entries marked taken. Doses with no entry are not counted.")
        if hist:
            pivot = pd.DataFrame(hist).pivot_table(index="date", columns="status", values="medication",
                                                   aggfunc="count", fill_value=0)
            cols = [s for s in meds.STATUSES if s in pivot.columns]
            st.bar_chart(pivot[cols], color=[STATUS_COLORS[s] for s in cols])
        else:
            st.write("No medication entries in the last 7 days.")
        st.subheader("Today")
        st.dataframe(pd.DataFrame([{"Time": m["reminder_time"], "Medicine": m["name"],
                                    "Status": STATUS_LABELS[m["status"]]} for m in schedule]),
                     hide_index=True, width="stretch")
        st.subheader("Missed in the last 7 days")
        missed = [r for r in hist if r["status"] == "missed"]
        if missed:
            st.dataframe(pd.DataFrame(missed)[["date", "medication", "time"]].rename(
                columns={"date": "Date", "medication": "Medicine", "time": "Due"}),
                hide_index=True, width="stretch")
        else:
            st.write("No missed medicines recorded.")

    with tabs[2]:
        if len(checkins) >= 2:
            st.line_chart(trend_frame(checkins), color=["#0E7C86", "#0B3C5D", "#E0A030"])
        else:
            st.write("The chart appears after two check-ins.")
        wf = [f for f in ws.analyze(checkins, now.date())]
        st.subheader("Patterns over time")
        findings = analyze_patterns(checkins)
        st.markdown(badge("Local statistical analysis", "ai-off"), unsafe_allow_html=True)
        if len(checkins) < 5:
            st.write("Pattern analysis needs at least 5 check-ins.")
        elif not findings:
            st.write("No notable patterns found in the recent check-ins.")
        for f in findings:
            st.info(f.text)
            st.caption(f"Evidence: {f.evidence}")
        st.caption("Linear regression, a comparison of recent and earlier scores, and correlation on self-reported scores. "
                   "Small samples and self-reporting limit this. It is not a diagnosis.")
        st.subheader("Flags from simple rules")
        for f in wf:
            (st.warning if f["severity"] == "warn" else st.info)(f["message"])
        if not wf:
            st.success("No flags from the check-in rules.")
        with st.expander("How these flags work"):
            st.markdown(
                f"- **Low score:** the latest mood, wellbeing or activity answer is {ws.LOW_VALUE} or lower.\n"
                f"- **Drop:** the latest answer is {ws.DROP_THRESHOLD} or more points below the average of the "
                f"previous check-ins (up to {ws.BASELINE_MAX}, at least {ws.BASELINE_MIN} needed).\n"
                f"- **Missing:** no check-in for {ws.MISSING_DAYS} or more days.\n\n"
                "These compare self-reported numbers only. They are not a medical assessment or diagnosis.")
        if checkins:
            df = pd.DataFrame(checkins)[["checkin_date", "mood", "wellbeing", "activity", "notes"]]
            df.columns = ["Date", "Mood", "Wellbeing", "Activity", "Notes"]
            st.dataframe(df.iloc[::-1], hide_index=True, width="stretch")

    with tabs[3]:
        st.subheader("Emergency alerts")
        em = cs.list_emergency_events(db_path, elder["id"])
        if em:
            st.dataframe(pd.DataFrame([{"When": _fmt(e["triggered_at"]), "Delivery": _delivery(e["alert_sent"]),
                                        "Note": e["delivery_note"]} for e in em]),
                         hide_index=True, width="stretch")
        else:
            st.write("No emergency events recorded.")
        st.subheader("Fall events (simulated)")
        st.caption("These come from simulated sensor data, not a real device.")
        falls = cs.list_fall_events(db_path, elder["id"])
        if falls:
            st.dataframe(pd.DataFrame([{"When": _fmt(f["detected_at"]),
                                        "Type": "Fall" if f.get("kind", "fall") == "fall" else "Unusual movement",
                                        "Peak (g)": round(f["peak_g"], 2), "Threshold (g)": f["threshold_g"]} for f in falls]),
                         hide_index=True, width="stretch")
        else:
            st.write("No fall events recorded.")

    with tabs[4]:
        st.button("Mark all as read", on_click=notes.mark_all_read, args=(db_path,))
        items = notes.list_notifications(db_path, 50)
        if items:
            st.dataframe(pd.DataFrame([{"When": _fmt(n["created_at"]), "Type": n["category"].capitalize(),
                                        "Message": n["message"], "Delivery": _delivery(not n["simulated"]),
                                        "Status": "Read" if n["read"] else "New"} for n in items]),
                         hide_index=True, width="stretch")
        else:
            st.write("No notifications yet.")
