"""Bandit window scoring: q(a) is the mean over the K-band window starting at a."""

from __future__ import annotations

import json

import numpy as np
import pytest

from ml.agents.bandit_agent import FEATURE_DIM, BanditAgent
from ml.environments.state import NUM_BAND_FEATURES

N = 8


def rand_obs(rng: np.random.Generator, n: int) -> np.ndarray:
    return np.asarray(rng.normal(size=(NUM_BAND_FEATURES * n,)), dtype=np.float64)


def hand_obs(n: int, feat0: list[float]) -> np.ndarray:
    """Observation whose band b has first feature feat0[b] and zeros elsewhere."""
    obs = np.zeros((NUM_BAND_FEATURES * n,), dtype=np.float64)
    for b, v in enumerate(feat0):
        obs[b * NUM_BAND_FEATURES] = float(v)
    return obs


def band_features(obs: np.ndarray, n: int) -> np.ndarray:
    bands = np.asarray(obs[: NUM_BAND_FEATURES * n], dtype=np.float64).reshape(
        n, NUM_BAND_FEATURES
    )
    return np.hstack([bands, np.ones((n, 1), dtype=np.float64)])


def test_k1_matches_the_old_single_band_formulas():
    """With K = 1 the window agent must reproduce the old per-band update exactly."""
    rng = np.random.default_rng(7)
    n = 6
    agent = BanditAgent(n, bandwidth_k=1, rng=np.random.default_rng(7))
    # Inline copy of the OLD formulas, kept independent of the agent under test.
    w = np.zeros(FEATURE_DIM, dtype=np.float64)
    b = np.full(n, agent.optimistic_init, dtype=np.float64)
    v = np.zeros(n, dtype=np.int64)

    steps = [
        (rand_obs(rng, n), int(rng.integers(0, n)), float(rng.normal() * 5.0))
        for _ in range(100)
    ]
    for obs, action, reward in steps:
        agent.learn(obs, action, reward, obs)
        phi = band_features(obs, n)[action]
        err = reward / agent.reward_scale - float(phi @ w + b[action])
        w = w + agent.learning_rate * err * phi
        b[action] += agent.bias_learning_rate * err
        v[action] += 1

    for _ in range(50):
        obs = rand_obs(rng, n)
        assert np.allclose(agent.q_values(obs), band_features(obs, n) @ w + b, atol=1e-12)
    assert np.allclose(agent.weights, w, atol=1e-12)
    assert np.allclose(agent.band_bias, b, atol=1e-12)
    assert np.array_equal(agent.visit_counts, v)


def test_k2_q_values_average_the_window():
    n = 4
    agent = BanditAgent(n, bandwidth_k=2)
    agent.weights[:] = 0.0
    agent.weights[0] = 1.0
    agent.band_bias = np.array([0.0, 10.0, 20.0, 30.0])
    obs = hand_obs(n, [0.0, 1.0, 2.0, 3.0])
    # Per-band values are b + 10b = [0, 11, 22, 33]; action 3 wraps to band 0.
    expected = np.array([(0 + 11) / 2, (11 + 22) / 2, (22 + 33) / 2, (33 + 0) / 2])
    assert np.allclose(agent.q_values(obs), expected, atol=1e-12)


def test_k2_learn_updates_the_whole_window():
    n = 5
    agent = BanditAgent(n, bandwidth_k=2)
    obs = rand_obs(np.random.default_rng(11), n)
    before_bias = agent.band_bias.copy()
    before_w = agent.weights.copy()
    action, reward = 2, 7.5
    window = [2, 3]
    phi = band_features(obs, n)[window].mean(axis=0)
    err = reward / agent.reward_scale - float(phi @ before_w + before_bias[window].mean())

    agent.learn(obs, action, reward, obs)

    for band in window:
        assert agent.band_bias[band] == pytest.approx(
            before_bias[band] + agent.bias_learning_rate * err
        )
        assert agent.visit_counts[band] == 1
    for band in (0, 1, 4):
        assert agent.band_bias[band] == pytest.approx(before_bias[band])
        assert agent.visit_counts[band] == 0
    assert np.allclose(agent.weights, before_w + agent.learning_rate * err * phi, atol=1e-12)


@pytest.mark.parametrize("k", [0, -1, N + 1, 100])
def test_bandwidth_k_outside_1_to_n_raises(k):
    with pytest.raises(ValueError):
        BanditAgent(N, bandwidth_k=k)


def test_bandwidth_k_equal_to_n_covers_the_whole_spectrum():
    agent = BanditAgent(N, bandwidth_k=N)
    assert agent._windows.shape == (N, N)
    obs = rand_obs(np.random.default_rng(3), N)
    assert np.allclose(agent.q_values(obs), agent.q_values(obs)[0])


def test_save_load_round_trip_preserves_bandwidth_k(tmp_path):
    n = 6
    agent = BanditAgent(n, bandwidth_k=3)
    rng = np.random.default_rng(21)
    for i in range(20):
        obs = rand_obs(rng, n)
        agent.learn(obs, i % n, float(i % 5), obs)

    path = tmp_path / "bandit_k3.npz"
    agent.save(path)
    restored = BanditAgent.load(path)

    assert restored.bandwidth_k == 3
    assert restored._windows.shape == (n, 3)
    assert np.allclose(restored.weights, agent.weights)
    assert np.allclose(restored.band_bias, agent.band_bias)
    assert np.array_equal(restored.visit_counts, agent.visit_counts)
    for _ in range(10):
        obs = rand_obs(rng, n)
        assert np.allclose(restored.q_values(obs), agent.q_values(obs))


def test_legacy_checkpoint_without_bandwidth_k_loads_as_k1(tmp_path):
    n = 6
    agent = BanditAgent(n)
    rng = np.random.default_rng(33)
    for i in range(10):
        obs = rand_obs(rng, n)
        agent.learn(obs, i % n, float(i), obs)
    agent.save(tmp_path / "legacy.npz")

    data = np.load(tmp_path / "legacy.npz", allow_pickle=True)
    hp = json.loads(str(data["hyperparams"]))
    assert "bandwidth_k" in hp
    del hp["bandwidth_k"]
    stripped = tmp_path / "stripped.npz"
    np.savez(
        stripped,
        weights=data["weights"],
        band_bias=data["band_bias"],
        visit_counts=data["visit_counts"],
        num_bands=data["num_bands"],
        hyperparams=json.dumps(hp),
    )

    loaded = BanditAgent.load(stripped)
    assert loaded.bandwidth_k == 1
    obs = rand_obs(rng, n)
    assert np.allclose(loaded.q_values(obs), agent.q_values(obs))


def test_train_bandit_reads_receiver_bandwidth_k():
    from ml.training.trainer import train
    from ml.utils.config import load_scenario

    cfg = dict(load_scenario("D"))
    cfg.update({"bands": 8, "emitters": 3, "duration_steps": 60})
    cfg["receiver"] = {**cfg["receiver"], "bandwidth_k": 2}

    result = train("bandit", cfg, episode_count=1, eval_episodes=1)
    assert result["agent"].bandwidth_k == 2
    assert result["summary"]["hyperparams"]["bandwidth_k"] == 2

    explicit = train(
        "bandit", cfg, hyperparams={"bandwidth_k": 1}, episode_count=1, eval_episodes=1
    )
    assert explicit["agent"].bandwidth_k == 1
    assert explicit["summary"]["hyperparams"]["bandwidth_k"] == 1
