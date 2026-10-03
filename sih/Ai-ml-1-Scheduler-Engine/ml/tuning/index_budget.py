"""Per-scenario Index coverage budgets, tuned once and read back at build time.

``scripts/tune_index_budget.py`` writes ``ml/configs/index_budgets.json``; the
``algo == "index"`` branch of ``scripts/train_all.py`` reads it through here so
a registered Index model carries the budget its deadline was derived from.
Scenarios with no entry keep the ``COVERAGE_BUDGET`` module default.
"""

from __future__ import annotations

import json
from pathlib import Path

from ml.utils.config import SCENARIO_IDS

BUDGETS_PATH: Path = Path(__file__).resolve().parents[1] / "configs" / "index_budgets.json"


def load_budgets(path: str | Path | None = None) -> dict[str, float]:
    """Read the ``{"budgets": {scenario: budget}}`` mapping, or ``{}`` when missing."""
    resolved = Path(path) if path is not None else BUDGETS_PATH
    if not resolved.exists():
        return {}
    budgets = json.loads(resolved.read_text(encoding="utf-8")).get("budgets", {})
    for scenario_id, budget in budgets.items():
        if scenario_id not in SCENARIO_IDS:
            raise ValueError(f"unknown scenario in budgets file: {scenario_id!r}")
        if not isinstance(budget, (int, float)) or not 0.0 < float(budget) <= 1.0:
            raise ValueError(f"budget for scenario {scenario_id!r} must lie in (0, 1], got {budget!r}")
    return {scenario_id: float(budget) for scenario_id, budget in budgets.items()}


def budget_for(scenario_id: str, budgets: dict[str, float]) -> float | None:
    """The scenario's tuned budget, or ``None`` when it has no entry."""
    return budgets.get(scenario_id)


def choose_budget(
    candidates: dict[float, dict[str, float]],
    sweep: dict[str, float],
    margin: float = 0.0,
    default: float = 0.5,
) -> float:
    """Pick the Index coverage budget that keeps sweep coverage at the best Pd.

    A budget is feasible when its ``run_intercept_rate`` is at least the fixed
    sweep's minus ``margin`` (default 0: never below the sweep); among the
    feasible ones the highest ``pd`` wins, with ``pd`` values within 0.001
    counted as tied and the larger budget winning. With nothing feasible the
    sweep's own budget (``default``) is kept.
    """
    floor = sweep["run_intercept_rate"] - margin
    feasible = {b: m for b, m in candidates.items() if m["run_intercept_rate"] >= floor}
    if not feasible:
        return default
    best_pd = max(m["pd"] for m in feasible.values())
    tied = [b for b, m in feasible.items() if best_pd - m["pd"] <= 0.001]
    return max(tied)
