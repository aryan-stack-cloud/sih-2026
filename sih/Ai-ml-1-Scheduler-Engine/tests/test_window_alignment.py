"""Observation-based window alignment (opt-in, default off).

The receiver observes a contiguous K-band window starting at the named band. For K = 2 the
window (a-1, a) contains the target band a just as (a, a+1) does, so the agent can choose
which neighbour rides along: the one with the higher detection EWMA.
"""

from __future__ import annotations

import json

import numpy as np
import pytest

from ml.agents.base import Agent, align_window_start
from ml.agents.bandit_agent import BanditAgent
from ml.agents.factory import build_agent
from ml.agents.q_learning_agent import QLearningAgent

N = 8


def make_obs(n: int, ewma: list[float], tuned: list[int]) -> np.ndarray:
    """A flat observation with a chosen EWMA profile and tuned block.

    Layout (ml/environments/state.py): obs[:7N] band-major features with feature index 1
    the detection EWMA, obs[7N:8N] the tuned one-hot, then two receiver scalars.
    """
    obs = np.zeros(8 * n + 2, dtype=np.float32)
    for b, e in enumerate(ewma):
        obs[b * 7 + 1] = float(e)
    for t in tuned:
        obs[7 * n + int(t)] = 1.0
    return obs


def rollout_obs(n: int = N, count: int = 20, seed: int = 3) -> list[np.ndarray]:
    """Real observations from a short rollout (tuned block sums to K = 2)."""
    from ml.environments.environment import EWEnvironment

    env = EWEnvironment(num_bands=n, duration_steps=60, num_emitters=3, seed=seed)
    rng = np.random.default_rng(seed)
    obs, _ = env.reset(seed=seed)
    out = []
    for _ in range(count):
        out.append(np.asarray(obs, dtype=np.float32))
        obs, _, _, _, _ = env.step(int(rng.integers(0, n)))
    return out


# -- the function ---------------------------------------------------------------------------------


def test_picks_left_neighbour_when_its_ewma_is_higher():
    obs = make_obs(N, [0.0, 0.9, 0.0, 0.1, 0.0, 0.0, 0.0, 0.0], [2, 3])
    assert align_window_start(2, obs, N) == 1


def test_keeps_start_when_right_neighbour_is_higher():
    obs = make_obs(N, [0.0, 0.1, 0.0, 0.9, 0.0, 0.0, 0.0, 0.0], [2, 3])
    assert align_window_start(2, obs, N) == 2


def test_tie_keeps_the_start():
    obs = make_obs(N, [0.0, 0.5, 0.0, 0.5, 0.0, 0.0, 0.0, 0.0], [2, 3])
    assert align_window_start(2, obs, N) == 2


def test_wraps_at_zero_looking_at_band_n_minus_1():
    obs = make_obs(N, [0.0, 0.2, 0.0, 0.0, 0.0, 0.0, 0.0, 0.8], [0, 1])
    assert align_window_start(0, obs, N) == N - 1


def test_wraps_at_top_looking_at_band_0():
    obs = make_obs(N, [0.9, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.1], [N - 1, 0])
    assert align_window_start(N - 1, obs, N) == N - 1
    obs2 = make_obs(N, [0.1, 0.0, 0.0, 0.0, 0.0, 0.0, 0.9, 0.0], [N - 1, 0])
    assert align_window_start(N - 1, obs2, N) == N - 2


def test_k1_returns_action_unchanged():
    obs = make_obs(N, [0.9, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0], [4])
    assert align_window_start(4, obs, N) == 4


def test_k3_returns_action_unchanged():
    obs = make_obs(N, [0.9, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0], [1, 2, 3])
    assert align_window_start(2, obs, N) == 2


def test_all_zero_tuned_block_returns_action_unchanged():
    obs = make_obs(N, [0.9, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.9], [])
    assert align_window_start(5, obs, N) == 5


def test_result_always_contains_the_target_band():
    rng = np.random.default_rng(0)
    for _ in range(30):
        ewma = list(rng.random(N))
        tuned = [int(rng.integers(0, N)), int(rng.integers(0, N))]
        obs = make_obs(N, ewma, tuned)
        a = int(rng.integers(0, N))
        got = align_window_start(a, obs, N)
        assert got in (a, (a - 1) % N)


def test_returns_a_python_int_and_accepts_lists():
    obs = make_obs(N, [0.0, 0.9, 0.0, 0.1, 0.0, 0.0, 0.0, 0.0], [2, 3])
    got = align_window_start(np.int64(2), list(obs), N)
    assert type(got) is int
    assert got == 1


def test_default_agents_have_the_flag_off():
    assert Agent.align_window is False
    assert BanditAgent(N).align_window is False
    assert QLearningAgent(N).align_window is False


# -- wiring: flag off identical, flag on equals the rule ------------------------------------------------


def test_bandit_flag_off_matches_default_construction():
    obs_list = rollout_obs()
    off = BanditAgent(N, align_window=False, rng=np.random.default_rng(11))
    default = BanditAgent(N, rng=np.random.default_rng(11))
    assert [off.select_action(o, explore=False) for o in obs_list] == [
        default.select_action(o, explore=False) for o in obs_list
    ]


def test_bandit_flag_on_applies_the_rule():
    obs_list = rollout_obs()
    off = BanditAgent(N, align_window=False, rng=np.random.default_rng(11))
    on = BanditAgent(N, align_window=True, rng=np.random.default_rng(11))
    for o in obs_list:
        unaligned = off.select_action(o, explore=False)
        assert on.select_action(o, explore=False) == align_window_start(unaligned, o, N)


def test_q_learning_flag_off_matches_default_construction():
    obs_list = rollout_obs()
    off = QLearningAgent(N, align_window=False, rng=np.random.default_rng(11))
    default = QLearningAgent(N, rng=np.random.default_rng(11))
    assert [off.select_action(o, explore=False) for o in obs_list] == [
        default.select_action(o, explore=False) for o in obs_list
    ]


def test_q_learning_flag_on_applies_the_rule():
    obs_list = rollout_obs()
    off = QLearningAgent(N, align_window=False, rng=np.random.default_rng(11))
    on = QLearningAgent(N, align_window=True, rng=np.random.default_rng(11))
    for o in obs_list:
        unaligned = off.select_action(o, explore=False)
        assert on.select_action(o, explore=False) == align_window_start(unaligned, o, N)


def _tiny_dqn():
    from ml.agents.dqn_agent import DeepRLAgent
    from ml.environments.environment import EWEnvironment

    env = EWEnvironment(num_bands=N, duration_steps=60, num_emitters=3, seed=3)
    base = DeepRLAgent(
        num_bands=N,
        algorithm="dqn",
        align_window=False,
        learning_starts=50,
        buffer_size=500,
        batch_size=32,
        total_timesteps=200,
        device="cpu",
    )
    base.fit(env, total_timesteps=200, seed=3)
    return base


def test_dqn_flag_off_matches_default_construction():
    from ml.agents.dqn_agent import DeepRLAgent

    base = _tiny_dqn()
    default = DeepRLAgent(num_bands=N, algorithm="dqn")
    default.model = base.model
    obs_list = rollout_obs()
    assert [base.select_action(o, explore=False) for o in obs_list] == [
        default.select_action(o, explore=False) for o in obs_list
    ]


def test_dqn_flag_on_applies_the_rule():
    from ml.agents.dqn_agent import DeepRLAgent

    base = _tiny_dqn()
    on = DeepRLAgent(num_bands=N, algorithm="dqn", align_window=True)
    on.model = base.model
    for o in rollout_obs():
        unaligned = base.select_action(o, explore=False)
        assert on.select_action(o, explore=False) == align_window_start(unaligned, o, N)


# -- persistence --------------------------------------------------------------------------------------


def test_bandit_save_load_keeps_the_flag(tmp_path):
    agent = BanditAgent(N, align_window=True, rng=np.random.default_rng(0))
    path = tmp_path / "bandit.npz"
    agent.save(path)
    restored = BanditAgent.load(path)
    assert restored.align_window is True


def test_bandit_old_file_without_key_loads_flag_off(tmp_path):
    agent = BanditAgent(N, align_window=True, rng=np.random.default_rng(0))
    path = tmp_path / "bandit_old.npz"
    agent.save(path)
    data = dict(np.load(path, allow_pickle=False))
    hp = json.loads(str(data["hyperparams"]))
    del hp["align_window"]
    data["hyperparams"] = json.dumps(hp)
    np.savez(path, **data)
    assert BanditAgent.load(path).align_window is False


def test_q_learning_save_load_keeps_the_flag(tmp_path):
    agent = QLearningAgent(N, align_window=True, rng=np.random.default_rng(0))
    path = tmp_path / "q.json"
    agent.save(path)
    assert QLearningAgent.load(path).align_window is True


def test_q_learning_old_file_without_key_loads_flag_off(tmp_path):
    agent = QLearningAgent(N, align_window=True, rng=np.random.default_rng(0))
    path = tmp_path / "q_old.json"
    agent.save(path)
    payload = json.loads(path.read_text(encoding="utf-8"))
    del payload["hyperparams"]["align_window"]
    path.write_text(json.dumps(payload), encoding="utf-8")
    assert QLearningAgent.load(path).align_window is False


def test_dqn_save_load_keeps_the_flag(tmp_path):
    from ml.agents.dqn_agent import DeepRLAgent

    agent = _tiny_dqn()
    agent.align_window = True
    path = tmp_path / "dqn_align"
    agent.save(path)
    sidecar = json.loads((tmp_path / "dqn_align.meta.json").read_text(encoding="utf-8"))
    assert sidecar["align_window"] is True
    assert DeepRLAgent.load(path).align_window is True


def test_dqn_old_sidecar_without_key_loads_flag_off(tmp_path):
    from ml.agents.dqn_agent import DeepRLAgent

    agent = _tiny_dqn()
    path = tmp_path / "dqn_old"
    agent.save(path)
    meta_path = tmp_path / "dqn_old.meta.json"
    meta = json.loads(meta_path.read_text(encoding="utf-8"))
    assert "align_window" not in meta
    assert DeepRLAgent.load(path).align_window is False


# -- hyperparams / describe -----------------------------------------------------------------------------


def test_hyperparams_omit_the_key_when_off():
    assert "align_window" not in BanditAgent(N).hyperparams()
    assert "align_window" not in QLearningAgent(N).hyperparams()


def test_hyperparams_contain_true_when_on():
    assert BanditAgent(N, align_window=True).hyperparams()["align_window"] is True
    assert QLearningAgent(N, align_window=True).hyperparams()["align_window"] is True


def test_describe_includes_flag_only_when_true():
    assert "align_window" not in BanditAgent(N).describe()
    assert BanditAgent(N, align_window=True).describe()["align_window"] is True
    assert "align_window" not in QLearningAgent(N).describe()
    assert QLearningAgent(N, align_window=True).describe()["align_window"] is True


def test_dqn_hyperparams_rule():
    from ml.agents.dqn_agent import DeepRLAgent

    assert "align_window" not in DeepRLAgent(num_bands=N, algorithm="dqn").hyperparams()
    assert DeepRLAgent(num_bands=N, algorithm="dqn", align_window=True).hyperparams()[
        "align_window"
    ] is True


# -- factory ----------------------------------------------------------------------------------------------


@pytest.mark.parametrize("policy", ["bandit", "q_learning", "dqn", "ppo"])
def test_build_agent_with_align_window_true(policy):
    agent = build_agent(policy, N, {"align_window": True})
    assert agent.align_window is True


@pytest.mark.parametrize("policy", ["bandit", "q_learning", "dqn", "ppo"])
def test_build_agent_defaults_to_flag_off(policy):
    assert build_agent(policy, N, {}).align_window is False
