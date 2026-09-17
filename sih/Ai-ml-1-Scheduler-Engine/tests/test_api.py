"""Contract tests against API_CONTRACT.md Section 4 (Ai-ml-1 Levels 1, 4, 5, 6).

The fixture in tests/fixtures/state_vector.json was captured from a real EWEnvironment run, so
these tests exercise the shape the Backend will actually receive rather than a hand-invented one.
"""

from __future__ import annotations

import json
import time
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from ml.api.main import app, engine, registry

FIXTURE = Path(__file__).parent / "fixtures" / "state_vector.json"


@pytest.fixture(scope="module")
def client() -> TestClient:
    with TestClient(app) as c:
        yield c


@pytest.fixture
def decide_body() -> dict:
    return json.loads(FIXTURE.read_text(encoding="utf-8"))


# -- Level 1: service scaffold ----------------------------------------------------------------

def test_health_returns_ok(client):
    r = client.get("/internal/health")
    assert r.status_code == 200
    body = r.json()
    assert body["success"] is True
    assert body["data"] == {"status": "ok"}
    assert body["requestId"].startswith("req_")


# -- Level 4: decide / learn ------------------------------------------------------------------

def test_decide_returns_a_contract_shaped_action(client, decide_body):
    r = client.post("/internal/decide", json=decide_body)
    assert r.status_code == 200
    data = r.json()["data"]
    assert set(data) == {"action", "model_id", "decision_id"}
    assert 0 <= data["action"]["next_band"] < len(decide_body["state"]["bands"])
    assert data["decision_id"].startswith("dec_")


def test_decide_meets_the_nfr_002_latency_budget(client, decide_body):
    """< 50 ms per decision for bandit/Q-Learning (NFR-002)."""
    client.post("/internal/decide", json=decide_body)  # warm the session
    timings = []
    for _ in range(20):
        started = time.perf_counter()
        r = client.post("/internal/decide", json=decide_body)
        timings.append((time.perf_counter() - started) * 1000.0)
        assert r.status_code == 200
    p95 = sorted(timings)[int(0.95 * len(timings)) - 1]
    assert p95 < 50.0, f"p95 decision latency {p95:.1f} ms exceeds the 50 ms budget"


@pytest.mark.parametrize("policy", ["bandit", "q_learning"])
def test_every_tabular_policy_is_selectable_through_the_same_endpoint(client, decide_body, policy):
    body = {**decide_body, "policy": policy, "simulation_id": f"sim_{policy[:8]}"}
    r = client.post("/internal/decide", json=body)
    assert r.status_code == 200
    assert "next_band" in r.json()["data"]["action"]


def test_learn_acknowledges_a_backend_computed_reward(client, decide_body):
    decided = client.post("/internal/decide", json=decide_body).json()["data"]
    r = client.post(
        "/internal/learn",
        json={
            "simulation_id": decide_body["simulation_id"],
            "decision_id": decided["decision_id"],
            "state": decide_body["state"],
            "action": decided["action"],
            "reward": 12.0,
        },
    )
    assert r.status_code == 200
    assert r.json()["data"]["acknowledged"] is True


def test_learn_actually_moves_the_policy(client, decide_body):
    """A bandit that ignored /internal/learn would still return 200; check the estimates move."""
    sim = "sim_deadbeef"
    body = {**decide_body, "simulation_id": sim}
    decided = client.post("/internal/decide", json=body).json()["data"]
    before = engine.describe_session(sim, "bandit")["band_values"]

    for _ in range(30):
        client.post(
            "/internal/learn",
            json={
                "simulation_id": sim,
                "decision_id": decided["decision_id"],
                "state": body["state"],
                "action": decided["action"],
                "reward": 25.0,
            },
        )
        decided = client.post("/internal/decide", json=body).json()["data"]

    after = engine.describe_session(sim, "bandit")["band_values"]
    assert before != after


def test_learn_for_an_unknown_decision_is_not_acknowledged(client, decide_body):
    r = client.post(
        "/internal/learn",
        json={
            "simulation_id": "sim_00000000",
            "decision_id": "dec_ffffffff",
            "state": decide_body["state"],
            "action": {"next_band": 0},
            "reward": 1.0,
        },
    )
    assert r.status_code == 200
    assert r.json()["data"]["acknowledged"] is False


def test_reset_clears_a_simulation_session(client, decide_body):
    body = {**decide_body, "simulation_id": "sim_11112222"}
    client.post("/internal/decide", json=body)
    r = client.post("/internal/reset", json={"simulation_id": "sim_11112222"})
    assert r.json()["data"]["cleared_sessions"] >= 1
    assert engine.describe_session("sim_11112222", "bandit") is None


def test_reset_without_a_simulation_id_is_a_validation_error(client):
    r = client.post("/internal/reset", json={})
    assert r.status_code == 422
    assert r.json()["error"]["code"] == "VALIDATION_ERROR"


# -- Section 1: envelope + error mapping ------------------------------------------------------

def test_validation_errors_use_the_documented_envelope(client, decide_body):
    bad = {**decide_body, "policy": "random_forest"}
    r = client.post("/internal/decide", json=bad)
    assert r.status_code == 422
    body = r.json()
    assert body["success"] is False
    assert body["error"]["code"] == "VALIDATION_ERROR"
    assert body["error"]["details"]


def test_a_band_outside_the_contract_bounds_is_rejected(client, decide_body):
    broken = json.loads(json.dumps(decide_body))
    broken["state"]["bands"][0]["recent_detection_rate_ewma"] = 5.0  # contract says [0, 1]
    r = client.post("/internal/decide", json=broken)
    assert r.status_code == 422


def test_unknown_state_fields_are_rejected_rather_than_silently_dropped(client, decide_body):
    """extra='forbid' is what catches Backend/Ai-ml-1 contract drift at the boundary."""
    broken = json.loads(json.dumps(decide_body))
    broken["state"]["bands"][0]["signal_strength_dbm"] = -70
    r = client.post("/internal/decide", json=broken)
    assert r.status_code == 422


def test_missing_model_returns_resource_not_found(client):
    r = client.get("/internal/models/model_bandit_deadbeef")
    assert r.status_code == 404
    assert r.json()["error"]["code"] == "RESOURCE_NOT_FOUND"


def test_missing_job_returns_resource_not_found(client):
    r = client.get("/internal/train/job_00000000/status")
    assert r.status_code == 404
    assert r.json()["error"]["code"] == "RESOURCE_NOT_FOUND"


# -- Level 5/6: training, registry, evaluation -------------------------------------------------

@pytest.mark.slow
def test_train_registers_a_model_and_reports_progress(client, tmp_path):
    r = client.post(
        "/internal/train",
        json={"algorithm": "bandit", "scenario": "A", "episode_count": 2,
              "hyperparams": {}, "seed_range": None},
    )
    assert r.status_code == 200
    job_id = r.json()["data"]["job_id"]

    deadline = time.time() + 900
    status = None
    while time.time() < deadline:
        status = client.get(f"/internal/train/{job_id}/status").json()["data"]
        assert status["status"] in ("running", "done", "failed")
        assert 0.0 <= status["progress"] <= 1.0
        if status["status"] != "running":
            break
        time.sleep(0.5)

    assert status["status"] == "done", status
    model_id = status["detail"]["model_id"]
    assert model_id.startswith("model_bandit_")

    detail = client.get(f"/internal/models/{model_id}").json()["data"]
    assert detail["algorithm"] == "bandit"
    assert detail["metrics"]["pd"] >= 0.0

    activated = client.post(f"/internal/models/{model_id}/activate").json()["data"]
    assert activated["active"] is True
    assert [m["model_id"] for m in
            client.get("/internal/models", params={"algorithm": "bandit", "active": True})
            .json()["data"]] == [model_id]


def test_activation_deactivates_only_the_same_algorithm(tmp_path):
    """/internal/models/{id}/activate: 'deactivates previous active model of same algorithm'."""
    from ml.agents.bandit_agent import BanditAgent
    from ml.agents.q_learning_agent import QLearningAgent
    from ml.model_registry import ModelRegistry

    reg = ModelRegistry(tmp_path)
    b1 = reg.register(BanditAgent(8), "bandit", activate=True)
    q1 = reg.register(QLearningAgent(8), "q_learning", activate=True)
    b2 = reg.register(BanditAgent(8), "bandit", activate=True)

    assert reg.get(b1.model_id).active is False
    assert reg.get(b2.model_id).active is True
    assert reg.get(q1.model_id).active is True  # untouched by the bandit promotion
    assert b2.version == 2


def test_registry_round_trips_a_trained_agent(tmp_path):
    from ml.agents.bandit_agent import BanditAgent
    from ml.model_registry import ModelRegistry

    reg = ModelRegistry(tmp_path)
    agent = BanditAgent(8, learning_rate=0.11)
    meta = reg.register(agent, "bandit", scenario="A", metrics={"pd": 0.42})
    restored = reg.load_agent(meta.model_id)
    assert restored.learning_rate == pytest.approx(0.11)
    assert reg.get(meta.model_id).metrics["pd"] == 0.42
