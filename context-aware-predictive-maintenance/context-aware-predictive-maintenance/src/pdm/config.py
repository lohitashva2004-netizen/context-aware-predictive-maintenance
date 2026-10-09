"""Shared constants. Keep these in sync with firmware/esp32_edge_node/config.h."""

# Feature order is part of the model contract: training and inference must agree.
FEATURES = ["vibration", "temperature", "current"]
CLASSES = ["Normal", "Warning", "Critical"]

# Firmware / dataset thresholds (Table 4 of the project report).
# A reading is Warning when a value is ABOVE its warning limit and
# Critical when ABOVE its critical limit. Calibrated for the laboratory motor.
THRESHOLDS = {
    "vibration":   {"warning": 3,    "critical": 7,    "unit": "pulses / 2 s"},
    "temperature": {"warning": 55.0, "critical": 70.0, "unit": "°C"},
    "current":     {"warning": 3.0,  "critical": 4.5,  "unit": "A"},
}

SAMPLE_PERIOD_S = 2          # one reading every two seconds
BUFFER_LENGTH = 60           # readings kept per channel (~2 minutes)
FORECAST_FIT_WINDOW = 10     # readings used for the linear fit
FORECAST_HORIZON_STEPS = 10  # steps ahead (~20 s)
TREND_WINDOW = 5             # readings per comparison block
TREND_THRESHOLD = 0.05       # 5 % drift flags Rising / Falling

# Floors stop near-zero baselines (e.g. idle current of 0.02 A) from turning
# tiny absolute changes into huge percentage swings in the trend indicator.
TREND_FLOORS = {"vibration": 1.0, "temperature": 1.0, "current": 0.1}
