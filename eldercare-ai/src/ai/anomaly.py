"""Local anomaly detection for wearable-style sensor windows (Isolation Forest, scikit-learn).

Method: summarise each 4 s window with nine numbers (peak, minimum, spread, jerk, time spent above 1.5 g,
stillness after the peak, ...) and train an Isolation Forest on SIMULATED NORMAL daily movement only.
Windows that look unlike normal movement get a high anomaly score. It is not trained on falls, so it
reports "unusual movement", not "fall". No network, no API; fixed random_state for repeatable results.
"""
from functools import lru_cache

import numpy as np
from sklearn.ensemble import IsolationForest

from src.safety.sensor_sim import HZ, NORMAL, simulate


def features(w: np.ndarray) -> list:
    i = int(np.argmax(w))
    after = w[min(i + HZ // 2, len(w) - 1):][: int(1.5 * HZ)]
    return [float(w.max()), float(w.min()), float(w.std()), float(w.mean()), float(np.ptp(w)),
            float(np.abs(np.diff(w)).max()), float((w > 1.5).mean()), float((w < 0.6).mean()),
            float(after.std()) if len(after) > 1 else 0.0]


class AnomalyDetector:
    def __init__(self, per_scenario: int = 120, contamination: float = 0.01):
        X = [features(simulate(s, seed)) for s in NORMAL for seed in range(per_scenario)]
        self.model = IsolationForest(n_estimators=200, contamination=contamination, random_state=0).fit(X)

    def score(self, window: np.ndarray):
        """Return (anomaly_score, is_unusual). Higher score = more unusual; flagged when the model says outlier."""
        x = [features(window)]
        return float(-self.model.decision_function(x)[0]), bool(self.model.predict(x)[0] == -1)


@lru_cache(maxsize=1)
def detector() -> AnomalyDetector:
    return AnomalyDetector()
