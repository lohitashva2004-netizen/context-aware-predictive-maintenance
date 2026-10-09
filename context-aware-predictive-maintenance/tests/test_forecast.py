import pytest
from pdm.forecast import project_channel, project_reading


def test_needs_history():
    assert project_channel([40.0, 41.0]) is None


def test_linear_ramp_is_extrapolated_exactly():
    # +1 °C per step; last of 10 points is 49 -> 10 steps later is 59
    history = [40.0 + i for i in range(10)]
    assert project_channel(history) == pytest.approx(59.0)


def test_flat_signal_stays_flat():
    assert project_channel([2.0] * 10) == pytest.approx(2.0)


def test_never_negative():
    assert project_channel([5, 4, 3, 2, 1, 0, 0, 0, 0, 0]) >= 0


def test_uses_only_latest_window():
    old_spike = [100.0] * 20
    recent = [40.0 + i for i in range(10)]
    assert project_channel(old_spike + recent) == pytest.approx(59.0)


def test_project_reading_has_model_features():
    h = {"vibration": [1] * 10, "temperature": [40.0 + i for i in range(10)], "current": [2.0] * 10}
    out = project_reading(h)
    assert set(out) == {"vibration", "temperature", "current"}
    assert project_reading({"vibration": [1], "temperature": [1], "current": [1]}) is None
