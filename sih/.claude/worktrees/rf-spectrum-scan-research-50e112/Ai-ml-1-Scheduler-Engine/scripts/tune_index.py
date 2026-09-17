"""Tune the index scheduler's six scalars against the graded metric.

Not against a proxy reward. The objective in ``ml/tuning/objective.py`` is a weighted comparison
against round-robin on identical seeds, so what the search maximises is the same thing a reviewer
reads off the comparison table.

Six parameters, a handful of seeds, and a few minutes: small enough that the search cannot
diverge, and small enough that every tuned number can be printed and defended individually. That
is the whole argument for tuning an index instead of training a network.

**The search never scores itself.** Six free parameters against three episodes will find
something: the first run of this script reported +1.84 against a +0.41 default on its own search
seeds, which is a fit and not a result. The search runs on the training seeds and every reported
number comes from a hold-out set it never saw. A tuned configuration that does not beat the
shipped defaults on the hold-out is rejected, and saying so is the result.

    python scripts/tune_index.py --scenario B --train 3 --holdout 8 --iterations 4
    python scripts/tune_index.py --scenario B --objective coverage --write ml/configs/index_B.json
"""

from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import numpy as np  # noqa: E402
from scipy.optimize import differential_evolution  # noqa: E402

from ml.agents.factory import build_agent  # noqa: E402
from ml.agents.index_agent import IndexAgent  # noqa: E402
from ml.training.trainer import evaluate  # noqa: E402
from ml.tuning.objective import (  # noqa: E402
    OBJECTIVES,
    IndexParams,
    objective_score,
    params_to_agent_kwargs,
    train_holdout_seeds,
)
from ml.utils.config import load_scenario  # noqa: E402


def coverage_cycle_s(scenario: dict) -> float:
    receiver = scenario["receiver"]
    dwells = math.ceil(scenario["bands"] / receiver["bandwidth_k"])
    return dwells * (receiver["step_ms"] + receiver["tuning_delay_ms"]) / 1000.0


def reference_summary(scenario: dict, seeds) -> dict:
    sweep = build_agent(
        "baseline",
        scenario["bands"],
        {"stride": scenario["receiver"]["bandwidth_k"], "mode": "round_robin"},
    )
    return evaluate(sweep, scenario, seeds=seeds)


def score_params(params: IndexParams, scenario: dict, seeds, reference: dict, weights) -> float:
    agent = IndexAgent.from_scenario(
        scenario, **params_to_agent_kwargs(params, coverage_cycle_s(scenario))
    )
    return objective_score(evaluate(agent, scenario, seeds=seeds), reference, weights)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--scenario", default="B")
    parser.add_argument("--train", type=int, default=3, help="episodes the search may score")
    parser.add_argument("--holdout", type=int, default=8, help="episodes reserved for validation")
    parser.add_argument("--objective", default="balanced", choices=sorted(OBJECTIVES))
    parser.add_argument("--iterations", type=int, default=4, help="differential-evolution generations")
    parser.add_argument("--popsize", type=int, default=3, help="population multiplier per parameter")
    parser.add_argument("--seed", type=int, default=0)
    parser.add_argument("--write", type=Path, default=None, help="write the tuned params as JSON")
    args = parser.parse_args()

    scenario = load_scenario(args.scenario)
    train_seeds, holdout_seeds = train_holdout_seeds(scenario, args.train, args.holdout)
    weights = OBJECTIVES[args.objective]
    default = IndexParams.default()

    train_reference = reference_summary(scenario, train_seeds)
    holdout_reference = reference_summary(scenario, holdout_seeds)

    print(
        f"\n{scenario['name']}  |  objective '{args.objective}'"
        f"  |  train seeds {train_seeds}  |  hold-out seeds {holdout_seeds}"
    )
    print(f"  reference (round-robin, hold-out): Pd {holdout_reference['pd']:.4f}  "
          f"run-intercept {holdout_reference['run_intercept_rate']:.4f}  "
          f"censored AIT {holdout_reference['ait_censored']:.0f}")

    default_train = score_params(default, scenario, train_seeds, train_reference, weights)
    default_holdout = score_params(default, scenario, holdout_seeds, holdout_reference, weights)

    evaluations = {"n": 0}

    def cost(vector) -> float:
        evaluations["n"] += 1
        return -score_params(
            IndexParams.from_vector(vector), scenario, train_seeds, train_reference, weights
        )

    result = differential_evolution(
        cost,
        bounds=IndexParams.bounds(),
        maxiter=args.iterations,
        popsize=args.popsize,
        seed=args.seed,
        polish=False,
        init="sobol",
        workers=1,
        x0=np.asarray(default.to_vector()),
    )

    tuned = IndexParams.from_vector(result.x)
    tuned_train = -float(result.fun)
    tuned_holdout = score_params(tuned, scenario, holdout_seeds, holdout_reference, weights)

    print(f"\n  {'':<10}{'train':>12}{'hold-out':>12}   after {evaluations['n']} evaluations")
    print("  " + "-" * 36)
    print(f"  {'default':<10}{default_train:>+12.4f}{default_holdout:>+12.4f}")
    print(f"  {'tuned':<10}{tuned_train:>+12.4f}{tuned_holdout:>+12.4f}")

    generalisation = tuned_train - tuned_holdout
    if generalisation > 0.5 * max(abs(tuned_train), 1e-9):
        print(
            f"\n  The tuned score fell by {generalisation:+.4f} off the training seeds. "
            "That gap is the fit, not the policy."
        )

    if tuned_holdout <= default_holdout:
        print(
            "\n  REJECTED: the tuned parameters do not beat the shipped defaults on seeds the\n"
            "  search never saw. Keeping the defaults is the result."
        )
        chosen, chosen_score = default, default_holdout
    else:
        print("\n  ACCEPTED: the tuned parameters win on the hold-out as well as the training set.")
        chosen, chosen_score = tuned, tuned_holdout

    print("\n  parameter          default      chosen")
    print("  " + "-" * 38)
    for field, was, now in zip(
        ("w_value", "w_info", "w_novelty", "w_deadline", "rho_min", "coverage_budget"),
        default.to_vector(),
        chosen.to_vector(),
    ):
        print(f"  {field:<16}{was:>10.3f}{now:>12.3f}")
    print()

    if args.write:
        payload = {
            "scenario": scenario["scenario_id"],
            "objective": args.objective,
            "train_seeds": train_seeds,
            "holdout_seeds": holdout_seeds,
            "accepted": chosen is tuned,
            "holdout_score_vs_round_robin": chosen_score,
            "params": {
                name: value
                for name, value in zip(
                    ("w_value", "w_info", "w_novelty", "w_deadline", "rho_min", "coverage_budget"),
                    chosen.to_vector(),
                )
            },
        }
        args.write.parent.mkdir(parents=True, exist_ok=True)
        args.write.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
        print(f"  written to {args.write}\n")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
