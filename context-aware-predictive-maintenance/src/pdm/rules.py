"""Deterministic threshold logic - the Python twin of the ESP32 firmware state machine."""

from __future__ import annotations

from typing import Mapping, Optional

from .config import THRESHOLDS


def classify_reading(vibration: float, temperature: float, current: float) -> str:
    """Return 'Normal', 'Warning' or 'Critical' using the firmware thresholds."""
    values = {"vibration": vibration, "temperature": temperature, "current": current}
    if any(values[k] > THRESHOLDS[k]["critical"] for k in values):
        return "Critical"
    if any(values[k] > THRESHOLDS[k]["warning"] for k in values):
        return "Warning"
    return "Normal"


def channel_alerts(reading: Mapping[str, float]) -> list[dict]:
    """List every channel that is above a limit, worst first.

    Naming the offending channel is deliberate: an operator with a few seconds
    to decide needs to know *which* sensor tripped, not just a probability.
    """
    labels = {"vibration": "Vibration", "temperature": "Temperature", "current": "Current"}
    out = []
    for ch, limits in THRESHOLDS.items():
        v = reading[ch]
        if v > limits["critical"]:
            level = "Critical"
        elif v > limits["warning"]:
            level = "Warning"
        else:
            continue
        out.append({"channel": labels[ch], "level": level, "value": v, "unit": limits["unit"]})
    out.sort(key=lambda a: a["level"] != "Critical")
    return out


_FAULT_NAMES = {"vibration": "Bearing", "current": "Overload", "temperature": "Thermal"}


def dominant_fault(vibration: float, temperature: float, current: float) -> Optional[str]:
    """Map the channel closest to its critical limit onto a fault family.

    vibration -> Bearing, current -> Overload, temperature -> Thermal.
    Returns None when the machine is Normal.
    """
    values = {"vibration": vibration, "temperature": temperature, "current": current}
    if classify_reading(**values) == "Normal":
        return None
    ratio = {k: values[k] / THRESHOLDS[k]["critical"] for k in values}
    return _FAULT_NAMES[max(ratio, key=ratio.get)]
