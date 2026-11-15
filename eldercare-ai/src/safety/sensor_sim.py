"""Simulated wearable accelerometer data (acceleration magnitude in g, 50 Hz, 4 s windows).

Entirely synthetic. It lets the fall-detection logic be demonstrated and tested; it says nothing
about how real people or real sensors behave.
"""
import numpy as np

HZ, SECONDS = 50, 4
N = HZ * SECONDS
T = np.arange(N) / HZ

SCENARIOS = {
    "standing": "Standing still",
    "sitting": "Sitting down gently",
    "walking": "Walking",
    "stairs": "Climbing stairs",
    "sit_hard": "Sitting down heavily",
    "stumble": "Stumble, then keeps walking",
    "fall_soft": "Soft fall, then lying still",
    "fall": "Hard fall, then lying still",
}
NORMAL = ("standing", "sitting", "walking", "stairs", "sit_hard")


def _walk(rng, amp, freq):
    return 1 + amp * np.sin(2 * np.pi * freq * T + rng.uniform(0, 6.28)) + rng.normal(0, 0.05, N)


def _bump(sig, center, height, width=0.06):
    return sig + height * np.exp(-0.5 * ((T - center) / width) ** 2)


def simulate(scenario: str, seed: int) -> np.ndarray:
    rng = np.random.default_rng(seed)
    if scenario == "standing":
        return 1 + rng.normal(0, 0.02, N)
    if scenario == "sitting":
        return _bump(1 + rng.normal(0, 0.03, N), rng.uniform(1, 3), rng.uniform(0.2, 0.5), 0.2)
    if scenario == "walking":
        return _walk(rng, rng.uniform(0.2, 0.35), rng.uniform(1.6, 2.0))
    if scenario == "stairs":
        return _walk(rng, rng.uniform(0.35, 0.55), rng.uniform(1.9, 2.4))
    if scenario == "sit_hard":
        return _bump(1 + rng.normal(0, 0.04, N), rng.uniform(1, 2.5), rng.uniform(0.7, 1.1), 0.08)
    if scenario == "stumble":
        sig = _walk(rng, 0.3, 1.8)
        return _bump(sig, rng.uniform(1, 2.5), rng.uniform(1.4, 1.9), 0.05)
    if scenario in ("fall", "fall_soft"):
        t0 = rng.uniform(1.0, 2.0)
        height = rng.uniform(2.2, 3.3) if scenario == "fall" else rng.uniform(1.6, 2.0)
        pre = _walk(rng, 0.25, 1.8)
        sig = np.where(T < t0 - 0.2, pre, 1 + rng.normal(0, 0.02, N))
        sig = np.where((T >= t0 - 0.2) & (T < t0), 0.3 + rng.normal(0, 0.05, N), sig)   # brief free-fall dip
        return _bump(sig, t0 + 0.02, height + 1.0 - 0.0, 0.04)
    raise ValueError("Unknown scenario")
