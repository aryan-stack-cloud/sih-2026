"""Prediction windows (Ai-ml-2 Level 6).

Level 6 DoD: given a fixture buffer of a known periodic sequence, the endpoint returns a
next-active-window that contains the true next activation time.
"""

from __future__ import annotations

import pytest

from periodicity.config import EstimatorConfig
from periodicity.estimator.periodicity_estimator import estimate_period
from periodicity.inference.prediction import (
    next_activation,
    phase_at,
    predict,
    window_halfwidth,
)

CFG = EstimatorConfig()


def clean(period: int = 20, cycles: int = 15, start: int = 0) -> list[float]:
    return [start + k * period for k in range(cycles)]


def test_window_contains_the_true_next_activation():
    """The Level 6 Definition of Done, stated directly."""
    ts = clean(period=20, cycles=15)          # activations at 0, 20, ... 280
    e = estimate_period(ts, CFG)
    p = predict(e, now=285.0, cfg=CFG)        # the true next activation is 300
    assert p.predicted_next_active_window is not None
    assert p.predicted_next_active_window.contains(300.0)


@pytest.mark.parametrize("period", [10, 20, 35, 50])
@pytest.mark.parametrize("offset", [1, 7])
def test_window_contains_the_next_activation_across_periods_and_phases(period, offset):
    ts = clean(period=period, cycles=15, start=offset)
    e = estimate_period(ts, CFG)
    last = ts[-1]
    p = predict(e, now=last + 1.0, cfg=CFG)
    assert p.predicted_next_active_window.contains(last + period)


def test_prediction_is_strictly_in_the_future():
    e = estimate_period(clean(), CFG)
    for now in (0.0, 55.0, 100.0, 283.5):
        assert next_activation(e, now) > now


def test_next_activation_advances_by_exactly_one_period():
    e = estimate_period(clean(period=20), CFG)
    first = next_activation(e, 100.0)
    second = next_activation(e, first + 0.001)
    assert second - first == pytest.approx(e.period, abs=0.01)


def test_phase_runs_forward_and_wraps():
    e = estimate_period(clean(period=20), CFG)
    ref = e.reference_time
    assert phase_at(e, ref) == pytest.approx(0.0, abs=0.01)
    assert phase_at(e, ref + 10) == pytest.approx(0.5, abs=0.05)
    assert phase_at(e, ref + 20) == pytest.approx(0.0, abs=0.01)


def test_a_tight_fit_gives_a_narrow_window_and_a_loose_one_gives_a_wide_window():
    import numpy as np

    def jittered(jitter):
        rng = np.random.default_rng(1)
        t, ts = 0, []
        for _ in range(20):
            ts.append(t)
            t += 20 + (int(rng.integers(-jitter, jitter + 1)) if jitter else 0)
        return window_halfwidth(estimate_period(ts, CFG), CFG)

    assert jittered(0) < jittered(4)


def test_window_never_collapses_below_a_schedulable_step():
    e = estimate_period(clean(), CFG)
    assert window_halfwidth(e, CFG) >= CFG.min_window_halfwidth


def test_window_never_spans_more_than_half_a_period():
    """A window covering the whole cycle is the same as saying nothing."""
    import numpy as np

    rng = np.random.default_rng(5)
    t, ts = 0, []
    for _ in range(24):
        ts.append(t)
        t += 20 + int(rng.integers(-9, 10))
    e = estimate_period(ts, CFG)
    if e.usable:
        assert window_halfwidth(e, CFG) <= e.period * CFG.max_window_halfwidth_fraction + 1e-9


# -- the explicit "no claim" ---------------------------------------------------------------------

def test_unusable_estimate_yields_a_well_formed_nothing():
    """The Backend calls predict for every band, including ones holding nothing periodic."""
    e = estimate_period([0, 5], CFG)
    p = predict(e, now=10.0, cfg=CFG)
    assert p.predicted_next_active_window is None
    assert p.estimated_period is None
    assert p.confidence == 0.0
    assert p.reason


def test_no_claim_serialises_to_the_contract_shape_with_nulls():
    p = predict(estimate_period([0, 5], CFG), now=10.0, cfg=CFG)
    body = p.to_contract()
    assert set(body) == {"predicted_next_active_window", "estimated_period", "confidence"}
    assert body["predicted_next_active_window"] is None
    assert body["confidence"] == 0.0


def test_usable_prediction_serialises_to_the_contract_shape():
    p = predict(estimate_period(clean(), CFG), now=285.0, cfg=CFG)
    body = p.to_contract()
    assert set(body) == {"predicted_next_active_window", "estimated_period", "confidence"}
    assert set(body["predicted_next_active_window"]) == {"start", "end"}
    assert body["estimated_period"] == pytest.approx(20, abs=0.5)


def test_phase_of_an_unusable_estimate_is_zero_not_an_error():
    assert phase_at(estimate_period([0, 5], CFG), 10.0) == 0.0
