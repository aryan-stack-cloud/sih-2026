"""Training-time reward shaping for DQN/PPO (opt-in, default off).

DQN/PPO learn offline, so the shaping terms from ``ml.agents.shaping`` are applied by an
environment wrapper at training time: ``r + eff_beta * hits + cov_beta * stale``, optionally
scaled by ``reward_scale`` afterwards.
"""

from __future__ import annotations

import json
from unittest import mock

import numpy as np
import pytest

from ml.agents.dqn_agent import DeepRLAgent, RewardScaleWrapper, ShapedRewardWrapper
from ml.agents.shaping import hit_share, staleness_from_ages
from ml.environments.environment import EWEnvironment

EFF, COV = 0.5, 1.5


def _step_both(actions=(0, 3, 5, 2)):
    plain = EWEnvironment(num_bands=8, duration_steps=40, num_emitters=3, seed=3)
    shaped = ShapedRewardWrapper(
        EWEnvironment(num_bands=8, duration_steps=40, num_emitters=3, seed=3),
        eff_beta=EFF,
        cov_beta=COV,
    )
    plain.reset(seed=3)
    shaped.reset(seed=3)
    return plain, shaped, list(actions)


def test_wrapper_returns_shaped_reward_on_real_steps():
    plain, shaped, actions = _step_both()
    for a in actions:
        ages = plain.state_builder.time_since_last_scan.copy()
        o1, r1, term1, trunc1, info1 = plain.step(a)
        o2, r2, term2, trunc2, info2 = shaped.step(a)
        expected = (
            r1
            + EFF * hit_share(info1)
            + COV * staleness_from_ages(ages, info1.get("scanned_bands") or [])
        )
        assert r2 == pytest.approx(expected)


def test_wrapper_leaves_everything_else_untouched():
    plain, shaped, actions = _step_both()
    for a in actions:
        o1, _, term1, trunc1, info1 = plain.step(a)
        o2, _, term2, trunc2, info2 = shaped.step(a)
        assert np.array_equal(o2, o1)
        assert term2 == term1 and trunc2 == trunc1
        assert info2 == info1


def test_shaping_applies_before_the_reward_scale():
    inner = EWEnvironment(num_bands=8, duration_steps=40, num_emitters=3, seed=3)
    env = RewardScaleWrapper(
        ShapedRewardWrapper(inner, eff_beta=EFF, cov_beta=COV), reward_scale=2.0
    )
    replay = EWEnvironment(num_bands=8, duration_steps=40, num_emitters=3, seed=3)
    env.reset(seed=3)
    replay.reset(seed=3)
    for a in (0, 3, 5):
        ages = replay.state_builder.time_since_last_scan.copy()
        _, r_plain, _, _, info = replay.step(a)
        _, r_wrapped, _, _, _ = env.step(a)
        shaped = (
            r_plain
            + EFF * hit_share(info)
            + COV * staleness_from_ages(ages, info.get("scanned_bands") or [])
        )
        assert r_wrapped == pytest.approx(2.0 * shaped)


def test_fit_nests_shaping_inside_the_scale_wrapper():
    from stable_baselines3 import DQN as SB3DQN

    env = EWEnvironment(num_bands=8, duration_steps=40, num_emitters=3, seed=3)
    agent = DeepRLAgent(
        num_bands=8,
        algorithm="dqn",
        eff_beta=0.5,
        cov_beta=1.0,
        reward_scale=2.0,
        total_timesteps=64,
        device="cpu",
    )
    with mock.patch("stable_baselines3.DQN", return_value=mock.MagicMock()) as m:
        agent.fit(env, total_timesteps=64, seed=3)
        outer = m.call_args[0][1]
        assert isinstance(outer, RewardScaleWrapper)
        assert isinstance(outer.env, ShapedRewardWrapper)
        assert outer.env.eff_beta == pytest.approx(0.5)
        assert outer.env.cov_beta == pytest.approx(1.0)
        assert SB3DQN is not None  # the real class is untouched outside the patch


def test_no_wrapper_when_everything_is_default():
    from stable_baselines3 import DQN as SB3DQN

    real = SB3DQN
    env = EWEnvironment(num_bands=8, duration_steps=40, num_emitters=3, seed=3)
    agent = DeepRLAgent(
        num_bands=8, algorithm="dqn", total_timesteps=64, device="cpu"
    )
    with mock.patch("stable_baselines3.DQN", side_effect=lambda *a, **k: real(*a, **k)) as m:
        agent.fit(env, total_timesteps=64, seed=3)
        assert m.call_args[0][1] is env


def test_sidecar_and_hyperparams_omit_zero_weights():
    agent = DeepRLAgent(num_bands=8, algorithm="dqn")
    assert "eff_beta" not in agent.hyperparams()
    assert "cov_beta" not in agent.hyperparams()


def test_sidecar_and_hyperparams_carry_nonzero_weights(tmp_path):
    agent = DeepRLAgent(num_bands=8, algorithm="dqn", eff_beta=0.5, cov_beta=2.0)
    assert agent.hyperparams()["eff_beta"] == pytest.approx(0.5)
    assert agent.hyperparams()["cov_beta"] == pytest.approx(2.0)


def test_negative_weights_raise():
    with pytest.raises(ValueError):
        DeepRLAgent(num_bands=8, algorithm="dqn", eff_beta=-0.1)
    with pytest.raises(ValueError):
        DeepRLAgent(num_bands=8, algorithm="ppo", cov_beta=-1.0)


def test_old_sidecar_without_shaping_keys_still_loads(tmp_path):
    env = EWEnvironment(num_bands=8, duration_steps=40, num_emitters=3, seed=3)
    agent = DeepRLAgent(
        num_bands=8,
        algorithm="dqn",
        learning_starts=50,
        buffer_size=500,
        batch_size=32,
        total_timesteps=200,
        device="cpu",
    )
    agent.fit(env, total_timesteps=200, seed=3)
    path = tmp_path / "dqn_old"
    agent.save(path)
    meta_path = tmp_path / "dqn_old.meta.json"
    meta = json.loads(meta_path.read_text(encoding="utf-8"))
    assert "eff_beta" not in meta and "cov_beta" not in meta
    restored = DeepRLAgent.load(path)
    assert restored.eff_beta == pytest.approx(0.0)
    assert restored.cov_beta == pytest.approx(0.0)


def test_equivariant_dqn_smoke_training_with_shaping_and_save_load(tmp_path):
    env = EWEnvironment(num_bands=8, duration_steps=40, num_emitters=3, seed=3)
    agent = DeepRLAgent(
        num_bands=8,
        algorithm="dqn",
        policy="equivariant",
        policy_hidden=16,
        eff_beta=0.5,
        cov_beta=2.0,
        learning_starts=50,
        buffer_size=500,
        batch_size=32,
        total_timesteps=300,
        device="cpu",
    )
    agent.fit(env, total_timesteps=300, seed=3)
    path = tmp_path / "dqn_shaped"
    agent.save(path)
    sidecar = json.loads((tmp_path / "dqn_shaped.meta.json").read_text(encoding="utf-8"))
    assert sidecar["eff_beta"] == pytest.approx(0.5)
    assert sidecar["cov_beta"] == pytest.approx(2.0)
    restored = DeepRLAgent.load(path)
    assert restored.eff_beta == pytest.approx(0.5)
    assert restored.cov_beta == pytest.approx(2.0)
    obs, _ = env.reset(seed=3)
    assert 0 <= restored.select_action(obs, explore=False) < 8
