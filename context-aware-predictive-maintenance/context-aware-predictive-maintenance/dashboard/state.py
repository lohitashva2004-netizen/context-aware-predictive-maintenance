"""Thread-safe rolling buffers shared between the MQTT thread and Dash callbacks."""

from __future__ import annotations

import threading
import time
from collections import deque

from pdm.config import BUFFER_LENGTH, FEATURES


class TelemetryBuffer:
    """Sixty readings per channel (~2 minutes) - enough history for the
    classifier, the forecast fit and the trend indicator to share one buffer."""

    def __init__(self, maxlen: int = BUFFER_LENGTH):
        self._lock = threading.Lock()
        self._data = {f: deque(maxlen=maxlen) for f in FEATURES}
        self._state = deque(maxlen=maxlen)
        self._stamp = deque(maxlen=maxlen)
        self.last_update: float | None = None

    def add(self, payload: dict) -> None:
        with self._lock:
            for f in FEATURES:
                self._data[f].append(float(payload[f]))
            self._state.append(str(payload.get("state", "Unknown")))
            self._stamp.append(time.strftime("%H:%M:%S"))
            self.last_update = time.time()

    def snapshot(self) -> dict:
        with self._lock:
            snap = {f: list(self._data[f]) for f in FEATURES}
            snap["state"] = list(self._state)
            snap["time"] = list(self._stamp)
            snap["last_update"] = self.last_update
            return snap
