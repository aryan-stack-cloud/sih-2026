"""Phase-independent probability of intercept, per policy (solution spec Section 11.1).

Every other comparison in this project is measured at whatever relative phase the seed produced.
This one sweeps the emitter's initial phase across its whole range and reports the fraction of
phases at which each policy intercepts it at least once, so no schedule can be flattered by
happening to start in step with the spectrum.

``worst`` is the min-max criterion: the emitter the policy handles least well. A good mean with a
bad worst case is a schedule that reliably misses one specific threat.

    python scripts/phase_sweep.py --scenario B --policies baseline,index,ctmc --episodes 5
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from ml.agents.ctmc_floor import CTMCFloorAgent  # noqa: E402
from ml.agents.factory import build_agent  # noqa: E402
from ml.agents.index_agent import IndexAgent  # noqa: E402
from ml.environments.environment import make_env  # noqa: E402
from ml.evaluation.phase_sweep import phase_sweep_report  # noqa: E402
from ml.evaluation.runner import run_episode  # noqa: E402
from ml.utils.config import episode_seeds, load_scenario  # noqa: E402


def make_agent(policy: str, scenario: dict):
    if policy == "index":
        return IndexAgent.from_scenario(scenario)
    if policy == "ctmc":
        return CTMCFloorAgent(scenario["bands"])
    if policy in ("baseline", "random"):
        return build_agent(
            "baseline",
            scenario["bands"],
            {
                "stride": scenario["receiver"]["bandwidth_k"],
                "mode": "random" if policy == "random" else "round_robin",
            },
        )
    return build_agent(policy, scenario["bands"])


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--scenario", default="B")
    parser.add_argument("--policies", default="baseline,index,ctmc")
    parser.add_argument("--episodes", type=int, default=5)
    parser.add_argument("--offsets", type=int, default=64)
    args = parser.parse_args()

    scenario = load_scenario(args.scenario)
    seeds = episode_seeds(scenario, args.episodes)
    policies = [p.strip().lower() for p in args.policies.split(",") if p.strip()]

    rows = []
    for policy in policies:
        means, weighted, worst = [], [], []
        for seed in seeds:
            env = make_env(scenario, seed=seed)
            agent = make_agent(policy, scenario)
            run_episode(env, agent, seed=seed)
            report = phase_sweep_report(env.history, env.ground_truth, offsets=args.offsets)
            means.append(report["mean"])
            weighted.append(report["priority_weighted"])
            worst.append(report["worst_case"])
        rows.append(
            (
                policy,
                sum(means) / len(means),
                sum(weighted) / len(weighted),
                sum(worst) / len(worst),
            )
        )

    width = max(len(p) for p, *_ in rows) + 2
    header = f"{'policy':<{width}}{'PI (mean)':>14}{'PI (priority)':>16}{'PI (worst)':>14}"
    print(
        f"\n{scenario['name']}  |  phase-independent probability of intercept"
        f"  |  {len(seeds)} episodes, {args.offsets} phases"
    )
    print("=" * len(header))
    print(header)
    print("-" * len(header))
    for policy, mean, weighted_mean, worst_case in rows:
        print(f"{policy:<{width}}{mean:>14.4f}{weighted_mean:>16.4f}{worst_case:>14.4f}")
    print("-" * len(header))
    print(
        "\nFraction of emitter start phases at which the policy intercepts at least once.\n"
        "'worst' is the min-max criterion: the emitter this policy handles least well.\n"
    )


if __name__ == "__main__":
    main()
