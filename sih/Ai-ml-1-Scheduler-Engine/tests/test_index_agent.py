"""IndexAgent -- the SCT policy as a contract-shaped agent (solution spec Sections 4, 5, 9).

The pieces are tested in isolation elsewhere. This file tests them wired together: does the agent
actually honour its deadlines, does it still prefer value when nothing is overdue, and does it
hand back a breakdown the dashboard can render.
"""

from __future__ import annotations

import numpy as np
import pytest

from ml.agents.base import Agent
from ml.agents.factory import build_agent
from ml.agents.index_agent import IndexAgent
from ml.environments.state import StateBuilder

N = 16


class _Receiver:
    """The duck-typed receiver state StateBuilder.update expects."""

    def __init__(self, start: int = 0) -> None:
        self.tuned_start = start
        self.dwell_remaining_ms = 0
        self.tuning_delay_countdown_ms = 0

    def tuned_bands(self, k, n):
        return [(self.tuned_start + i) % n for i in range(k)]


def observation(priority: np.ndarray | None = None) -> np.ndarray:
    sb = StateBuilder(N, band_priority_weights=priority)
    sb.update([], [], _Receiver(), 1)
    return sb.to_vector()


def agent(**kwargs) -> IndexAgent:
    """An agent with the randomised floor switched off.

    The floor deliberately dominates a cold start -- no periodicity confidence means nearly every
    look is drawn from the CTMC -- so leaving it on here would test the floor rather than the
    index. Its own behaviour, and the fact that it never breaks a deadline, live in
    tests/test_index_floor_mixing.py.
    """
    defaults = dict(
        num_bands=N, bandwidth_k=1, deadline_s=0.280, slot_s=0.010, retune_s=0.005,
        rho_min=0.0, rho_max=0.0,
    )
    defaults.update(kwargs)
    a = IndexAgent(**defaults)
    a.start_episode()
    return a


def run(a: IndexAgent, steps: int, detect: set[int] | None = None):
    """Drive the agent for a while, reporting detections only on the chosen bands in ``detect``."""
    obs = observation()
    staleness = []
    for _ in range(steps):
        a.select_action(obs)
        scanned = a.last_bands
        detected = [b for b in scanned if detect and b in detect]
        a.observe({"scanned_bands": scanned, "detected_bands": detected})
        staleness.append(a.time_since_last_scan.copy())
    return np.array(staleness)


# -- shape and contract --------------------------------------------------------------------------

def test_it_is_an_agent_of_the_index_policy_type():
    a = agent()
    assert isinstance(a, Agent)
    assert a.policy_type == "index"


def test_the_factory_builds_it_from_the_contract_policy_name():
    a = build_agent("index", num_bands=N)
    assert isinstance(a, IndexAgent)


def test_it_returns_a_band_index_inside_the_spectrum():
    a = agent()
    for _ in range(50):
        action = a.select_action(observation())
        assert isinstance(action, (int, np.integer))
        assert 0 <= action < N
        a.observe({"scanned_bands": a.last_bands, "detected_bands": []})


def test_it_covers_exactly_the_receivers_instantaneous_bandwidth():
    a = agent(bandwidth_k=3)
    a.select_action(observation())
    assert len(a.last_bands) == 3


# -- the coverage guarantee ------------------------------------------------------------------------

def test_no_band_is_ever_left_past_its_deadline():
    """The guarantee, end to end. 16 bands at K=1 is a 16-step cycle inside a 28-step deadline."""
    a = agent()
    staleness = run(a, steps=400)
    assert staleness.max() <= a.deadline_slots.max()


def test_it_reports_its_own_feasibility():
    """An oversubscribed receiver must say so rather than silently starving bands."""
    tight = IndexAgent(num_bands=64, bandwidth_k=1, deadline_s=0.050, slot_s=0.010, retune_s=0.005)
    assert not tight.feasibility.feasible
    assert tight.feasibility.required_bandwidth_k > 1

    roomy = agent()
    assert roomy.feasibility.feasible


def test_a_permanently_loud_band_does_not_starve_the_others():
    """The IMPLEMENTATION.md failure, at agent level rather than in the index alone."""
    a = agent()
    staleness = run(a, steps=400, detect={0})
    assert staleness.max() <= a.deadline_slots.max()
    # And the loud band is still favoured: it should be visited more often than average.
    visits = (staleness[:, 0] == 0).sum()
    assert visits > 400 / N


# -- value seeking ----------------------------------------------------------------------------------

def test_it_prefers_the_band_it_believes_is_active():
    """With deadlines slack, the value term decides."""
    a = agent(deadline_s=10.0)  # 1000 slots, effectively no pressure over this horizon
    a.belief.belief[:] = 0.01
    a.belief.belief[5] = 0.99
    assert a.select_action(observation()) == 5


def test_it_prefers_a_higher_priority_band_when_beliefs_are_equal():
    priority = np.ones(N)
    priority[9] = 2.0
    a = agent(deadline_s=10.0)
    a.belief.belief[:] = 0.5
    assert a.select_action(observation(priority)) == 9


# -- learning from hits and misses -------------------------------------------------------------------

def test_a_detection_raises_the_belief_for_that_band():
    a = agent()
    a.belief.belief[:] = 0.5
    before = float(a.belief.belief[4])
    a.select_action(observation())
    a.observe({"scanned_bands": [4], "detected_bands": [4]})
    assert float(a.belief.belief[4]) > before


def test_a_miss_lowers_the_belief_for_that_band():
    a = agent()
    a.belief.belief[:] = 0.5
    a.select_action(observation())
    a.observe({"scanned_bands": [4], "detected_bands": []})
    assert float(a.belief.belief[4]) < 0.5


def test_an_unscanned_band_only_drifts():
    a = agent()
    a.belief.belief[:] = 0.5
    a.observe({"scanned_bands": [4], "detected_bands": [4]})
    assert float(a.belief.belief[7]) == pytest.approx(0.5, abs=0.05)


# -- explainability ------------------------------------------------------------------------------

def test_it_records_a_breakdown_for_the_last_decision():
    a = agent()
    a.select_action(observation())
    assert set(a.last_breakdown) == {"value", "information", "novelty", "deadline", "elapsed_s"}
    assert all(isinstance(v, float) for v in a.last_breakdown.values())


def test_the_breakdown_describes_the_band_that_was_actually_chosen():
    a = agent(deadline_s=10.0)
    a.belief.belief[:] = 0.01
    a.belief.belief[11] = 0.99
    chosen = a.select_action(observation())
    assert chosen == 11
    assert a.last_breakdown["value"] > 0.0


# -- lifecycle -----------------------------------------------------------------------------------

def test_start_episode_clears_staleness_and_belief():
    a = agent()
    run(a, steps=50, detect={2})
    a.start_episode(1)
    assert np.all(a.time_since_last_scan == 0)
    assert a.belief.belief == pytest.approx(a.belief.stationary)


def test_two_agents_with_the_same_seed_choose_identically():
    a, b = agent(), agent()
    for _ in range(60):
        obs = observation()
        assert a.select_action(obs) == b.select_action(obs)
        a.observe({"scanned_bands": a.last_bands, "detected_bands": []})
        b.observe({"scanned_bands": b.last_bands, "detected_bands": []})


def test_describe_reports_the_tuned_weights_for_the_model_registry():
    a = agent()
    described = a.describe()
    assert described["policy_type"] == "index"
    assert "w_value" in described
    assert "deadline_slots" in described
