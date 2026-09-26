"""DQN/PPO must train on many spectrum realisations, not one replayed layout.

SB3 auto-resets its environment with ``seed=None``, and ``EWEnvironment.reset(seed=None)``
replays the same seed by design (the reproducibility tests depend on that). Before
``_SeedCyclingEnv`` existed, every deep-RL training episode was therefore the identical emitter
layout, and the trained policies collapsed onto one constant band.
"""

from __future__ import annotations

import numpy as np

from ml.environments.environment import make_env
from ml.training.trainer import _SeedCyclingEnv, deep_training_seeds
from ml.utils.config import load_scenario


def _layout(env) -> np.ndarray:
    return np.asarray(env.unwrapped.ground_truth.occupancy)


def test_every_training_episode_gets_a_different_spectrum():
    cfg = load_scenario("B")
    seeds = deep_training_seeds(cfg, [1042], total_timesteps=3 * cfg["duration_steps"])
    env = _SeedCyclingEnv(make_env(cfg, seed=seeds[0]), seeds)

    first = _layout(env) if env.unwrapped.ground_truth is not None else None
    env.reset()                       # what SB3 does on its first reset (it passes its own seed)
    a = _layout(env).copy()
    env.reset(seed=None)              # what SB3 does on every auto-reset afterwards
    b = _layout(env).copy()

    assert first is None or first.shape == a.shape
    assert not np.array_equal(a, b), "auto-reset replayed the previous episode's spectrum"


def test_training_seeds_cover_every_episode_and_avoid_the_evaluation_seeds():
    cfg = load_scenario("B")
    total = 50_000
    seeds = deep_training_seeds(cfg, [cfg["seed"] + 1000 + i for i in range(20)], total)

    episodes_run = -(-total // cfg["duration_steps"])
    assert len(set(seeds)) >= episodes_run
    lo, hi = cfg["seed_range"]
    assert not set(seeds) & set(range(lo, hi))


def test_trainer_only_knobs_never_reach_the_sb3_constructor():
    """``reference_bands`` lives in dqn.yaml/ppo.yaml for the trainer; SB3 rejects it."""
    import pytest

    pytest.importorskip("stable_baselines3")
    from ml.agents.factory import build_agent
    from ml.training.trainer import train

    for algo in ("dqn", "ppo"):
        agent = build_agent(algo, 16, {"total_timesteps": 256})
        assert "reference_bands" not in agent.sb3_kwargs

    hp = {"total_timesteps": 256, "learning_starts": 64, "n_steps": 128, "batch_size": 32}
    for algo in ("dqn", "ppo"):
        extra = {k: v for k, v in hp.items() if not (algo == "dqn" and k == "n_steps")}
        if algo == "ppo":
            extra.pop("learning_starts")
        result = train(algo, "B", hyperparams=extra, eval_episodes=1)
        assert result["agent"].model is not None


def test_an_explicit_seed_list_long_enough_is_kept_as_is():
    cfg = load_scenario("B")
    explicit = list(range(5000, 5100))
    assert deep_training_seeds(cfg, explicit, total_timesteps=10_000) == explicit
