"""Index coverage-budget pass-through: the tuned budget must reach the agent.

``ml/configs/index_tuned_B.json`` holds a tuned ``coverage_budget``, but the
``algo == "index"`` branch of ``scripts/train_all.py`` used to build the agent
from weights and ``rho_min`` only, so every registered Index model silently ran
on the 0.5 module default. These tests pin the override path end to end.
"""

from __future__ import annotations

import importlib.util
import json
import math
from pathlib import Path

import pytest

from ml.agents.index_agent import COVERAGE_BUDGET, IndexAgent
from ml.tuning.index_budget import BUDGETS_PATH, budget_for, load_budgets
from ml.utils.config import load_scenario


def _cycle_and_slot(scenario_id: str = "B") -> tuple[float, float]:
    """The revisit cycle and slot the deadline formula divides, per scenario."""
    scenario = load_scenario(scenario_id)
    receiver = dict(scenario.get("receiver") or {})
    num_bands = int(scenario["bands"])
    bandwidth_k = int(receiver.get("bandwidth_k", 1))
    slot_s = float(receiver.get("step_ms", 10.0)) / 1000.0
    retune_s = float(receiver.get("tuning_delay_ms", 0.0)) / 1000.0
    cycle = math.ceil(num_bands / bandwidth_k) * (slot_s + retune_s)
    return cycle, slot_s


def test_the_default_budget_is_the_module_constant():
    a = IndexAgent.from_scenario(load_scenario("B"))
    assert a.describe()["coverage_budget"] == 0.5
    assert a.describe()["coverage_budget"] == COVERAGE_BUDGET


def test_the_default_deadline_matches_cycle_over_budget():
    cycle, slot_s = _cycle_and_slot("B")
    a = IndexAgent.from_scenario(load_scenario("B"))
    expected_slots = int(math.ceil((cycle / COVERAGE_BUDGET) / slot_s))
    assert int(a.deadline_slots.max()) == expected_slots


def test_a_smaller_budget_stretches_the_deadline():
    cycle, slot_s = _cycle_and_slot("B")
    default = IndexAgent.from_scenario(load_scenario("B"))
    narrow = IndexAgent.from_scenario(load_scenario("B"), coverage_budget=0.25)
    # The formula's own ratio: (cycle / 0.25) / (cycle / 0.5) is exactly 2.
    expected_ratio = (cycle / 0.25) / (cycle / COVERAGE_BUDGET)
    actual_ratio = float(narrow.deadlines.deadlines_s[0]) / float(default.deadlines.deadlines_s[0])
    assert actual_ratio == pytest.approx(expected_ratio)
    assert narrow.describe()["coverage_budget"] == 0.25
    # Slots round up, so the ratio holds only within one slot of doubling.
    assert abs(int(narrow.deadline_slots.max()) - 2 * int(default.deadline_slots.max())) <= 1


def test_an_explicit_deadline_beats_the_budget():
    a = IndexAgent.from_scenario(load_scenario("B"), deadline_s=0.5, coverage_budget=0.25)
    assert a.deadline_slots.max() == 50
    assert a.describe()["coverage_budget"] is None


@pytest.mark.parametrize("bad", [0, -0.1, 1.5])
def test_out_of_range_budgets_raise(bad):
    with pytest.raises(ValueError, match=r"coverage_budget must lie in \(0, 1\]"):
        IndexAgent.from_scenario(load_scenario("B"), coverage_budget=bad)


def test_load_budgets_returns_empty_when_the_file_is_missing(tmp_path):
    assert load_budgets(tmp_path / "no-such-file.json") == {}


def test_load_budgets_parses_a_file(tmp_path):
    path = tmp_path / "index_budgets.json"
    path.write_text(json.dumps({"budgets": {"A": 0.35, "B": 0.25}}), encoding="utf-8")
    assert load_budgets(path) == {"A": 0.35, "B": 0.25}


def test_load_budgets_rejects_a_value_above_one(tmp_path):
    path = tmp_path / "index_budgets.json"
    path.write_text(json.dumps({"budgets": {"A": 1.2}}), encoding="utf-8")
    with pytest.raises(ValueError):
        load_budgets(path)


def test_load_budgets_rejects_an_unknown_scenario(tmp_path):
    path = tmp_path / "index_budgets.json"
    path.write_text(json.dumps({"budgets": {"Z": 0.3}}), encoding="utf-8")
    with pytest.raises(ValueError):
        load_budgets(path)


def test_budget_for_returns_none_when_the_scenario_is_unlisted():
    assert budget_for("B", {"A": 0.35}) is None
    assert budget_for("A", {"A": 0.35}) == pytest.approx(0.35)


def test_budgets_path_points_at_the_configs_file():
    assert BUDGETS_PATH == Path(__file__).resolve().parent.parent / "ml" / "configs" / "index_budgets.json"


def _load_train_all():
    path = Path(__file__).resolve().parent.parent / "scripts" / "train_all.py"
    spec = importlib.util.spec_from_file_location("train_all_under_test", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_train_one_records_the_budget_in_hyperparams(monkeypatch):
    import ml.tuning.index_budget as index_budget_mod

    monkeypatch.setattr(index_budget_mod, "load_budgets", lambda path=None: {"B": 0.25})
    train_all = _load_train_all()
    if hasattr(train_all, "load_budgets"):
        monkeypatch.setattr(train_all, "load_budgets", lambda path=None: {"B": 0.25})
    result = train_all.train_one("index", "B", timesteps=0, eval_episodes=1)
    assert result["model_id"]
    from ml.model_registry import ModelRegistry

    meta = ModelRegistry().get(result["model_id"])
    assert meta.hyperparams["coverage_budget"] == 0.25
