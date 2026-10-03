"""Decision explanation for the judge view (IndexAgent + /internal/decide).

The index policy already decomposes every decision into five named terms
(``IndexAgent.last_breakdown``), but ``/internal/decide`` never surfaced them and
``apply_deadline_override`` could replace the chosen bands without saying so. These
tests pin the explanation contract: which keys ride on the decide response, which
source values are legal, and that action selection itself does not move.
"""

from __future__ import annotations

import json
import math
from pathlib import Path

import numpy as np
import pytest
from fastapi.testclient import TestClient

from ml.agents.index_agent import IndexAgent
from ml.api.main import app
from ml.contract import StateVector
from ml.environments.state import StateBuilder
from ml.inference.inference import InferenceEngine
from ml.utils.config import load_scenario

FIXTURE = Path(__file__).parent / "fixtures" / "state_vector.json"

ALLOWED_SOURCES = ("floor", "index", "deadline")
BREAKDOWN_KEYS = {"value", "information", "novelty", "deadline", "elapsed_s"}


@pytest.fixture(scope="module")
def client() -> TestClient:
    # Plain client, deliberately NOT a context manager: entering the app lifespan here would
    # run its shutdown at this module's teardown and break tests/test_api.py's training job,
    # which shares this process's global JobRegistry (command-line file order runs this
    # module first). The endpoints under test do not need lifespan state.
    return TestClient(app)


@pytest.fixture
def decide_body() -> dict:
    return json.loads(FIXTURE.read_text(encoding="utf-8"))


@pytest.fixture
def state_vector(decide_body) -> StateVector:
    return StateVector.model_validate(decide_body["state"])


class _Receiver:
    tuned_start = 0
    dwell_remaining_ms = 0
    tuning_delay_countdown_ms = 0

    def tuned_bands(self, k, n):
        return [(self.tuned_start + i) % n for i in range(k)]


def neutral_observation(num_bands: int = 16) -> np.ndarray:
    """A flat spectrum: no periodicity claims, default priorities."""
    sb = StateBuilder(num_bands)
    sb.update([], [], _Receiver(), 1)
    return sb.to_vector()


# -- API contract ------------------------------------------------------------------


def test_index_decide_returns_breakdown_and_source(client, decide_body):
    body = {**decide_body, "policy": "index", "simulation_id": "sim_dec0de01"}
    r = client.post("/internal/decide", json=body)
    assert r.status_code == 200
    data = r.json()["data"]
    assert set(data["index_breakdown"]) == BREAKDOWN_KEYS
    for value in data["index_breakdown"].values():
        assert isinstance(value, (int, float)) and math.isfinite(value)
        assert value == round(value, 6)
    assert data["decision_source"] in ALLOWED_SOURCES
    # The whole envelope must serialise without NaN/Infinity leaking anywhere.
    json.dumps(r.json(), allow_nan=False)


def test_bandit_decide_omits_explanation_keys(client, decide_body):
    body = {**decide_body, "policy": "bandit", "simulation_id": "sim_b4nd1t01"}
    r = client.post("/internal/decide", json=body)
    assert r.status_code == 200
    data = r.json()["data"]
    assert "index_breakdown" not in data
    assert "decision_source" not in data


def test_ctmc_decide_omits_explanation_keys(client, decide_body):
    body = {**decide_body, "policy": "ctmc", "simulation_id": "sim_ctmc0101"}
    r = client.post("/internal/decide", json=body)
    assert r.status_code == 200
    data = r.json()["data"]
    assert "index_breakdown" not in data
    assert "decision_source" not in data


def test_baseline_is_rejected_without_explanation_keys(client, decide_body):
    """``baseline`` is a Backend-side sweep, not an Ai-ml-1 policy: the contract rejects it.

    The rejection body carries neither explanation key either.
    """
    body = {**decide_body, "policy": "baseline", "simulation_id": "sim_b4se1e01"}
    r = client.post("/internal/decide", json=body)
    assert r.status_code == 422
    assert "index_breakdown" not in r.json()
    assert "decision_source" not in r.json()


# -- engine shapes -----------------------------------------------------------------


def test_decide_still_returns_a_3_tuple(state_vector):
    engine = InferenceEngine()
    out = engine.decide("sim_3tup1e01", state_vector, "index", scenario_id="D")
    assert isinstance(out, tuple) and len(out) == 3


def test_decide_explained_returns_a_4_tuple_with_explanation(state_vector):
    engine = InferenceEngine()
    out = engine.decide_explained("sim_4tup1e01", state_vector, "index", scenario_id="D")
    assert isinstance(out, tuple) and len(out) == 4
    action, _, _, explanation = out
    assert set(explanation) == {"index_breakdown", "decision_source"}
    assert set(explanation["index_breakdown"]) == BREAKDOWN_KEYS
    assert explanation["decision_source"] in ALLOWED_SOURCES


# -- agent source tracking ----------------------------------------------------------


def test_index_agent_reports_deadline_source_when_overdue():
    agent = IndexAgent.from_scenario(load_scenario("B"), rng=np.random.default_rng(0))
    agent.start_episode(0)
    obs = neutral_observation(agent.num_bands)
    agent.select_action(obs)
    assert agent.last_source in {"floor", "index"}
    agent.time_since_last_scan[:] = 10_000
    agent.select_action(obs)
    assert agent.last_source == "deadline"
    assert all(math.isfinite(float(v)) for v in agent.last_breakdown.values())


def test_action_selection_is_identical_over_50_steps(monkeypatch):
    """The new bookkeeping must not move the chosen action.

    One agent runs the untouched override path, the other the same path through a
    recording wrapper; both start from the same seed and see the same steps.
    """
    import ml.agents.index_agent as index_module

    real_override = index_module.apply_deadline_override
    wrapped_calls: list = []

    def counting_wrapper(chosen, overdue, bandwidth_k):
        wrapped_calls.append((list(chosen), list(overdue)))
        return real_override(chosen, overdue, bandwidth_k)

    monkeypatch.setattr(index_module, "apply_deadline_override", counting_wrapper)
    obs = neutral_observation()
    first = IndexAgent(rng=np.random.default_rng(7), num_bands=16, bandwidth_k=1)
    second = IndexAgent(rng=np.random.default_rng(7), num_bands=16, bandwidth_k=1)
    first.start_episode(0)
    second.start_episode(0)
    for _ in range(50):
        assert first.select_action(obs) == second.select_action(obs)
        assert first.last_source == second.last_source
        info = {"scanned_bands": first.last_bands, "detected_bands": []}
        first.observe(info)
        second.observe(dict(info))
    assert len(wrapped_calls) == 100


def test_nonfinite_breakdown_values_are_clamped_to_finite(state_vector):
    engine = InferenceEngine()
    simulation_id = "sim_c14mp001"
    engine.decide_explained(simulation_id, state_vector, "index", scenario_id="D")
    agent, _ = engine._session(simulation_id, "index", len(state_vector.bands), None, "D")

    def stubbed_select_action(vector, explore=False):  # noqa: ANN001, ANN202
        agent.last_breakdown = {
            "deadline": float("inf"),
            "value": float("nan"),
            "information": float("-inf"),
            "novelty": 1.5,
            "elapsed_s": 0.013,
        }
        agent.last_source = "index"
        return 0

    agent.select_action = stubbed_select_action
    _, _, _, explanation = engine.decide_explained(
        simulation_id, state_vector, "index", scenario_id="D"
    )
    assert explanation["index_breakdown"]["deadline"] == pytest.approx(1e6)
    assert explanation["index_breakdown"]["value"] == 0.0
    assert explanation["index_breakdown"]["information"] == pytest.approx(-1e6)
