"""The observe hook: how a belief-tracking policy hears what actually happened.

``learn()`` carries a scalar reward, which is the right shape for a value-learning agent and the
wrong shape for a belief-tracking one. SCT needs to know *which bands were looked at and which
of them detected*, because that is what a Bayesian update consumes -- and it is the literal
reading of the problem statement's "trained based on hits and misses".

The environment already puts both in its ``info`` dict. This hook is the one line that hands them
to the policy, and the default is a no-op so no existing agent changes behaviour.
"""

from __future__ import annotations

import numpy as np
import pytest

from ml.agents.base import Agent
from ml.agents.baseline_scanner import BaselineScanner
from ml.agents.index_agent import IndexAgent
from ml.evaluation.runner import run_episode
from ml.environments.environment import make_env
from ml.utils.config import load_scenario


class _Recorder(BaselineScanner):
    """A baseline that also records what it was told, so the wiring can be observed."""

    def __init__(self, num_bands: int, **kwargs) -> None:
        super().__init__(num_bands, **kwargs)
        self.seen: list[dict] = []

    def observe(self, info: dict) -> None:
        self.seen.append(info)


def test_the_base_agent_ignores_observations_by_default():
    """No existing policy changes behaviour because this hook exists."""
    agent = BaselineScanner(4)
    assert Agent.observe(agent, {"scanned_bands": [1], "detected_bands": [1]}) is None


def test_the_runner_hands_every_step_to_the_agent():
    scenario = load_scenario("A")
    env = make_env(scenario, seed=7)
    agent = _Recorder(scenario["bands"])
    run_episode(env, agent, seed=7)

    assert len(agent.seen) == scenario["duration_steps"]
    assert "scanned_bands" in agent.seen[0]
    assert "detected_bands" in agent.seen[0]


def test_an_index_agent_learns_its_beliefs_through_the_runner():
    """End to end: the belief must move away from its prior over a real episode."""
    scenario = load_scenario("A")
    env = make_env(scenario, seed=7)
    agent = IndexAgent(scenario["bands"], bandwidth_k=scenario.get("bandwidth_k", 1))
    prior = agent.belief.stationary.copy()

    run_episode(env, agent, seed=7)

    assert not np.allclose(agent.belief.belief, prior)


def test_an_index_agent_completes_an_episode_without_starving_a_band():
    """The coverage guarantee, against the real environment rather than a static observation."""
    scenario = load_scenario("A")
    env = make_env(scenario, seed=11)
    agent = IndexAgent(scenario["bands"], bandwidth_k=scenario.get("bandwidth_k", 1))
    run_episode(env, agent, seed=11)

    assert agent.time_since_last_scan.max() <= agent.deadline_slots.max()
