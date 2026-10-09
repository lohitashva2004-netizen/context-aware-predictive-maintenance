import pytest
from pdm.dataset import make_dataset
from pdm.forecast import project_reading
from pdm.model import fault_probability, predict_label, predict_proba, train
from pdm.rules import classify_reading
from pdm.simulate import run_scenario


@pytest.fixture(scope="module")
def model():
    return train(make_dataset())


def test_dataset_shape_and_classes():
    df = make_dataset()
    assert 990 <= len(df) <= 1010
    assert set(df["label"]) == {"Normal", "Warning", "Critical"}
    assert list(df.columns[:3]) == ["vibration", "temperature", "current"]


def test_dataset_is_reproducible():
    assert make_dataset(seed=1).equals(make_dataset(seed=1))


def test_probabilities_sum_to_one(model):
    p = predict_proba(model, {"vibration": 2, "temperature": 45.0, "current": 2.5})
    assert sum(p.values()) == pytest.approx(1.0)
    assert list(p) == ["Normal", "Warning", "Critical"]


@pytest.mark.parametrize("reading,expected", [
    ({"vibration": 1, "temperature": 38.0, "current": 1.8}, "Normal"),
    ({"vibration": 5, "temperature": 62.0, "current": 3.6}, "Warning"),
    ({"vibration": 9, "temperature": 80.0, "current": 5.5}, "Critical"),
    ({"vibration": 1, "temperature": 75.0, "current": 2.0}, "Critical"),
])
def test_canonical_points(model, reading, expected):
    assert predict_label(model, reading) == expected


def test_fault_probability(model):
    p = predict_proba(model, {"vibration": 9, "temperature": 80.0, "current": 5.5})
    assert fault_probability(p) > 0.9


def test_scenario_replay_agrees_with_rules_mostly(model):
    """Over the 100 s bench-test replay the forest should track the rule logic."""
    run = run_scenario()
    agree = sum(predict_label(model, r) == classify_reading(**r) for _, r in run)
    assert agree / len(run) > 0.85


def test_forecast_warns_before_threshold(model):
    """A steady thermal ramp should be flagged Warning before 55 °C is reached."""
    temps = [40.0 + 1.2 * i for i in range(10)]            # last = 50.8 °C (< 55)
    hist = {"vibration": [1] * 10, "temperature": temps, "current": [2.0] * 10}
    assert classify_reading(1, temps[-1], 2.0) == "Normal"
    projected = project_reading(hist)
    assert predict_label(model, projected) in ("Warning", "Critical")
