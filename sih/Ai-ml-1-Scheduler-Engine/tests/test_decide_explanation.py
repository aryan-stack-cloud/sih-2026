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


# -- golden action-identity loop ------------------------------------------------------
#
# The exact loop the golden values below were recorded with, on the PRE-CHANGE code
# (commit f3bd414). The recording script imports this helper, so the test loop and the
# recording loop cannot drift apart. A middle stretch forces staleness far past every
# deadline so the golden values cover the deadline-override path too.

GOLDEN_SEED = 7
GOLDEN_STEPS = 50
GOLDEN_STALE_START = 20
GOLDEN_STALE_STEPS = 10
GOLDEN_TSL = 10_000


def drive_golden_loop(agent, obs) -> list[int]:  # noqa: ANN001
    """Run the golden loop on an agent built exactly like the test builds it."""
    actions = []
    for step in range(GOLDEN_STEPS):
        if GOLDEN_STALE_START <= step < GOLDEN_STALE_START + GOLDEN_STALE_STEPS:
            agent.time_since_last_scan[:] = GOLDEN_TSL
        actions.append(int(agent.select_action(obs)))
        agent.observe({"scanned_bands": agent.last_bands, "detected_bands": []})
    return actions


# Recorded from the pre-change commit f3bd414 (scenario B, rng seed 7): the new code must
# reproduce these exactly -- the bookkeeping may observe the decision, never move it.
GOLDEN_ACTIONS_B_SEED7: tuple = (
    10, 14, 13, 0, 6, 4, 8, 15, 12, 2,
    15, 6, 5, 10, 11, 5, 1, 14, 4, 8,
    0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
    2, 4, 6, 8, 10, 12, 14, 13, 0, 1,
    2, 10, 0, 9, 4, 5, 7, 6, 12, 9,
)


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


def test_action_selection_matches_pre_change_golden_values():
    """The binding constraint: identical actions to the code BEFORE this change.

    The golden list was recorded from commit f3bd414 with this exact loop
    (``drive_golden_loop``); the new bookkeeping must reproduce it verbatim.
    """
    agent = IndexAgent.from_scenario(load_scenario("B"), rng=np.random.default_rng(GOLDEN_SEED))
    agent.start_episode(0)
    assert drive_golden_loop(agent, neutral_observation(agent.num_bands)) == list(
        GOLDEN_ACTIONS_B_SEED7
    )


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


def test_explanation_is_empty_when_the_source_is_unknown(state_vector):
    """A breakdown with no (or an unknown) source must not produce an explanation."""
    engine = InferenceEngine()
    simulation_id = "sim_nosrc001"
    engine.decide_explained(simulation_id, state_vector, "index", scenario_id="D")
    agent, _ = engine._session(simulation_id, "index", len(state_vector.bands), None, "D")

    def stubbed_select_action(vector, explore=False):  # noqa: ANN001, ANN202
        agent.last_breakdown = {
            "value": 0.5,
            "information": 0.1,
            "novelty": 0.0,
            "deadline": 0.2,
            "elapsed_s": 0.013,
        }
        del agent.last_source
        return 0

    agent.select_action = stubbed_select_action
    _, _, _, explanation = engine.decide_explained(
        simulation_id, state_vector, "index", scenario_id="D"
    )
    assert explanation == {}
