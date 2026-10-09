"""Random Forest wrapper: train, persist, load, predict_proba."""

from __future__ import annotations

from pathlib import Path
from typing import Mapping

import joblib
import pandas as pd
from sklearn.ensemble import RandomForestClassifier

from .config import CLASSES, FEATURES
from .dataset import make_dataset

DEFAULT_MODEL_PATH = Path(__file__).resolve().parents[2] / "models" / "rf_model.joblib"


def train(df: pd.DataFrame | None = None, seed: int = 42) -> RandomForestClassifier:
    """Fit the 100-tree forest described in the report (bootstrap sampling on)."""
    df = make_dataset(seed=seed) if df is None else df
    model = RandomForestClassifier(n_estimators=100, random_state=seed, n_jobs=-1)
    model.fit(df[FEATURES], df["label"])
    return model


def load_or_train(path: Path | str = DEFAULT_MODEL_PATH) -> RandomForestClassifier:
    """Load the committed model; retrain transparently if it is missing or
    was pickled by an incompatible scikit-learn version."""
    path = Path(path)
    try:
        return joblib.load(path)
    except Exception:
        return train()


def predict_proba(model: RandomForestClassifier, reading: Mapping[str, float]) -> dict:
    """Per-class probabilities for one reading, always ordered Normal/Warning/Critical.

    The one-row DataFrame uses the exact training column names, which avoids
    feature-name warnings and silent column-order bugs.
    """
    frame = pd.DataFrame([[reading[f] for f in FEATURES]], columns=FEATURES)
    proba = model.predict_proba(frame)[0]
    by_class = dict(zip(model.classes_, proba))
    return {c: float(by_class.get(c, 0.0)) for c in CLASSES}


def predict_label(model: RandomForestClassifier, reading: Mapping[str, float]) -> str:
    probs = predict_proba(model, reading)
    return max(probs, key=probs.get)


def fault_probability(probs: Mapping[str, float]) -> float:
    """Composite fault percentage = P(Warning) + P(Critical)."""
    return probs["Warning"] + probs["Critical"]
