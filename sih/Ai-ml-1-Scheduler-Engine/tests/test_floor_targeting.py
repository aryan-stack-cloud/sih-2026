"""Pointing the randomised floor at the bands that still need it (solution spec Section 7.2).

The spec is explicit that the floor draws "from a continuous-time Markov chain over *uncharacterised*
bands". Wiring it to draw uniformly over the whole spectrum instead was measurably expensive: with
the floor active but untargeted, scenario B fell 7% below round-robin on run intercept rate, because
random looks were being spent on bands the index already models well.

Targeting keeps the guarantee and recovers the cost. Every band still gets looked at, because the
deadline override is downstream of the floor and binds regardless; what changes is where the
*discretionary* random looks land.

The degenerate cases both resolve toward looking rather than not looking. Nothing characterised
means the floor covers everything, which is the cold start. Everything characterised also means the
floor covers everything, because "we understand the spectrum" is never a reason to stop watching it.
"""

from __future__ import annotations

import numpy as np
import pytest

from ml.agents.index_agent import IndexAgent
from ml.environments.state import StateBuilder

N = 8


class _Receiver:
    tuned_start = 0
    dwell_remaining_ms = 0
    tuning_delay_countdown_ms = 0

    def tuned_bands(self, k, n):
        return [(self.tuned_start + i) % n for i in range(k)]


def observation(confidence) -> np.ndarray:
    sb = StateBuilder(N)
    sb.update([], [], _Receiver(), 1)
    sb.periodicity_confidence = np.asarray(confidence, dtype=np.float32)
    return sb.to_vector()


def agent(seed: int = 0, **kwargs) -> IndexAgent:
    defaults = dict(
        num_bands=N, bandwidth_k=1, deadline_s=10.0, slot_s=0.010, retune_s=0.005,
        rho_min=1.0,  # pure floor, so its choices are what is observed
    )
    defaults.update(kwargs)
    a = IndexAgent(rng=np.random.default_rng(seed), **defaults)
    a.start_episode()
    return a


def bands_visited(a: IndexAgent, obs: np.ndarray, steps: int = 600) -> set[int]:
    seen = set()
    for _ in range(steps):
        a.select_action(obs)
        seen.update(a.last_bands)
        a.observe({"scanned_bands": a.last_bands, "detected_bands": []})
    return seen


def uncharacterised(a: IndexAgent, obs: np.ndarray) -> list[int]:
    """The bands the floor is allowed to draw from, read off the public characterisation."""
    known = a.characterisation(obs)
    return [b for b in range(N) if known[b] < a.floor_confidence_threshold]


def test_the_floor_avoids_bands_the_index_already_models():
    """Six bands confidently modelled, two not. Discretionary looks belong to the two."""
    confidence = np.full(N, 0.95)
    confidence[[2, 5]] = 0.0
    assert uncharacterised(agent(seed=1), observation(confidence)) == [2, 5]


def test_the_floor_visits_only_those_bands_while_they_stay_unknown():
    """The behavioural half, kept short so evidence does not graduate them mid-test."""
    confidence = np.full(N, 0.95)
    confidence[[2, 5]] = 0.0
    assert bands_visited(agent(seed=1), observation(confidence), steps=24) == {2, 5}


def test_bands_graduate_out_of_the_floors_remit_once_enough_looks_land_on_them():
    """Characterisation is evidence-based, so watching a band is what retires it from the floor."""
    confidence = np.full(N, 0.95)
    confidence[[2, 5]] = 0.0
    a = agent(seed=1)
    obs = observation(confidence)
    assert uncharacterised(a, obs) == [2, 5]
    bands_visited(a, obs, steps=400)
    assert uncharacterised(a, obs) == []


def test_a_cold_start_lets_the_floor_cover_everything():
    assert bands_visited(agent(seed=2), observation(np.zeros(N))) == set(range(N))


def test_a_fully_characterised_spectrum_also_lets_the_floor_cover_everything():
    """Understanding the spectrum is never a reason to stop watching it."""
    assert bands_visited(agent(seed=3), observation(np.ones(N))) == set(range(N))


def test_the_confidence_threshold_is_configurable():
    confidence = np.full(N, 0.5)
    confidence[4] = 0.1
    obs = observation(confidence)
    strict = uncharacterised(agent(seed=4, floor_confidence_threshold=0.3), obs)
    loose = uncharacterised(agent(seed=4, floor_confidence_threshold=0.8), obs)
    assert strict == [4]
    assert len(loose) == N


def test_targeting_tracks_periodicity_confidence_as_it_changes():
    """A band the periodicity estimator becomes sure about leaves the floor's remit immediately.

    Evidence is the other half of characterisation and accrues slowly; a confident periodicity fit
    retires a band at once, without waiting for the look count to catch up.
    """
    a = agent(seed=5)
    assert uncharacterised(a, observation(np.zeros(N))) == list(range(N))

    confidence = np.full(N, 0.95)
    confidence[7] = 0.0
    assert uncharacterised(a, observation(confidence)) == [7]


# -- the guarantee is untouched ------------------------------------------------------------------

def test_targeting_never_lets_a_band_pass_its_deadline():
    """The deadline override sits downstream of the floor, so restricting the floor cannot starve.

    Confidence is high everywhere except one band, so an untargeted floor would still wander and an
    untargeted-but-restricted one would camp. Either way the deadline must hold.
    """
    a = agent(seed=6, deadline_s=0.300)  # 30 slots against a 120 ms cycle
    assert a.feasibility.feasible
    confidence = np.full(N, 0.99)
    confidence[1] = 0.0
    obs = observation(confidence)

    worst = 0
    for _ in range(900):
        a.select_action(obs)
        a.observe({"scanned_bands": a.last_bands, "detected_bands": []})
        worst = max(worst, int(a.time_since_last_scan.max()))
    assert worst <= int(a.deadline_slots.max())


def test_every_band_is_still_visited_even_when_the_floor_ignores_most_of_them():
    a = agent(seed=7, deadline_s=0.300)
    confidence = np.full(N, 0.99)
    confidence[1] = 0.0
    assert bands_visited(a, observation(confidence), steps=900) == set(range(N))
