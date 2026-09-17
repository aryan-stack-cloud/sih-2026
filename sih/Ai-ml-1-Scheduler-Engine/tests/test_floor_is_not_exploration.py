"""The randomised floor is part of the policy, not an exploration bonus.

This distinction cost a real bug. ``run_episode`` evaluates with ``explore=False``, which is
correct for an epsilon-greedy learner: at evaluation time you want the greedy policy, not the
noisy one. The floor was gated on the same flag, so every evaluation ran with it switched off.

That silently removed the guarantee the whole design rests on. Clarkson & Pollington's result says
the randomised component is what bounds worst-case behaviour against an emitter no model predicts;
turning it off at evaluation time means the numbers describe a policy that carries no such bound.
In the synchronisation-trap scenario it was the difference between intercepting the emitter and
reporting a flawless sweep with a probability of detection of exactly zero.

The rule: **epsilon-greedy exploration is optional and belongs to learning; the floor is
structural and belongs to the policy.** ``explore`` may switch off the former and must never
switch off the latter.
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


def observation(confidence: float = 0.0) -> np.ndarray:
    sb = StateBuilder(N)
    sb.update([], [], _Receiver(), 1)
    sb.periodicity_confidence = np.full(N, confidence, dtype=np.float32)
    return sb.to_vector()


def agent(seed: int = 0, **kwargs) -> IndexAgent:
    defaults = dict(
        num_bands=N, bandwidth_k=1, deadline_s=10.0, slot_s=0.010, retune_s=0.005, rho_min=0.3
    )
    defaults.update(kwargs)
    a = IndexAgent(rng=np.random.default_rng(seed), **defaults)
    a.start_episode()
    return a


def drive(a: IndexAgent, steps: int, explore: bool) -> None:
    obs = observation(confidence=1.0)  # annealed, so rho sits near rho_min
    for _ in range(steps):
        a.select_action(obs, explore=explore)
        a.observe({"scanned_bands": a.last_bands, "detected_bands": []})


def test_the_floor_still_fires_when_exploration_is_off():
    """The regression. Evaluation runs with explore=False and must keep the guarantee."""
    a = agent(seed=1)
    drive(a, 2000, explore=False)
    assert a.floor_draws > 0


def test_the_floor_fires_at_the_same_rate_with_and_without_exploration():
    evaluating = agent(seed=1)
    drive(evaluating, 2000, explore=False)
    learning = agent(seed=1)
    drive(learning, 2000, explore=True)
    assert evaluating.floor_draws == pytest.approx(learning.floor_draws, rel=0.25)


def test_a_zero_floor_is_still_zero_under_both_flags():
    for explore in (True, False):
        a = agent(seed=2, rho_min=0.0, rho_max=0.0)
        drive(a, 300, explore=explore)
        assert a.floor_draws == 0


def test_an_evaluation_run_is_still_reproducible():
    """Removing the gate must not make evaluation depend on call order or wall clock."""
    first, second = agent(seed=5), agent(seed=5)
    obs = observation(confidence=1.0)
    for _ in range(200):
        assert first.select_action(obs, explore=False) == second.select_action(obs, explore=False)
        first.observe({"scanned_bands": first.last_bands, "detected_bands": []})
        second.observe({"scanned_bands": second.last_bands, "detected_bands": []})
