"""Per-band occupancy belief (SCT solution spec Section 3.1).

The restless-bandit-with-reset structure the index policy rests on: looking at a band resets the
belief, not looking lets it drift toward stationarity. The reset is *soft*, because the sensor is
imperfect, and the amount of reset is governed by the detector's own ROC.

The property that matters most operationally is that repeated misses drive the belief toward the
chain's stationary value, never to zero. A band that goes quiet must never become worthless, or
the pop-up threat in an abandoned band is undetectable by construction.
"""

from __future__ import annotations

import numpy as np
import pytest

from ml.belief.occupancy import OccupancyBelief

P01, P10 = 0.05, 0.05          # symmetric chain, stationary belief 0.5
STATIONARY = P01 / (P01 + P10)


def belief(num_bands: int = 4, p01: float = P01, p10: float = P10, prior=None) -> OccupancyBelief:
    return OccupancyBelief(num_bands, p01=p01, p10=p10, prior=prior)


# -- drift -------------------------------------------------------------------------------------

def test_stationary_belief_is_a_fixed_point_of_the_drift():
    b = belief(prior=STATIONARY)
    b.predict()
    assert b.belief == pytest.approx(np.full(4, STATIONARY))


def test_belief_drifts_toward_stationary_when_nothing_is_observed():
    b = belief(num_bands=2, p01=0.1, p10=0.3, prior=np.array([0.0, 1.0]))
    stationary = 0.1 / (0.1 + 0.3)
    for _ in range(200):
        b.predict()
    assert b.belief == pytest.approx(np.full(2, stationary), abs=1e-6)


def test_drift_is_monotone_toward_stationary():
    b = belief(num_bands=1, p01=0.1, p10=0.3, prior=np.array([0.0]))
    path = []
    for _ in range(5):
        b.predict()
        path.append(float(b.belief[0]))
    assert all(nxt > cur for cur, nxt in zip(path, path[1:]))


# -- correction --------------------------------------------------------------------------------

def test_detection_and_miss_match_the_hand_computed_posterior():
    """omega=0.5, Pd=0.9, Pfa=0.1 gives exactly 0.9 on a hit and 0.1 on a miss."""
    b = belief(num_bands=2, prior=np.array([0.5, 0.5]))
    b.correct(bands=[0, 1], detections=[True, False], p_d=0.9, p_fa=0.1)
    assert b.belief == pytest.approx(np.array([0.9, 0.1]))


def test_a_perfect_sensor_resets_the_belief_to_certainty():
    b = belief(num_bands=2, prior=np.array([0.5, 0.5]))
    b.correct(bands=[0, 1], detections=[True, False], p_d=1.0, p_fa=0.0)
    assert b.belief == pytest.approx(np.array([1.0, 0.0]))


def test_an_imperfect_sensor_leaves_residual_doubt_after_a_miss():
    """The soft reset. A naive implementation writes zero here and over-trusts the sensor."""
    b = belief(num_bands=1, prior=np.array([0.5]))
    b.correct(bands=[0], detections=[False], p_d=0.8, p_fa=0.05)
    assert 0.0 < float(b.belief[0]) < 0.5


def test_correct_leaves_unscanned_bands_untouched():
    b = belief(num_bands=3, prior=np.array([0.2, 0.5, 0.8]))
    b.correct(bands=[1], detections=[True], p_d=0.9, p_fa=0.1)
    assert float(b.belief[0]) == pytest.approx(0.2)
    assert float(b.belief[2]) == pytest.approx(0.8)


def test_repeated_misses_never_drive_the_belief_to_zero():
    """A band that goes quiet must not become worthless -- that is the pop-up-threat failure."""
    b = belief(num_bands=1, prior=np.array([0.5]))
    for _ in range(500):
        b.predict()
        b.correct(bands=[0], detections=[False], p_d=0.8, p_fa=0.05)
    assert float(b.belief[0]) > 1e-3


def test_even_a_perfect_sensor_recovers_belief_after_one_slot():
    """Certainty of absence is certainty about *now*, not about the next slot."""
    b = belief(num_bands=1, p01=0.05, p10=0.05, prior=np.array([0.5]))
    b.correct(bands=[0], detections=[False], p_d=1.0, p_fa=0.0)
    assert float(b.belief[0]) == pytest.approx(0.0)
    b.predict()
    assert float(b.belief[0]) == pytest.approx(0.05)


def test_belief_stays_inside_the_unit_interval_under_adversarial_input():
    b = belief(num_bands=2, prior=np.array([1.0, 0.0]))
    for _ in range(50):
        b.predict()
        b.correct(bands=[0, 1], detections=[True, False], p_d=0.99, p_fa=0.01)
        assert np.all(b.belief >= 0.0) and np.all(b.belief <= 1.0)


def test_per_band_detection_probabilities_are_honoured():
    """A loud band and a quiet band scanned in the same dwell update differently."""
    b = belief(num_bands=2, prior=np.array([0.5, 0.5]))
    b.correct(bands=[0, 1], detections=[False, False], p_d=[0.99, 0.20], p_fa=0.01)
    assert float(b.belief[0]) < float(b.belief[1])


# -- information gain --------------------------------------------------------------------------

def test_entropy_is_maximal_at_even_odds():
    b = belief(num_bands=3, prior=np.array([0.5, 0.1, 0.9]))
    h = b.entropy()
    assert float(h[0]) > float(h[1])
    assert float(h[0]) > float(h[2])


def test_information_gain_is_never_negative():
    b = belief(num_bands=5, prior=np.linspace(0.01, 0.99, 5))
    assert np.all(b.information_gain(p_d=0.8, p_fa=0.05) >= -1e-12)


def test_an_uncertain_band_offers_more_information_than_a_settled_one():
    b = belief(num_bands=2, prior=np.array([0.5, 0.99]))
    gain = b.information_gain(p_d=0.8, p_fa=0.05)
    assert float(gain[0]) > float(gain[1])


def test_a_useless_sensor_offers_no_information():
    """When Pd == Pfa the observation is independent of the state, so a look learns nothing."""
    b = belief(num_bands=3, prior=np.array([0.2, 0.5, 0.8]))
    assert b.information_gain(p_d=0.3, p_fa=0.3) == pytest.approx(np.zeros(3), abs=1e-12)


def test_a_better_sensor_offers_more_information():
    b = belief(num_bands=1, prior=np.array([0.5]))
    weak = float(b.information_gain(p_d=0.6, p_fa=0.4)[0])
    strong = float(b.information_gain(p_d=0.95, p_fa=0.05)[0])
    assert strong > weak


# -- construction ------------------------------------------------------------------------------

def test_default_prior_is_the_stationary_distribution():
    b = belief(num_bands=3, p01=0.1, p10=0.3)
    assert b.belief == pytest.approx(np.full(3, 0.25))


def test_transition_probabilities_outside_the_unit_interval_are_rejected():
    with pytest.raises(ValueError):
        OccupancyBelief(2, p01=1.5, p10=0.1)
