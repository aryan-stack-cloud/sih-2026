"""How much of the receiver's time the randomised floor gets (solution spec Section 7.3).

The first rule annealed on the *mean* periodicity confidence across all bands. Measured on
scenario B that mean plateaued around 0.22, because most emitters there are not cleanly periodic
and the estimator is deliberately conservative about saying otherwise. The floor therefore took
61% of every episode's looks, permanently, and the index was overridden by uninformed randomness
most of the time. Detection fell to a wash against round-robin and coverage fell below it.

The fix ties the rate to the same quantity that already decides *where* the floor looks: the
fraction of the spectrum still uncharacterised. One notion of "characterised" now governs both, it
is self-calibrating, and it removes a tuning constant rather than adding one. Twelve of sixteen
bands modelled means a quarter of the looks stay discretionary, not half.

The floor is bounded below so the worst-case guarantee survives a fully modelled spectrum, and
bounded above so a caller can switch it off outright for an ablation.
"""

from __future__ import annotations

import numpy as np
import pytest

from ml.agents.index_agent import IndexAgent
from ml.environments.state import StateBuilder

N = 16


class _Receiver:
    tuned_start = 0
    dwell_remaining_ms = 0
    tuning_delay_countdown_ms = 0

    def tuned_bands(self, k, n):
        return [(self.tuned_start + i) % n for i in range(k)]


def observation(confidence) -> np.ndarray:
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


def confidence_with(known: int) -> np.ndarray:
    """``known`` bands above the characterisation threshold, the rest below it."""
    out = np.zeros(N, dtype=np.float32)
    out[:known] = 0.95
    return out


# -- the rule --------------------------------------------------------------------------------------

def test_a_cold_start_spends_every_look_on_the_floor():
    """Nothing known is the SIH26055 opening condition, and it is what the floor is for."""
    assert agent().exploration_rate(observation(0.0)) == pytest.approx(1.0)


def test_the_rate_is_the_fraction_of_the_spectrum_still_unknown():
    a = agent(rho_min=0.0)
    assert a.exploration_rate(observation(confidence_with(12))) == pytest.approx(4 / N)
    assert a.exploration_rate(observation(confidence_with(8))) == pytest.approx(8 / N)


def test_the_rate_falls_as_bands_become_characterised():
    a = agent(rho_min=0.0)
    rates = [a.exploration_rate(observation(confidence_with(k))) for k in (0, 4, 8, 12, N)]
    assert all(later < earlier for earlier, later in zip(rates, rates[1:]))


def test_a_fully_characterised_spectrum_falls_to_the_floor_minimum():
    a = agent(rho_min=0.1)
    assert a.exploration_rate(observation(1.0)) == pytest.approx(0.1)


def test_the_rate_never_drops_below_the_minimum():
    """The worst-case bound has to hold for the whole mission, not only its opening."""
    a = agent(rho_min=0.25)
    assert a.exploration_rate(observation(confidence_with(N))) == pytest.approx(0.25)
    assert a.exploration_rate(observation(confidence_with(15))) >= 0.25


def test_the_floor_can_be_switched_off_for_an_ablation():
    a = agent(rho_min=0.0, rho_max=0.0)
    assert a.exploration_rate(observation(0.0)) == 0.0


def test_the_floor_can_be_pinned_on_for_a_baseline_arm():
    a = agent(rho_min=1.0)
    assert a.exploration_rate(observation(1.0)) == pytest.approx(1.0)


def test_a_minimum_above_the_maximum_is_rejected():
    with pytest.raises(ValueError):
        agent(rho_min=0.8, rho_max=0.2)


# -- one notion of characterised -------------------------------------------------------------------

def test_the_rate_and_the_targeting_agree_on_what_is_characterised():
    """Whatever the threshold is set to, both halves must read it the same way.

    If they disagreed, the floor could be given a share of the looks and no bands to spend them
    on, or bands to cover and no looks to do it with.
    """
    a = agent(rho_min=0.0, floor_confidence_threshold=0.5)
    obs = observation(confidence_with(10))
    assert len(a._uncharacterised_bands(obs)) / N == pytest.approx(a.exploration_rate(obs))


def test_raising_the_threshold_raises_the_rate():
    obs = observation(np.full(N, 0.5, dtype=np.float32))
    lenient = agent(rho_min=0.0, floor_confidence_threshold=0.3).exploration_rate(obs)
    strict = agent(rho_min=0.0, floor_confidence_threshold=0.9).exploration_rate(obs)
    assert strict > lenient


# -- the measured regression -------------------------------------------------------------------------

def test_a_partially_modelled_spectrum_leaves_most_looks_with_the_index():
    """The regression this rule exists to prevent.

    Under the old mean-confidence rule, scenario B settled at a floor share of 61% for the whole
    episode. With three quarters of the spectrum modelled the index should keep three quarters of
    the looks.
    """
    a = agent()
    assert a.exploration_rate(observation(confidence_with(12))) < 0.3
