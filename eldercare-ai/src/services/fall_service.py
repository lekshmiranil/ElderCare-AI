"""Fall detection demo: a transparent rule plus a local ML anomaly check, on SIMULATED data only.

Rule (deterministic, configurable): a fall is flagged when the peak acceleration reaches the threshold AND
the person is almost still for the following 1.5 s. ML (anomaly.py): flags unusual movement. Outcome:
  fall    = rule triggered (impact + stillness)
  unusual = only the ML model flagged it
  none    = neither
No real-world accuracy is claimed: the data is synthetic.
"""
from datetime import datetime

import numpy as np

from src.ai.anomaly import detector
from src.database.connection import get_connection
from src.safety.sensor_sim import HZ
from src.services.medication_service import ValidationError
from src.services.notification_service import add_notification

DEFAULT_THRESHOLD, MIN_T, MAX_T, STILL_STD = 2.5, 1.5, 4.0, 0.15


def get_threshold(db_path) -> float:
    with get_connection(db_path) as c:
        row = c.execute("SELECT value FROM app_settings WHERE key='fall_threshold_g'").fetchone()
    try:
        return float(row["value"]) if row else DEFAULT_THRESHOLD
    except ValueError:
        return DEFAULT_THRESHOLD


def set_threshold(db_path, value: float) -> None:
    if not (MIN_T <= float(value) <= MAX_T):
        raise ValidationError(f"The threshold must be between {MIN_T} and {MAX_T} g.")
    with get_connection(db_path) as c:
        c.execute("INSERT INTO app_settings (key,value) VALUES ('fall_threshold_g',?) "
                  "ON CONFLICT(key) DO UPDATE SET value=excluded.value", (str(float(value)),))


def rule_detect(window: np.ndarray, threshold_g: float) -> dict:
    i = int(np.argmax(window))
    peak = float(window[i])
    after = window[min(i + HZ // 2, len(window) - 1):][: int(1.5 * HZ)]
    still_std = float(after.std()) if len(after) > 1 else 0.0
    return {"peak_g": peak, "still_std": still_std, "impact": peak >= threshold_g,
            "still": len(after) > 10 and still_std < STILL_STD,
            "triggered": peak >= threshold_g and len(after) > 10 and still_std < STILL_STD}


def assess(window: np.ndarray, threshold_g: float) -> dict:
    rule = rule_detect(window, threshold_g)
    score, unusual = detector().score(window)
    outcome = "fall" if rule["triggered"] else "unusual" if unusual else "none"
    return {**rule, "threshold_g": threshold_g, "ml_score": score, "ml_unusual": unusual, "outcome": outcome}


def record_event(db_path, elder_id: int, result: dict, scenario: str, now=None) -> None:
    """Store a fall/unusual-movement event and a SIMULATED caregiver notification. Nothing is ever sent."""
    now = now or datetime.now()
    if result["outcome"] == "none":
        return
    with get_connection(db_path) as c:
        c.execute("INSERT INTO fall_events (elder_id,detected_at,peak_g,threshold_g,simulated,kind,ml_score,scenario) "
                  "VALUES (?,?,?,?,1,?,?,?)", (elder_id, now.isoformat(timespec="seconds"), result["peak_g"],
                                               result["threshold_g"], result["outcome"], result["ml_score"], scenario))
    label = "Simulated fall detected" if result["outcome"] == "fall" else "Simulated unusual movement detected"
    add_notification(db_path, "fall", f"{label} (peak {result['peak_g']:.1f} g). Caregiver notification simulated.",
                     simulated=True, now=now)
