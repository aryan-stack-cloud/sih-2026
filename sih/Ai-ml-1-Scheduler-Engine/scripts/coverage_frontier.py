"""Map the coverage-versus-value frontier of the SCT index scheduler.

The IMPLEMENTATION.md finding was that detection density and run coverage sit on a Pareto
frontier: no reward weight buys both. The index scheduler does not abolish that frontier, it
gives you an interpretable dial onto it -- ``COVERAGE_BUDGET``, the fraction of receiver time the
guaranteed coverage cycle is allowed to consume.

At budget 1.0 the deadline equals the coverage cycle and the policy is round-robin with extra
steps. As the budget falls, more receiver time is freed for value seeking. This script walks that
dial and prints where each setting lands, so the choice is a documented trade rather than a
hyperparameter someone picked.

    python scripts/coverage_frontier.py --scenario B --episodes 5
"""

from __future__ import annotations

import argparse
import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from ml.agents.factory import build_agent  # noqa: E402
from ml.agents.index_agent import IndexAgent  # noqa: E402
from ml.training.trainer import evaluate  # noqa: E402
from ml.utils.config import episode_seeds, load_scenario  # noqa: E402

COLUMNS = [
    ("Pd", "pd", "{:.4f}"),
    ("HPDR", "hpdr", "{:.4f}"),
    ("Run intercept", "run_intercept_rate", "{:.4f}"),
    ("Intercept ratio", "interception_ratio", "{:.4f}"),
    ("AIT censored", "ait_censored", "{:.0f}"),
    ("Scan eff", "scan_efficiency", "{:.4f}"),
]


def coverage_cycle_s(scenario: dict) -> float:
    receiver = scenario["receiver"]
    dwells = math.ceil(scenario["bands"] / receiver["bandwidth_k"])
    return dwells * (receiver["step_ms"] + receiver["tuning_delay_ms"]) / 1000.0


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--scenario", default="B")
    parser.add_argument("--episodes", type=int, default=5)
    parser.add_argument(
        "--seed-offset",
        type=int,
        default=0,
        help="skip this many leading seeds, so a configuration can be validated on episodes that "
             "were not used to choose it",
    )
    parser.add_argument(
        "--budgets",
        default="1.0,0.8,0.6,0.4,0.25,0.15",
        help="fractions of receiver time committed to guaranteed coverage",
    )
    args = parser.parse_args()

    scenario = load_scenario(args.scenario)
    seeds = episode_seeds(scenario, args.episodes + args.seed_offset)[args.seed_offset:]
    cycle = coverage_cycle_s(scenario)

    rows: list[tuple[str, dict]] = []

    sweep = build_agent(
        "baseline",
        scenario["bands"],
        {"stride": scenario["receiver"]["bandwidth_k"], "mode": "round_robin"},
    )
    rows.append(("round-robin", evaluate(sweep, scenario, seeds=seeds)))

    for budget in [float(b) for b in args.budgets.split(",")]:
        agent = IndexAgent.from_scenario(scenario, deadline_s=cycle / budget)
        label = f"index @ {budget:.2f}"
        rows.append((label, evaluate(agent, scenario, seeds=seeds)))

    width = max(len(label) for label, _ in rows) + 2
    header = f"{'policy':<{width}}" + "".join(f"{name:>17}" for name, _, _ in COLUMNS)
    print(f"\n{scenario['name']}  |  coverage cycle {cycle * 1e3:.0f} ms  |  {len(seeds)} episodes")
    print("=" * len(header))
    print(header)
    print("-" * len(header))
    for label, summary in rows:
        line = f"{label:<{width}}"
        for _, key, fmt in COLUMNS:
            value = summary.get(key)
            line += f"{fmt.format(value):>17}" if value is not None else f"{'-':>17}"
        print(line)
    print("-" * len(header))
    print(
        "\nBudget is the fraction of receiver time the guaranteed coverage cycle may consume.\n"
        "1.00 is round-robin with extra steps; lower frees time for value seeking.\n"
    )


if __name__ == "__main__":
    main()
