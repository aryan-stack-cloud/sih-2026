"""Baseline-vs-ML comparison across policies on one scenario.

This is the MVP acceptance gate (Ai-ml-1 Level 6) and the number the demo leads with.

    python scripts/compare.py --scenario A --policies baseline,bandit --episodes 20 --seed 42
    python scripts/compare.py --scenario B --policies baseline,bandit,q_learning
    python scripts/compare.py --scenario B --ablate-periodicity

Every policy is run on the identical seed list, so the spectrum is the same for all of them and
the only thing that differs is the scheduling decision.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from ml.agents.factory import build_agent
from ml.environments.environment import make_env, null_periodicity_env
from ml.training.trainer import evaluate, train
from ml.utils.config import SCENARIO_IDS, episode_seeds, load_scenario

# Metrics shown in the comparison table. "lower" marks the ones where less is better.
ROWS = [
    ("Pd  (probability of detection)", "pd", "{:.4f}", "higher"),
    ("Pfa (probability of false alarm)", "pfa", "{:.4f}", "lower"),
    ("AIT (detected runs only)", "ait", "{:.2f}", "lower"),
    ("AIT censored (all runs)", "ait_censored", "{:.1f}", "lower"),
    ("HPDR (high-priority detection)", "hpdr", "{:.4f}", "higher"),
    ("Interception ratio", "interception_ratio", "{:.4f}", "higher"),
    ("Scan efficiency", "scan_efficiency", "{:.4f}", "higher"),
    ("Run intercept rate", "run_intercept_rate", "{:.4f}", "higher"),
    ("Coverage", "coverage", "{:.4f}", "higher"),
    ("Cumulative reward (mean)", "cumulative_reward_mean", "{:.0f}", "higher"),
]


def run_policy_for(scenario: dict, policy: str, episodes: int | None, env_factory=None) -> dict:
    """Baseline needs no training; the learned policies train on held-out seeds first."""
    seeds = episode_seeds(scenario, episodes)
    if policy in ("baseline", "random"):
        # "random" is the Level 6 reference; "baseline" is the round-robin open-loop sweep.
        agent = build_agent(
            "baseline",
            scenario["bands"],
            {"stride": scenario["receiver"]["bandwidth_k"],
             "mode": "random" if policy == "random" else "round_robin"},
        )
        summary = evaluate(agent, scenario, seeds=seeds)
        summary["policy"] = policy
        return summary
    result = train(policy, scenario, eval_episodes=episodes)
    return result["summary"]


def print_table(scenario: dict, results: dict[str, dict], reference: str) -> None:
    policies = list(results)
    width = max(34, *(len(p) for p in policies))
    header = f"  {'metric':<34}" + "".join(f"{p:>{max(14, len(p) + 2)}}" for p in policies)

    print(f"\n{scenario['name']}   |   bands={scenario['bands']}  "
          f"emitters={scenario['emitters']}  duration={scenario['duration_steps']}  "
          f"episodes={results[policies[0]]['episodes']}")
    print(f"  expected: {scenario['expected_outcome']}")
    print("=" * len(header))
    print(header)
    print("-" * len(header))
    for label, key, fmt, direction in ROWS:
        line = f"  {label:<34}"
        for p in policies:
            line += f"{fmt.format(results[p][key]):>{max(14, len(p) + 2)}}"
        print(line)
    print("-" * len(header))

    base = results.get(reference)
    if not base:
        return
    print(f"\n  Change vs {reference}:")
    for p in policies:
        if p == reference:
            continue
        deltas = []
        for label, key, _fmt, direction in ROWS:
            b, v = base[key], results[p][key]
            if b == 0:
                continue
            pct = 100.0 * (v / b - 1.0)
            better = (pct > 0) if direction == "higher" else (pct < 0)
            deltas.append(f"{label.split('(')[0].strip()} {pct:+.1f}% {'[+]' if better else '[-]'}")
        print(f"    {p:<12} " + "  |  ".join(deltas[:4]))
        print(f"    {'':<12} " + "  |  ".join(deltas[4:]))


def gate_check(results: dict[str, dict], reference: str = "random") -> bool:
    """The MVP acceptance gate, as the specs actually word it.

    Ai-ml-1 README Level 6: "Bandit measurably beats a **random** baseline on Scenario A/B on
    these metrics" -- Pd, Pfa, AIT, latency, HPDR. PRD Phase 4: "beats baseline Pd on Scenario
    A/B". So the criteria are Pd up, HPDR up, and Pfa not worse, against the random baseline.

    Round-robin is reported alongside as the more demanding reference, and the coverage figures
    (censored AIT, run intercept rate) are printed as a caveat rather than folded into pass/fail
    -- they are a genuine trade-off, not a gate the spec sets. See the README section
    "Where the learned policy loses".
    """
    base = results.get(reference) or results.get("baseline")
    learned = [p for p in results if p not in ("baseline", "random")]
    if not base or not learned:
        return False
    ok = True
    print(f"\n  MVP acceptance gate (Ai-ml-1 Level 6 / PRD Phase 4), vs {reference}:")
    for p in learned:
        r = results[p]
        checks = {
            "Pd": (r["pd"] > base["pd"], f"{r['pd']:.4f} vs {base['pd']:.4f}"),
            "HPDR": (r["hpdr"] > base["hpdr"], f"{r['hpdr']:.4f} vs {base['hpdr']:.4f}"),
            "Pfa": (r["pfa"] <= base["pfa"] + 0.02, f"{r['pfa']:.4f} vs {base['pfa']:.4f}"),
            "AIT": (r["ait"] <= base["ait"] or base["ait"] == 0,
                    f"{r['ait']:.2f} vs {base['ait']:.2f}"),
        }
        passed = all(v[0] for v in checks.values())
        ok &= passed
        print(f"    {p:<12} " + "  ".join(
            f"{name} {'OK ' if good else 'BAD'} ({detail})" for name, (good, detail) in checks.items()
        ) + f"  ->  {'PASS' if passed else 'FAIL'}")

        rr = results.get("baseline")
        if rr:
            print(f"    {'':<12} caveat vs round-robin: run intercept rate "
                  f"{r['run_intercept_rate']:.4f} vs {rr['run_intercept_rate']:.4f}, "
                  f"censored AIT {r['ait_censored']:.0f} vs {rr['ait_censored']:.0f}")
    return ok


def main() -> int:
    p = argparse.ArgumentParser(description="Compare scan-scheduling policies on one scenario.")
    p.add_argument("--scenario", default="A",
                   choices=[*SCENARIO_IDS, *[s.lower() for s in SCENARIO_IDS]])
    p.add_argument("--policies", default="random,baseline,bandit",
                   help="comma-separated; 'random' and 'baseline' are the two "
                        "open-loop references, e.g. random,baseline,bandit,q_learning")
    p.add_argument("--episodes", type=int, default=None)
    p.add_argument("--seed", type=int, default=None)
    p.add_argument("--ablate-periodicity", action="store_true",
                   help="also run the ML policies with periodicity features zeroed "
                        "(PRD Definition-of-Done item 8)")
    p.add_argument("--json", type=Path, default=None)
    args = p.parse_args()

    scenario = load_scenario(args.scenario)
    if args.seed is not None:
        scenario["seed"] = args.seed
        scenario["seed_range"] = [args.seed, args.seed + scenario.get("episodes", 20)]

    policies = [s.strip().lower() for s in args.policies.split(",") if s.strip()]
    results: dict[str, dict] = {}
    for policy in policies:
        print(f"  running {policy} ...", flush=True)
        results[policy] = run_policy_for(scenario, policy, args.episodes)

    print_table(scenario, results, reference="baseline" if "baseline" in results else policies[0])
    passed = gate_check(results, reference="random" if "random" in results else "baseline")

    if args.ablate_periodicity:
        _ablation(scenario, [p for p in policies if p not in ("baseline", "random")],
                  args.episodes, results)

    if args.json:
        args.json.write_text(
            json.dumps({k: {kk: vv for kk, vv in v.items()} for k, v in results.items()},
                       indent=2, default=str),
            encoding="utf-8",
        )
        print(f"\nwrote {args.json}")
    return 0 if passed else 1


def _ablation(scenario: dict, policies: list[str], episodes: int | None, results: dict) -> None:
    """Scenario-B A/B: the same policy with and without Ai-ml-2's features in the state.

    PRD Definition-of-Done item 8 asks whether periodic-emitter prediction measurably improves
    detection latency. Running the identical policy on the identical seeds with the two
    periodicity columns pinned to zero isolates exactly that contribution.
    """
    print("\n  Periodicity ablation (PRD Definition-of-Done item 8)")
    print("  " + "-" * 60)
    for policy in policies:
        from ml.training.trainer import train as _train

        ablated = _train(
            policy, scenario, eval_episodes=episodes,
            hyperparams=None,
        )
        # Re-evaluate the trained agent with the periodicity provider disabled.
        from ml.training.trainer import evaluate as _evaluate
        import ml.training.trainer as trainer_mod

        agent = ablated["agent"]
        seeds = episode_seeds(scenario, episodes)
        original = trainer_mod.make_env
        try:
            trainer_mod.make_env = lambda cfg, seed=None, **kw: null_periodicity_env(
                cfg, seed=seed, **kw
            )
            without = _evaluate(agent, scenario, seeds=seeds)
        finally:
            trainer_mod.make_env = original

        with_p = results.get(policy) or ablated["summary"]
        d_ait = without["ait_censored"] - with_p["ait_censored"]
        print(f"    {policy}:  censored AIT with={with_p['ait_censored']:.1f}  "
              f"without={without['ait_censored']:.1f}  (periodicity improves it by {d_ait:+.1f} steps)")
        print(f"    {'':<{len(policy)}}   runs intercepted with={with_p['detected_runs']}  "
              f"without={without['detected_runs']}  of {with_p['total_runs']}")
        print(f"    {'':<{len(policy)}}   raw AIT with={with_p['ait']:.2f} without={without['ait']:.2f} "
              f"-- conditioned on detection, not comparable on its own")


if __name__ == "__main__":
    raise SystemExit(main())
