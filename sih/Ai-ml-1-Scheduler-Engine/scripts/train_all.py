"""Train and register every policy for every scenario -- the full model set the product serves.

    python scripts/train_all.py                       # all six policies x scenarios A-G
    python scripts/train_all.py --workers 8           # in parallel processes
    python scripts/train_all.py --algos bandit,q_learning --scenarios A,B

Why one model per (policy, scenario): a model's weights are sized to its scenario's band count
(16, 24 or 32), and ``ModelRegistry.resolve`` serves each run the model trained on its own scenario
first. bandit / q_learning / dqn / ppo go through ``ml.training.trainer.train``; index and ctmc are
derived rather than trained -- index is built from the hold-out-validated weights in
``ml/configs/index_tuned_B.json``, ctmc from its fixed form -- and every one is scored with the
same ``trainer.evaluate`` before it is registered.

DQN/PPO train for ``--timesteps`` at 16 bands; ``trainer._scale_for_band_count`` scales that (and
the exploration budget) up for 24- and 32-band scenarios.
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

ENGINE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ENGINE))

ALGOS = ("dqn", "ppo", "bandit", "q_learning", "index", "ctmc")
SCENARIOS = tuple("ABCDEFG")
# Rough relative cost, so the longest jobs start first and the tail of a parallel run is short.
_COST = {"dqn": 100, "ppo": 90, "q_learning": 20, "bandit": 15, "index": 5, "ctmc": 1}
METRIC_KEYS = (
    "pd", "pfa", "ait", "ait_censored", "median_latency", "hpdr", "interception_ratio",
    "scan_efficiency", "run_intercept_rate", "cumulative_reward_mean", "episodes",
    "decision_latency_ms_mean",
)


def train_one(algo: str, scenario_id: str, timesteps: int, eval_episodes: int) -> dict:
    """Train/build, evaluate and register one model. Runs inside a worker process."""
    import warnings

    warnings.filterwarnings("ignore")
    if algo in ("dqn", "ppo"):
        import torch

        torch.set_num_threads(1)   # one core per job; parallelism comes from --workers

    from ml.model_registry import ModelRegistry
    from ml.training.trainer import evaluate, train
    from ml.utils.config import load_scenario

    cfg = load_scenario(scenario_id)
    if algo == "index":
        from ml.agents.index_agent import IndexAgent
        from ml.scheduling.index_policy import IndexWeights

        tuned = json.loads((ENGINE / "ml/configs/index_tuned_B.json").read_text())["params"]
        weights = IndexWeights(w_value=tuned["w_value"], w_info=tuned["w_info"],
                               w_novelty=tuned["w_novelty"], w_deadline=tuned["w_deadline"])
        agent = IndexAgent.from_scenario(cfg, weights=weights, rho_min=tuned["rho_min"])
        summary = evaluate(agent, cfg, episodes=eval_episodes)
        summary["hyperparams"] = {k: tuned[k] for k in
                                  ("w_value", "w_info", "w_novelty", "w_deadline", "rho_min")}
    elif algo == "ctmc":
        from ml.agents.ctmc_floor import CTMCFloorAgent

        agent = CTMCFloorAgent(num_bands=int(cfg["bands"]), mean_dwell_slots=1.0)
        summary = evaluate(agent, cfg, episodes=eval_episodes)
        summary["hyperparams"] = {"mean_dwell_slots": 1.0}
    else:
        hp = {"total_timesteps": timesteps} if algo in ("dqn", "ppo") else {}
        result = train(algo, cfg, hyperparams=hp, eval_episodes=eval_episodes)
        agent, summary = result["agent"], result["summary"]

    if algo in ("index", "ctmc"):   # trained ones record it in trainer.train
        from ml.features.periodicity_provider import serving_periodicity_source

        summary["hyperparams"]["periodicity_source"] = serving_periodicity_source()
    metrics = {k: summary[k] for k in METRIC_KEYS if k in summary}
    meta = ModelRegistry().register(agent, algorithm=algo, scenario=scenario_id,
                                    hyperparams=summary.get("hyperparams"),
                                    seed_range=cfg.get("seed_range"), metrics=metrics)
    return {"algorithm": algo, "scenario": scenario_id, "model_id": meta.model_id,
            "num_bands": meta.num_bands, "metrics": metrics,
            "periodicity_source": summary["hyperparams"].get("periodicity_source")}


def main() -> int:
    p = argparse.ArgumentParser(description="Train and register every policy for every scenario.")
    p.add_argument("--algos", default=",".join(ALGOS))
    p.add_argument("--scenarios", default=",".join(SCENARIOS))
    p.add_argument("--timesteps", type=int, default=100_000,
                   help="DQN/PPO timesteps at 16 bands (scaled up for 24/32)")
    p.add_argument("--eval-episodes", type=int, default=10)
    p.add_argument("--workers", type=int, default=1, help="parallel worker processes")
    p.add_argument("--activate", default="B",
                   help="scenario whose models become each algorithm's active default ('' = none)")
    p.add_argument("--_one", nargs=2, metavar=("ALGO", "SCENARIO"), help=argparse.SUPPRESS)
    args = p.parse_args()

    if args._one:   # worker mode: one job, result as the last stdout line
        print(json.dumps(train_one(args._one[0], args._one[1], args.timesteps,
                                   args.eval_episodes)), flush=True)
        return 0

    algos = [a.strip() for a in args.algos.split(",") if a.strip()]
    scenarios = [s.strip().upper() for s in args.scenarios.split(",") if s.strip()]
    bands = {"A": 16, "B": 16, "C": 24, "D": 24, "E": 32, "F": 32, "G": 24}
    jobs = sorted(((a, s) for a in algos for s in scenarios),
                  key=lambda j: -(_COST[j[0]] * bands[j[1]]))
    env = dict(os.environ, OMP_NUM_THREADS="1", MKL_NUM_THREADS="1", PYTHONUNBUFFERED="1")

    def run(job):
        started = time.time()
        cmd = [sys.executable, str(Path(__file__).resolve()), "--_one", *job,
               "--timesteps", str(args.timesteps), "--eval-episodes", str(args.eval_episodes)]
        proc = subprocess.run(cmd, cwd=str(ENGINE), env=env, capture_output=True, text=True)
        lines = [ln for ln in proc.stdout.splitlines() if ln.startswith("{")]
        result = json.loads(lines[-1]) if proc.returncode == 0 and lines else None
        return job, result, proc.stderr[-600:], time.time() - started

    print(f"training {len(jobs)} models with {args.workers} worker(s)", flush=True)
    registered: list[dict] = []
    with ThreadPoolExecutor(max_workers=max(1, args.workers)) as pool:
        for future in as_completed([pool.submit(run, j) for j in jobs]):
            (algo, scenario), result, err, secs = future.result()
            if result is None:
                print(f"  FAILED {algo:10s} {scenario}  ({secs / 60:.1f} min)\n{err}", flush=True)
                continue
            registered.append(result)
            m = result["metrics"]
            print(f"  {algo:10s} {scenario}  {result['model_id']}  Pd={m.get('pd', 0):.3f}  "
                  f"efficiency={m.get('scan_efficiency', 0):.3f}  "
                  f"periodicity={result['periodicity_source']}  ({secs / 60:.1f} min)", flush=True)

    if args.activate:
        from ml.model_registry import ModelRegistry

        registry = ModelRegistry()
        for result in registered:
            if result["scenario"] == args.activate.upper():
                registry.activate(result["model_id"])
                print(f"  activated {result['model_id']} as the {result['algorithm']} default",
                      flush=True)
    return 0 if len(registered) == len(jobs) else 1


if __name__ == "__main__":
    raise SystemExit(main())
