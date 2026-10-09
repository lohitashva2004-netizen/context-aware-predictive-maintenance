"""Short-horizon forecasting by least-squares linear extrapolation."""

from __future__ import annotations

from typing import Mapping, Optional, Sequence

import numpy as np

from .config import FEATURES, FORECAST_FIT_WINDOW, FORECAST_HORIZON_STEPS


def project_channel(values: Sequence[float], window: int = FORECAST_FIT_WINDOW,
                    horizon: int = FORECAST_HORIZON_STEPS) -> Optional[float]:
    """Fit a straight line to the last ``window`` readings and extend it
    ``horizon`` steps. Returns None until enough history exists."""
    recent = np.asarray(list(values)[-window:], dtype=float)
    if recent.size < 3:
        return None
    x = np.arange(recent.size)
    slope, intercept = np.polyfit(x, recent, 1)
    projected = slope * (recent.size - 1 + horizon) + intercept
    return float(max(projected, 0.0))   # none of the channels can go negative


def project_reading(history: Mapping[str, Sequence[float]], **kwargs) -> Optional[dict]:
    """Project all three channels; the result has the same keys as a live reading,
    so it can be fed straight into the same classifier."""
    out = {}
    for ch in FEATURES:
        value = project_channel(history[ch], **kwargs)
        if value is None:
            return None
        out[ch] = value
    return out
