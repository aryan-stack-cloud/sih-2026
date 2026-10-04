"""Richer features and agent-side shaping for the contextual bandit (task 3a).

Options under test (all default to today's behaviour): polynomial pairwise products of the
per-band features (``poly_degree``/``poly_features``), next-band features (``neighbor_features``,
optionally folded into the products via ``poly_neighbor``), and two small shaping terms
(``eff_beta``/``cov_beta``) applied in ``learn()`` from the last outcome seen by ``observe()``.
"""

from __future__ import annotations

import json

import numpy as np
import pytest

from ml.agents.bandit_agent import BanditAgent
from ml.agents.factory import build_agent
from ml.agents.shaping import staleness_from_observation
from ml.algorithms.exploration import EpsilonSchedule
from ml.environments.state import BAND_FEATURES

CONST_EPS = EpsilonSchedule(mode="constant", start=0.0, end=0.0)


def random_obs(n: int, seed: int) -> np.ndarray:
    rng = np.random.default_rng(seed)
    return rng.random(8 * n + 2).astype(np.float64)


def naive_phi(
    obs: np.ndarray,
    n: int,
    neighbor_features: tuple = (),
    poly_degree: int = 1,
    poly_features: int = 5,
    poly_neighbor: bool = False,
) -> list[list[float]]:
    """Reference feature map: plain loops, no broadcasting tricks."""
    bands = [[float(obs[b * 7 + f]) for f in range(7)] for b in range(n)]
    out = []
    for a in range(n):
        row = list(bands[a]) + [1.0]
        neigh = [bands[(a + 1) % n][idx] for idx in neighbor_features]
        row.extend(neigh)
        if poly_degree == 2:
            src = list(bands[a][:poly_features])
            if poly_neighbor and neighbor_features:
                src.extend(neigh)
            for i in range(len(src)):
                for j in range(i, len(src)):
                    row.append(src[i] * src[j])
        out.append(row)
    return out


def expected_dim(neighbor_features, poly_degree, poly_features, poly_neighbor) -> int:
    m = poly_features + (len(neighbor_features) if poly_neighbor and neighbor_features else 0)
    return 8 + len(neighbor_features) + (m * (m + 1) // 2 if poly_degree == 2 else 0)


# -- feature map vs the naive reference ----------------------------------------------------------


@pytest.mark.parametrize("n", [8, 16])
def test_feature_map_defaults_match_naive(n):
    agent = BanditAgent(n)
    assert agent.weights.shape == (8,)
    for seed in range(5):
        obs = random_obs(n, seed)
        assert np.allclose(agent._band_features(obs), naive_phi(obs, n))
    assert agent.weights.shape[0] == expected_dim((), 1, 5, False) == 8


@pytest.mark.parametrize("n", [8, 16])
def test_feature_map_poly5_matches_naive(n):
    agent = BanditAgent(n, poly_degree=2, poly_features=5)
    assert agent.weights.shape == (expected_dim((), 2, 5, False),)
    for seed in range(5):
        obs = random_obs(n, seed)
        assert np.allclose(
            agent._band_features(obs),
            naive_phi(obs, n, poly_degree=2, poly_features=5),
        )


@pytest.mark.parametrize("n", [8, 16])
def test_feature_map_poly7_matches_naive(n):
    agent = BanditAgent(n, poly_degree=2, poly_features=7)
    assert agent.weights.shape == (expected_dim((), 2, 7, False),)
    for seed in range(5):
        obs = random_obs(n, seed)
        assert np.allclose(
            agent._band_features(obs),
            naive_phi(obs, n, poly_degree=2, poly_features=7),
        )


@pytest.mark.parametrize("n", [8, 16])
def test_feature_map_neighbor_matches_naive(n):
    agent = BanditAgent(n, neighbor_features=[0, 1, 2])
    assert agent.weights.shape == (expected_dim([0, 1, 2], 1, 5, False),)
    for seed in range(5):
        obs = random_obs(n, seed)
        assert np.allclose(
            agent._band_features(obs),
            naive_phi(obs, n, neighbor_features=(0, 1, 2)),
        )


@pytest.mark.parametrize("n", [8, 16])
def test_feature_map_neighbor_poly_matches_naive(n):
    agent = BanditAgent(n, neighbor_features=[0, 1, 2], poly_neighbor=True, poly_degree=2)
    assert agent.weights.shape == (expected_dim([0, 1, 2], 2, 5, True),)
    for seed in range(5):
        obs = random_obs(n, seed)
        assert np.allclose(
            agent._band_features(obs),
            naive_phi(obs, n, neighbor_features=(0, 1, 2), poly_degree=2, poly_neighbor=True),
        )


# -- defaults are byte-identical to today ----------------------------------------------------------


def test_defaults_are_byte_identical_to_today():
    n = 8
    plain = BanditAgent(n, rng=np.random.default_rng(4))
    explicit = BanditAgent(
        n,
        poly_degree=1,
        poly_features=5,
        neighbor_features=(),
        poly_neighbor=False,
        eff_beta=0.0,
        cov_beta=0.0,
        rng=np.random.default_rng(4),
    )
    rng = np.random.default_rng(9)
    steps = [(rng.random(8 * n + 2), float(rng.normal()), int(rng.integers(0, n))) for _ in range(30)]
    for obs, reward, action in steps:
        plain.learn(obs, action, reward, obs)
        explicit.learn(obs, action, reward, obs)
    assert np.array_equal(plain.weights, explicit.weights)
    assert np.array_equal(plain.band_bias, explicit.band_bias)
    probe = random_obs(n, 123)
    assert np.array_equal(plain.q_values(probe), explicit.q_values(probe))


# -- shaping ---------------------------------------------------------------------------------------


def test_eff_beta_shifts_the_update_by_the_expected_target():
    n = 8
    obs = random_obs(n, 11)
    action, reward, scale, beta = 3, 1.0, 10.0, 2.0
    plain = BanditAgent(n, reward_scale=scale, epsilon=CONST_EPS, rng=np.random.default_rng(1))
    shaped = BanditAgent(
        n, reward_scale=scale, eff_beta=beta, epsilon=CONST_EPS, rng=np.random.default_rng(1)
    )
    shaped.observe({"scanned_bands": [3, 4], "detected_bands": [3]})
    plain.learn(obs, action, reward, obs)
    shaped.learn(obs, action, reward, obs)
    hits = 0.5
    shift = beta * hits / scale
    phi = plain._band_features(obs)[action]
    assert shaped.weights - plain.weights == pytest.approx(0.05 * shift * phi)
    assert shaped.band_bias[action] - plain.band_bias[action] == pytest.approx(0.05 * shift)
    others = [b for b in range(n) if b != action]
    assert np.allclose(shaped.band_bias[others], plain.band_bias[others])


def test_cov_beta_adds_beta_times_window_staleness():
    n = 8
    obs = np.zeros(8 * n + 2)
    obs[3 * 7 + 0] = 0.25
    obs[4 * 7 + 0] = 0.75
    obs[7 * n + 3] = 1.0
    obs[7 * n + 4] = 1.0
    action, reward, scale, beta = 3, 1.0, 10.0, 2.0
    plain = BanditAgent(n, reward_scale=scale, epsilon=CONST_EPS, rng=np.random.default_rng(2))
    shaped = BanditAgent(
        n, reward_scale=scale, cov_beta=beta, epsilon=CONST_EPS, rng=np.random.default_rng(2)
    )
    assert staleness_from_observation(obs, action, n) == pytest.approx(0.5)
    plain.learn(obs, action, reward, obs)
    shaped.learn(obs, action, reward, obs)
    shift = beta * 0.5 / scale
    phi = plain._band_features(obs)[action]
    assert shaped.weights - plain.weights == pytest.approx(0.05 * shift * phi)
    assert shaped.band_bias[action] - plain.band_bias[action] == pytest.approx(0.05 * shift)


def test_shaping_is_inactive_at_zero():
    n = 8
    obs = random_obs(n, 13)
    info = {"scanned_bands": [1, 2], "detected_bands": [1, 2]}
    with_observe = BanditAgent(n, rng=np.random.default_rng(3))
    without_observe = BanditAgent(n, rng=np.random.default_rng(3))
    with_observe.observe(info)
    with_observe.learn(obs, 1, 2.0, obs)
    without_observe.learn(obs, 1, 2.0, obs)
    assert np.array_equal(with_observe.weights, without_observe.weights)
    assert np.array_equal(with_observe.band_bias, without_observe.band_bias)


def test_eff_beta_adds_nothing_without_observe():
    n = 8
    obs = random_obs(n, 17)
    plain = BanditAgent(n, rng=np.random.default_rng(5))
    shaped = BanditAgent(n, eff_beta=3.0, rng=np.random.default_rng(5))
    plain.learn(obs, 2, 1.5, obs)
    shaped.learn(obs, 2, 1.5, obs)
    assert np.array_equal(shaped.weights, plain.weights)
    assert np.array_equal(shaped.band_bias, plain.band_bias)


def test_observe_returns_none():
    agent = BanditAgent(8, eff_beta=1.0)
    assert agent.observe({"scanned_bands": [0], "detected_bands": [0]}) is None


# -- persistence ------------------------------------------------------------------------------------


def test_save_load_round_trip_with_all_options(tmp_path):
    n = 8
    agent = BanditAgent(
        n,
        poly_degree=2,
        poly_features=6,
        neighbor_features=[0, 1, 2],
        poly_neighbor=True,
        eff_beta=1.0,
        cov_beta=1.0,
        rng=np.random.default_rng(6),
    )
    rng = np.random.default_rng(7)
    for i in range(20):
        obs = rng.random(8 * n + 2)
        agent.learn(obs, i % n, float(rng.normal()), obs)
    path = tmp_path / "bandit_opts.npz"
    agent.save(path)
    restored = BanditAgent.load(path)
    assert np.array_equal(restored.weights, agent.weights)
    assert restored.hyperparams() == agent.hyperparams()
    agent.rng = np.random.default_rng(0)
    restored.rng = np.random.default_rng(0)
    probes = [random_obs(n, 100 + i) for i in range(20)]
    assert [restored.select_action(o, explore=False) for o in probes] == [
        agent.select_action(o, explore=False) for o in probes
    ]


def test_old_file_without_new_keys_loads_as_default(tmp_path):
    agent = BanditAgent(8, rng=np.random.default_rng(8))
    path = tmp_path / "bandit_old.npz"
    agent.save(path)
    data = dict(np.load(path, allow_pickle=False))
    hp = json.loads(str(data["hyperparams"]))
    assert not (set(hp) & {"poly_degree", "poly_features", "neighbor_features",
                           "poly_neighbor", "eff_beta", "cov_beta"})
    restored = BanditAgent.load(path)
    assert restored.weights.shape == (8,)
    assert (restored.poly_degree, restored.poly_features, restored.poly_neighbor) == (1, 5, False)
    assert tuple(restored.neighbor_features) == ()
    assert (restored.eff_beta, restored.cov_beta) == (0.0, 0.0)


def test_weight_length_mismatch_raises(tmp_path):
    agent = BanditAgent(8, poly_degree=2, rng=np.random.default_rng(9))
    path = tmp_path / "bandit_bad.npz"
    agent.save(path)
    data = dict(np.load(path, allow_pickle=False))
    data["weights"] = np.zeros(8)
    np.savez(path, **data)
    with pytest.raises(ValueError, match="weight"):
        BanditAgent.load(path)


# -- hyperparams, validation, factory -----------------------------------------------------------------


def test_hyperparams_omit_new_keys_at_default():
    hp = BanditAgent(8).hyperparams()
    for key in ("poly_degree", "poly_features", "neighbor_features",
                "poly_neighbor", "eff_beta", "cov_beta"):
        assert key not in hp


def test_hyperparams_contain_new_keys_when_set():
    hp = BanditAgent(
        8, poly_degree=2, poly_features=6, neighbor_features=[0, 5],
        poly_neighbor=True, eff_beta=1.5, cov_beta=0.5,
    ).hyperparams()
    assert hp["poly_degree"] == 2
    assert hp["poly_features"] == 6
    assert list(hp["neighbor_features"]) == [0, 5]
    assert hp["poly_neighbor"] is True
    assert hp["eff_beta"] == pytest.approx(1.5)
    assert hp["cov_beta"] == pytest.approx(0.5)


@pytest.mark.parametrize("kwargs", [
    {"poly_degree": 0},
    {"poly_degree": 3},
    {"poly_features": 0},
    {"poly_features": 8},
    {"neighbor_features": [7]},
    {"neighbor_features": [-1]},
    {"eff_beta": -0.1},
    {"cov_beta": -1.0},
])
def test_invalid_values_raise(kwargs):
    with pytest.raises(ValueError):
        BanditAgent(8, **kwargs)


def test_feature_weights_names_new_entries():
    agent = BanditAgent(8, neighbor_features=[0, 1], poly_degree=2, poly_features=2)
    names = list(agent.feature_weights())
    assert names[:8] == [*BAND_FEATURES, "bias"]
    assert names[8:10] == ["next_time_since_last_scan", "next_recent_detection_rate_ewma"]
    assert names[10] == "time_since_last_scan*time_since_last_scan"
    assert "recent_detection_rate_ewma*recent_detection_rate_ewma" in names
    assert len(names) == agent.weights.shape[0]


def test_build_agent_plumbing():
    agent = build_agent("bandit", 8, {
        "poly_degree": 2,
        "poly_features": 6,
        "neighbor_features": [0, 1, 2],
        "poly_neighbor": True,
        "eff_beta": 1.0,
        "cov_beta": 0.5,
    })
    assert isinstance(agent, BanditAgent)
    assert (agent.poly_degree, agent.poly_features, agent.poly_neighbor) == (2, 6, True)
    assert tuple(agent.neighbor_features) == (0, 1, 2)
    assert (agent.eff_beta, agent.cov_beta) == (1.0, 0.5)
    assert agent.weights.shape == (expected_dim([0, 1, 2], 2, 6, True),)


def test_training_smoke_with_all_options_on():
    from ml.environments.environment import EWEnvironment
    from ml.evaluation.runner import run_episode

    agent = build_agent("bandit", 8, {
        "poly_degree": 2,
        "poly_features": 5,
        "neighbor_features": [0, 1, 2],
        "poly_neighbor": True,
        "eff_beta": 1.0,
        "cov_beta": 0.5,
    })
    env = EWEnvironment(num_bands=8, duration_steps=60, num_emitters=3, seed=3)
    run_episode(env, agent, seed=3, learn=True)
    assert np.all(np.isfinite(agent.weights))
    assert np.all(np.isfinite(agent.band_bias))
