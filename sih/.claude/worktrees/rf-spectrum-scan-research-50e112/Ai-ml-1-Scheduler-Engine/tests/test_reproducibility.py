"""Reproducibility and regression guards (NFR-006, Ai-ml-1 Level 8, TEST-030..034).

Two properties, and the second is the one that makes the whole evaluation meaningful:

1. Identical seed + config -> identical output, run to run.
2. Identical seed -> identical *spectrum*, whichever policy is running. Without this, a
   baseline-vs-ML comparison is two different experiments and the headline number is noise.
"""

from __future__ import annotations

import numpy as np
import pytest

from ml.agents.bandit_agent import BanditAgent
from ml.agents.baseline_scanner import BaselineScanner
from ml.agents.q_learning_agent import QLearningAgent
from ml.environments.environment import make_env
from ml.evaluation.runner import run_episode
from ml.utils.config import SCENARIO_IDS, load_scenario
from ml.utils.seeding import make_seed_bundle

SHORT = {"duration_steps": 300}


def scenario(sid: str = "A", **overrides) -> dict:
    cfg = load_scenario(sid)
    cfg.update(SHORT)
    cfg.update(overrides)
    return cfg


# -- seeding ----------------------------------------------------------------------------------

def test_seed_bundle_is_reproducible():
    a, b = make_seed_bundle(7), make_seed_bundle(7)
    assert np.array_equal(a.ground_truth.random(10), b.ground_truth.random(10))
    assert np.array_equal(a.noise.random(10), b.noise.random(10))


def test_seed_streams_are_independent_of_each_other():
    bundle = make_seed_bundle(7)
    assert not np.array_equal(bundle.ground_truth.random(10), bundle.noise.random(10))


# -- ground truth ------------------------------------------------------------------------------

@pytest.mark.parametrize("scenario_id", SCENARIO_IDS)
def test_ground_truth_is_bit_identical_for_a_seed(scenario_id):
    cfg = scenario(scenario_id)
    a, b = make_env(cfg, seed=99), make_env(cfg, seed=99)
    a.reset()
    b.reset()
    assert np.array_equal(a.ground_truth.occupancy, b.ground_truth.occupancy)
    assert np.array_equal(a.ground_truth.owner, b.ground_truth.owner)
    assert np.array_equal(a.ground_truth.activation_starts, b.ground_truth.activation_starts)


def test_different_seeds_give_different_ground_truth():
    cfg = scenario()
    a, b = make_env(cfg, seed=1), make_env(cfg, seed=2)
    a.reset()
    b.reset()
    assert not np.array_equal(a.ground_truth.occupancy, b.ground_truth.occupancy)


def test_the_spectrum_is_identical_whichever_policy_runs():
    """The controlled-experiment property behind every Section 13 comparison."""
    cfg = scenario("B")
    results = {}
    for name, agent in [
        ("baseline", BaselineScanner(cfg["bands"], stride=2)),
        ("bandit", BanditAgent(cfg["bands"])),
        ("q_learning", QLearningAgent(cfg["bands"])),
    ]:
        env = make_env(cfg, seed=555)
        run_episode(env, agent, seed=555, learn=True, explore=False)
        results[name] = env.ground_truth.occupancy.copy()

    assert np.array_equal(results["baseline"], results["bandit"])
    assert np.array_equal(results["baseline"], results["q_learning"])


# -- full episodes -------------------------------------------------------------------------------

def test_repeated_baseline_episodes_produce_identical_metrics():
    cfg = scenario()
    runs = []
    for _ in range(2):
        env = make_env(cfg, seed=31)
        runs.append(run_episode(env, BaselineScanner(cfg["bands"], stride=2), seed=31))
    a, b = runs
    assert a.as_dict() == b.as_dict()


def test_repeated_bandit_training_produces_an_identical_policy():
    """TEST-032: run-to-run reproducibility given a fixed seed."""
    cfg = scenario("B")
    trained = []
    for _ in range(2):
        agent = BanditAgent(cfg["bands"], rng=np.random.default_rng(0))
        for i, seed in enumerate([201, 202, 203]):
            run_episode(make_env(cfg, seed=seed), agent, seed=seed, learn=True, episode=i)
        trained.append(agent)
    assert np.array_equal(trained[0].weights, trained[1].weights)
    assert np.array_equal(trained[0].band_bias, trained[1].band_bias)


def test_repeated_q_learning_training_produces_an_identical_table():
    cfg = scenario("B")
    tables = []
    for _ in range(2):
        agent = QLearningAgent(cfg["bands"], rng=np.random.default_rng(0))
        for i, seed in enumerate([301, 302]):
            run_episode(make_env(cfg, seed=seed), agent, seed=seed, learn=True, episode=i)
        tables.append(agent.q_table)
    assert tables[0] == tables[1]


def test_greedy_inference_is_deterministic():
    """Deployment runs with exploration off, so a replayed simulation must replay exactly."""
    cfg = scenario()
    actions = []
    for _ in range(2):
        agent = BanditAgent(cfg["bands"])
        env = make_env(cfg, seed=77)
        obs, _ = env.reset(seed=77)
        agent.start_episode(0)
        picks = []
        for _ in range(60):
            a = agent.select_action(obs, explore=False)
            picks.append(a)
            obs, r, _, _, _ = env.step(a)
            agent.learn(obs, a, r, obs)
        actions.append(picks)
    assert actions[0] == actions[1]


# -- regression thresholds ------------------------------------------------------------------------

@pytest.mark.parametrize("scenario_id", SCENARIO_IDS)
def test_baseline_metrics_stay_within_sane_bounds(scenario_id):
    """TEST-034 distribution-shift guard: every scenario must remain scoreable.

    Deliberately loose. This catches a scenario config or emitter change that makes a scenario
    degenerate (nothing ever active, or everything always active), which would silently turn the
    comparison into a no-op rather than failing loudly.
    """
    cfg = scenario(scenario_id)
    env = make_env(cfg, seed=42)
    m = run_episode(env, BaselineScanner(cfg["bands"], stride=2), seed=42)

    occupancy = env.ground_truth.occupancy.mean()
    assert 0.01 < occupancy < 0.99, f"scenario {scenario_id} occupancy {occupancy:.3f} is degenerate"
    assert 0.0 < m.pd < 1.0
    assert 0.0 <= m.pfa < 0.5
    assert m.total_runs > 0
    assert m.coverage > 0.0
