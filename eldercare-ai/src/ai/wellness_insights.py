"""Local statistical analysis of self-reported wellness check-ins (linear regression, robust comparison, correlation).

Input: check-ins (mood, wellbeing, activity, scores 1-5) oldest first. Output: findings, each with its evidence.
Limitations: small samples, self-reported data, correlation is not cause, and nothing here is a diagnosis.
It needs at least MIN_POINTS check-ins and says nothing otherwise.
"""
from dataclasses import dataclass
from datetime import date
from statistics import median

import numpy as np
from sklearn.linear_model import LinearRegression

MIN_POINTS = 5
TREND_PER_WEEK = 0.5     # score points per week
MIN_R2 = 0.3
SHIFT = 1.0              # recent median vs earlier median
CORR = 0.6
METRICS = ("mood", "wellbeing", "activity")


@dataclass(frozen=True)
class Finding:
    kind: str          # trend | shift | variability | association
    metric: str
    text: str
    evidence: dict


def analyze_patterns(checkins) -> list:
    if len(checkins) < MIN_POINTS:
        return []
    days = np.array([(date.fromisoformat(c["checkin_date"]) - date.fromisoformat(checkins[0]["checkin_date"])).days
                     for c in checkins]).reshape(-1, 1)
    out = []
    for m in METRICS:
        y = np.array([c[m] for c in checkins], dtype=float)
        reg = LinearRegression().fit(days, y)
        slope_week, r2 = float(reg.coef_[0]) * 7, float(reg.score(days, y))
        if abs(slope_week) >= TREND_PER_WEEK and r2 >= MIN_R2:
            direction = "downward" if slope_week < 0 else "upward"
            out.append(Finding("trend", m, f"Self-reported {m} has trended {direction} by about {abs(slope_week):.1f} points "
                               f"per week over {len(checkins)} check-ins.", {"slope_per_week": round(slope_week, 2), "r2": round(r2, 2)}))
        if len(checkins) >= 7:
            recent, earlier = median(y[-3:]), median(y[:-3])
            if abs(recent - earlier) >= SHIFT:
                word = "lower" if recent < earlier else "higher"
                out.append(Finding("shift", m, f"The last 3 {m} scores are {word} than earlier ones (median {recent:g} "
                                   f"compared with {earlier:g}).", {"recent_median": recent, "earlier_median": earlier}))
    mood = np.array([c["mood"] for c in checkins], dtype=float)
    if len(checkins) >= 7 and mood.std() > 1.0:
        out.append(Finding("variability", "mood", f"Self-reported mood has varied a lot (standard deviation {mood.std():.1f}).",
                           {"std": round(float(mood.std()), 2)}))
    act = np.array([c["activity"] for c in checkins], dtype=float)
    if len(checkins) >= 7 and mood.std() >= 0.5 and act.std() >= 0.5:
        r = float(np.corrcoef(act, mood)[0, 1])
        if r >= CORR:
            out.append(Finding("association", "mood", f"On days with lower activity, mood also tended to be lower (correlation "
                               f"{r:.2f}). This is an association, not proof of cause.", {"correlation": round(r, 2)}))
    return out
