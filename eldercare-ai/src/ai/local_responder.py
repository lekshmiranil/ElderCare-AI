"""Deterministic reply handlers and safety rules. No network, no AI, no API key.

Every Reply carries a `source` so the UI can tell the person where it came from:
  app_data     : read straight from the app's records (medicines, appointments, contacts)
  safety       : fixed safety message
  general      : fixed local reply that does not use the person's records
  knowledge    : passages from the local knowledge base, shown as written, with their sources
  gemini / gemini_cache : text written by Gemini (set only by assistant.py)
"""
import re
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional

from src.database.queries import list_upcoming_appointments
from src.services import medication_service as meds
from src.services import wellness_service as wellness

# ---- deterministic safety vocabulary (runs alongside the ML urgency model) ------------------------
EMERGENCY = [
    r"\b(emergency|ambulance|chest pain|heart attack|stroke|unconscious|unresponsive|bleeding|faint(ed|ing)?)\b",
    r"\b(pass(ed)? out|black(ed)? out|collaps\w*|chok(e|ed|ing)|overdos\w*|lost consciousness)\b",
    r"\b(can'?t|cannot|can not|unable to|hardly|struggling to) breathe?\b", r"\bnot breathing\b",
    r"\b(i )?(fell|fallen|have fallen)\b", r"\b(slurred|drooping)\b", r"\bnot responding\b",
    r"\b(swallowed|taken|took) (too many|a lot of|lots of)\b", r"\btoo many (tablets|pills|medicines)\b",
    r"\bvomiting blood\b", r"\b(hit|hurt|bumped) my head\b|\bhead injury\b", r"\bsmoke in the house\b", r"\bon fire\b|\bfire in\b", r"\bbroke into\b"]
SELF_HARM = [r"\b(want to die|kill myself|end my life|suicid\w*|don'?t want to live|better off dead|hurt myself)\b"]
MEDICAL_ADVICE = [
    r"\b(dose|dosage|dosing|overdose)\b", r"\bhow (much|many)\b.*\b(take|tablet|pill|medicine)",
    r"\b(diagnos\w*|prescrib\w*)\b", r"\bdo i have\b", r"\bside effects?\b",
    r"\bshould i (stop|skip|double|increase|reduce|take more|take less)\b",
    r"\b(double|increase|reduce|stop)\b.*\b(medicine|medication|tablet|pill|dose)\b",
    r"\b\d+\s?(mg|ml|mcg)\b"]


def _has(text: str, patterns) -> bool:
    t = (text or "").lower()
    return any(re.search(p, t) for p in patterns)


def has_emergency(text): return _has(text, EMERGENCY)
def has_self_harm(text): return _has(text, SELF_HARM)
def has_medical_advice(text): return _has(text, MEDICAL_ADVICE)


@dataclass(frozen=True)
class Reply:
    text: str
    source: str
    notice: Optional[str] = None
    trace: dict = field(default_factory=dict)
    sources: tuple = ()
    action: Optional[dict] = None   # e.g. a reminder waiting for the person's confirmation

    @property
    def speech(self) -> str:
        """Plain text for the browser's voice: list lines become sentences."""
        clean = re.sub(r"[*_#`]", "", self.text)
        return re.sub(r"\s*\n\s*(- )?", ". ", clean).replace("..", ".").strip()


def _cg(caregiver) -> str:
    return f"{caregiver['name']} ({caregiver['relationship']}), phone {caregiver['phone']}"


# ---- safety replies ----------------------------------------------------------------------------------
def emergency_reply(caregiver) -> Reply:
    return Reply("If you are in danger or feel seriously unwell, call 112 now or ask someone near you for help. "
                 f"This app cannot call emergency services for you. Your caregiver is {_cg(caregiver)}.", "safety")


def self_harm_reply(caregiver) -> Reply:
    return Reply("I am really sorry you are in so much pain. You are not alone. Please tell someone near you, or call "
                 f"{_cg(caregiver)}, right now. You can also call Tele-MANAS on 14416 at any time, or 112 if you "
                 "are in immediate danger. This app cannot call anyone for you.", "safety")


def medical_advice_reply() -> Reply:
    return Reply("I cannot give medical advice, diagnose problems, or say how much of a medicine to take. "
                 "Please ask your doctor or pharmacist. I can read out your saved medicine schedule if you ask "
                 "about your medicines today.", "safety")


def urgent_reply(caregiver) -> Reply:
    return Reply("Thank you for telling me. This is worth mentioning to your caregiver or doctor soon. I cannot judge "
                 f"how serious it is. Your caregiver is {_cg(caregiver)}. If it gets worse or you feel very unwell, "
                 "call 112.", "safety")


# ---- data-backed and small-talk replies ----------------------------------------------------------------
def _medicine_reply(db_path, elder, now, upcoming_only: bool) -> Reply:
    schedule = meds.todays_schedule(db_path, elder["id"], now)
    if upcoming_only:
        pending = [m for m in schedule if m["status"] in ("upcoming", "overdue")]
        if not pending:
            return Reply("You have no more medicines left to take today according to your saved schedule.", "app_data")
        m = pending[0]
        extra = " It is overdue, so please check it." if m["status"] == "overdue" else ""
        return Reply(f"Your next medicine on your saved schedule is {m['name']} at {m['reminder_time']}.{extra}", "app_data")
    if not schedule:
        return Reply("There are no medicines saved yet. You can add them in the Medications page.", "app_data")
    lines = [f"- {m['reminder_time']} {m['name']}: {m['status']}" for m in schedule]
    return Reply("Here are your medicines for today from your saved schedule:\n" + "\n".join(lines), "app_data")


def data_reply(intent: str, db_path, elder, caregiver, now: datetime, name: str = None) -> Optional[Reply]:
    """Deterministic answer for an intent, or None if this intent has no fixed handler."""
    first = name or elder["name"].split()[0]
    if intent == "medicines_today":
        return _medicine_reply(db_path, elder, now, False)
    if intent == "next_medicine":
        return _medicine_reply(db_path, elder, now, True)
    if intent == "caregiver":
        return Reply(f"Your caregiver is {_cg(caregiver)}. I cannot place calls for you, but you can use this number.", "app_data")
    if intent == "appointment":
        appts = list_upcoming_appointments(db_path, elder["id"], now.isoformat(timespec="minutes"))
        if not appts:
            return Reply("You have no appointments saved.", "app_data")
        a = appts[0]
        when = datetime.fromisoformat(a["appt_datetime"]).strftime("%A %d %B at %H:%M")
        where = f" at {a['location']}" if a["location"] else ""
        return Reply(f"Your next appointment is {a['title']} on {when}{where}.", "app_data")
    if intent == "checkin":
        done = wellness.get_today(db_path, elder["id"], now) is not None
        return Reply("You have already done today's check-in. Thank you." if done else
                     "You have not done today's check-in yet. Open Daily check-in in the menu.", "app_data")
    if intent == "time_date":
        return Reply(f"It is {now.strftime('%A %d %B %Y')}, and the time is {now.strftime('%H:%M')}.", "general")
    if intent == "greeting":
        return Reply(f"Hello {first}. You can ask me about your medicines, appointments or your caregiver.", "general")
    if intent == "how_are_you":
        return Reply("I am here and ready to help. How are you feeling today?", "general")
    if intent == "thanks":
        return Reply("You are welcome.", "general")
    return None


def fallback_reply(intent: str, caregiver) -> Reply:
    """Local reply when Gemini is off or unavailable. Honest about what it cannot do."""
    if intent == "feeling":
        return Reply("I am sorry you feel this way. You could do today's check-in so your caregiver can see how "
                     f"you are. If you feel unwell, please tell {caregiver['name']} or your doctor.", "general")
    return Reply("I cannot chat freely right now because AI chat is off. I can still help with your medicines, "
                 "your next appointment, your check-in, or your caregiver.", "general")
