import os

import pytest

from povichain.core.errors import CalibrationError, InsufficientCalibrationLength
from povichain.ingestion.calibration_loader import load_processed_calibration
from povichain.ingestion.trace_loader import (
    EnvelopeFixedReplay,
    ExactCycleReplay,
    ExactOnceReplay,
    MedianFixedReplay,
    make_replay,
)


ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
SCHEMA = os.path.join(ROOT, "schemas", "processed_calibration.schema.json")
PLACEHOLDER = os.path.join(
    ROOT, "data", "placeholders", "processed", "device_profiles.placeholder.yaml"
)


def test_exact_cycle_replay_wraps_around():
    r = ExactCycleReplay((1.0, 2.0, 3.0))
    assert [r.next_value() for _ in range(7)] == [1.0, 2.0, 3.0, 1.0, 2.0, 3.0, 1.0]


def test_exact_once_replay_raises_on_exhaustion():
    r = ExactOnceReplay((1.0, 2.0))
    r.next_value()
    r.next_value()
    with pytest.raises(InsufficientCalibrationLength):
        r.next_value()


def test_median_fixed_returns_median():
    r = MedianFixedReplay((10.0, 20.0, 30.0, 40.0, 50.0))
    assert r.next_value() == 30.0


def test_envelope_fixed_bands():
    data = (10.0, 20.0, 30.0, 40.0, 50.0)
    assert EnvelopeFixedReplay(data, "low").next_value() == 10.0
    assert EnvelopeFixedReplay(data, "median").next_value() == 30.0
    assert EnvelopeFixedReplay(data, "high").next_value() == 50.0


def test_make_replay_rejects_unknown_mode():
    with pytest.raises(ValueError):
        make_replay("stochastic", (1.0,))


def test_load_processed_calibration_matches_placeholder():
    try:
        import yaml  # noqa: F401
    except Exception:
        pytest.skip("pyyaml_missing")
    cal = load_processed_calibration(PLACEHOLDER, SCHEMA)
    assert cal.pi4_groth16 is not None
    assert cal.pi4_stark is not None
    assert cal.esp32 is not None
    assert cal.calibration_policy.replay_mode is not None
