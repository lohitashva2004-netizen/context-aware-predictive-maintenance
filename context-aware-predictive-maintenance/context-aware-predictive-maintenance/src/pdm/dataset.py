"""Synthetic training data.

IMPORTANT: no labelled real-fault recordings were available for the prototype,
so the training set is *synthesised* from the threshold-defined regions of the
feature space (report §4.2). Gaussian jitter around region centroids mimics the
sensor noise floor. Labels come from the same rules the firmware uses, which
means the classifier learns the threshold geometry - it does not learn anything
about real bearing or winding degradation. See the README "Limitations" section.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from .config import FEATURES
from .rules import classify_reading

# (vibration, temperature, current) centroids and noise sigma per channel.
_CENTROIDS = {
    "Normal":   (1.0, 40.0, 2.0),
    "Warning":  (5.0, 62.0, 3.7),
    "Critical": (9.0, 80.0, 5.5),
}
_SIGMA = (0.8, 3.0, 0.35)


def make_dataset(n_samples: int = 1001, seed: int = 42) -> pd.DataFrame:
    """Generate roughly ``n_samples`` labelled rows.

    Half of each class is jittered around the all-channel centroid; the other
    half has a *single* channel pushed to the class level while the rest stay
    healthy, so the model sees the "any one channel can trigger" behaviour.
    """
    rng = np.random.default_rng(seed)
    base = np.array(_CENTROIDS["Normal"])
    sigma = np.array(_SIGMA)
    per_class = n_samples // 3
    rows = []
    for cls, centroid in _CENTROIDS.items():
        centroid = np.array(centroid)
        for i in range(per_class):
            point = centroid.copy()
            if i % 2 == 1 and cls != "Normal":
                keep = rng.integers(0, 3)
                masked = base.copy()
                masked[keep] = centroid[keep]
                point = masked
            point = point + rng.normal(0.0, sigma)
            point[0] = max(0, round(point[0]))       # pulse counts are integers
            point[1] = float(np.clip(point[1], 20, 120))
            point[2] = float(np.clip(point[2], 0, 8))
            rows.append(point)
    df = pd.DataFrame(rows, columns=FEATURES)
    df["label"] = [classify_reading(*r) for r in df[FEATURES].itertuples(index=False)]
    return df.sample(frac=1.0, random_state=seed).reset_index(drop=True)
