"""Estimator against hand-computed inter-arrival sequences (Ai-ml-2 Levels 4, 5, 7)."""

from __future__ import annotations

import numpy as np
import pytest

from periodicity.config import EstimatorConfig
from periodicity.estimator.periodicity_estimator import (
    cluster_activations,
    estimate_period,
    independent_trials,
    rayleigh_p,
)

CFG = EstimatorConfig()


# -- Level 4: constant period ------------------------------------------------------------------

@pytest.mark.parametrize("period", [10, 15, 20, 35, 50])
def test_recovers_a_clean_constant_period(period):
    ts = [k * period for k in range(12)]
    e = estimate_period(ts, CFG)
    assert e.usable
    assert e.period == pytest.approx(period, abs=0.3)
    assert e.confidence > 0.99


def test_recovers_period_when_the_series_does_not_start_at_zero():
    e = estimate_period([7 + k * 20 for k in range(12)], CFG)
    assert e.period == pytest.approx(20, abs=0.3)


def test_phase_and_reference_time_locate_the_cycle():
    ts = [7 + k * 20 for k in range(12)]
    e = estimate_period(ts, CFG)
    # reference_time is a moment at phase 0; activations sit a whole number of periods from it.
    offset = (ts[-1] - e.reference_time) % e.period
    assert min(offset, e.period - offset) < 0.5


# -- Level 4: the sparse-sampling case that breaks median inter-arrival --------------------------

def test_recovers_the_period_when_cycles_were_missed():
    """The receiver is elsewhere most of the time, so gaps are multiples of the period.

    Median inter-arrival would report 40 here. Phase folding recovers 20.
    """
    ts = [0, 40, 60, 120, 160, 200, 260, 300, 360, 400]
    gaps = np.diff(ts)
    assert np.median(gaps) != 20  # the naive answer is wrong...
    e = estimate_period(ts, CFG)
    assert e.period == pytest.approx(20, abs=0.5)  # ...and the fit is right
    assert e.confidence > 0.95


def test_prefers_the_fundamental_over_its_divisors():
    """5 and 10 fold these as tightly as 20 does; 20 is the answer that predicts correctly."""
    e = estimate_period([k * 20 for k in range(10)], CFG)
    assert e.period == pytest.approx(20, abs=0.3)


# -- Level 5: jitter and confidence -------------------------------------------------------------

def test_recovers_a_jittered_period():
    rng = np.random.default_rng(0)
    t, ts = 0, []
    for _ in range(20):
        ts.append(t)
        t += 20 + int(rng.integers(-3, 4))
    e = estimate_period(ts, CFG)
    assert e.period == pytest.approx(20, abs=1.5)
    assert e.confidence > 0.95


def test_confidence_degrades_with_jitter():
    def fit(jitter):
        rng = np.random.default_rng(3)
        t, ts = 0, []
        for _ in range(16):
            ts.append(t)
            t += 20 + (int(rng.integers(-jitter, jitter + 1)) if jitter else 0)
        return estimate_period(ts, CFG).resultant_length

    assert fit(0) > fit(3) > fit(8)


def test_no_estimate_below_minimum_samples():
    e = estimate_period([0, 20, 40], CFG)
    assert not e.usable
    assert e.confidence == 0.0
    assert "activations" in e.reason


def test_no_estimate_when_the_span_is_too_short_to_show_a_repeat():
    e = estimate_period([100, 101, 102, 103, 104, 105, 106, 107, 108], CFG)
    assert not e.usable


def test_confidence_improves_as_consistent_activations_accumulate():
    seen = [estimate_period([k * 20 for k in range(n)], CFG).confidence for n in (8, 12, 20, 40)]
    assert seen == sorted(seen)


# -- Level 7: no false claims on the four non-periodic classes -----------------------------------

def _false_positive_rate(generator, n_activations: int, trials: int = 60) -> float:
    claims = 0
    for seed in range(trials):
        e = estimate_period(generator(seed, n_activations), CFG)
        if e.confidence > CFG.low_confidence_threshold:
            claims += 1
    return claims / trials


def gen_random(seed: int, n: int) -> list[float]:
    """PRD 'random' class: stochastic per-slot activation -> memoryless gaps."""
    rng = np.random.default_rng(seed)
    t, ts = 0, []
    while len(ts) < n:
        t += 1 + int(rng.geometric(0.12))
        ts.append(t)
    return ts


def gen_intermittent(seed: int, n: int) -> list[float]:
    """PRD 'intermittent' class: bursts of activity with variable silent gaps."""
    rng = np.random.default_rng(seed)
    t, ts = 0, []
    while len(ts) < n:
        t += int(rng.integers(20, 60))
        for _ in range(int(rng.integers(2, 6))):
            ts.append(t)
            t += 1
            if len(ts) >= n:
                break
    return ts


def gen_fixed(seed: int, n: int) -> list[float]:
    """PRD 'fixed' class: continuously active, so detected on consecutive steps."""
    return [100 + i for i in range(n * 3)]


def gen_agile(seed: int, n: int) -> list[float]:
    """PRD 'agile' class: hops away and back, so this band sees irregular clusters."""
    rng = np.random.default_rng(seed)
    t, ts = 0, []
    while len(ts) < n:
        t += int(rng.integers(5, 40))
        for _ in range(int(rng.integers(1, 4))):
            ts.append(t)
            t += 1
            if len(ts) >= n:
                break
    return ts


@pytest.mark.parametrize(
    "generator", [gen_random, gen_intermittent, gen_fixed, gen_agile],
    ids=["random", "intermittent", "fixed", "agile"],
)
def test_no_false_periodicity_claims_on_non_periodic_emitters(generator):
    """Level 7 DoD, stated as a measured false-positive rate.

    Confidence is 1 - p, so at the documented 0.95 threshold the false-positive rate should sit
    around the nominal 5%. Allowing 15% leaves room for sampling noise at 60 trials without
    letting a genuine regression through.
    """
    rate = _false_positive_rate(generator, n_activations=40)
    assert rate <= 0.15, f"{generator.__name__} claimed periodicity {rate:.0%} of the time"


def test_periodic_emitters_are_still_detected_confidently():
    """The other half of Level 7: suppressing false claims must not suppress true ones."""
    def gen(seed, n):
        rng = np.random.default_rng(seed)
        ts = []
        for k in range(400):
            if rng.random() < 0.4:
                ts.append(k * 20)
            if len(ts) >= n:
                break
        return ts

    claims = sum(
        estimate_period(gen(s, 25), CFG).confidence > CFG.low_confidence_threshold
        for s in range(40)
    )
    assert claims >= 38


# -- the two statistical corrections ------------------------------------------------------------

def test_activation_clustering_collapses_one_burst_into_one_sample():
    ts = np.array([10.0, 11.0, 12.0, 50.0, 51.0, 90.0])
    assert cluster_activations(ts, gap=3.0).tolist() == [10.0, 50.0, 90.0]


def test_clustering_keeps_well_separated_detections_apart():
    ts = np.array([0.0, 20.0, 40.0])
    assert cluster_activations(ts, gap=3.0).tolist() == [0.0, 20.0, 40.0]


def test_rayleigh_p_falls_as_concentration_rises():
    assert rayleigh_p(20, 0.1) > rayleigh_p(20, 0.5) > rayleigh_p(20, 0.95)


def test_rayleigh_p_falls_as_samples_accumulate():
    assert rayleigh_p(5, 0.7) > rayleigh_p(20, 0.7) > rayleigh_p(60, 0.7)


def test_look_elsewhere_correction_scales_with_the_search_range():
    """Searching more periods must cost confidence, or the best of 2000 always looks great."""
    narrow = independent_trials(span=200, min_period=3, max_period=10)
    wide = independent_trials(span=200, min_period=3, max_period=200)
    assert wide > narrow >= 1.0


def test_duplicate_timestamps_do_not_inflate_the_evidence():
    clean = estimate_period([k * 20 for k in range(12)], CFG)
    duped = estimate_period([k * 20 for k in range(12)] * 3, CFG)
    assert duped.samples == clean.samples
