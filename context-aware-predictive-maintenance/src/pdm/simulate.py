"""Scenario generator mirroring the 100-second bench test in report §5.3.

0-30 s   idle                               (~1 pulse, ~40 °C, ~2 A)
30-55 s  bearing perturbation + thermal     (3-4 pulses, ~59 °C)
55-75 s  overload, partial thermal recovery (4.5-5.5 A, ~50 °C)
75-100 s thermal climbs again               (~65 °C)

This is a *model of the reported test*, used for demos and unit tests. It is not
recorded sensor data.
"""

from __future__ import annotations

import numpy as np


def scenario_reading(t: float, rng: np.random.Generator) -> dict:
    vib, temp, cur = 1.0, 40.0, 2.0
    if t >= 30:
        vib = 3.5
        temp = 59.0
    if 55 <= t < 75:
        temp = 50.0
        cur = 5.0
    elif t >= 75:
        temp = 65.0
        cur = 3.0 if t >= 80 else 5.0
    vib = max(0, round(vib + rng.normal(0, 0.8)))
    temp = float(temp + rng.normal(0, 0.8))
    cur = float(max(cur + rng.normal(0, 0.25), 0))
    return {"vibration": vib, "temperature": round(temp, 1), "current": round(cur, 2)}


def run_scenario(duration_s: int = 100, step_s: int = 2, seed: int = 7):
    rng = np.random.default_rng(seed)
    return [(t, scenario_reading(t, rng)) for t in range(0, duration_s, step_s)]
