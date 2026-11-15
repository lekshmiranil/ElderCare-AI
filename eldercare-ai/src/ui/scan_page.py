"""Scan a prescription: OCR (optional) -> suggested medicines -> the person checks, edits, sets times and confirms."""
from datetime import datetime

import streamlit as st

from src.ai import doc_extract as de
from src.services.medication_service import ValidationError
from src.ui.theme import badge

MAX_BYTES = 5 * 1024 * 1024


def _read_image(data: bytes) -> None:
    try:
        with st.spinner("Reading the image..."):
            st.session_state["scan_text"] = de.ocr_image(data)
    except de.OCRUnavailable:
        st.session_state["scan_error"] = "Image reading is not installed. Paste the text instead, or see the README."
    except Exception:
        st.session_state["scan_error"] = "The image could not be read. Try a clearer, straighter photo, or paste the text."


def render(db_path, elder) -> None:
    ss = st.session_state
    st.title("Scan a prescription")
    st.info("This reads a prescription and suggests medicines. Nothing is saved until you check every line, set the "
            "reminder times yourself, and confirm. Reading can make mistakes, especially with handwriting.")
    if msg := ss.pop("flash_ok", None):
        st.success(msg)
    if err := ss.pop("scan_error", None):
        st.error(err)

    if de.ocr_available():
        up = st.file_uploader("Photo of the prescription (PNG or JPG)", type=["png", "jpg", "jpeg"])
        if up is not None:
            if up.size > MAX_BYTES:
                st.error("That file is too large (5 MB maximum).")
            elif st.button("Read the text from the image"):
                _read_image(up.getvalue())
                st.rerun()
    else:
        st.caption("Reading photos needs the optional add-on: run `pip install -r requirements-ocr.txt`. "
                   "You can still paste the prescription text below.")

    text = st.text_area("Prescription text (you can correct it here)", key="scan_text", height=180)
    if st.button("Find medicines in this text"):
        ss["scan_candidates"] = de.parse_medications(text)
        ss["scan_round"] = ss.get("scan_round", 0) + 1

    cands = ss.get("scan_candidates")
    if cands is None:
        return
    if not cands:
        st.warning("No medicines were found. Check the text, or add medicines yourself on the Medications page.")
        return

    rnd = ss.get("scan_round", 0)
    st.subheader("Suggested medicines")
    st.caption("Reminder times are not read from the document. Please set each one yourself.")
    chosen = []
    for i, c in enumerate(cands):
        with st.container(border=True):
            include = st.checkbox("Include this medicine", value=c.confidence == "good", key=f"inc{rnd}_{i}")
            st.markdown(badge("Looks complete" if c.confidence == "good" else "Check carefully", "ok" if c.confidence == "good" else "attention"),
                        unsafe_allow_html=True)
            st.caption(f"Read from: {c.source_line}")
            name = st.text_input("Medicine name", c.name, key=f"nm{rnd}_{i}")
            strength = st.text_input("Strength", c.strength, key=f"st{rnd}_{i}")
            sched = st.text_input("Prescribed schedule (as written)", c.schedule_text, key=f"sc{rnd}_{i}")
            t = st.time_input("Reminder time (you choose)", value=datetime.strptime("08:00", "%H:%M").time(), step=300, key=f"tm{rnd}_{i}")
            if include:
                chosen.append({"name": name, "strength": strength, "schedule_text": sched, "reminder_time": t.strftime("%H:%M")})

    confirmed = st.checkbox("I have checked every medicine, strength, schedule and time against the original document.", key=f"cf{rnd}")
    if st.button("Save the selected medicines", disabled=not confirmed):
        try:
            n = de.save_confirmed(db_path, elder["id"], chosen, confirmed)
            ss["flash_ok"] = f"Saved {n} medicine(s). You can see them on the Medications page."
            ss.pop("scan_candidates", None)
            ss["scan_text"] = ""
            st.rerun()
        except ValidationError as e:
            st.error(str(e))
