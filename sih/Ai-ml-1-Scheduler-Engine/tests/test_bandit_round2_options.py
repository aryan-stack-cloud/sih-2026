"""Round-2 options of the contextual bandit: a decision-time staleness bonus and periodicity-phase harmonics.

``age_bonus``     adds ``age_bonus * mean staleness of the window's bands`` to the action score. It acts at decision time only (it is
                  not part of the learned estimate), so it keeps coverage directly instead of through the learned reward.
``phase_fourier`` appends conf * cos(2 pi phase) and conf * sin(2 pi phase) of the band and of the next band to the feature vector, so
                  a linear score can express "this periodic band is about to switch on".

Both default to off, and a default agent must stay what it was (same features, same scores, same registry record).
"""

from __future__ import annotations

import numpy as np
import pytest

from ml.agents.bandit_agent import BanditAgent
from ml.agents.factory import build_agent
from ml.algorithms.exploration import EpsilonSchedule
from ml.environments.state import BAND_FEATURES

CONST_EPS = EpsilonSchedule(mode="constant", start=0.0, end=0.0)
AGE = BAND_FEATURES.index("time_since_last_scan")
PHASE = BAND_FEATURES.index("periodicity_phase")
CONF = BAND_FEATURES.index("periodicity_confidence")


def obs_with_window(n: int, seed: int, k: int = 2) -> np.ndarray:
    """A random observation whose tuned-bands block marks ``k`` bands (the receiver's window size)."""
    rng = np.random.default_rng(seed)
    obs = rng.random(8 * n + 2)
    obs[7 * n : 8 * n] = 0.0
    obs[7 * n : 7 * n + k] = 1.0
    return obs


def ages_of(obs: np.ndarray, n: int) -> np.ndarray:
    return obs[: 7 * n].reshape(n, 7)[:, AGE]


def make(n: int = 8, seed: int = 0, **options) -> BanditAgent:
    agent = BanditAgent(n, epsilon=CONST_EPS, rng=np.random.default_rng(seed), **options)
    rng = np.random.default_rng(100 + seed)
    agent.weights = rng.normal(0.0, 0.3, agent.weights.shape)
    agent.band_bias = rng.normal(0.4, 0.1, n)
    return agent


# ---- defaults ---------------------------------------------------------------------------------------------------------------


def test_defaults_are_untouched() -> None:
    agent = BanditAgent(8)
    assert agent.age_bonus == 0.0
    assert agent.phase_fourier is False
    assert agent.weights.shape == (8,)
    hp = agent.hyperparams()
    assert "age_bonus" not in hp and "phase_fourier" not in hp


def test_default_scores_are_the_linear_rule() -> None:
    n = 8
    agent = make(n)
    obs = obs_with_window(n, 1)
    bands = obs[: 7 * n].reshape(n, 7)
    phi = np.hstack([bands, np.ones((n, 1))])
    np.testing.assert_allclose(agent.q_values(obs), phi @ agent.weights + agent.band_bias)


# ---- age_bonus --------------------------------------------------------------------------------------------------------------


@pytest.mark.parametrize("k", [1, 2, 3])
def test_age_bonus_adds_the_mean_staleness_of_the_window(k: int) -> None:
    n = 8
    plain, bonus = make(n), make(n, age_bonus=0.5)
    obs = obs_with_window(n, 2, k=k)
    ages = ages_of(obs, n)
    expected = np.array([sum(ages[(a + j) % n] for j in range(k)) / k for a in range(n)])
    np.testing.assert_allclose(bonus.q_values(obs) - plain.q_values(obs), 0.5 * expected)


def test_age_bonus_is_not_part_of_the_learned_estimate() -> None:
    n = 8
    plain, bonus = make(n), make(n, age_bonus=0.7)
    obs, nxt = obs_with_window(n, 3), obs_with_window(n, 4)
    for agent in (plain, bonus):
        agent.learn(obs, 2, 5.0, nxt)
    np.testing.assert_allclose(bonus.weights, plain.weights)
    np.testing.assert_allclose(bonus.band_bias, plain.band_bias)


def test_age_bonus_pulls_the_choice_toward_a_stale_window() -> None:
    n = 8
    agent = BanditAgent(n, epsilon=CONST_EPS, rng=np.random.default_rng(0), age_bonus=1.0)
    agent.weights[:] = 0.0
    agent.band_bias[:] = 0.5
    obs = np.zeros(8 * n + 2)
    obs[7 * n : 7 * n + 2] = 1.0                      # K = 2
    for b in (4, 5):                                   # a stale pair of bands
        obs[b * 7 + AGE] = 1.0
    assert agent.select_action(obs, explore=False) == 4


def test_age_bonus_must_not_be_negative() -> None:
    with pytest.raises(ValueError, match="age_bonus"):
        BanditAgent(8, age_bonus=-0.1)


# ---- phase_fourier ----------------------------------------------------------------------------------------------------------


def test_phase_fourier_appends_the_harmonics_of_the_band_and_the_next_band() -> None:
    n = 6
    agent = make(n, phase_fourier=True)
    obs = obs_with_window(n, 5)
    bands = obs[: 7 * n].reshape(n, 7)
    phi = agent._band_features(obs)
    assert phi.shape == (n, 8 + 4) and agent.weights.shape == (12,)
    for a in range(n):
        nxt = (a + 1) % n
        own = [bands[a, CONF] * np.cos(2 * np.pi * bands[a, PHASE]), bands[a, CONF] * np.sin(2 * np.pi * bands[a, PHASE])]
        nb = [bands[nxt, CONF] * np.cos(2 * np.pi * bands[nxt, PHASE]), bands[nxt, CONF] * np.sin(2 * np.pi * bands[nxt, PHASE])]
        np.testing.assert_allclose(phi[a, 8:], own + nb)


def test_phase_fourier_columns_come_last_after_neighbours_and_products() -> None:
    n = 6
    agent = make(n, phase_fourier=True, poly_degree=2, neighbor_features=(0, 1, 2), poly_neighbor=True)
    plain = make(n, poly_degree=2, neighbor_features=(0, 1, 2), poly_neighbor=True)
    obs = obs_with_window(n, 6)
    phi, base = agent._band_features(obs), plain._band_features(obs)
    assert phi.shape[1] == base.shape[1] + 4 == agent._feature_dim()
    np.testing.assert_allclose(phi[:, : base.shape[1]], base)


def test_phase_fourier_changes_the_scores_only_through_its_weights() -> None:
    n = 6
    agent = make(n, phase_fourier=True)
    obs = obs_with_window(n, 7)
    before = agent.q_values(obs)
    agent.weights[-4:] = 0.0
    zeroed = agent.q_values(obs)
    base = make(n)
    base.weights = agent.weights[:8].copy()
    base.band_bias = agent.band_bias.copy()
    np.testing.assert_allclose(zeroed, base.q_values(obs))
    assert not np.allclose(before, zeroed)


# ---- persistence, factory, description ---------------------------------------------------------------------------------------


def test_options_survive_save_and_load(tmp_path) -> None:
    n = 8
    agent = make(n, age_bonus=0.25, phase_fourier=True, poly_degree=2, align_window=True)
    path = tmp_path / "agent.npz"
    agent.save(path)
    loaded = BanditAgent.load(path)
    assert loaded.age_bonus == 0.25 and loaded.phase_fourier is True
    obs = obs_with_window(n, 8)
    np.testing.assert_allclose(loaded.q_values(obs), agent.q_values(obs))
    hp = loaded.hyperparams()
    assert hp["age_bonus"] == 0.25 and hp["phase_fourier"] is True


def test_load_rejects_a_checkpoint_whose_width_disagrees_with_the_options(tmp_path) -> None:
    agent = make(8, phase_fourier=True)
    path = tmp_path / "agent.npz"
    agent.save(path)
    data = dict(np.load(path, allow_pickle=False))
    data["weights"] = data["weights"][:-1]
    np.savez(path, **data)
    with pytest.raises(ValueError, match="phase_fourier"):
        BanditAgent.load(path)


def test_the_factory_builds_the_options_from_yaml_style_keys() -> None:
    agent = build_agent("bandit", 16, {"age_bonus": 0.1, "phase_fourier": True, "poly_degree": 2})
    assert isinstance(agent, BanditAgent)
    assert agent.age_bonus == 0.1 and agent.phase_fourier is True
    assert agent.describe()["hyperparams"]["age_bonus"] == 0.1


def test_feature_weights_name_the_harmonics() -> None:
    agent = make(8, phase_fourier=True)
    names = list(agent.feature_weights())
    assert names[-4:] == ["phase_cos", "phase_sin", "next_phase_cos", "next_phase_sin"]
    assert len(names) == agent.weights.shape[0]
