# AI features: what is AI, what is not

**Rule used throughout:** safety messages, emergency handling, reminders, medicine schedules and answers about saved
records are deterministic code, never AI-written text. Gemini is optional, off by default, and the app is fully
usable without it. Every reply shows where it came from.

| # | Feature | Where it runs | Status |
|---|---------|---------------|--------|
| 1 | LLM conversational assistant | Gemini (optional) | Built |
| 2 | Natural-language understanding (intents, reminders) | Local ML + rules | Built |
| 3 | Context-aware personalization | Local data, Gemini context | Built |
| 4 | RAG knowledge assistant with sources | Local retrieval, Gemini optional | Built |
| 5 | Analysis of self-reported wellness patterns | Local statistics (regression, correlation) | Built |
| 6 | NLP urgency classification | Local ML + keyword rules | Built |
| 7 | Anomaly detection on wearable-style sensor data | Local Isolation Forest, synthetic data | Built |
| 8 | Caregiver activity summaries | Rule-based, Gemini optional | Built |
| 9 | OCR + NLP medicine extraction with human confirmation | Local OCR (optional add-on) + rules | Built |
| 10 | Voice: speech in, AI processing, speech out | Browser speech + the above | Built |

Measured quality is in `docs/AI_EVALUATION.md` (regenerate with `python -m src.ai.evaluate`) and enforced by tests.
All test sets are small and written by the project author, so they are indicative, not guarantees.

## 1. LLM conversational assistant (Gemini, optional)
- **Input:** an open-ended message (chat, feelings) not recognised as a safety, data or small-talk request, plus the preferred name, interests, usual times and the current time. No history, no medicines, no phone numbers.
- **Processing:** Gemini through `AIManager` (switch, cache, daily limit, spacing, one attempt, quota pause).
- **Output:** up to three plain sentences, cleaned and checked by a deterministic medical-advice filter before display.
- **Deterministic parts:** routing, the safety filter, limits, cache, labels. **AI part:** only the wording of open chat.
- **Limitations:** needs internet and a key; can be wrong; has no live data (weather, news); messages go to Google. Without Gemini a local reply says AI chat is off.

## 2. Natural-language understanding
- **Intent:** TF-IDF word and character n-grams + logistic regression over 14 intents; confidence below 0.45 counts as "unknown".
- **Reminders:** after the ML recognises a reminder request, explicit rules extract the task and time. Unclear times ("at 4") are asked about, never guessed; medicine reminders are refused and sent to the Medications page; nothing is saved without a confirmation tap. Reminders repeat daily.
- **Limitations:** about 250 hand-written training phrases, English only; no dates beyond a daily time.

## 3. Personalization
- **Input:** the My profile page (name, preferred name, interests, wake and bed times) and saved reminders.
- **Use:** the app greets by the preferred name; the Gemini prompt includes preferred name, interests, usual times and current time.
- **Limitations:** light personalization; interests only influence Gemini wording; nothing is learned automatically.

## 4. RAG knowledge assistant
- **Input:** a question classified as a knowledge question. **Retrieval:** TF-IDF + cosine similarity over 10 short documents (`src/ai/knowledge`), top 3 passages, minimum score 0.12.
- **Output:** without Gemini, the best passages shown as written with their source titles. With Gemini, an answer using only those passages and citing them; it is rejected (passages shown instead) if it cites nothing valid or gives medical advice. If nothing matches, it says it has no information.
- **Limitations:** the knowledge base is demo content written for this project (general wellbeing tips, not medical advice, not from official guidelines). A stricter score threshold rejects all off-topic questions but lowers correct matches by 10 to 20 points; retrieval only runs after the ML intent step, so this was left permissive.

## 5. Wellness pattern analysis
- **Input:** at least 5 check-ins (mood, wellbeing, activity, 1 to 5). **Processing:** linear regression trend per week (with R²), recent-versus-earlier medians, variability, and mood/activity correlation, only when both vary.
- **Output:** findings with their numbers ("evidence"). **Limitations:** tiny samples, self-reported, correlation is not cause, not a diagnosis. This is classical statistics, not deep learning.
- The Phase 3 flags (low score, drop, missing) are separate fixed rules and are not AI.

## 6. Urgency classification
- **Input:** the message. **Processing:** a 3-class model (routine, urgent, emergency) **and** keyword rules for emergencies and self-harm wording; either triggers. **Output:** a fixed safety message (112, caregiver, and Tele-MANAS 14416 for distress), never generated text.
- **Why both:** on a fresh test set the model alone caught 5 of 8 emergency phrases; with the rules, 8 of 8, with 0 false alarms on the non-emergency phrases tested. A false alarm is preferred to a missed emergency.
- **Limitations:** small English test sets; not clinically validated. The message tells the person to call 112; the app does not contact emergency services.

## 7. Sensor anomaly detection (fall demo)
- **Input:** 4-second accelerometer-magnitude windows at 50 Hz, **simulated** by `sensor_sim.py`.
- **Processing:** an Isolation Forest trained only on simulated normal movement (9 summary features) flags unusual windows; a separate deterministic rule (peak at or above a configurable threshold, then about 1.5 s of stillness) decides "fall". Outcomes: fall, unusual movement, none.
- **Limitations:** synthetic data makes the numbers look better than real life would. No real-world accuracy is claimed. Real use needs real wearable data, validation, and a real notification channel.

## 8. Caregiver summaries
- **Input:** 7-day counts and averages (never names, phone numbers or medicine names). **Output:** a rule-based summary always; Gemini can write one on request.
- **Safeguard:** every number in a Gemini summary must appear in the facts it was given, otherwise the rule-based summary is shown with a notice.
- **Limitations:** summaries describe recorded data only; unrecorded doses are not counted.

## 9. Prescription extraction
- **Input:** an image (OCR via RapidOCR, optional `requirements-ocr.txt`, offline) or pasted text.
- **Processing:** OCR → row grouping → repair of common digit confusions in patterns like 1-0-1 → rule-based line parser (form, name, strength, schedule text).
- **Human in the loop:** suggestions only. The person edits, ticks each medicine, **chooses reminder times themselves** (times are never read or invented), and confirms they checked the original. One invalid line saves nothing.
- **Limitations:** OCR errors on blurry or handwritten text; no drug-name database, so spelling is not verified; names with digits or extra words (for example "Vit D3") can be misread, which the evaluation includes on purpose.

## 10. Voice interaction
- Browser speech recognition → the pipeline above → browser speech synthesis. Voice never uses Gemini and keeps working when Gemini is off or out of quota.
- **Limitations:** Chrome and Edge for input; recognition runs on the browser vendor's online service.

## API reliability and quota protection
| Protection | Where |
|---|---|
| Gemini off by default; manual switch; works with no key | `AIManager`, sidebar |
| No call on page load or refresh (tested) | `tests/test_no_calls_on_load.py` |
| Safety, emergency, data and reminder messages never reach Gemini (tested) | `assistant.py` |
| Cache of successful answers, 24 h, hashes only | `manager.py` |
| Daily limit, minimum spacing, input caps per request type | `manager.py`, `.env` |
| 429 / RESOURCE_EXHAUSTED detected, paused 30 min, never retried automatically, manual Retry | `gemini.py`, `manager.py` |
| Bad key or model name: paused 24 h with a clear message | `manager.py` |
| Key only in a request header; never in the UI, logs or errors (tested) | `gemini.py` |
| Fakes exist only in `tests/`; the app never simulates a Gemini answer | `tests/fakes.py` |
| Every feature can be tested with no quota: local mode plus fake providers | whole test suite |
