"""Agent behavior: convergence, exploration, checkpointing (Ai-ml-1 Levels 3, 7)."""

from __future__ import annotations

import numpy as np
import pytest

from ml.agents.bandit_agent import BanditAgent
from ml.agents.baseline_scanner import BaselineScanner
from ml.agents.factory import build_agent
from ml.agents.q_learning_agent import QLearningAgent
from ml.algorithms.exploration import EpsilonSchedule, epsilon_greedy
from ml.environments.state import NUM_BAND_FEATURES, StateBuilder

N = 8


def observation(ewma: list[float] | None = None) -> np.ndarray:
    """A minimal observation with a chosen detection-rate profile."""
    sb = StateBuilder(N)
    sb.update([], [], type("R", (), {
        "tuned_bands": lambda self, k, n: [0],
        "dwell_remaining_ms": 0,
        "tuning_delay_countdown_ms": 0,
        "tuned_start": 0,
    })(), 1)
    if ewma:
        sb.recent_detection_rate_ewma = np.array(ewma, dtype=np.float32)
    return sb.to_vector()


# -- baseline ---------------------------------------------------------------------------------

def test_round_robin_cycles_deterministically():
    a = BaselineScanner(N, stride=2)
    a.start_episode()
    assert [a.select_action(observation()) for _ in range(6)] == [0, 2, 4, 6, 0, 2]


def test_baseline_ignores_the_observation_entirely():
    """Open loop means open loop -- feedback must not change the scan order."""
    a, b = BaselineScanner(N, stride=1), BaselineScanner(N, stride=1)
    a.start_episode()
    b.start_episode()
    hot = observation([1.0] * N)
    assert [a.select_action(hot) for _ in range(8)] == [b.select_action(observation()) for _ in range(8)]


def test_fixed_order_walks_the_configured_list():
    a = BaselineScanner(N, mode="fixed_order", band_order=[3, 1, 7])
    a.start_episode()
    assert [a.select_action(observation()) for _ in range(5)] == [3, 1, 7, 3, 1]


def test_fixed_order_requires_a_band_order():
    with pytest.raises(ValueError, match="requires a band_order"):
        BaselineScanner(N, mode="fixed_order")


def test_baseline_restarts_its_sweep_each_episode():
    a = BaselineScanner(N, stride=3)
    a.start_episode(0)
    [a.select_action(observation()) for _ in range(4)]
    a.start_episode(1)
    assert a.select_action(observation()) == 0


# -- bandit -----------------------------------------------------------------------------------

def test_bandit_band_values_converge_to_the_paying_arm():
    """Level 3 DoD: band-value estimates converge on a synthetic reward stream."""
    agent = BanditAgent(N, epsilon=EpsilonSchedule(mode="constant", start=0.0, end=0.0))
    agent.start_episode()
    obs = observation()
    payoffs = {3: 10.0}
    for _ in range(400):
        for band in range(N):
            agent.learn(obs, band, payoffs.get(band, 0.0), obs)
    values = agent.band_values()
    assert int(np.argmax(values)) == 3
    assert values[3] > values[np.arange(N) != 3].max()


def test_bandit_learns_a_positive_weight_for_a_feature_that_predicts_reward():
    """The shared weights are what transfer across bands; check the sign is learnable."""
    agent = BanditAgent(N, learning_rate=0.05, epsilon=EpsilonSchedule(mode="constant", start=0.0, end=0.0))
    agent.start_episode()
    hot, cold = observation([1.0] * N), observation([0.0] * N)
    for _ in range(300):
        for band in range(N):
            agent.learn(hot, band, 10.0, hot)
            agent.learn(cold, band, 0.0, cold)
    assert agent.feature_weights()["recent_detection_rate_ewma"] > 0.0


def test_bandit_forgets_band_identity_between_episodes():
    """Emitters move between simulations; a per-band bias must not survive into the next one.

    Carrying it forward made the agent camp on bands that were busy during training and silent
    at evaluation -- it scored worse than round-robin while looking like a trained policy.
    """
    agent = BanditAgent(N)
    agent.start_episode(0)
    obs = observation()
    for _ in range(200):
        agent.learn(obs, 5, 20.0, obs)
    assert agent.band_values()[5] > agent.band_values()[0]

    agent.start_episode(1)
    assert np.allclose(agent.band_values(), agent.optimistic_init)
    assert agent.visit_counts.sum() == 0


def test_bandit_keeps_its_shared_weights_between_episodes():
    agent = BanditAgent(N)
    agent.start_episode(0)
    obs = observation([1.0] * N)
    for _ in range(100):
        agent.learn(obs, 2, 15.0, obs)
    learned = agent.weights.copy()
    agent.start_episode(1)
    assert np.allclose(agent.weights, learned)


def test_bandit_checkpoint_round_trip(tmp_path):
    agent = BanditAgent(N, learning_rate=0.07)
    agent.start_episode()
    obs = observation([0.5] * N)
    for i in range(50):
        agent.learn(obs, i % N, float(i % 3), obs)

    path = tmp_path / "bandit.npz"
    agent.save(path)
    restored = BanditAgent.load(path)
    assert np.allclose(restored.weights, agent.weights)
    assert restored.num_bands == N
    assert restored.learning_rate == pytest.approx(0.07)


def test_epsilon_greedy_explores_at_epsilon_one():
    rng = np.random.default_rng(0)
    values = np.array([0.0, 0.0, 5.0, 0.0])
    picks = {epsilon_greedy(values, 1.0, rng) for _ in range(60)}
    assert len(picks) > 1


def test_epsilon_greedy_exploits_at_epsilon_zero():
    rng = np.random.default_rng(0)
    values = np.array([0.0, 0.0, 5.0, 0.0])
    assert all(epsilon_greedy(values, 0.0, rng) == 2 for _ in range(20))


def test_epsilon_greedy_breaks_ties_randomly():
    """With optimistic init every arm starts tied; argmax would freeze on band 0."""
    rng = np.random.default_rng(0)
    tied = np.zeros(6)
    assert len({epsilon_greedy(tied, 0.0, rng) for _ in range(60)}) > 1


def test_epsilon_schedule_decays_and_floors():
    s = EpsilonSchedule(start=1.0, end=0.1, decay=0.5)
    assert s.value(0) == pytest.approx(1.0)
    assert s.value(1) == pytest.approx(0.5)
    assert s.value(50) == pytest.approx(0.1)


def test_epsilon_schedule_rejects_an_inverted_range():
    with pytest.raises(ValueError, match="end <= start"):
        EpsilonSchedule(start=0.1, end=0.9)


# -- Q-learning -------------------------------------------------------------------------------

def test_q_learning_table_is_keyed_on_context_not_band_index():
    """Two bands with identical features must share one table entry, or the table never fills."""
    agent = QLearningAgent(N)
    obs = observation([0.0] * N)
    keys = agent._keys(obs)
    assert len(set(keys)) == 1


def test_q_learning_bootstraps_toward_future_value():
    """The bootstrap term is what the bandit cannot represent.

    optimistic_init must be non-zero here: with an all-zero table there is no future value to
    bootstrap against, and the done/not-done updates would be identical for the wrong reason.
    """
    obs = observation([0.0] * N)
    terminal = QLearningAgent(N, learning_rate=0.5, discount=0.9, optimistic_init=0.5)
    terminal.learn(obs, 0, 10.0, obs, done=True)

    ongoing = QLearningAgent(N, learning_rate=0.5, discount=0.9, optimistic_init=0.5)
    ongoing.learn(obs, 0, 10.0, obs, done=False)

    assert ongoing.q_values(obs)[0] > terminal.q_values(obs)[0]


def test_q_learning_table_stays_within_its_capacity():
    agent = QLearningAgent(N)
    rng = np.random.default_rng(0)
    for _ in range(500):
        obs = observation(list(rng.random(N)))
        agent.learn(obs, int(rng.integers(0, N)), float(rng.normal()), obs)
    assert 0 < len(agent.q_table) <= agent.describe()["table_capacity"]


def test_q_learning_checkpoint_round_trip(tmp_path):
    agent = QLearningAgent(N, learning_rate=0.2)
    obs = observation([0.3] * N)
    for i in range(30):
        agent.learn(obs, i % N, float(i), obs)
    path = tmp_path / "q.json"
    agent.save(path)
    restored = QLearningAgent.load(path)
    assert restored.q_table == agent.q_table
    assert restored.learning_rate == pytest.approx(0.2)


# -- factory ----------------------------------------------------------------------------------

@pytest.mark.parametrize("policy,expected", [
    ("baseline", "baseline"), ("bandit", "bandit"), ("q_learning", "q_learning")
])
def test_factory_builds_each_contract_policy(policy, expected):
    assert build_agent(policy, N).policy_type == expected


def test_factory_rejects_a_policy_outside_the_contract_enum():
    with pytest.raises(ValueError, match="unknown policy"):
        build_agent("random_forest", N)


def test_factory_applies_hyperparameter_overrides():
    agent = build_agent("bandit", N, {"learning_rate": 0.99})
    assert agent.learning_rate == pytest.approx(0.99)
