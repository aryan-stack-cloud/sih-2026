"""Period estimation from hits *and* misses (SCT solution spec Section 3.2).

The hits-only estimator in periodicity_estimator.py needs >= min_samples (8) distinct
activations before it will claim anything (Level 5 DoD). A band watched for a single cycle
never reaches that under a realistic scan schedule. Misses are informative: a look that found
nothing at time t rules out every (T, phi) pair that predicted illumination there. This module
uses that to recover a confident estimate from far sparser evidence -- the whole reason
RUNNING.md gives for the periodicity/scheduler interaction not yet meeting its DoD item.
"""

from __future__ import annotations

import numpy as np
import pytest

from periodicity.config import EstimatorConfig
from periodicity.estimator.periodicity_estimator import estimate_period_with_misses

CFG = EstimatorConfig()


def _cycle(period: int, on_steps: set[int], n_cycles: int, start: int = 0):
    """One (timestamp, detected) pair per step, `n_cycles` full periods starting at `start`."""
    out = []
    for t in range(start, start + period * n_cycles):
        out.append((float(t), (t - start) % period in on_steps))
    return out


def test_recovers_period_from_two_cycles_that_the_hits_only_estimator_cannot():
    """4 hits + 36 misses from two period-20 cycles: not enough activations for the old
    estimator (needs 8), but the misses pin the period down well before that count. A single
    cycle is deliberately not enough here either -- min_cycles_observed exists precisely so a
    span that has never repeated cannot masquerade as a confirmed period."""
    obs = _cycle(period=20, on_steps={0, 1}, n_cycles=2)
    assert sum(1 for _, z in obs if z) == 4  # sanity: far below min_samples

    e = estimate_period_with_misses(obs, CFG)
    assert e.usable
    assert e.period == pytest.approx(20, abs=1.0)
    assert e.confidence > 0.5


def test_does_not_claim_periodicity_from_misses_alone():
    """All misses, no detections at all: nothing to fold a period onto."""
    obs = [(float(t), False) for t in range(60)]
    e = estimate_period_with_misses(obs, CFG)
    assert not e.usable


def test_prefers_the_period_whose_misses_are_also_explained():
    """Two periods both explain the 2 hits (20 and its subharmonic-adjacent neighbours), but
    only the true one also explains where the misses fell across two full cycles."""
    obs = _cycle(period=20, on_steps={0, 1}, n_cycles=3)
    e = estimate_period_with_misses(obs, CFG)
    assert e.period == pytest.approx(20, abs=1.0)
    assert e.confidence > 0.9


def test_more_cycles_raises_confidence():
    one = estimate_period_with_misses(_cycle(20, {0, 1}, 1), CFG)
    three = estimate_period_with_misses(_cycle(20, {0, 1}, 3), CFG)
    assert three.confidence >= one.confidence


def test_random_emitter_does_not_produce_a_confident_claim():
    """Same hit rate as the periodic case, but scattered at random: no period should win big."""
    rng = np.random.default_rng(0)
    obs = [(float(t), bool(rng.random() < 0.1)) for t in range(200)]
    e = estimate_period_with_misses(obs, CFG)
    if e.usable:
        assert e.confidence < CFG.low_confidence_threshold


# -- Service integration: the point of all this is that Backend can now report misses too -------

def test_service_prefers_hits_and_misses_once_a_miss_is_recorded():
    """Fewer hits than the hits-only estimator's min_samples, but real misses recorded too:
    the service should route to estimate_period_with_misses and still produce a usable fit."""
    from periodicity.service import PeriodicityService

    svc = PeriodicityService(CFG)
    sim = "sim_svc_misses"
    for t, detected in _cycle(period=20, on_steps={0, 1}, n_cycles=3):
        if detected:
            svc.update(sim, band_id=5, detection_timestamp=t)
        else:
            svc.observe_miss(sim, band_id=5, timestamp=t)

    fit = svc.estimate(sim, band_id=5)
    assert fit.usable
    assert fit.period == pytest.approx(20, abs=1.0)
    assert fit.samples < CFG.min_samples  # fewer hit-activations than the old gate requires

    svc.reset(sim)


def test_service_falls_back_to_hits_only_with_no_misses_recorded():
    """No miss ever reported for this band: same behaviour as before this change."""
    from periodicity.service import PeriodicityService

    svc = PeriodicityService(CFG)
    sim = "sim_svc_hits_only"
    for k in range(12):
        svc.update(sim, band_id=2, detection_timestamp=float(k * 20))

    fit = svc.estimate(sim, band_id=2)
    assert fit.usable
    assert fit.period == pytest.approx(20, abs=0.3)

    svc.reset(sim)
