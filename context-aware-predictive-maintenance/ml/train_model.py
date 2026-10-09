"""Generate the synthetic dataset, train the Random Forest and save artefacts.

    python ml/train_model.py

Writes:
    data/synthetic_dataset.csv   the ~1000 labelled samples
    models/rf_model.joblib       the trained 100-tree forest
    models/training_report.json  sanity-check metrics + feature importances
"""

import json
from pathlib import Path

import joblib
from sklearn.metrics import classification_report
from sklearn.model_selection import train_test_split

from pdm.config import FEATURES
from pdm.dataset import make_dataset
from pdm.model import train

ROOT = Path(__file__).resolve().parents[1]


def main() -> None:
    df = make_dataset()
    (ROOT / "data").mkdir(exist_ok=True)
    (ROOT / "models").mkdir(exist_ok=True)
    df.to_csv(ROOT / "data" / "synthetic_dataset.csv", index=False)

    # Hold-out check only: labels are threshold-defined, so a high score here
    # shows the model learned the threshold geometry, NOT real-world accuracy.
    tr, te = train_test_split(df, test_size=0.25, stratify=df["label"], random_state=42)
    check = train(tr)
    report = classification_report(te["label"], check.predict(te[FEATURES]), output_dict=True)

    final = train(df)
    joblib.dump(final, ROOT / "models" / "rf_model.joblib")

    summary = {
        "n_samples": len(df),
        "class_counts": df["label"].value_counts().to_dict(),
        "holdout_accuracy_synthetic": round(report["accuracy"], 4),
        "feature_importances": {f: round(float(i), 4) for f, i in zip(FEATURES, final.feature_importances_)},
        "note": "Synthetic, rule-labelled data. Not evidence of real-world fault-detection accuracy.",
    }
    (ROOT / "models" / "training_report.json").write_text(json.dumps(summary, indent=2))
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
