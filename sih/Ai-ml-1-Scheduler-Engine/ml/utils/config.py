"""Loaders for scenario configs (ml/experiments/) and hyperparameters (ml/configs/)."""

from __future__ import annotations

from pathlib import Path

import yaml

ML_ROOT = Path(__file__).resolve().parent.parent
SCENARIO_DIR = ML_ROOT / "experiments"
CONFIG_DIR = ML_ROOT / "configs"

SCENARIO_IDS = ("A", "B", "C", "D", "E", "F", "G")


def load_scenario(scenario_id: str) -> dict:
    """Load one of the seven PRD Section 13 scenarios by its id."""
    sid = str(scenario_id).strip().upper()
    if sid not in SCENARIO_IDS:
        raise ValueError(f"unknown scenario {scenario_id!r}; expected one of {SCENARIO_IDS}")
    path = SCENARIO_DIR / f"scenario_{sid.lower()}.yaml"
    with path.open(encoding="utf-8") as f:
        return yaml.safe_load(f)


def all_scenarios() -> dict[str, dict]:
    return {sid: load_scenario(sid) for sid in SCENARIO_IDS}


def load_hyperparams(algorithm: str) -> dict:
    """Load default hyperparameters for an algorithm (ml/configs/<algorithm>.yaml)."""
    path = CONFIG_DIR / f"{algorithm}.yaml"
    if not path.exists():
        return {}
    with path.open(encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def episode_seeds(scenario: dict, episodes: int | None = None) -> list[int]:
    """The seed for each episode of a scenario run.

    Every policy evaluated on a scenario must use this same list -- that is what makes the
    Section 13 baseline-vs-ML comparison a controlled experiment rather than two separate runs.
    """
    start, end = scenario.get("seed_range", [scenario.get("seed", 42), scenario.get("seed", 42) + 20])
    n = episodes if episodes is not None else scenario.get("episodes", 20)
    return [int(start) + i for i in range(int(n))] if end > start else [int(start)] * int(n)
