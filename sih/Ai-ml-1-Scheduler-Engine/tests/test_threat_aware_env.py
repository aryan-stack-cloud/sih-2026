"""Threat-aware training environment (Task 3).

When ``threat_aware`` is on, each scan lets the environment update its per-band
priority weights from the ground truth: weights decay toward their base values
every step, and every detected band snaps to the priority of the emitter seen
there. Only detected bands reveal anything, so nothing leaks. With the flag
off, the weights are never touched and behaviour is identical to today's.
"""

from __future__ import annotations

import numpy as np
import pytest

from ml.environments.environment import EWEnvironment, make_env
from ml.utils.config import load_scenario


def test_flag_off_leaves_priority_weights_at_base():
    env = make_env(load_scenario("B"), seed=7)
    env.reset()
    base = env.state_builder.band_priority_weight.copy()
    for t in range(200):
        env.step(t % env.num_bands)
    assert np.array_equal(env.state_builder.band_priority_weight, base)


def test_flag_on_learns_high_priority_weights_within_bounds():
    cfg = {**load_scenario("B"), "high_priority_fraction": 1.0}
    env = make_env(cfg, seed=7, threat_aware=True)
    env.reset()
    for t in range(300):
        env.step(t % env.num_bands)
    w = env.state_builder.band_priority_weight
    assert bool((w > 1.0).any())
    assert bool((w <= 2.0).all())
    assert bool((w >= 1.0).all())


def test_observe_priority_sets_detected_band_and_decays():
    env = make_env(load_scenario("B"), seed=7, threat_aware=True, priority_decay=0.5)
    env.reset()
    env.ground_truth.priority[0, 3] = 2.0
    env._observe_priority(0, [3])
    assert float(env.state_builder.band_priority_weight[3]) == 2.0
    env._observe_priority(1, [])
    assert float(env.state_builder.band_priority_weight[3]) == 1.5
    env._observe_priority(1, [])
    assert float(env.state_builder.band_priority_weight[3]) == 1.25


def test_reset_restores_base_weights_between_episodes():
    cfg = {**load_scenario("B"), "high_priority_fraction": 1.0}
    env = make_env(cfg, seed=7, threat_aware=True)
    env.reset()
    base = env.state_builder.band_priority_weight.copy()
    for t in range(300):
        env.step(t % env.num_bands)
    assert not np.array_equal(env.state_builder.band_priority_weight, base)
    env.reset()
    assert np.array_equal(env.state_builder.band_priority_weight, base)


def test_flag_on_does_not_change_predetection_outputs():
    cfg = load_scenario("B")
    seed = next(
        s
        for s in range(100)
        if _detected_on_step_zero(cfg, s) == []
    )
    off = make_env(cfg, seed=seed)
    on = make_env(cfg, seed=seed, threat_aware=True)
    obs_off, _ = off.reset()
    obs_on, _ = on.reset()
    assert np.array_equal(obs_off, obs_on)
    step_off = off.step(0)
    step_on = on.step(0)
    assert step_off[1] == step_on[1]
    assert np.array_equal(step_off[0], step_on[0])


def _detected_on_step_zero(cfg: dict, seed: int) -> list:
    env = make_env(cfg, seed=seed)
    env.reset()
    env.step(0)
    return list(env.history[-1]["detected_bands"])


def test_make_env_honours_threat_aware_in_config():
    cfg = {**load_scenario("B"), "threat_aware": True}
    assert make_env(cfg, seed=1).threat_aware is True
    assert make_env(load_scenario("B"), seed=1).threat_aware is False
    # An explicit override wins over the config file value.
    assert make_env(cfg, seed=1, threat_aware=False).threat_aware is False


@pytest.mark.parametrize("bad_decay", [0, 1.5])
def test_invalid_priority_decay_raises(bad_decay):
    with pytest.raises(ValueError):
        EWEnvironment(priority_decay=bad_decay)
