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
