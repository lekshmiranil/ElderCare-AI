"""Care Companion pipeline: safety first, then local ML understanding, then (optionally) Gemini.

Order of decisions (first match wins):
 1. Self-harm wording (rules)                       -> fixed safety reply
 2. Emergency wording (rules) OR ML urgency=emergency -> fixed safety reply
 3. Medical-advice request (rules OR ML intent)      -> fixed refusal
 4. ML urgency=urgent                                -> fixed "tell your caregiver/doctor" reply
 5. ML intent is a data/small-talk intent            -> deterministic answer from saved records
 6. Otherwise (open chat, feelings, low confidence)  -> Gemini if on and available, else local reply
Gemini is never used for steps 1-5, and its output is checked before it is shown.
"""
import re
from datetime import datetime

from src.services import profile_service

from . import local_responder as lr
from . import rag
from .reminder_nlu import parse_reminder
from .classifiers import intent_classifier, urgency_classifier
from .manager import AIManager
from .providers.base import AIRequest

CONF_MIN = 0.45          # below this the intent is treated as unknown (goes to the open-chat path)
URGENCY_EMERGENCY = 0.40   # chosen from the evaluation: more ML recall with 0 false alarms on the non-emergency test phrases
URGENCY_URGENT = 0.60
DATA_INTENTS = {"medicines_today", "next_medicine", "caregiver", "appointment", "checkin",
                "time_date", "greeting", "how_are_you", "thanks"}

SYSTEM_PROMPT = (
    "You are a warm, patient companion for an older adult living at home. Reply in at most three short, "
    "plain sentences. Never give medical advice, diagnoses, medicine names or doses. If they mention health "
    "worries, gently suggest talking to their caregiver or doctor. For danger, tell them to call 112. "
    "You cannot see their records, the weather or any live information, and you cannot call anyone: never "
    "claim otherwise. Be kind, never condescending."
)


def _clean_llm_text(text: str) -> str:
    text = re.sub(r"[*_#`>]", "", text).strip()
    return text[:600]


def _reminder_reply(text: str) -> lr.Reply:
    d = parse_reminder(text)
    if d.problem == "medicine":
        return lr.Reply("Medicines need to be added on the Medications page so they are tracked properly. "
                        "I can set reminders for other things, such as a walk or a phone call.", "general")
    if d.problem == "no_task":
        return lr.Reply("What would you like me to remind you about, and at what time?", "general")
    if d.problem in ("no_time", "ambiguous_time"):
        why = "I did not hear a time." if d.problem == "no_time" else "I am not sure if that is morning or evening."
        return lr.Reply(f"{why} Please say it again with am or pm, for example: remind me to {d.task.lower()} at 5 pm.", "general")
    return lr.Reply(f"I understood: {d.task} at {d.time}. This reminder will show every day at that time and you can "
                    "delete it later. Shall I save it?", "general", action={"type": "confirm_reminder", "task": d.task, "time": d.time})


def _knowledge_reply(question: str, manager: AIManager, now) -> lr.Reply:
    passages = rag.retrieve(question)
    if not passages:
        return lr.Reply("I do not have information about that in my knowledge base. You could ask your doctor, "
                        "pharmacist or caregiver.", "general", trace={"retrieved": []})
    trace = {"retrieved": [{"source": p.title, "score": round(p.score, 2)} for p in passages]}
    system, user = rag.grounded_prompt(question[:300], passages)
    outcome = manager.complete(AIRequest("knowledge_rag", system, user, 220, 4000), now)
    notice = outcome.notice
    if outcome.text:
        if rag.valid_citations(outcome.text, len(passages)) and not lr.has_medical_advice(outcome.text):
            cited = sorted({int(x) for x in re.findall(r"\[(\d+)\]", outcome.text)})
            titles = tuple(dict.fromkeys(passages[c - 1].title for c in cited))
            return lr.Reply(re.sub(r"\s*\[\d+\]", "", outcome.text).strip()[:600], outcome.source, None, trace, titles)
        notice = "Gemini's answer did not cite the knowledge base properly, so the original passages are shown."
    return lr.Reply(rag.extractive_answer(passages), "knowledge", notice, trace, tuple(dict.fromkeys(p.title for p in passages)))


def answer(db_path, elder, caregiver, text: str, manager: AIManager, now: datetime = None) -> lr.Reply:
    now = now or datetime.now()
    text = (text or "").strip()
    if not text:
        return lr.Reply("I did not catch that. You can type or speak your question again.", "general")

    prefs = profile_service.get_preferences(db_path)
    name = profile_service.display_name(elder, prefs)
    intent, conf, _ = intent_classifier().predict(text)
    urg, urg_conf, urg_probs = urgency_classifier().predict(text)
    trace = {"intent": intent, "intent_confidence": round(conf, 2), "urgency": urg,
             "urgency_probabilities": {k: round(v, 2) for k, v in urg_probs.items()}}

    def done(reply: lr.Reply, route: str, **extra) -> lr.Reply:
        return lr.Reply(reply.text, reply.source, reply.notice, {**trace, "route": route, **extra}, reply.sources, reply.action)

    if lr.has_self_harm(text):
        return done(lr.self_harm_reply(caregiver), "safety rules: self-harm wording")
    if lr.has_emergency(text):
        return done(lr.emergency_reply(caregiver), "safety rules: emergency wording")
    if urg == "emergency" and urg_probs["emergency"] >= URGENCY_EMERGENCY:
        return done(lr.emergency_reply(caregiver), "ML urgency model: emergency")
    if lr.has_medical_advice(text) or (intent == "medical_advice" and conf >= CONF_MIN):
        return done(lr.medical_advice_reply(), "safety: medical advice request")
    if urg == "urgent" and urg_probs["urgent"] >= URGENCY_URGENT:
        return done(lr.urgent_reply(caregiver), "ML urgency model: urgent")
    if intent == "set_reminder" and conf >= CONF_MIN:
        return done(_reminder_reply(text), "reminder understanding (ML intent + extraction rules)")
    if intent == "knowledge_question" and conf >= CONF_MIN:
        reply = _knowledge_reply(text, manager, now)
        return lr.Reply(reply.text, reply.source, reply.notice, {**trace, "route": "knowledge base retrieval", **reply.trace}, reply.sources)
    if intent in DATA_INTENTS and conf >= CONF_MIN:
        reply = lr.data_reply(intent, db_path, elder, caregiver, now, name=name)
        if reply:
            return done(reply, "deterministic handler (no AI text)")

    # Open conversation. Only here may Gemini be used, and only if the person switched it on.
    context = [f"Person's name: {name}."]
    if prefs["interests"]:
        context.append(f"Their interests: {prefs['interests']}.")
    if prefs["wake_time"] or prefs["bedtime"]:
        context.append(f"Usual wake time {prefs['wake_time'] or 'unknown'}, bedtime {prefs['bedtime'] or 'unknown'}.")
    context.append(f"Current time: {now:%H:%M}.")
    outcome = manager.complete(AIRequest("companion_chat", SYSTEM_PROMPT, " ".join(context) + f" They said: {text}"), now)
    if outcome.text:
        out = _clean_llm_text(outcome.text)
        if lr.has_medical_advice(out):
            return done(lr.medical_advice_reply(), "Gemini output blocked by safety filter", model=outcome.model)
        return done(lr.Reply(out, outcome.source, outcome.notice), f"Gemini ({outcome.source})", model=outcome.model)
    fb = lr.fallback_reply(intent, caregiver)
    return done(lr.Reply(fb.text, fb.source, outcome.notice), "local fallback (Gemini not used)")
