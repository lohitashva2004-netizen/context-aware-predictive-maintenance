from pdm.trend import classify_trend


def hist(v, t, c):
    return {"vibration": v, "temperature": t, "current": c}


def flat(n=10):
    return hist([1] * n, [40.0] * n, [2.0] * n)


def test_short_history_is_stable():
    assert classify_trend(flat(6)) == "Stable"


def test_flat_is_stable():
    assert classify_trend(flat()) == "Stable"


def test_rising_on_any_channel():
    h = flat()
    h["temperature"] = [40.0] * 5 + [44.0] * 5      # +10 %
    assert classify_trend(h) == "Rising"


def test_falling():
    h = flat()
    h["temperature"] = [50.0] * 5 + [44.0] * 5
    assert classify_trend(h) == "Falling"


def test_small_drift_is_ignored():
    h = flat()
    h["temperature"] = [40.0] * 5 + [41.0] * 5      # +2.5 %
    assert classify_trend(h) == "Stable"


def test_rising_beats_falling():
    h = flat()
    h["temperature"] = [40.0] * 5 + [45.0] * 5
    h["current"] = [3.0] * 5 + [2.0] * 5
    assert classify_trend(h) == "Rising"
