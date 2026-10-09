import pytest
from pdm.rules import classify_reading, channel_alerts, dominant_fault


@pytest.mark.parametrize("v,t,c,expected", [
    (1, 35, 0.0, "Normal"),
    (3, 55, 3.0, "Normal"),          # limits are strict "above"
    (4, 40, 2.0, "Warning"),
    (1, 60, 2.0, "Warning"),
    (1, 40, 3.5, "Warning"),
    (8, 40, 2.0, "Critical"),
    (1, 71, 2.0, "Critical"),
    (1, 40, 4.6, "Critical"),
    (4, 60, 3.5, "Warning"),         # several warnings are still Warning
    (8, 60, 3.5, "Critical"),        # worst channel wins
])
def test_classify_reading(v, t, c, expected):
    assert classify_reading(v, t, c) == expected


def test_channel_alerts_name_the_sensor():
    alerts = channel_alerts({"vibration": 1, "temperature": 72.0, "current": 3.4})
    assert alerts[0]["channel"] == "Temperature" and alerts[0]["level"] == "Critical"
    assert alerts[1]["channel"] == "Current" and alerts[1]["level"] == "Warning"


def test_dominant_fault():
    assert dominant_fault(1, 35, 2.0) is None
    assert dominant_fault(9, 40, 2.0) == "Bearing"
    assert dominant_fault(1, 40, 5.0) == "Overload"
    assert dominant_fault(1, 72, 2.0) == "Thermal"
