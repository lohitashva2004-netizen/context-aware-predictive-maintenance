"""Replay the simulated bench scenario through the Random Forest and plot the
sensor traces, severity output and forecast. Writes docs/images/replay_summary.png.

    python scripts/replay_scenario.py
"""

from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

from pdm.config import FEATURES, THRESHOLDS
from pdm.forecast import project_reading
from pdm.model import load_or_train, predict_label
from pdm.simulate import run_scenario

OUT = Path(__file__).resolve().parents[1] / "docs" / "images" / "replay_summary.png"
LEVEL = {"Normal": 0, "Warning": 1, "Critical": 2}


def main() -> None:
    model = load_or_train()
    hist = {f: [] for f in FEATURES}
    times, state, future = [], [], []
    for t, r in run_scenario():
        for f in FEATURES:
            hist[f].append(r[f])
        times.append(t)
        state.append(LEVEL[predict_label(model, r)])
        proj = project_reading(hist)
        future.append(LEVEL[predict_label(model, proj)] if proj else None)

    fig, ax = plt.subplots(4, 1, figsize=(9, 9), sharex=True)
    for a, (f, title) in zip(ax, [("vibration", "Vibration (pulses / 2 s)"), ("temperature", "Temperature (°C)"), ("current", "Current (A)")]):
        a.plot(times, hist[f], lw=1.4)
        a.axhline(THRESHOLDS[f]["warning"], color="#eab308", ls=":", lw=1)
        a.axhline(THRESHOLDS[f]["critical"], color="#ef4444", ls=":", lw=1)
        a.set_ylabel(title, fontsize=8)
    ax[3].step(times, state, where="post", label="Random Forest (live)")
    ax[3].step(times, [x if x is not None else 0 for x in future], where="post", ls="--", label="Forecast (+20 s)")
    ax[3].set_yticks([0, 1, 2], ["Normal", "Warning", "Critical"])
    ax[3].set_xlabel("Time (s)"); ax[3].legend(fontsize=8, loc="upper left")
    fig.suptitle("Software replay of the simulated 100 s bench scenario", fontsize=11)
    fig.tight_layout()
    fig.savefig(OUT, dpi=140)
    print("saved", OUT)


if __name__ == "__main__":
    main()
