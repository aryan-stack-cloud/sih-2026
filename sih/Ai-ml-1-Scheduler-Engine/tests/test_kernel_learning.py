"""Learning the occupancy transition kernel from hits and misses (solution spec Section 3.1).

The problem statement asks for exactly this: "The model should then be trained based on hits and
misses." Until now the occupancy chain used fixed p01 and p10, so the belief drifted toward a
prior nobody had measured.

The estimator works on noisy observations, not states, so it must undo the detector's own ROC.
A naive count of detections over looks is biased upward by false alarms and downward by misses,
and on this receiver -- Pd around 0.84, Pfa around 0.067 -- both errors are large enough to matter.
"""

from __future__ import annotations

import numpy as np
import pytest

from ml.belief.kernel_learning import KernelEstimator

P_D, P_FA = 0.9, 0.05


def chain(steps: int, p01: float, p10: float, seed: int = 0) -> np.ndarray:
    """Ground-truth occupancy of one band under a known two-state chain."""
    rng = np.random.default_rng(seed)
    state = rng.random() < p01 / (p01 + p10)
    out = np.empty(steps, dtype=bool)
    for t in range(steps):
        out[t] = state
        state = (rng.random() >= p10) if state else (rng.random() < p01)
    return out


def observe_all(
    est: KernelEstimator, truth: np.ndarray, seed: int = 1, band: int = 0, stride: int = 1
) -> None:
    """Feed the estimator noisy looks at one band, every ``stride`` steps."""
    rng = np.random.default_rng(seed)
    for t in range(0, len(truth), stride):
        p = P_D if truth[t] else P_FA
        est.observe(t, [band], [bool(rng.random() < p)])


def estimator(num_bands: int = 1, **kwargs) -> KernelEstimator:
    defaults = dict(p_d=P_D, p_fa=P_FA, prior_strength=20.0)
    defaults.update(kwargs)
    return KernelEstimator(num_bands, **defaults)


# -- recovering a known chain ---------------------------------------------------------------------

def test_it_recovers_a_known_stationary_occupancy():
    est = estimator()
    observe_all(est, chain(20_000, p01=0.02, p10=0.08))  # stationary 0.2
    assert float(est.stationary()[0]) == pytest.approx(0.2, abs=0.04)


def test_it_recovers_a_known_switching_rate():
    est = estimator()
    observe_all(est, chain(20_000, p01=0.05, p10=0.05))  # lambda = 0.9
    p01, p10 = est.kernels()
    assert float(p01[0] + p10[0]) == pytest.approx(0.10, abs=0.04)


def test_a_sticky_band_is_distinguished_from_a_flappy_one():
    sticky = estimator()
    observe_all(sticky, chain(20_000, p01=0.01, p10=0.01, seed=2))
    flappy = estimator()
    observe_all(flappy, chain(20_000, p01=0.4, p10=0.4, seed=2))

    sticky_switch = float(sum(a[0] for a in sticky.kernels()))
    flappy_switch = float(sum(a[0] for a in flappy.kernels()))
    assert flappy_switch > 3.0 * sticky_switch


# -- undoing the detector -------------------------------------------------------------------------

def test_it_corrects_for_false_alarms():
    """A band that is never active still shows detections at the false-alarm rate."""
    est = estimator()
    observe_all(est, np.zeros(20_000, dtype=bool))
    assert float(est.stationary()[0]) < 0.05


def test_it_corrects_for_missed_detections():
    """A band that is always active is missed 16% of the time on this receiver."""
    est = estimator()
    observe_all(est, np.ones(20_000, dtype=bool))
    assert float(est.stationary()[0]) > 0.95


def test_a_blind_detector_cannot_teach_it_anything():
    """When Pd equals Pfa the observation is independent of the state, so evidence is worthless."""
    est = KernelEstimator(1, p_d=0.3, p_fa=0.3, prior_strength=20.0, p01_prior=0.07, p10_prior=0.03)
    observe_all(est, chain(5_000, p01=0.4, p10=0.4))
    p01, p10 = est.kernels()
    assert float(p01[0]) == pytest.approx(0.07, abs=0.01)
    assert float(p10[0]) == pytest.approx(0.03, abs=0.01)


# -- the prior ---------------------------------------------------------------------------------------

def test_it_returns_the_prior_before_any_evidence():
    est = estimator(p01_prior=0.07, p10_prior=0.03)
    p01, p10 = est.kernels()
    assert float(p01[0]) == pytest.approx(0.07)
    assert float(p10[0]) == pytest.approx(0.03)


def test_evidence_gradually_overrides_the_prior():
    """The estimate must walk from the prior toward the truth as looks accumulate.

    ``prior_strength`` is measured in pseudo-looks, so "a few" means few relative to it: at the
    default of 20, sixty real looks already outweigh the prior three to one.
    """
    truth = chain(20_000, p01=0.02, p10=0.08)  # stationary 0.2, prior says 0.5
    moved = []
    for looks in (5, 50, 20_000):
        est = estimator(p01_prior=0.5, p10_prior=0.5)
        observe_all(est, truth[:looks])
        moved.append(0.5 - float(est.stationary()[0]))

    assert all(later > earlier for earlier, later in zip(moved, moved[1:]))
    assert moved[0] < 0.15   # barely moved
    assert moved[-1] > 0.25  # essentially all evidence


def test_bands_are_estimated_independently():
    est = estimator(num_bands=2)
    quiet = chain(10_000, p01=0.01, p10=0.2, seed=3)   # stationary ~0.048
    busy = chain(10_000, p01=0.2, p10=0.01, seed=4)    # stationary ~0.952
    observe_all(est, quiet, band=0, seed=5)
    observe_all(est, busy, band=1, seed=6)
    assert float(est.stationary()[0]) < float(est.stationary()[1])


# -- guardrails ----------------------------------------------------------------------------------------

def test_kernels_always_stay_probabilities():
    for p01, p10 in ((0.001, 0.001), (0.5, 0.5), (0.9, 0.9), (0.01, 0.99)):
        est = estimator()
        observe_all(est, chain(4_000, p01=p01, p10=p10, seed=7))
        a, b = est.kernels()
        assert 0.0 <= float(a[0]) <= 1.0
        assert 0.0 <= float(b[0]) <= 1.0
        assert 0.0 < float(a[0] + b[0]) <= 1.0


def test_sparse_looks_still_produce_a_usable_estimate():
    """A real scheduler revisits a band every several steps, not every step."""
    est = estimator()
    observe_all(est, chain(40_000, p01=0.02, p10=0.08, seed=8), stride=7)
    assert float(est.stationary()[0]) == pytest.approx(0.2, abs=0.06)


def test_forgetting_lets_it_track_an_environment_that_changes():
    """A band that goes quiet halfway through must not be remembered as busy for ever."""
    est = estimator(forgetting=0.999)
    busy = np.ones(6_000, dtype=bool)
    quiet = np.zeros(6_000, dtype=bool)
    observe_all(est, np.concatenate([busy, quiet]))
    assert float(est.stationary()[0]) < 0.4


def test_reset_clears_all_evidence():
    est = estimator(p01_prior=0.07, p10_prior=0.03)
    observe_all(est, chain(5_000, p01=0.4, p10=0.4))
    est.reset()
    p01, p10 = est.kernels()
    assert float(p01[0]) == pytest.approx(0.07)
    assert float(p10[0]) == pytest.approx(0.03)
