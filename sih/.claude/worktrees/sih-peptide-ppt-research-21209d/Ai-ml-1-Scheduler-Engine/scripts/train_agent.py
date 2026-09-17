"""Train a scheduler policy and register it (Ai-ml-1 Level 5, and Level 9 for DQN/PPO).

    python scripts/train_agent.py --algo bandit --scenario B --episodes 30
    python scripts/train_agent.py --algo q_learning --scenario B --episodes 40 --activate
    python scripts/train_agent.py --algo dqn --scenario B --timesteps 50000   # V2, gated

The DQN/PPO path is a V2 stretch goal gated behind the bandit clearing the MVP acceptance bar on
Scenario A/B (Ai-ml-1 Level 9, PRD Section 24). ``--force`` is required to run it, so it cannot
be reached by accident.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from ml.model_registry import ModelRegistry
from ml.training.trainer import train
from ml.utils.config import SCENARIO_IDS, load_scenario
from ml.utils.logging import configure

GATED = ("dqn", "ppo")


def main() -> int:
    p = argparse.ArgumentParser(description="Train and register a scan-scheduling policy.")
    p.add_argument("--algo", default="bandit", choices=["bandit", "q_learning", "dqn", "ppo"])
    p.add_argument("--scenario", default="A",
                   choices=[*SCENARIO_IDS, *[s.lower() for s in SCENARIO_IDS]])
    p.add_argument("--episodes", type=int, default=None, help="training episodes (tabular agents)")
    p.add_argument("--timesteps", type=int, default=None, help="SB3 total_timesteps (dqn/ppo)")
    p.add_argument("--eval-episodes", type=int, default=None)
    p.add_argument("--seed", type=int, default=None)
    p.add_argument("--activate", action="store_true", help="promote the model after training")
    p.add_argument("--force", action="store_true",
                   help="required for dqn/ppo, which are gated behind the MVP result")
    p.add_argument("--json", type=Path, default=None)
    args = p.parse_args()

    if args.algo in GATED and not args.force:
        print(
            f"\n  {args.algo.upper()} is a V2 stretch goal (Ai-ml-1 Level 9).\n"
            "  The PRD gates it behind the contextual bandit demonstrably beating the open-loop\n"
            "  baseline on Scenario A/B, and names early Deep RL as a scope-creep risk\n"
            "  (Section 24). Confirm the gate first:\n\n"
            "      python scripts/compare.py --scenario A --policies baseline,bandit\n"
            "      python scripts/compare.py --scenario B --policies baseline,bandit\n\n"
            f"  Then re-run with --force to train {args.algo}.\n"
        )
        return 2

    configure()
    scenario = load_scenario(args.scenario)
    if args.seed is not None:
        scenario["seed"] = args.seed
        scenario["seed_range"] = [args.seed, args.seed + scenario.get("episodes", 20)]

    hyperparams: dict = {}
    if args.timesteps is not None:
        hyperparams["total_timesteps"] = args.timesteps

    print(f"\n  training {args.algo} on scenario {scenario['scenario_id']} ...", flush=True)
    result = train(
        algorithm=args.algo,
        scenario=scenario,
        hyperparams=hyperparams,
        episode_count=args.episodes,
        eval_episodes=args.eval_episodes,
        progress=lambda frac, detail: print(f"    {frac * 100:5.1f}%  {detail}", flush=True),
    )
    summary = result["summary"]

    registry = ModelRegistry()
    meta = registry.register(
        result["agent"],
        algorithm=args.algo,
        scenario=scenario["scenario_id"],
        hyperparams=summary.get("hyperparams"),
        metrics={k: summary[k] for k in ("pd", "pfa", "ait", "hpdr", "scan_efficiency") if k in summary},
        activate=args.activate,
    )

    print(f"\n  registered {meta.model_id}  (version {meta.version}, active={meta.active})")
    print(f"  train: {summary['train_episodes']} episodes in {summary['train_seconds']}s")
    print(f"  eval : Pd={summary['pd']:.4f}  Pfa={summary['pfa']:.4f}  AIT={summary['ait']:.2f}  "
          f"HPDR={summary['hpdr']:.4f}  SE={summary['scan_efficiency']:.4f}")
    print(f"  decision latency: {summary['decision_latency_ms_mean']:.3f} ms/step "
          f"(NFR-002 budget: {'150' if args.algo in GATED else '50'} ms)")

    if result["train_curve"] and len(result["train_curve"]) > 1:
        curve = result["train_curve"]
        print(f"  reward curve: {curve[0]:.0f} -> {curve[-1]:.0f}")

    if hasattr(result["agent"], "feature_weights"):
        print("  learned feature weights:")
        for name, weight in result["agent"].feature_weights().items():
            print(f"    {name:<32} {weight:+.4f}")

    if args.json:
        args.json.write_text(json.dumps(summary, indent=2, default=str), encoding="utf-8")
        print(f"\n  wrote {args.json}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
