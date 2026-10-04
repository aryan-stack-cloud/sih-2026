"""Mixed training horizons for the tabular trainer (opt-in, default unchanged).

Tabular agents train on full-length episodes but are served for 80 to 400 steps; episodes of
mixed lengths (short, short, full, ...) improve short-run efficiency. `train_horizons` is a
training-hyperparameter only: it never reaches the agent constructors.
"""

from __future__ import annotations

import pytest

from ml.training import trainer as T
from ml.training.trainer import train


def _cfg():
    from ml.utils.config import load_scenario

    cfg = dict(load_scenario("B"))
    cfg["duration_steps"] = 40
    return cfg


def test_training_episodes_use_configured_horizons(monkeypatch):
    durations = []
    orig_run = T.run_episode

    def spy(env, *args, **kwargs):
        durations.append(env.duration_steps)
        return orig_run(env, *args, **kwargs)

    monkeypatch.setattr(T, "run_episode", spy)
    res = train(
        "bandit",
        _cfg(),
        hyperparams={"train_horizons": [10, 20, 0]},
        episode_count=6,
        eval_episodes=1,
    )
    assert durations[:6] == [10, 20, 40, 10, 20, 40]
    assert res["summary"]["hyperparams"]["train_horizons"] == [10, 20, 0]


def test_horizons_never_reach_the_agent_constructor(monkeypatch):
    import ml.training.trainer as TT

    seen: dict = {}
    orig_build = TT.build_agent

    def spy(policy, num_bands, hyperparams=None, *args, **kwargs):
        seen["hyperparams"] = dict(hyperparams or {})
        return orig_build(policy, num_bands, hyperparams, *args, **kwargs)

    monkeypatch.setattr(TT, "build_agent", spy)
    train(
        "bandit",
        _cfg(),
        hyperparams={"train_horizons": [10, 20, 0]},
        episode_count=2,
        eval_episodes=1,
    )
    assert "train_horizons" not in seen["hyperparams"]


def test_empty_horizons_behaves_exactly_as_today():
    cfg = _cfg()
    plain = train("bandit", cfg, episode_count=6, eval_episodes=1)
    explicit_empty = train(
        "bandit", cfg, hyperparams={"train_horizons": []}, episode_count=6, eval_episodes=1
    )
    assert explicit_empty["train_curve"] == plain["train_curve"]
    assert "train_horizons" not in explicit_empty["summary"]["hyperparams"]
    assert "train_horizons" not in plain["summary"]["hyperparams"]


@pytest.mark.parametrize("bad", [[-1], ["x"], [1.5], [10, -2], [True], "10", 10])
def test_invalid_horizons_raise_value_error(bad):
    with pytest.raises(ValueError):
        train(
            "bandit",
            _cfg(),
            hyperparams={"train_horizons": bad},
            episode_count=2,
            eval_episodes=1,
        )


def test_deep_path_ignores_horizons(monkeypatch):
    seen: dict = {}
    orig_deep = T._train_deep

    def spy(agent, cfg, seeds, merged, progress, explicit_seeds=False):
        seen["merged"] = dict(merged)
        return orig_deep(agent, cfg, seeds, merged, progress, explicit_seeds=explicit_seeds)

    monkeypatch.setattr(T, "_train_deep", spy)
    res = train(
        "dqn",
        _cfg(),
        hyperparams={
            "train_horizons": [10, 20],
            "total_timesteps": 128,
            "learning_starts": 50,
            "buffer_size": 500,
            "batch_size": 32,
        },
        episode_count=2,
        eval_episodes=1,
    )
    assert "train_horizons" not in seen["merged"]
    assert res["summary"]["hyperparams"]["train_horizons"] == [10, 20]
    assert res["agent"].model is not None


@pytest.mark.parametrize("policy", ["bandit", "q_learning", "dqn", "ppo"])
def test_yaml_default_horizons_never_reach_constructors(policy, monkeypatch):
    """A `train_horizons` in the yaml defaults must not leak into the agents.

    `build_agent` re-reads the yaml itself, so popping the key in `train()` is not enough:
    without a pop here the bandit/Q constructors raise unexpected-keyword and the deep
    agents smuggle it into SB3. `train()` must still record the horizons.
    """
    import ml.agents.factory as F
    from ml.utils.config import load_hyperparams as real_load

    def patched(name):
        cfg = dict(real_load(name))
        if name == policy:
            cfg["train_horizons"] = [80, 0]
        return cfg

    monkeypatch.setattr(F, "load_hyperparams", patched)
    from ml.agents.factory import build_agent

    agent = build_agent(policy, 8, {})
    if policy in ("dqn", "ppo"):
        assert "train_horizons" not in agent.sb3_kwargs


def test_train_records_yaml_default_horizons(monkeypatch):
    import ml.training.trainer as TT
    from ml.utils.config import load_hyperparams as real_load

    def patched(name):
        cfg = dict(real_load(name))
        if name == "bandit":
            cfg["train_horizons"] = [80, 0]
        return cfg

    monkeypatch.setattr(TT, "load_hyperparams", patched)
    res = train("bandit", _cfg(), episode_count=2, eval_episodes=1)
    assert res["summary"]["hyperparams"]["train_horizons"] == [80, 0]
