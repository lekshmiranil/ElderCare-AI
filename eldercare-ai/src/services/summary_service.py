"""Caregiver activity summaries: a rule-based one (always available) and an optional Gemini-written one.

The Gemini version only receives counts and averages, never names, phone numbers or medicine names, and its
answer is rejected unless every number in it appears in the facts it was given.
"""
import json
import re
from datetime import datetime

from src.ai.manager import AIManager
from src.ai.providers.base import AIRequest
from src.ai.wellness_insights import analyze_patterns
from src.services import caregiver_service as cs
from src.services import medication_service as meds
from src.services import wellness_service as ws

SYSTEM = ("You write a short update for a family caregiver about an older person's past week. Use ONLY the facts in the "
          "JSON. Write at most 90 words in plain, calm language. Do not give medical advice or diagnoses, and do not "
          "mention any number that is not in the JSON.")


def collect_facts(db_path, elder, now=None) -> dict:
    now = now or datetime.now()
    hist = meds.history(db_path, elder["id"], 7, now)
    adh = cs.adherence(hist)
    checkins = ws.list_checkins(db_path, elder["id"], 7, now)
    em = [e for e in cs.list_emergency_events(db_path, elder["id"]) if (now - datetime.fromisoformat(e["triggered_at"])).days < 7]
    falls = [f for f in cs.list_fall_events(db_path, elder["id"]) if (now - datetime.fromisoformat(f["detected_at"])).days < 7]
    schedule = meds.todays_schedule(db_path, elder["id"], now)
    return {
        "period_days": 7, "mood_scale_max": 5,
        "medicine_entries_recorded": adh["recorded"], "taken": adh["taken"], "skipped": adh["skipped"], "missed": adh["missed"],
        "adherence_percent": adh["rate"], "overdue_today": sum(m["status"] == "overdue" for m in schedule),
        "checkins": len(checkins),
        "average_mood": round(sum(c["mood"] for c in checkins) / len(checkins), 1) if checkins else None,
        "latest_mood": checkins[-1]["mood"] if checkins else None,
        "pattern_findings": [f.text for f in analyze_patterns(ws.list_checkins(db_path, elder["id"], 14, now))],
        "emergency_alerts": len(em), "fall_or_unusual_movement_events": len(falls),
    }


def local_summary(facts: dict, name: str) -> str:
    parts = []
    if facts["medicine_entries_recorded"]:
        parts.append(f"{name} had {facts['taken']} of {facts['medicine_entries_recorded']} recorded medicine entries marked taken "
                     f"in the last {facts['period_days']} days ({facts['adherence_percent']}%), with {facts['missed']} missed and "
                     f"{facts['skipped']} skipped.")
    else:
        parts.append("No medicine entries were recorded in the last 7 days.")
    if facts["overdue_today"]:
        parts.append(f"{facts['overdue_today']} medicine(s) are overdue today.")
    if facts["checkins"]:
        parts.append(f"{facts['checkins']} wellness check-in(s) were done, with an average mood of {facts['average_mood']} out of 5.")
    else:
        parts.append("No wellness check-ins were recorded.")
    parts += facts["pattern_findings"][:3]
    parts.append(f"There were {facts['emergency_alerts']} emergency alert(s) and {facts['fall_or_unusual_movement_events']} simulated "
                 "fall or unusual-movement event(s).")
    return " ".join(parts)


def _numbers(text: str) -> set:
    return set(re.findall(r"\d+(?:\.\d+)?", text))


def numbers_supported(summary: str, facts: dict) -> bool:
    """Every number written in the summary must exist in the facts (guards against invented figures)."""
    return _numbers(summary) <= _numbers(json.dumps(facts))


def gemini_summary(manager: AIManager, facts: dict, name: str, now=None):
    """Returns (text, source, notice). Falls back to the rule-based summary whenever Gemini is not used or not trusted."""
    prompt_facts = {k: v for k, v in facts.items()}
    outcome = manager.complete(AIRequest("caregiver_summary", SYSTEM, "Facts: " + json.dumps(prompt_facts), 220, 4000), now)
    if outcome.text and numbers_supported(outcome.text, facts):
        return outcome.text.strip(), outcome.source, None
    notice = outcome.notice
    if outcome.text:
        notice = "Gemini's summary contained a figure that is not in your data, so the rule-based summary is shown."
    return local_summary(facts, name), "local", notice
