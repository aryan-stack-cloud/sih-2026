"""The agent's slow loop: learning each band's occupancy kernel while it schedules.

Two timescales. The fast loop picks a band every step. The slow loop refreshes the transition
kernels every ``kernel_refresh_steps``, off the per-decision critical path, so the latency budget
in NFR-002 is untouched by it.

What this buys: a band whose activity the receiver has actually measured stops drifting toward a
prior nobody chose. A busy band's belief decays slowly after a miss; a sparse band's collapses.
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


def observation() -> np.ndarray:
    sb = StateBuilder(N)
    sb.update([], [], _Receiver(), 1)
    return sb.to_vector()


def agent(**kwargs) -> IndexAgent:
    defaults = dict(
        num_bands=N, bandwidth_k=1, deadline_s=0.200, slot_s=0.010, retune_s=0.005,
        rho_min=0.0, rho_max=0.0, kernel_refresh_steps=50,
    )
    defaults.update(kwargs)
    a = IndexAgent(**defaults)
    a.start_episode()
    return a


def drive(a: IndexAgent, steps: int, active: set[int]) -> None:
    """Run the agent against a spectrum where ``active`` bands are always on and others never."""
    obs = observation()
    for t in range(steps):
        a.select_action(obs)
        detected = [b for b in a.last_bands if b in active]
        a.observe({"scanned_bands": a.last_bands, "detected_bands": detected, "t": t})


# -- the slow loop runs at all ---------------------------------------------------------------------

def test_the_kernel_is_refreshed_on_the_slow_loop_not_every_step():
    a = agent(kernel_refresh_steps=50)
    before = a.belief.p01.copy()
    drive(a, 10, active={0})
    assert a.belief.p01 == pytest.approx(before), "kernels must not move on the fast loop"
    drive(a, 200, active={0})
    assert not np.allclose(a.belief.p01, before)


def test_kernel_learning_can_be_switched_off():
    a = agent(learn_kernels=False)
    before = a.belief.p01.copy(), a.belief.p10.copy()
    drive(a, 400, active={0, 1})
    assert a.belief.p01 == pytest.approx(before[0])
    assert a.belief.p10 == pytest.approx(before[1])


# -- what it learns ----------------------------------------------------------------------------------

def test_a_permanently_active_band_learns_a_high_stationary_occupancy():
    a = agent()
    drive(a, 600, active={3})
    stationary = a.kernels.stationary()
    assert float(stationary[3]) > 0.7


def test_a_permanently_idle_band_learns_a_low_stationary_occupancy():
    a = agent()
    drive(a, 600, active={3})
    stationary = a.kernels.stationary()
    assert float(stationary[5]) < 0.3


def test_busy_and_idle_bands_end_with_different_kernels():
    a = agent()
    drive(a, 600, active={0, 1})
    assert float(a.belief.p01[0]) > float(a.belief.p01[5])


def test_the_learned_kernel_changes_how_belief_drifts():
    """The point of learning it: an unobserved band decays toward what was measured, not a guess."""
    a = agent()
    drive(a, 600, active={2})

    a.belief.belief[:] = 0.5
    for _ in range(200):
        a.belief.predict()
    assert float(a.belief.belief[2]) > float(a.belief.belief[6])


# -- lifecycle -----------------------------------------------------------------------------------------

def test_start_episode_clears_the_learned_kernels():
    a = agent()
    drive(a, 600, active={0})
    learned = a.belief.p01.copy()
    a.start_episode(1)
    assert not np.allclose(a.belief.p01, learned)


def test_describe_reports_whether_kernels_are_being_learned():
    assert agent().describe()["learn_kernels"] is True
    assert agent(learn_kernels=False).describe()["learn_kernels"] is False


def test_the_agent_survives_an_info_dict_with_no_timestamp():
    """The runner's info dict is the environment's, and it carries no ``t``. Do not require one."""
    a = agent()
    a.select_action(observation())
    a.observe({"scanned_bands": [0], "detected_bands": [0]})
    a.observe({"scanned_bands": [0], "detected_bands": []})
    assert a.kernels.stationary().shape == (N,)
