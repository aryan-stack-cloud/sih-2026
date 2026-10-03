"""Selection rule for the per-scenario Index coverage budget (spec decision D2).

``choose_budget`` keeps every budget whose run-intercept rate stays within
``margin`` of the fixed sweep, then takes the highest Pd, breaking near-ties
(within 0.001) toward the larger budget. The CLI smoke test pins the tuning
script end to end on a single seed.
"""

from __future__ import annotations

import importlib.util
import json
import re
import subprocess
import sys
from pathlib import Path

from ml.tuning.index_budget import choose_budget, load_budgets


def test_highest_feasible_pd_wins():
    sweep = {"pd": 0.50, "run_intercept_rate": 0.80}
    candidates = {
        0.5: {"pd": 0.60, "run_intercept_rate": 0.80},
        0.25: {"pd": 0.70, "run_intercept_rate": 0.795},
    }
    assert choose_budget(candidates, sweep, margin=0.01) == 0.25


def test_infeasible_budget_with_highest_pd_is_skipped():
    sweep = {"pd": 0.50, "run_intercept_rate": 0.80}
    candidates = {
        0.5: {"pd": 0.90, "run_intercept_rate": 0.50},
        0.25: {"pd": 0.60, "run_intercept_rate": 0.80},
    }
    assert choose_budget(candidates, sweep) == 0.25


def test_ties_within_0_001_pick_the_larger_budget():
    sweep = {"pd": 0.50, "run_intercept_rate": 0.80}
    candidates = {
        0.5: {"pd": 0.7005, "run_intercept_rate": 0.80},
        0.25: {"pd": 0.70, "run_intercept_rate": 0.80},
    }
    assert choose_budget(candidates, sweep) == 0.5


def test_a_gap_just_over_0_001_is_not_a_tie():
    sweep = {"pd": 0.50, "run_intercept_rate": 0.80}
    candidates = {
        0.5: {"pd": 0.702, "run_intercept_rate": 0.80},
        0.25: {"pd": 0.70, "run_intercept_rate": 0.80},
    }
    assert choose_budget(candidates, sweep) == 0.5
    flipped = {
        0.5: {"pd": 0.70, "run_intercept_rate": 0.80},
        0.25: {"pd": 0.702, "run_intercept_rate": 0.80},
    }
    assert choose_budget(flipped, sweep) == 0.25


def test_nothing_feasible_returns_the_default():
    sweep = {"pd": 0.50, "run_intercept_rate": 0.80}
    candidates = {
        0.5: {"pd": 0.90, "run_intercept_rate": 0.50},
        0.25: {"pd": 0.80, "run_intercept_rate": 0.40},
    }
    assert choose_budget(candidates, sweep) == 0.5
    assert choose_budget(candidates, sweep, default=0.35) == 0.35


def test_the_default_margin_is_strict():
    # The default margin is 0: a budget a hair below the sweep is infeasible.
    sweep = {"pd": 0.50, "run_intercept_rate": 0.80}
    candidates = {
        0.5: {"pd": 0.90, "run_intercept_rate": 0.7999},
        0.25: {"pd": 0.60, "run_intercept_rate": 0.80},
    }
    assert choose_budget(candidates, sweep) == 0.25


def test_a_margin_of_0_01_admits_what_0_rejects():
    sweep = {"pd": 0.50, "run_intercept_rate": 0.80}
    candidates = {
        0.5: {"pd": 0.90, "run_intercept_rate": 0.795},
        0.25: {"pd": 0.60, "run_intercept_rate": 0.80},
    }
    assert choose_budget(candidates, sweep) == 0.25
    assert choose_budget(candidates, sweep, margin=0.01) == 0.5


def test_sweep_coverage_equal_to_a_candidate_is_feasible():
    sweep = {"pd": 0.50, "run_intercept_rate": 0.80}
    candidates = {
        0.25: {"pd": 0.60, "run_intercept_rate": 0.80},
    }
    assert choose_budget(candidates, sweep) == 0.25


def test_a_decimal_exact_gap_of_0_001_is_a_tie():
    # In binary floating point 0.701 - 0.700 is 0.001000000000000011, just
    # over 0.001. A decimal-exact 0.001 gap must still count as tied.
    sweep = {"pd": 0.50, "run_intercept_rate": 0.80}
    candidates = {
        0.5: {"pd": 0.700, "run_intercept_rate": 0.80},
        0.25: {"pd": 0.701, "run_intercept_rate": 0.80},
    }
    assert choose_budget(candidates, sweep) == 0.5


def test_a_gap_of_0_0011_is_not_a_tie():
    sweep = {"pd": 0.50, "run_intercept_rate": 0.80}
    candidates = {
        0.5: {"pd": 0.700, "run_intercept_rate": 0.80},
        0.25: {"pd": 0.7011, "run_intercept_rate": 0.80},
    }
    assert choose_budget(candidates, sweep) == 0.25


def _load_tune_script():
    path = Path(__file__).resolve().parent.parent / "scripts" / "tune_index_budget.py"
    spec = importlib.util.spec_from_file_location("tune_index_budget_under_test", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_eval_jobs_run_through_the_serving_provider(monkeypatch):
    import ml.training.trainer as trainer_mod

    calls: list[int] = []
    real_serving_env = trainer_mod._serving_env

    def recording(cfg, seed):
        calls.append(seed)
        return real_serving_env(cfg, seed)

    monkeypatch.setattr(trainer_mod, "_serving_env", recording)
    tune = _load_tune_script()
    scenario_id, spec, metrics = tune._eval_job(("B", "sweep", [2000]))
    assert scenario_id == "B"
    assert metrics["pd"] > 0
    assert calls == [2000]


def test_cli_dry_run_names_the_chosen_budget():
    engine = Path(__file__).resolve().parent.parent
    proc = subprocess.run(
        [sys.executable, "scripts/tune_index_budget.py",
         "--scenarios", "B", "--budgets", "0.5,0.25",
         "--seeds", "2000-2000", "--dry-run"],
        cwd=str(engine), capture_output=True, text=True, timeout=180,
    )
    assert proc.returncode == 0, proc.stderr[-2000:]
    assert re.search(r"chosen budget:\s*(0\.5|0\.25)", proc.stdout)


def test_cli_margin_is_plumbed_to_the_written_rule(tmp_path):
    engine = Path(__file__).resolve().parent.parent
    out = tmp_path / "budgets.json"
    proc = subprocess.run(
        [sys.executable, "scripts/tune_index_budget.py",
         "--scenarios", "B", "--budgets", "0.5,0.25",
         "--seeds", "2000-2000", "--margin", "0.01", "--out", str(out)],
        cwd=str(engine), capture_output=True, text=True, timeout=180,
    )
    assert proc.returncode == 0, proc.stderr[-2000:]
    written = json.loads(out.read_text(encoding="utf-8"))
    assert "minus 0.01" in written["rule"]
    assert load_budgets(out) == written["budgets"]
