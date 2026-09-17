"""What it means for a band to be characterised (solution spec Section 7.3).

This notion governs two things at once: where the randomised floor looks, and how much of the
receiver's time it gets. Getting it wrong is expensive in both directions, and the first two
attempts did.

Attempt one used the mean periodicity confidence across the spectrum. It plateaued around 0.22 on
scenario B and the floor took 61% of every episode for ever.

Attempt two used per-band periodicity confidence, which was worse: 72 to 89%. The reason is the
interesting one. **Periodicity confidence only rises for cleanly periodic emitters.** A band
holding a random or intermittent emitter never earns it, and an *empty* band never earns it either
-- yet an empty band is the most thoroughly characterised thing in the spectrum. We know exactly
what it is. Scoring it as unknown sends discretionary looks to the one place with nothing to find.

The right notion is evidence, not periodicity: a band is characterised when the model of it is
backed by enough looks. That is what the occupancy-kernel estimator already measures, so
characterisation is the better of its evidence weight and whatever the periodicity estimator can
add on top.
"""

from __future__ import annotations

import numpy as np
import pytest

from ml.agents.index_agent import IndexAgent
from ml.belief.kernel_learning import KernelEstimator
from ml.environments.state import StateBuilder

N = 8


class _Receiver:
    tuned_start = 0
    dwell_remaining_ms = 0
    tuning_delay_countdown_ms = 0

    def tuned_bands(self, k, n):
        return [(self.tuned_start + i) % n for i in range(k)]


def observation(confidence=0.0) -> np.ndarray:
    sb = StateBuilder(N)
    sb.update([], [], _Receiver(), 1)
    sb.periodicity_confidence = np.broadcast_to(
        np.asarray(confidence, dtype=np.float32), (N,)
    ).copy()
    return sb.to_vector()


def agent(**kwargs) -> IndexAgent:
    defaults = dict(num_bands=N, bandwidth_k=1, deadline_s=10.0, slot_s=0.010, retune_s=0.005)
    defaults.update(kwargs)
    a = IndexAgent(rng=np.random.default_rng(0), **defaults)
    a.start_episode()
    return a


# -- evidence confidence on the estimator ---------------------------------------------------------

def test_a_band_never_looked_at_has_no_evidence():
    est = KernelEstimator(N, p_d=0.9, p_fa=0.05)
    assert est.evidence_confidence() == pytest.approx(np.zeros(N))


def test_evidence_confidence_rises_with_looks():
    est = KernelEstimator(N, p_d=0.9, p_fa=0.05, prior_strength=20.0)
    before = float(est.evidence_confidence()[0])
    for t in range(30):
        est.observe(t, [0], [False])
    assert float(est.evidence_confidence()[0]) > before


def test_evidence_confidence_approaches_one_but_never_exceeds_it():
    est = KernelEstimator(N, p_d=0.9, p_fa=0.05, prior_strength=20.0)
    for t in range(5000):
        est.observe(t, [0], [t % 3 == 0])
    value = float(est.evidence_confidence()[0])
    assert 0.9 < value <= 1.0


def test_evidence_is_tracked_per_band():
    est = KernelEstimator(N, p_d=0.9, p_fa=0.05)
    for t in range(50):
        est.observe(t, [2], [False])
    confidence = est.evidence_confidence()
    assert float(confidence[2]) > float(confidence[5])


def test_a_stronger_prior_needs_more_looks_to_overcome():
    weak = KernelEstimator(N, p_d=0.9, p_fa=0.05, prior_strength=5.0)
    strong = KernelEstimator(N, p_d=0.9, p_fa=0.05, prior_strength=200.0)
    for t in range(50):
        weak.observe(t, [0], [False])
        strong.observe(t, [0], [False])
    assert float(weak.evidence_confidence()[0]) > float(strong.evidence_confidence()[0])


# -- the agent's combined notion ---------------------------------------------------------------------

def test_an_empty_band_becomes_characterised_by_being_looked_at():
    """The regression. An empty band is the most characterised thing in the spectrum."""
    a = agent()
    obs = observation(confidence=0.0)
    assert a.exploration_rate(obs) == pytest.approx(1.0)

    for t in range(400):
        a.select_action(obs)
        a.observe({"scanned_bands": a.last_bands, "detected_bands": []})
    assert a.exploration_rate(obs) < 0.3


def test_periodicity_confidence_can_characterise_a_band_on_its_own():
    """A band the estimator understands needs no further evidence to graduate."""
    a = agent()
    assert a.exploration_rate(observation(confidence=0.99)) == pytest.approx(a.rho_min)


def test_characterisation_takes_the_better_of_evidence_and_periodicity():
    a = agent()
    obs = observation(confidence=0.0)
    for t in range(400):
        a.select_action(obs)
        a.observe({"scanned_bands": a.last_bands, "detected_bands": []})
    by_evidence = a.exploration_rate(obs)
    by_both = a.exploration_rate(observation(confidence=0.99))
    assert by_both <= by_evidence


def test_the_floor_share_settles_near_its_minimum_once_the_spectrum_is_known():
    """The number that matters. 72% of every episode was the bug; this is the fix."""
    a = agent(rho_min=0.1)
    obs = observation(confidence=0.0)
    for t in range(600):
        a.select_action(obs)
        a.observe({"scanned_bands": a.last_bands, "detected_bands": []})
    assert a.exploration_rate(obs) == pytest.approx(0.1, abs=0.05)


def test_a_cold_start_is_still_all_floor():
    """Annealing sooner must not remove the opening condition the floor exists for."""
    assert agent().exploration_rate(observation(confidence=0.0)) == pytest.approx(1.0)


def test_resetting_the_episode_returns_to_a_cold_start():
    a = agent()
    obs = observation(confidence=0.0)
    for t in range(400):
        a.select_action(obs)
        a.observe({"scanned_bands": a.last_bands, "detected_bands": []})
    a.start_episode(1)
    assert a.exploration_rate(obs) == pytest.approx(1.0)
