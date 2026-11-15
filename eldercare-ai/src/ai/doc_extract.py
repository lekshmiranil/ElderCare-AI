"""Reading medicine details from a prescription: OCR (optional add-on) then rule-based NLP extraction.

Pipeline: image -> OCR text (RapidOCR, runs offline, optional install) -> line parser -> CANDIDATES.
Candidates are only suggestions. Nothing is saved until the person edits, ticks each medicine, sets the
reminder times THEMSELVES (times are never read or invented) and confirms they checked the original document.
Limitations: OCR errors on blurry or handwritten text, no drug-name database (so spelling is not verified),
English only, and printed prescriptions work much better than handwritten ones.
"""
import io
import re
from dataclasses import dataclass
from functools import lru_cache

from src.services import medication_service as meds

FORM = r"(?:tab(?:let)?s?|cap(?:sule)?s?|syp|syrup|inj(?:ection)?|oint(?:ment)?|drops?)"
STRENGTH = r"\d+(?:\.\d+)?\s?(?:mg|mcg|g|ml|iu)\b"
SCHEDULE_PATTERNS = [
    r"\b\d-\d-\d(?:-\d)?\b", r"\b(?:once|twice|thrice|three times|four times)\s+(?:a\s+|per\s+)?(?:day|daily|week)\b",
    r"\b(?:od|bd|bid|tds|tid|qid|hs|sos)\b", r"\b(?:morning|night|bedtime|evening)\b",
    r"\b(?:after|before|with)\s+(?:food|meals?|breakfast|lunch|dinner|water)\b",
    r"\bfor\s+\d+\s+(?:days?|weeks?|months?)\b", r"\bx\s?\d+\s?(?:days?|weeks?)\b"]
HEADER_WORDS = {"patient", "doctor", "dr", "date", "name", "age", "sex", "address", "clinic", "hospital", "phone", "signature",
                "advice", "diagnosis", "rx", "weight", "regd", "reg", "sign", "follow", "review", "next", "visit", "mobile"}
LINE = re.compile(rf"^\s*(?:\d+\s*[\.\)]\s*)?(?:({FORM})\s*\.?\s+)?([A-Za-z][A-Za-z\-]{{2,}}(?:\s[A-Za-z\-]{{3,}})?)\s*({STRENGTH})?(.*)$", re.I)


class OCRUnavailable(RuntimeError):
    pass


@dataclass(frozen=True)
class Candidate:
    name: str
    strength: str
    schedule_text: str
    source_line: str
    confidence: str      # "good" when name, form or strength, and a schedule were all found; otherwise "check"


def ocr_available() -> bool:
    try:
        import rapidocr_onnxruntime  # noqa: F401
        return True
    except Exception:
        return False


@lru_cache(maxsize=1)
def _engine():
    from rapidocr_onnxruntime import RapidOCR
    return RapidOCR()


def ocr_image(data: bytes) -> str:
    """Return the text found in an image, one line per row, top to bottom."""
    if not ocr_available():
        raise OCRUnavailable("The optional OCR add-on is not installed.")
    import numpy as np
    from PIL import Image
    img = np.array(Image.open(io.BytesIO(data)).convert("RGB"))
    result, _ = _engine()(img)
    if not result:
        return ""
    # Group boxes into rows by vertical position, then read each row left to right.
    boxes = sorted(((sum(p[1] for p in b) / 4, max(p[1] for p in b) - min(p[1] for p in b), b[0][0], t) for b, t, _ in result))
    rows, current, row_y = [], [], None
    for y, height, x, text in boxes:
        if row_y is not None and abs(y - row_y) < max(height, 1) * 0.6:
            current.append((x, text))
        else:
            if current:
                rows.append(current)
            current, row_y = [(x, text)], y
    if current:
        rows.append(current)
    return "\n".join(fix_dose_digits(" ".join(t for _, t in sorted(r))) for r in rows)


_PATTERN = re.compile(r"(?<![\w])[\dlIOo|]-[\dlIOo|]-[\dlIOo|](?:-[\dlIOo|])?(?![\w])")


def fix_dose_digits(text: str) -> str:
    """OCR often reads 1 as l/I/| and 0 as O inside patterns like 1-0-1. Repair only those patterns."""
    def repair(m):
        return m.group(0).translate(str.maketrans({"l": "1", "I": "1", "|": "1", "O": "0", "o": "0"}))
    return _PATTERN.sub(repair, text)


def parse_medications(text: str) -> list:
    out = []
    for raw in fix_dose_digits(text or "").splitlines():
        line = raw.strip()
        m = LINE.match(line)
        if not line or not m:
            continue
        form, name, strength, rest = m.group(1), m.group(2).strip(), (m.group(3) or "").strip(), m.group(4)
        if name.split()[0].lower().rstrip(".") in HEADER_WORDS or not (form or strength):
            continue
        rest_clean = re.sub(r"\s+", " ", rest).strip(" -:,.")
        found = any(re.search(p, rest_clean, re.I) for p in SCHEDULE_PATTERNS)
        schedule = rest_clean[:120] if found else ""
        out.append(Candidate(name=name, strength=strength, schedule_text=schedule, source_line=line,
                             confidence="good" if (schedule and (form or strength)) else "check"))
    return out


def save_confirmed(db_path, elder_id: int, items: list, confirmed: bool) -> int:
    """Save medicines the person has reviewed. Refuses unless they confirmed, and validates everything first.

    Each item: {"name", "strength", "schedule_text", "reminder_time"}. reminder_time must come from the person.
    """
    if not confirmed:
        raise meds.ValidationError("Please confirm that you checked the medicines against the original document.")
    if not items:
        raise meds.ValidationError("No medicines are selected.")
    cleaned = []
    for it in items:
        name = f"{it['name'].strip()} {it.get('strength', '').strip()}".strip()
        cleaned.append(meds.validate_medication(name, it["schedule_text"], it["reminder_time"]))   # raises before any save
    for name, schedule, time in cleaned:
        meds.add_medication(db_path, elder_id, name, schedule, time)
    return len(cleaned)
