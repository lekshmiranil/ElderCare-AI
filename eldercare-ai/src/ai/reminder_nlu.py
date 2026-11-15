"""Understanding "remind me to ... at ..." requests: rule-based entity extraction (task and time).

The intent ("this is a reminder request") comes from the local ML classifier; this module then pulls out the
details with explicit rules. It never guesses an unclear time: it asks. Medicines are refused here, because
they must be added on the Medications page where they are tracked.
"""
import re
from dataclasses import dataclass
from typing import Optional

PREFIX = re.compile(r"^\s*(please\s+)?(can you\s+|could you\s+)?(i want a\s+)?(set\s+(a\s+)?)?(reminder|remind me)\s*"
                    r"(for|to|about)?\s*", re.I)
MERIDIEM = re.compile(r"\b(\d{1,2})(?::(\d{2}))?\s*(a\.?m\.?|p\.?m\.?)(?![a-z])", re.I)
PLAIN = re.compile(r"\b(?:at|by|around)\s+(\d{1,2})(?::(\d{2}))?\b", re.I)
PART = re.compile(r"\b(?:in the\s+|at\s+)?(morning|afternoon|evening|night)\b", re.I)
MEDICINE = re.compile(r"\b(medicine|medicines|medication|tablet|tablets|pill|pills|dose|injection)\b", re.I)


@dataclass(frozen=True)
class ReminderDraft:
    task: str
    time: Optional[str] = None        # "HH:MM" when understood
    problem: Optional[str] = None     # "medicine" | "no_time" | "ambiguous_time" | "no_task"


def _hhmm(h: int, m: int) -> Optional[str]:
    return f"{h:02d}:{m:02d}" if 0 <= h <= 23 and 0 <= m <= 59 else None


def parse_reminder(text: str) -> ReminderDraft:
    body = PREFIX.sub("", text.strip(), count=1)
    task_src, time_str, problem = body, None, None

    m = MERIDIEM.search(body)
    if m:
        h, mins, mer = int(m.group(1)), int(m.group(2) or 0), m.group(3).lower().replace(".", "")
        if 1 <= h <= 12:
            h = (h % 12) + (12 if mer == "pm" else 0)
            time_str = _hhmm(h, mins)
        task_src = body[:m.start()] + " " + body[m.end():]
    else:
        plain = PLAIN.search(body)
        part = PART.search(body)
        if plain:
            h, mins = int(plain.group(1)), int(plain.group(2) or 0)
            if h >= 13:
                time_str = _hhmm(h, mins)
            elif part and 1 <= h <= 12:
                p = part.group(1).lower()
                if p == "morning":
                    time_str = _hhmm(h % 12, mins)
                elif p in ("afternoon", "evening"):
                    time_str = _hhmm((h % 12) + 12, mins)
                elif p == "night" and 6 <= h <= 11:
                    time_str = _hhmm(h + 12, mins)
                elif p == "night" and h == 12:
                    time_str = _hhmm(0, mins)
            if time_str is None:
                problem = "ambiguous_time"
            task_src = body[:plain.start()] + " " + body[plain.end():]
        elif re.search(r"\bnoon\b", body, re.I):
            time_str, task_src = "12:00", re.sub(r"\b(at\s+)?noon\b", " ", body, flags=re.I)
        elif re.search(r"\bmidnight\b", body, re.I):
            time_str, task_src = "00:00", re.sub(r"\b(at\s+)?midnight\b", " ", body, flags=re.I)
        else:
            problem = "no_time"

    task = PART.sub(" ", task_src)
    task = re.sub(r"\b(tomorrow|today|every day|daily|please)\b", " ", task, flags=re.I)
    task = re.sub(r"\s+", " ", task).strip(" ,.-")
    task = re.sub(r"^(to|about)\s+", "", task, flags=re.I).strip()
    task = re.sub(r"\s+(at|by|around|in the|in)$", "", task, flags=re.I).strip()
    if not task:
        return ReminderDraft("", time_str, "no_task")
    task = task[0].upper() + task[1:]
    if MEDICINE.search(task):
        return ReminderDraft(task, time_str, "medicine")
    return ReminderDraft(task, time_str, problem)
