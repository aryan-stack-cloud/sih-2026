"""A served registry model starts every simulation the way the offline harness starts an episode.

The contextual bandit's per-band biases are per-WORLD state. A checkpoint stores the biases of the last training episode, and the
engine used to serve the loaded agent as it came off disk, so the live bandit began each run camped on the last training world's
busy bands while every offline evaluation (``run_episode`` calls ``start_episode``) began from the optimistic sweep. Q-learning,
DQN and PPO were unaffected, which is why only the bandit's served results differed from the harness's.
"""

from __future__ import annotations

import numpy as np

from ml.agents.bandit_agent import BanditAgent
from ml.agents.q_learning_agent import QLearningAgent
from ml.inference.inference import InferenceEngine
from ml.model_registry import ModelRegistry
from tests.test_model_resolution import _state


def _bandit_with_stale_biases(num_bands: int = 16) -> BanditAgent:
    agent = BanditAgent(num_bands)
    agent.band_bias[:] = np.linspace(-1.0, 1.0, num_bands)      # what "the last training world" left behind
    agent.visit_counts[:] = 7
    return agent


def test_a_served_bandit_starts_from_the_optimistic_sweep_not_from_the_last_training_world(tmp_path):
    reg = ModelRegistry(tmp_path)
    reg.register(_bandit_with_stale_biases(), "bandit", scenario="B", activate=True)
    engine = InferenceEngine(reg)

    engine.decide("sim_00000001", _state(16), "bandit", scenario_id="B")
    served = engine.describe_session("sim_00000001", "bandit")

    assert served["band_values"] == [BanditAgent(16).optimistic_init] * 16
    assert served["visit_counts"] == [0] * 16


def test_two_simulations_do_not_share_a_bandits_learned_biases(tmp_path):
    reg = ModelRegistry(tmp_path)
    reg.register(_bandit_with_stale_biases(), "bandit", scenario="B", activate=True)
    engine = InferenceEngine(reg)

    _, _, decision_id = engine.decide("sim_00000002", _state(16), "bandit", scenario_id="B")
    engine.learn("sim_00000002", decision_id, _state(16), _action(3), 5.0, _state(16, scanned=(3,)))
    other = engine.describe_session("sim_00000003", "bandit")      # not created yet
    assert other is None
    engine.decide("sim_00000003", _state(16), "bandit", scenario_id="B")
    assert engine.describe_session("sim_00000003", "bandit")["band_values"] == [0.5] * 16


def test_a_pinned_model_is_started_fresh_too(tmp_path):
    reg = ModelRegistry(tmp_path)
    meta = reg.register(_bandit_with_stale_biases(), "bandit", scenario="B")
    engine = InferenceEngine(reg)

    engine.decide("sim_00000004", _state(16), "bandit", model_id=meta.model_id)
    assert engine.describe_session("sim_00000004", "bandit")["band_values"] == [0.5] * 16


def test_a_served_q_learner_keeps_its_trained_table(tmp_path):
    trained = QLearningAgent(16)
    trained.q_table[(1, 2, 0, 1)] = 0.75
    reg = ModelRegistry(tmp_path)
    reg.register(trained, "q_learning", scenario="B", activate=True)
    engine = InferenceEngine(reg)

    engine.decide("sim_00000005", _state(16), "q_learning", scenario_id="B")
    assert engine.describe_session("sim_00000005", "q_learning")["table_size"] == 1


def _action(band: int):
    from ml.contract import Action

    return Action(next_band=band)
