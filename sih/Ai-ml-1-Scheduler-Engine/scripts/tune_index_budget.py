"""Tune the per-scenario Index coverage budget against the fixed sweep.

For each scenario the round-robin sweep and Index at every candidate budget are
evaluated on the SAME seeds via ``ml.training.trainer.evaluate`` -- which runs
every episode through Ai-ml-2's in-process serving estimator, exactly like
``scripts/compare.py`` and the registration-time evaluation, so the tuned
budget describes the served system. Then the budget with the best Pd among
those whose run-intercept rate stays within margin of the sweep is kept (spec
decision D2, ``ml.tuning.index_budget``). Writes ``ml/configs/index_budgets.json``
for ``train_all.py`` to read back.

    python scripts/tune_index_budget.py --scenarios B --budgets 0.5,0.25 --seeds 2000-2009
    python scripts/tune_index_budget.py --scenarios A,B,C,D,E,F,G --workers 4
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import tempfile
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

ENGINE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ENGINE))

from ml.tuning.index_budget import BUDGETS_PATH, choose_budget
from ml.utils.config import SCENARIO_IDS

METRIC_KEYS = ("pd", "run_intercept_rate", "ait_censored", "scan_efficiency",
               "detected_runs", "total_runs")


def rule_text(margin: float) -> str:
    return (f"highest Pd among budgets whose distinct-burst rate is at least the "
            f"sweep's minus {margin}; ties within 0.001 go to the larger budget; "
            f"none feasible keeps 0.5")


def parse_scenarios(spec: str) -> list[str]:
    scenarios = [s.strip().upper() for s in spec.split(",") if s.strip()]
    for sid in scenarios:
        if sid not in SCENARIO_IDS:
            raise ValueError(f"unknown scenario {sid!r}; expected one of {SCENARIO_IDS}")
    return scenarios


def parse_budgets(spec: str) -> list[float]:
    budgets = [float(s) for s in spec.split(",") if s.strip()]
    for b in budgets:
        if not 0.0 < b <= 1.0:
            raise ValueError(f"budget must lie in (0, 1], got {b!r}")
    return budgets


def parse_seeds(spec: str) -> list[int]:
    """A comma list of seeds and inclusive ranges, e.g. ``2000-2009`` or ``2000,2003``."""
    seeds: list[int] = []
    for part in spec.split(","):
        part = part.strip()
        if not part:
            continue
        if "-" in part:
            start, end = part.split("-", 1)
            seeds.extend(range(int(start), int(end) + 1))
        else:
            seeds.append(int(part))
    return seeds


def _eval_job(job: tuple[str, str, list[int]]) -> tuple[str, str, dict]:
    """Evaluate one (scenario, budget-or-sweep) on the given seeds.

    Module level so a ``ProcessPoolExecutor`` can pickle it on Windows; every
    import it needs happens inside, after the fresh interpreter starts.
    """
    scenario_id, spec, seeds = job

    from ml.agents.factory import build_agent
    from ml.agents.index_agent import IndexAgent
    from ml.scheduling.index_policy import IndexWeights
    from ml.training.trainer import evaluate
    from ml.utils.config import load_scenario

    scenario = load_scenario(scenario_id)
    if spec == "sweep":
        stride = int(scenario["receiver"]["bandwidth_k"])
        agent = build_agent(
            "baseline", scenario["bands"], {"stride": stride, "mode": "round_robin"})
    else:
        tuned = json.loads((ENGINE / "ml/configs/index_tuned_B.json").read_text())["params"]
        weights = IndexWeights(w_value=tuned["w_value"], w_info=tuned["w_info"],
                               w_novelty=tuned["w_novelty"], w_deadline=tuned["w_deadline"])
        agent = IndexAgent.from_scenario(
            scenario, weights=weights, rho_min=tuned["rho_min"],
            coverage_budget=float(spec))

    # trainer.evaluate, not runner.run_policy: it scores every episode through
    # Ai-ml-2's serving estimator (_serving_env), which is what a served model
    # actually sees. run_policy would use the training stand-in instead.
    summary = evaluate(agent, scenario, seeds=list(seeds))
    return scenario_id, spec, {k: summary[k] for k in METRIC_KEYS}


def _print_scenario(scenario_id: str, seeds: list[int], rows: dict,
                    budgets: list[float], chosen: float) -> None:
    print(f"\nScenario {scenario_id} (seeds {seeds[0]}-{seeds[-1]}, n={len(seeds)}):",
          flush=True)
    print(f"  {'budget':<8}{'Pd':>8}  {'bursts':>9}  {'ait_cens':>8}", flush=True)
    for spec in ["sweep", *(str(b) for b in budgets)]:
        m = rows[spec]
        print(f"  {spec:<8}{m['pd']:>8.4f}  "
              f"{m['detected_runs']:>3d}/{m['total_runs']:<3d}  "
              f"{m['ait_censored']:>8.1f}", flush=True)
    print(f"  chosen budget: {chosen}", flush=True)


def main() -> int:
    p = argparse.ArgumentParser(description="Tune per-scenario Index coverage budgets.")
    p.add_argument("--scenarios", default=",".join(SCENARIO_IDS))
    p.add_argument("--budgets", default="0.5,0.35,0.25,0.2184,0.15,0.1")
    p.add_argument("--seeds", default="2000-2009")
    p.add_argument("--workers", type=int, default=1)
    p.add_argument("--margin", type=float, default=0.0,
                   help="feasibility margin below the sweep's burst rate")
    p.add_argument("--out", type=Path, default=BUDGETS_PATH)
    p.add_argument("--dry-run", action="store_true", help="print, do not write")
    args = p.parse_args()

    scenarios = parse_scenarios(args.scenarios)
    budgets = parse_budgets(args.budgets)
    seeds = parse_seeds(args.seeds)

    jobs = [(sid, "sweep", seeds) for sid in scenarios]
    jobs += [(sid, str(b), seeds) for sid in scenarios for b in budgets]

    if args.workers > 1:
        with ProcessPoolExecutor(max_workers=args.workers) as pool:
            results = list(pool.map(_eval_job, jobs))
    else:
        results = [_eval_job(job) for job in jobs]

    table: dict[str, dict] = {sid: {} for sid in scenarios}
    for scenario_id, spec, metrics in results:
        table[scenario_id][spec] = metrics

    chosen_budgets: dict[str, float] = {}
    for sid in scenarios:
        candidates = {b: table[sid][str(b)] for b in budgets}
        chosen = choose_budget(candidates, table[sid]["sweep"], margin=args.margin)
        chosen_budgets[sid] = chosen
        _print_scenario(sid, seeds, table[sid], budgets, chosen)

    payload = {
        "_comment": "Per-scenario Index coverage budgets: the highest-Pd budget "
                    "whose distinct-burst rate stays within margin of the fixed "
                    "round-robin sweep (spec decision D2).",
        "rule": rule_text(args.margin),
        "tuning_seeds": seeds,
        "budgets": chosen_budgets,
        "table": table,
    }
    if args.dry_run:
        print(f"\ndry run: not writing {args.out}", flush=True)
    else:
        _write_json_atomic(args.out, payload)
        print(f"\nwrote {args.out}", flush=True)
    return 0


def _write_json_atomic(path: Path, payload: dict) -> None:
    """Write JSON so a reader never sees a half-written file.

    The temp file lives in the same directory so ``os.replace`` is an atomic
    rename on the same filesystem; a failed write removes the temp file.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_name = tempfile.mkstemp(dir=str(path.parent), suffix=".json.tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(payload, f, indent=2)
        os.replace(tmp_name, path)
    except BaseException:
        try:
            os.unlink(tmp_name)
        except OSError:
            pass
        raise


if __name__ == "__main__":
    raise SystemExit(main())
