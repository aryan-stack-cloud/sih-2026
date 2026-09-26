"""Which model serves a request, and what the served policy learns from each step.

Regression tests for three deployment bugs:

* one active model per algorithm could only serve scenarios with its band count -- DQN/PPO
  returned HTTP 500 elsewhere and the Backend silently swept round-robin instead;
* ``/internal/learn`` never called ``Agent.observe``, so the served index policy's belief and
  revisit deadlines never moved;
* a learn call carrying another simulation's decision id was applied anyway.
"""

from __future__ import annotations

import pytest

from ml.agents.bandit_agent import BanditAgent
from ml.contract import StateVector
from ml.inference.inference import InferenceEngine, NoCompatibleModelError
from ml.model_registry import ModelRegistry


def _state(num_bands: int, scanned: tuple[int, ...] = (), detected: tuple[int, ...] = ()) -> StateVector:
    """A contract StateVector as the Backend's StateBuilder leaves it after one step."""
    return StateVector.model_validate(
        {
            "bands": [
                {
                    "band_id": b,
                    "time_since_last_scan": 0 if b in scanned else 3,
                    "recent_detection_rate_ewma": 0.2 if b in detected else 0.0,
                    "consecutive_misses": 0 if b in detected else (1 if b in scanned else 0),
                    "periodicity_phase": 0.0,
                    "periodicity_confidence": 0.0,
                    "band_priority_weight": 1.0,
                    "tuning_cost_to_band": 0 if b in scanned else 3,
                }
                for b in range(num_bands)
            ],
            "receiver": {"tuned_bands": list(scanned), "dwell_remaining_ms": 0,
                         "tuning_delay_countdown_ms": 0},
        }
    )


# -- resolution --------------------------------------------------------------------------------

def test_a_model_trained_on_the_requested_scenario_beats_the_active_one(tmp_path):
    reg = ModelRegistry(tmp_path)
    active_a = reg.register(BanditAgent(16), "bandit", scenario="A", activate=True)
    trained_b = reg.register(BanditAgent(16), "bandit", scenario="B")

    assert reg.resolve("bandit", 16, "B").model_id == trained_b.model_id
    # With no scenario-specific model, the operator's active choice still wins.
    assert reg.resolve("bandit", 16, "E").model_id == active_a.model_id


def test_only_band_compatible_models_are_candidates(tmp_path):
    reg = ModelRegistry(tmp_path)
    reg.register(BanditAgent(16), "bandit", scenario="B", activate=True)
    wide = reg.register(BanditAgent(24), "bandit", scenario="D")

    assert reg.resolve("bandit", 24, "C").model_id == wide.model_id
    assert reg.resolve("bandit", 32, "E") is None


def test_records_carry_their_band_count(tmp_path):
    reg = ModelRegistry(tmp_path)
    meta = reg.register(BanditAgent(24), "bandit", scenario="D")
    assert reg.get(meta.model_id).num_bands == 24


def test_the_engine_serves_the_resolved_model_not_a_cold_learner(tmp_path):
    reg = ModelRegistry(tmp_path)
    reg.register(BanditAgent(16), "bandit", scenario="B", activate=True)
    wide = reg.register(BanditAgent(24), "bandit", scenario="D")
    engine = InferenceEngine(reg)

    _, served, _ = engine.decide("sim_0000000a", _state(24), "bandit", scenario_id="C")
    assert served == wide.model_id


def test_a_deep_policy_with_no_compatible_model_is_a_clear_error(tmp_path):
    engine = InferenceEngine(ModelRegistry(tmp_path))
    with pytest.raises(NoCompatibleModelError):
        engine.decide("sim_0000000b", _state(24), "dqn", scenario_id="D")


def test_a_pinned_model_of_the_wrong_band_count_is_rejected(tmp_path):
    reg = ModelRegistry(tmp_path)
    narrow = reg.register(BanditAgent(16), "bandit", scenario="B")
    engine = InferenceEngine(reg)
    with pytest.raises(ValueError, match="16 bands"):
        engine.decide("sim_0000000c", _state(24), "bandit", model_id=narrow.model_id)


def test_the_api_reports_a_missing_deep_model_as_409():
    from fastapi.testclient import TestClient

    from ml.api.main import app

    body = {"simulation_id": "sim_0000000d", "state": _state(24).model_dump(), "policy": "ppo",
            "scenario_id": "D"}
    with TestClient(app) as client:
        r = client.post("/internal/decide", json=body)
    assert r.status_code == 409
    assert r.json()["error"]["code"] == "NO_COMPATIBLE_MODEL"


def test_concurrent_registrations_from_separate_registries_are_all_kept(tmp_path):
    """Parallel training jobs are separate processes, each with its own ModelRegistry."""
    import threading

    errors: list[BaseException] = []

    def register_many(n: int) -> None:
        try:
            reg = ModelRegistry(tmp_path)      # own instance => own thread lock, like a process
            for _ in range(n):
                reg.register(BanditAgent(8), "bandit", scenario="A")
        except BaseException as exc:  # noqa: BLE001 - surfaced by the assertion below
            errors.append(exc)

    workers = [threading.Thread(target=register_many, args=(5,)) for _ in range(6)]
    for w in workers:
        w.start()
    for w in workers:
        w.join()

    assert errors == []
    assert len(ModelRegistry(tmp_path).list(algorithm="bandit")) == 30


# -- learn -> observe ----------------------------------------------------------------------------

@pytest.mark.parametrize("explicit", [True, False])
def test_learn_feeds_the_step_outcome_to_the_index_belief(tmp_path, explicit):
    engine = InferenceEngine(ModelRegistry(tmp_path))
    sim = "sim_0000000e"
    action, _, decision = engine.decide(sim, _state(16), "index")
    agent = engine._sessions[(sim, "index")][0]
    assert agent._steps_observed == 0

    scanned, detected = (action.next_band, (action.next_band + 1) % 16), (action.next_band,)
    extra = {"scanned_bands": list(scanned), "detected_bands": list(detected)} if explicit else {}
    assert engine.learn(sim, decision, _state(16), action, 1.0,
                        next_state=_state(16, scanned, detected), **extra)

    assert agent._steps_observed == 1
    assert agent.revisit_counts[list(scanned)].tolist() == [1, 1]
    assert agent.time_since_last_scan[list(scanned)].tolist() == [0, 0]
    assert agent.time_since_last_scan.sum() == 16 - 2


def test_a_decision_id_from_another_simulation_is_not_learned(tmp_path):
    engine = InferenceEngine(ModelRegistry(tmp_path))
    action, _, decision = engine.decide("sim_000000f1", _state(16), "bandit")
    engine.decide("sim_000000f2", _state(16), "bandit")

    assert engine.learn("sim_000000f2", decision, _state(16), action, 5.0) is False
    # The rightful owner can still learn from it.
    assert engine.learn("sim_000000f1", decision, _state(16), action, 5.0) is True


def test_a_session_reports_the_model_actually_serving_it(tmp_path):
    reg = ModelRegistry(tmp_path)
    first = reg.register(BanditAgent(16), "bandit", scenario="A")
    second = reg.register(BanditAgent(16), "bandit", scenario="B")
    engine = InferenceEngine(reg)
    sim = "sim_000000a1"

    _, served, _ = engine.decide(sim, _state(16), "bandit", model_id=first.model_id)
    assert served == first.model_id
    # A different pin under the same simulation id rebuilds the session instead of reporting the
    # new id for decisions still made by the old agent.
    _, served, _ = engine.decide(sim, _state(16), "bandit", model_id=second.model_id)
    assert served == second.model_id
    assert engine._sessions[(sim, "bandit")][1] == second.model_id


def test_a_pinned_model_of_another_algorithm_is_rejected(tmp_path):
    reg = ModelRegistry(tmp_path)
    bandit = reg.register(BanditAgent(16), "bandit", scenario="B")
    engine = InferenceEngine(reg)
    with pytest.raises(ValueError, match="bandit model"):
        engine.decide("sim_000000a2", _state(16), "dqn", model_id=bandit.model_id)


def test_a_retried_learn_is_acknowledged_but_applied_once(tmp_path):
    engine = InferenceEngine(ModelRegistry(tmp_path))
    sim = "sim_000000a3"
    action, _, decision = engine.decide(sim, _state(16), "index", scenario_id="B")
    agent = engine._sessions[(sim, "index")][0]
    scanned = (action.next_band, (action.next_band + 1) % 16)
    for _ in range(2):   # the second is an HTTP retry of the first
        assert engine.learn(sim, decision, _state(16), action, 1.0,
                            next_state=_state(16, scanned), scanned_bands=list(scanned),
                            detected_bands=[])
    assert agent._steps_observed == 1


def test_a_cold_index_is_built_for_the_scenario_receiver(tmp_path):
    engine = InferenceEngine(ModelRegistry(tmp_path))
    engine.decide("sim_000000a4", _state(24), "index", scenario_id="C")
    agent = engine._sessions[("sim_000000a4", "index")][0]
    assert agent.bandwidth_k == 2          # every scenario's receiver hears K=2 bands at once


def test_online_capable_policies_still_serve_without_a_registered_model(tmp_path):
    engine = InferenceEngine(ModelRegistry(tmp_path))
    for policy in ("index", "ctmc", "bandit", "q_learning"):
        action, served, _ = engine.decide(f"sim_cold_{policy}", _state(32), policy)
        assert served == f"online_{policy}"
        assert 0 <= action.next_band < 32
