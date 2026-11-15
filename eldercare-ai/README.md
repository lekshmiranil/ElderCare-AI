# ElderCare AI

An AI-assisted elderly care and independent-living assistant built with Python, Streamlit and SQLite.
It gives an older person a simple dashboard, a voice-enabled companion, medicine and check-in tracking, an
emergency button and fall-detection demo, and gives a caregiver a separate monitoring view.

**Runs fully offline in Demo Mode with no API key.** Gemini is an optional extra that is off by default.

## Quick start (Windows PowerShell)
```
python -m venv .venv
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python -m streamlit run app.py
```
macOS/Linux: activate with `source .venv/bin/activate`. Always start Streamlit as `python -m streamlit`.
Use **Reset demo data** in the sidebar to restore the sample data (the demo person is "Lekshmi"; change names on **My profile**).

Optional extras:
- **Prescription photo reading (OCR):** `pip install -r requirements-ocr.txt` (offline, no Tesseract needed). Pasted text works without it.
- **Gemini:** copy `.env.example` to `.env`, set `AI_PROVIDER=gemini`, `GEMINI_API_KEY=...` and a current `GEMINI_MODEL` (check Google AI Studio), then switch on "Use Gemini AI for open chat" in the sidebar.

Tests: `python -m pytest -q` (about a minute; no network, no API key needed).
Evaluation report: `python -m src.ai.evaluate` (writes `docs/AI_EVALUATION.md`).

## Features
| Area | What it does |
|---|---|
| Elderly dashboard | Greeting, today's medicines with Taken/Skip/Missed, overdue warnings, appointments, reminders, caregiver contact, check-in status, emergency button |
| Care Companion | Typed, spoken or button questions; voice replies; every answer labelled by source and explained |
| Medications | Add, edit, delete, 7-day history, missed-dose notifications, scan a prescription |
| Daily check-in | Mood, wellbeing, activity, notes; trends; transparent rule flags; statistical pattern analysis |
| Emergency help | Large button with confirmation, event log, honest "sent or simulated" status |
| Fall detection (simulation) | Simulated accelerometer data, configurable threshold, ML anomaly score, alerts, history |
| Caregiver dashboard | Adherence chart, missed doses, wellness trends and patterns, alerts, notifications, weekly summary |
| My profile | Names, caregiver details, preferences, reminders |

See `docs/AI_FEATURES.md` for the ten AI features (input, method, output, limits), and `docs/DEMO_SCRIPT.md` for a short demo walkthrough.

## Architecture
```
app.py                    entry point, navigation, error handling
config/                   settings from environment (.env), secrets never displayed
src/database/             SQLite schema, in-place upgrades, demo seed, small queries
src/services/             business logic with no UI code (medicines, check-ins, emergency, falls, reminders, summaries)
src/ai/                   classifiers, RAG, reminder NLU, anomaly model, document extraction, assistant pipeline
src/ai/providers/         LLMProvider interface, GeminiProvider (REST), errors
src/ai/manager.py         the only gateway to a cloud LLM: switch, cache, limits, quota pause
src/safety/               simulated sensor data
src/notifications/        notification channels (only a simulated one exists)
src/voice/                browser speech component (no network code of its own)
src/ui/                   Streamlit pages
tests/                    pytest suite (fakes live here only)
docs/                     AI features, evaluation, checklist, demo script
```
Care Companion decision order: self-harm and emergency wording → medical-advice refusal → urgent-symptom message →
reminders and knowledge questions → saved-data answers → open chat (Gemini if on, otherwise a local reply).
Gemini is only ever reached in the last step, the knowledge step and the summary button, each as one manual request.

## AI provider design
`LLMProvider` is a small interface; `GeminiProvider` implements it over REST (no SDK). `AIManager` applies every
protection (manual switch, cache, daily limit, spacing, one attempt, pause after 429, manual retry) and falls back to
local behaviour. Local replies are never labelled as Gemini. To add another provider, subclass `LLMProvider`.

## Privacy and safety
- Data stays in a local SQLite file that is git-ignored. Logs contain error types only, never names or messages.
- With Gemini on, open-chat text, preferences and counts-only summaries are sent to Google. Medicines, phone numbers and names (apart from the preferred name) are not.
- In Chrome and Edge the browser's own speech service processes voice. This is not Gemini.
- The app does not diagnose, prescribe or change doses. It cannot call emergency services or send real alerts: delivery is simulated and always shown as such.

## Accessibility
Large type, WCAG AA contrast (checked: lowest measured pair is 4.95:1), large buttons with visible keyboard focus
outlines, simple navigation, voice input and output, and responsive layout. Not done: a screen-reader audit.

## Known limitations
- Demo project: not a medical device and not tested with real older users.
- Intent, urgency, retrieval and extraction models are small, English-only and trained on phrases written for this project.
- Fall detection uses simulated data only; no real-world accuracy is claimed.
- Reminders repeat daily and only appear in the app; nothing pops up or sounds when the app is closed.
- Medicine reminder times follow the saved time but there is no push alert.
- The Gemini integration was built to Google's documented REST format and unit-tested with fakes; test it with your own key before relying on it.
- The knowledge base is demo content, not official medical guidance.

## Future improvements
Real notification channels (SMS or WhatsApp), real wearable integration and validation, push reminders, multi-user
accounts with login, a larger evaluated dataset and multilingual support (for example Malayalam and Hindi), local
speech models, and a clinician-reviewed knowledge base.

## Version control
`.env` and database files are ignored by `.gitignore`. Do not commit secrets or personal data.
