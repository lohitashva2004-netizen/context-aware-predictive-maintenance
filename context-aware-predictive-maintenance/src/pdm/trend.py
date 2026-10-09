"""Composite Rising / Falling / Stable indicator.

Deliberately simple: compare the mean of the latest five readings with the mean
of the five before them on every channel. It gives an operator an instant
"is this heading the wrong way?" signal without reading probability bars.
"""

from __future__ import annotations

from typing import Mapping, Sequence

import numpy as np

from .config import FEATURES, TREND_FLOORS, TREND_THRESHOLD, TREND_WINDOW


def classify_trend(history: Mapping[str, Sequence[float]]) -> str:
    n = TREND_WINDOW
    rising = falling = False
    for ch in FEATURES:
        vals = np.asarray(list(history[ch]), dtype=float)
        if vals.size < 2 * n:
            return "Stable"                      # not enough history yet
        prev, last = vals[-2 * n:-n].mean(), vals[-n:].mean()
        change = (last - prev) / max(abs(prev), TREND_FLOORS[ch])
        rising |= change > TREND_THRESHOLD
        falling |= change < -TREND_THRESHOLD
    if rising:                                   # the cautious reading wins a tie
        return "Rising"
    return "Falling" if falling else "Stable"
