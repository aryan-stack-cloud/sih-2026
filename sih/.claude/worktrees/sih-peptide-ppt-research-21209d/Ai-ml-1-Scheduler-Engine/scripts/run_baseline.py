"""Open-loop baseline run (FR-005).

Establishes the control-group numbers every learned policy is measured against.

    python scripts/run_baseline.py --scenario A --seed 42
    python scripts/run_baseline.py --scenario B --episodes 20 --json out.json
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from ml.agents.baseline_scanner import BaselineScanner
from ml.evaluation.runner import run_policy
from ml.utils.config import SCENARIO_IDS, load_scenario


def main() -> int:
    p = argparse.ArgumentParser(description="Run the open-loop baseline scanner.")
    p.add_argument("--scenario", default="A", choices=[*SCENARIO_IDS, *[s.lower() for s in SCENARIO_IDS]])
    p.add_argument("--seed", type=int, default=None, help="override the scenario base seed")
    p.add_argument("--episodes", type=int, default=None)
    p.add_argument("--mode", default="round_robin", choices=["round_robin", "fixed_order"])
    p.add_argument("--stride", type=int, default=None,
                   help="bands advanced per step; defaults to the receiver bandwidth K")
    p.add_argument("--json", type=Path, default=None, help="write the summary to this path")
    args = p.parse_args()

    scenario = load_scenario(args.scenario)
    if args.seed is not None:
        scenario["seed"] = args.seed
        scenario["seed_range"] = [args.seed, args.seed + scenario.get("episodes", 20)]

    stride = args.stride if args.stride is not None else scenario["receiver"]["bandwidth_k"]
    result = run_policy(
        scenario,
        agent_factory=lambda n: BaselineScanner(n, mode=args.mode, stride=stride),
        episodes=args.episodes,
        learn=False,
    )
    summary = result["summary"]

    print(f"\n{scenario['name']}  |  policy=baseline ({args.mode}, stride={stride})")
    print(f"bands={scenario['bands']}  emitters={scenario['emitters']}  "
          f"duration={scenario['duration_steps']}  episodes={summary['episodes']}")
    print("-" * 62)
    for label, key, fmt in [
        ("Probability of Detection (Pd)", "pd", "{:.4f}"),
        ("Probability of False Alarm (Pfa)", "pfa", "{:.4f}"),
        ("Average Intercept Time (AIT)", "ait", "{:.2f} steps"),
        ("High-Priority Detection Rate", "hpdr", "{:.4f}"),
        ("Interception Ratio", "interception_ratio", "{:.4f}"),
        ("Scan Efficiency", "scan_efficiency", "{:.4f}"),
        ("Coverage", "coverage", "{:.4f}"),
        ("Run intercept rate", "run_intercept_rate", "{:.4f}"),
        ("Cumulative reward (mean)", "cumulative_reward_mean", "{:.1f}"),
    ]:
        print(f"  {label:<34} {fmt.format(summary[key])}")
    print("-" * 62)
    print(f"  counts {summary['counts']}  wall={summary['wall_seconds']}s")

    if args.json:
        args.json.write_text(json.dumps(summary, indent=2), encoding="utf-8")
        print(f"\nwrote {args.json}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
