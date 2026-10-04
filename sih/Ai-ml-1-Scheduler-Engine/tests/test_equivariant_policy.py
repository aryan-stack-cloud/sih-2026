"""Permutation-equivariant DQN/PPO policies and the reward-scale knob.

The equivariant policy shares one weight vector across bands (like the bandit),
so "a band with high detection EWMA is worth tuning to" is learned once, not
once per band index. The default MlpPolicy path must behave exactly as today.
"""

from __future__ import annotations

import json

import gymnasium as gym
import numpy as np
import pytest
import torch as th

torch_impl = pytest.importorskip("torch")
sb3 = pytest.importorskip("stable_baselines3")

from ml.agents.dqn_agent import DeepRLAgent, RewardScaleWrapper
from ml.agents.equivariant_policy import (
    BandScorer,
    EquivariantDQNPolicy,
    EquivariantPPOPolicy,
    EquivariantQNetwork,
)
from ml.environments.environment import EWEnvironment


def _rand_obs(rng: np.random.Generator, n: int, batch: int = 4) -> np.ndarray:
    return rng.random((batch, 8 * n + 2), dtype=np.float32)


def _shift_obs(obs: np.ndarray, n: int, s: int) -> np.ndarray:
    """Cyclically shift the band blocks of a flat observation by s bands."""
    out = obs.copy()
    feats = obs[:, :7 * n].reshape(-1, n, 7)
    out[:, :7 * n] = np.roll(feats, shift=s, axis=1).reshape(-1, 7 * n)
    out[:, 7 * n:8 * n] = np.roll(obs[:, 7 * n:8 * n], shift=s, axis=1)
    return out


# -- BandScorer ---------------------------------------------------------------------------------


def test_band_scorer_is_cyclic_shift_equivariant_n8():
    rng = np.random.default_rng(0)
    n, hidden = 8, 16
    scorer = BandScorer(num_bands=n, hidden=hidden)
    scorer.eval()
    obs = _rand_obs(rng, n, batch=4)
    with th.no_grad():
        scores, _ = scorer(th.as_tensor(obs))
    for s in (1, 3, n - 1):
        shifted = _shift_obs(obs, n, s)
        with th.no_grad():
            scores_shifted, _ = scorer(th.as_tensor(shifted))
        assert np.allclose(
            scores_shifted.numpy(), np.roll(scores.numpy(), shift=s, axis=1), atol=1e-5
        ), f"equivariance failed for shift {s}"


def test_band_scorer_is_cyclic_shift_equivariant_n16():
    rng = np.random.default_rng(1)
    n, hidden = 16, 16
    scorer = BandScorer(num_bands=n, hidden=hidden)
    scorer.eval()
    obs = _rand_obs(rng, n, batch=4)
    with th.no_grad():
        scores, _ = scorer(th.as_tensor(obs))
    for s in (1, 3, n - 1):
        shifted = _shift_obs(obs, n, s)
        with th.no_grad():
            scores_shifted, _ = scorer(th.as_tensor(shifted))
        assert np.allclose(
            scores_shifted.numpy(), np.roll(scores.numpy(), shift=s, axis=1), atol=1e-5
        ), f"equivariance failed for shift {s}"


def test_band_scorer_shapes_and_neighbour_dependence():
    rng = np.random.default_rng(2)
    n, hidden = 8, 16
    scorer = BandScorer(num_bands=n, hidden=hidden)
    scorer.eval()
    obs = _rand_obs(rng, n, batch=2)
    with th.no_grad():
        scores, pooled = scorer(th.as_tensor(obs))
    assert scores.shape == (2, n)
    assert pooled.shape == (2, 2 * hidden)
    # Perturbing f_{a+1} must move s_a but leave s_{a+2} alone: the neighbour
    # input is band-local by construction, not a global leak. The global mean g
    # also sees every band, so keep it fixed with a cancelling pair.
    mod = obs.copy()
    mod[:, 7:14] += 0.5  # features of band 1 == f_{0+1}
    mod[:, 35:42] -= 0.5  # features of band 5, cancelling the mean shift
    with th.no_grad():
        scores_mod, _ = scorer(th.as_tensor(mod))
    delta = np.abs(scores_mod.numpy() - scores.numpy())
    assert delta[:, 0].max() > 1e-5
    assert delta[:, 2].max() < 1e-5


# -- PPO policy ---------------------------------------------------------------------------------


def _ppo_policy(n: int, hidden: int = 16):
    from gymnasium import spaces

    from ml.environments.state import StateBuilder

    obs_space = spaces.Box(low=0.0, high=1.0, shape=(StateBuilder.vector_size(n),), dtype=np.float32)
    act_space = spaces.Discrete(n)
    return EquivariantPPOPolicy(
        obs_space, act_space, lambda _: 3e-4, num_bands=n, hidden=hidden
    )


def test_ppo_policy_forward_evaluate_and_values_run():
    n, hidden = 8, 16
    policy = _ppo_policy(n, hidden)
    policy.eval()
    obs = th.rand(4, 8 * n + 2)
    actions, values, log_prob = policy(obs, deterministic=False)
    assert actions.shape == (4,)
    assert values.shape == (4, 1)
    act = th.as_tensor(np.array([0, 1, 2, 3]))
    values2, log_prob2, entropy = policy.evaluate_actions(obs, act)
    assert values2.shape == (4, 1)
    assert log_prob2.shape == (4,)
    assert entropy.shape == (4,)
    assert policy.predict_values(obs).shape == (4, 1)


def test_ppo_initial_policy_is_near_uniform():
    n, hidden = 8, 16
    policy = _ppo_policy(n, hidden)
    policy.eval()
    obs = th.rand(16, 8 * n + 2)
    with th.no_grad():
        dist = policy.get_distribution(obs)
        probs = dist.distribution.probs.cpu().numpy()
    assert (probs.max(axis=1) - 1.0 / n).max() < 0.05


# -- DQN policy ---------------------------------------------------------------------------------


def test_dqn_q_net_output_shape():
    from gymnasium import spaces

    from ml.environments.state import StateBuilder

    n, hidden = 8, 16
    obs_space = spaces.Box(low=0.0, high=1.0, shape=(StateBuilder.vector_size(n),), dtype=np.float32)
    act_space = spaces.Discrete(n)
    policy = EquivariantDQNPolicy(
        obs_space, act_space, lambda _: 1e-3, num_bands=n, hidden=hidden
    )
    policy.eval()
    obs = th.rand(4, 8 * n + 2)
    with th.no_grad():
        q = policy.q_net(obs)
    # q_net takes extracted features (== flat obs here) and returns one score per band.
    assert q.shape == (4, n)
    assert isinstance(policy.q_net, EquivariantQNetwork) or hasattr(policy.q_net, "scorer")


# -- smoke training -------------------------------------------------------------------------------


def test_dqn_equivariant_smoke_training_and_select_action():
    env = EWEnvironment(num_bands=8, duration_steps=80, num_emitters=4, seed=7)
    agent = DeepRLAgent(
        num_bands=8,
        algorithm="dqn",
        policy="equivariant",
        policy_hidden=16,
        learning_starts=50,
        buffer_size=500,
        batch_size=32,
        total_timesteps=300,
        device="cpu",
    )
    agent.fit(env, total_timesteps=300, seed=7)
    obs, _ = env.reset(seed=7)
    action = agent.select_action(obs, explore=False)
    assert isinstance(action, int) and 0 <= action < 8


def test_ppo_equivariant_smoke_training_and_select_action():
    env = EWEnvironment(num_bands=8, duration_steps=80, num_emitters=4, seed=7)
    agent = DeepRLAgent(
        num_bands=8,
        algorithm="ppo",
        policy="equivariant",
        policy_hidden=16,
        n_steps=64,
        batch_size=32,
        total_timesteps=256,
        device="cpu",
    )
    agent.fit(env, total_timesteps=256, seed=7)
    obs, _ = env.reset(seed=7)
    action = agent.select_action(obs, explore=False)
    assert isinstance(action, int) and 0 <= action < 8


# -- save / load ----------------------------------------------------------------------------------


def _greedy_actions(agent: DeepRLAgent, rng: np.random.Generator, n: int, count: int = 20) -> list[int]:
    obs = _rand_obs(rng, n, batch=count)
    return [int(agent.model.predict(o, deterministic=True)[0].reshape(-1)[0]) for o in obs]


def test_dqn_equivariant_save_load_round_trip(tmp_path):
    env = EWEnvironment(num_bands=8, duration_steps=80, num_emitters=4, seed=7)
    agent = DeepRLAgent(
        num_bands=8,
        algorithm="dqn",
        policy="equivariant",
        policy_hidden=16,
        learning_starts=50,
        buffer_size=500,
        batch_size=32,
        total_timesteps=300,
        device="cpu",
    )
    agent.fit(env, total_timesteps=300, seed=7)
    path = tmp_path / "dqn_eq"
    agent.save(path)
    sidecar = json.loads((tmp_path / "dqn_eq.meta.json").read_text(encoding="utf-8"))
    assert sidecar["sb3_policy"] == "equivariant"
    assert sidecar["policy_hidden"] == 16
    assert "reward_scale" in sidecar
    rng = np.random.default_rng(3)
    before = _greedy_actions(agent, rng, 8)
    restored = DeepRLAgent.load(path)
    assert restored.describe()["trained"] is True
    # Identical observations for both agents: reseed so the batch matches.
    rng2 = np.random.default_rng(3)
    before2 = _greedy_actions(agent, rng2, 8)
    rng3 = np.random.default_rng(3)
    after3 = _greedy_actions(restored, rng3, 8)
    assert before2 == after3
    assert before == before2


def test_ppo_equivariant_save_load_round_trip(tmp_path):
    env = EWEnvironment(num_bands=8, duration_steps=80, num_emitters=4, seed=7)
    agent = DeepRLAgent(
        num_bands=8,
        algorithm="ppo",
        policy="equivariant",
        policy_hidden=16,
        n_steps=64,
        batch_size=32,
        total_timesteps=256,
        device="cpu",
    )
    agent.fit(env, total_timesteps=256, seed=7)
    path = tmp_path / "ppo_eq"
    agent.save(path)
    sidecar = json.loads((tmp_path / "ppo_eq.meta.json").read_text(encoding="utf-8"))
    assert sidecar["sb3_policy"] == "equivariant"
    assert sidecar["policy_hidden"] == 16
    assert "reward_scale" in sidecar
    rng = np.random.default_rng(4)
    restored = DeepRLAgent.load(path)
    assert restored.describe()["trained"] is True
    rng2 = np.random.default_rng(4)
    before2 = _greedy_actions(agent, rng2, 8)
    rng3 = np.random.default_rng(4)
    after3 = _greedy_actions(restored, rng3, 8)
    assert before2 == after3


# -- reward scale ---------------------------------------------------------------------------------


def test_reward_wrapper_multiplies_rewards():
    env = EWEnvironment(num_bands=8, duration_steps=80, num_emitters=4, seed=7)
    env.reset(seed=7)
    _, r_plain, _, _, _ = env.step(0)
    wrapped = RewardScaleWrapper(EWEnvironment(num_bands=8, duration_steps=80, num_emitters=4, seed=7), reward_scale=2.0)
    wrapped.reset(seed=7)
    _, r_scaled, _, _, _ = wrapped.step(0)
    assert r_scaled == pytest.approx(2.0 * r_plain)


def test_reward_scale_one_adds_no_wrapper():
    from unittest import mock

    captured: dict = {}
    from stable_baselines3 import PPO as SB3PPO

    real_ppo = SB3PPO
    env = EWEnvironment(num_bands=8, duration_steps=80, num_emitters=4, seed=7)
    agent = DeepRLAgent(
        num_bands=8, algorithm="ppo", policy="equivariant", policy_hidden=16,
        n_steps=64, batch_size=32, total_timesteps=64, device="cpu", reward_scale=1.0,
    )
    with mock.patch("stable_baselines3.PPO", side_effect=lambda *a, **k: real_ppo(*a, **k)) as m:
        agent.fit(env, total_timesteps=64, seed=7)
        passed_env = m.call_args[0][1]
        assert not isinstance(passed_env, RewardScaleWrapper)


def test_reward_scale_nontrivial_wraps_env():
    from unittest import mock

    from stable_baselines3 import PPO as SB3PPO

    real_ppo = SB3PPO
    env = EWEnvironment(num_bands=8, duration_steps=80, num_emitters=4, seed=7)
    agent = DeepRLAgent(
        num_bands=8, algorithm="ppo", policy="equivariant", policy_hidden=16,
        n_steps=64, batch_size=32, total_timesteps=64, device="cpu", reward_scale=2.5,
    )
    with mock.patch("stable_baselines3.PPO", side_effect=lambda *a, **k: real_ppo(*a, **k)) as m:
        agent.fit(env, total_timesteps=64, seed=7)
        passed_env = m.call_args[0][1]
        assert isinstance(passed_env, RewardScaleWrapper)
        assert passed_env.reward_scale == pytest.approx(2.5)


# -- defaults unchanged -----------------------------------------------------------------------------


def test_default_hyperparams_have_no_new_keys():
    agent = DeepRLAgent(num_bands=16, algorithm="dqn")
    hp = agent.hyperparams()
    assert "policy_hidden" not in hp
    assert "reward_scale" not in hp


def test_old_style_sidecar_still_loads(tmp_path):
    # A checkpoint from before the new keys existed: hand-written sidecar.
    env = EWEnvironment(num_bands=8, duration_steps=80, num_emitters=4, seed=7)
    agent = DeepRLAgent(
        num_bands=8, algorithm="ppo", n_steps=64, batch_size=32,
        total_timesteps=64, device="cpu",
    )
    agent.fit(env, total_timesteps=64, seed=7)
    path = tmp_path / "oldstyle"
    agent.save(path)
    meta_path = tmp_path / "oldstyle.meta.json"
    meta = json.loads(meta_path.read_text(encoding="utf-8"))
    for key in ("policy_hidden", "reward_scale"):
        meta.pop(key, None)
    meta_path.write_text(json.dumps(meta), encoding="utf-8")
    restored = DeepRLAgent.load(path)
    assert restored.policy_hidden == 64
    assert restored.reward_scale == pytest.approx(1.0)
    obs, _ = env.reset(seed=7)
    assert 0 <= restored.select_action(obs, explore=False) < 8


# -- end-to-end equivariance --------------------------------------------------------------------------


def test_shifted_observation_shifts_greedy_action():
    n, shift, hidden = 8, 3, 16
    env = EWEnvironment(num_bands=n, duration_steps=80, num_emitters=4, seed=7)
    agent = DeepRLAgent(
        num_bands=n, algorithm="ppo", policy="equivariant", policy_hidden=hidden,
        n_steps=64, batch_size=32, total_timesteps=64, device="cpu",
    )
    agent.fit(env, total_timesteps=64, seed=7)
    rng = np.random.default_rng(9)
    obs = _rand_obs(rng, n, batch=1)[0]
    shifted = _shift_obs(obs[None, :], n, shift)[0]
    a, _ = agent.model.predict(obs, deterministic=True)
    b, _ = agent.model.predict(shifted, deterministic=True)
    assert int(np.asarray(b).reshape(-1)[0]) == (int(np.asarray(a).reshape(-1)[0]) + shift) % n
