"""The MVP acceptance gate (Ai-ml-1 Level 6 DoD / PRD Phase 4 sign-off).

Ai-ml-1 README Level 6: "Bandit measurably beats a **random** baseline on Scenario A/B on these
metrics" -- Pd, Pfa, AIT, latency, HPDR. PRD Phase 4: "Bandit agent trains and beats baseline Pd
on Scenario A/B". Everything downstream, DQN included, is gated behind this.

These tests assert what is actually true, including the part that is not flattering: the learned
policy wins decisively on detection density (Pd, HPDR, scan efficiency) and loses on distinct-run
coverage. That loss is pinned by ``test_learned_policy_trades_run_coverage_for_density`` on
purpose -- a documented weakness that nobody can quietly regress or quietly fix without the suite
telling them.

Marked ``slow``: these run real training. Skip with ``-m "not slow"`` during inner-loop work.
"""

from __future__ import annotations

import numpy as np
import pytest

from ml.agents.bandit_agent import BanditAgent
from ml.agents.baseline_scanner import BaselineScanner
from ml.environments.environment import make_env, null_periodicity_env
from ml.evaluation.evaluator import aggregate
from ml.evaluation.runner import run_episode
from ml.utils.config import load_scenario

pytestmark = pytest.mark.slow

TRAIN_SEEDS = [1042 + i for i in range(8)]
EVAL_SEEDS = [42 + i for i in range(5)]


def scenario(sid: str) -> dict:
    cfg = load_scenario(sid)
    cfg["duration_steps"] = 1000  # shortened so the gate runs in CI time
    return cfg


def score(cfg: dict, agent, learn: bool, env_factory=make_env) -> dict:
    episodes = []
    for i, seed in enumerate(EVAL_SEEDS):
        env = env_factory(cfg, seed=seed)
        episodes.append(run_episode(env, agent, seed=seed, learn=learn, explore=False, episode=i))
    return aggregate(episodes)


def trained_bandit(cfg: dict) -> BanditAgent:
    agent = BanditAgent(cfg["bands"], rng=np.random.default_rng(0))
    for i, seed in enumerate(TRAIN_SEEDS):
        run_episode(make_env(cfg, seed=seed), agent, seed=seed, learn=True, episode=i)
    return agent


def random_baseline(cfg: dict) -> dict:
    return score(cfg, BaselineScanner(cfg["bands"], mode="random"), learn=False)


def round_robin_baseline(cfg: dict) -> dict:
    stride = cfg["receiver"]["bandwidth_k"]
    return score(cfg, BaselineScanner(cfg["bands"], stride=stride), learn=False)


# -- the gate ------------------------------------------------------------------------------------

@pytest.mark.parametrize("scenario_id", ["A", "B"])
def test_bandit_beats_the_random_baseline(scenario_id):
    """The Level 6 / Phase 4 criterion, against the reference the spec names."""
    cfg = scenario(scenario_id)
    base = random_baseline(cfg)
    bandit = score(cfg, trained_bandit(cfg), learn=True)

    assert bandit["pd"] > base["pd"], (
        f"Scenario {scenario_id}: Pd {bandit['pd']:.4f} did not beat random {base['pd']:.4f}"
    )
    assert bandit["hpdr"] > base["hpdr"], (
        f"Scenario {scenario_id}: HPDR {bandit['hpdr']:.4f} did not beat random {base['hpdr']:.4f}"
    )
    assert bandit["scan_efficiency"] > base["scan_efficiency"]


@pytest.mark.parametrize("scenario_id", ["A", "B"])
def test_bandit_also_beats_the_round_robin_sweep_on_detection(scenario_id):
    """The harder reference: the legacy open-loop scanner this project exists to replace."""
    cfg = scenario(scenario_id)
    base = round_robin_baseline(cfg)
    bandit = score(cfg, trained_bandit(cfg), learn=True)

    assert bandit["pd"] > base["pd"]
    assert bandit["hpdr"] > base["hpdr"]
    assert bandit["scan_efficiency"] > base["scan_efficiency"]


def test_the_learned_policy_does_not_pay_for_its_gains_with_false_alarms():
    """A policy that simply lowered its bar would win Pd and lose the point."""
    cfg = scenario("B")
    base = round_robin_baseline(cfg)
    bandit = score(cfg, trained_bandit(cfg), learn=True)
    assert bandit["pfa"] <= base["pfa"] + 0.02


# -- the documented weakness -----------------------------------------------------------------------

@pytest.mark.parametrize("scenario_id", ["A", "B"])
def test_learned_policy_trades_run_coverage_for_density(scenario_id):
    """Pins the known trade-off so it stays honest and visible.

    With instantaneous bandwidth K = 2 over 16 bands, a scheduler can either spread thin and
    catch the *start* of many short activation runs, or concentrate and observe far more active
    spectrum. The round-robin sweep takes the first option; the reward of Equation 10.1 pushes
    the learned policy toward the second.

    So the learned policy currently reports a lower run intercept rate and a worse censored AIT
    than the sweep. That is a real limitation, not a metric artifact, and it belongs in the demo
    narrative rather than being buried. ``w5_redundant`` is the knob that moves along this
    frontier (see the README).

    If a future change makes the learned policy win on coverage too, this test fails -- which is
    the point: the claim in the README would then need updating rather than silently going stale.
    """
    cfg = scenario(scenario_id)
    sweep = round_robin_baseline(cfg)
    bandit = score(cfg, trained_bandit(cfg), learn=True)

    assert bandit["run_intercept_rate"] < sweep["run_intercept_rate"], (
        "the run-coverage trade-off has changed; update the README claim and this test"
    )
    assert bandit["ait_censored"] > sweep["ait_censored"]
    # ...but it observes far more active spectrum per scan, which is the compensating win.
    assert bandit["scan_efficiency"] > sweep["scan_efficiency"]


# -- PRD Definition-of-Done item 8 -------------------------------------------------------------------

def test_periodicity_features_improve_detection_latency_on_scenario_b():
    """Same policy, same seeds, same spectrum -- only the two Ai-ml-2 columns differ.

    Compared on CENSORED AIT, not raw AIT. Raw AIT averages only the runs a policy actually
    caught, so the better policy scores worse on it: the extra runs periodicity lets the agent
    intercept are precisely the hard, late ones, and they pull the conditional mean up. See the
    module docstring of ml/evaluation/evaluator.py.
    """
    cfg = scenario("B")
    agent = trained_bandit(cfg)

    with_features = score(cfg, agent, learn=True)
    without_features = score(cfg, agent, learn=True, env_factory=null_periodicity_env)

    assert with_features["ait_censored"] <= without_features["ait_censored"], (
        f"periodicity features did not improve censored AIT: "
        f"{with_features['ait_censored']:.2f} vs {without_features['ait_censored']:.2f}"
    )
    assert with_features["run_intercept_rate"] >= without_features["run_intercept_rate"]
