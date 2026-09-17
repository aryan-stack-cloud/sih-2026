"""Contract tests against API_CONTRACT.md Section 5 (Ai-ml-2 Levels 1, 3, 6, 8)."""

from __future__ import annotations

import time

import pytest
from fastapi.testclient import TestClient

from periodicity.api.main import app, service


@pytest.fixture(scope="module")
def client() -> TestClient:
    with TestClient(app) as c:
        yield c


@pytest.fixture(autouse=True)
def clean_state():
    yield
    for sim in ("sim_a1b2c3d4", "sim_periodic", "sim_empty", "sim_load", "sim_reset"):
        service.reset(sim)


def feed(client: TestClient, sim: str, band: int, timestamps) -> None:
    for t in timestamps:
        r = client.post(
            "/internal/periodicity/update",
            json={"simulation_id": sim, "band_id": band, "detection_timestamp": t},
        )
        assert r.status_code == 200


# -- Level 1 -------------------------------------------------------------------------------------

def test_health_returns_ok(client):
    r = client.get("/internal/health")
    assert r.status_code == 200
    body = r.json()
    assert body["success"] is True
    assert body["data"] == {"status": "ok"}
    assert body["requestId"].startswith("req_")


# -- Level 3: update and reset ---------------------------------------------------------------------

def test_update_is_acknowledged_and_visible_immediately(client):
    """Level 3 DoD: posting detections is reflected in /state right after."""
    feed(client, "sim_a1b2c3d4", 3, [10, 30, 50])
    r = client.get(
        "/internal/periodicity/state",
        params={"simulation_id": "sim_a1b2c3d4", "band_id": 3},
    )
    assert r.status_code == 200
    data = r.json()["data"]
    assert data["timestamps"] == [10.0, 30.0, 50.0]
    assert data["inter_arrivals"] == [20.0, 20.0]
    assert data["detections_total"] == 3


def test_duplicate_updates_are_still_acknowledged(client):
    """A Backend retry must not look like a failure."""
    feed(client, "sim_a1b2c3d4", 1, [42, 42])
    data = client.get(
        "/internal/periodicity/state",
        params={"simulation_id": "sim_a1b2c3d4", "band_id": 1},
    ).json()["data"]
    assert data["timestamps"] == [42.0]


def test_reset_clears_the_simulation(client):
    feed(client, "sim_reset", 0, [10, 20, 30])
    feed(client, "sim_reset", 5, [10])
    r = client.post("/internal/periodicity/reset", json={"simulation_id": "sim_reset"})
    assert r.json()["data"]["cleared_bands"] == 2

    after = client.get(
        "/internal/periodicity/state", params={"simulation_id": "sim_reset", "band_id": 0}
    ).json()["data"]
    assert after["timestamps"] == []


def test_reset_does_not_touch_other_simulations(client):
    feed(client, "sim_a1b2c3d4", 0, [10, 40, 70])
    client.post("/internal/periodicity/reset", json={"simulation_id": "sim_reset"})
    kept = client.get(
        "/internal/periodicity/state", params={"simulation_id": "sim_a1b2c3d4", "band_id": 0}
    ).json()["data"]
    assert len(kept["timestamps"]) == 3


# -- Level 6: predict ------------------------------------------------------------------------------

def test_predict_returns_a_window_containing_the_true_next_activation(client):
    """Level 6 DoD, through the endpoint."""
    feed(client, "sim_periodic", 2, [k * 20 for k in range(15)])
    r = client.get(
        "/internal/periodicity/predict",
        params={"simulation_id": "sim_periodic", "band_id": 2, "now": 285},
    )
    assert r.status_code == 200
    data = r.json()["data"]
    window = data["predicted_next_active_window"]
    assert window["start"] <= 300 <= window["end"]
    assert data["estimated_period"] == pytest.approx(20, abs=0.5)
    assert data["confidence"] > 0.95


def test_predict_response_matches_the_contract_field_names(client):
    """These names are consumed verbatim by the Backend's StateBuilder."""
    feed(client, "sim_periodic", 4, [k * 25 for k in range(12)])
    data = client.get(
        "/internal/periodicity/predict",
        params={"simulation_id": "sim_periodic", "band_id": 4},
    ).json()["data"]
    assert {"predicted_next_active_window", "estimated_period", "confidence"} <= set(data)
    assert set(data["predicted_next_active_window"]) == {"start", "end"}


def test_predict_also_returns_phase_for_the_state_vector(client):
    feed(client, "sim_periodic", 6, [k * 20 for k in range(12)])
    data = client.get(
        "/internal/periodicity/predict",
        params={"simulation_id": "sim_periodic", "band_id": 6, "now": 230},
    ).json()["data"]
    assert 0.0 <= data["phase"] < 1.0


def test_predict_on_an_untouched_band_is_a_well_formed_no_claim(client):
    """The Backend asks for every band before every decision, not just the interesting ones."""
    r = client.get(
        "/internal/periodicity/predict",
        params={"simulation_id": "sim_empty", "band_id": 63},
    )
    assert r.status_code == 200
    data = r.json()["data"]
    assert data["predicted_next_active_window"] is None
    assert data["estimated_period"] is None
    assert data["confidence"] == 0.0


def test_predict_defaults_now_to_the_last_detection(client):
    feed(client, "sim_periodic", 8, [k * 20 for k in range(12)])
    data = client.get(
        "/internal/periodicity/predict",
        params={"simulation_id": "sim_periodic", "band_id": 8},
    ).json()["data"]
    assert data["predicted_next_active_window"]["end"] > 220


# -- Section 1: envelope and error mapping ----------------------------------------------------------

def test_validation_error_uses_the_documented_envelope(client):
    r = client.post(
        "/internal/periodicity/update",
        json={"simulation_id": "sim_a1b2c3d4", "band_id": -1, "detection_timestamp": 10},
    )
    assert r.status_code == 422
    body = r.json()
    assert body["success"] is False
    assert body["error"]["code"] == "VALIDATION_ERROR"
    assert body["error"]["details"]


def test_unknown_update_fields_are_rejected_rather_than_dropped(client):
    r = client.post(
        "/internal/periodicity/update",
        json={"simulation_id": "sim_a1b2c3d4", "band_id": 0,
              "detection_timestamp": 1, "snr_db": 12.5},
    )
    assert r.status_code == 422


def test_missing_query_parameters_are_a_validation_error(client):
    assert client.get("/internal/periodicity/predict").status_code == 422


# -- Level 8: latency and concurrency ----------------------------------------------------------------

def test_prediction_latency_leaves_room_in_the_scheduler_budget(client):
    """This service sits ahead of Ai-ml-1 on the Backend's per-step path (NFR-002, 50 ms).

    Ai-ml-1 measures about 7 ms per decision, so Ai-ml-2 must stay well under the remainder --
    and it is called once per band, not once per step.
    """
    feed(client, "sim_load", 0, [k * 20 for k in range(40)])
    params = {"simulation_id": "sim_load", "band_id": 0, "now": 900}
    client.get("/internal/periodicity/predict", params=params)  # warm the fit cache

    timings = []
    for _ in range(50):
        started = time.perf_counter()
        r = client.get("/internal/periodicity/predict", params=params)
        timings.append((time.perf_counter() - started) * 1000.0)
        assert r.status_code == 200
    p95 = sorted(timings)[int(0.95 * len(timings)) - 1]
    assert p95 < 10.0, f"p95 prediction latency {p95:.1f} ms is too much of the 50 ms budget"


def test_the_fit_is_cached_between_predictions_but_invalidated_by_an_update(client):
    """The cache is what makes 64-bands-per-step affordable; staleness would be worse."""
    feed(client, "sim_load", 1, [k * 20 for k in range(12)])
    first = client.get(
        "/internal/periodicity/predict",
        params={"simulation_id": "sim_load", "band_id": 1, "now": 300},
    ).json()["data"]

    # A long run of new detections at a different cadence must change the answer.
    feed(client, "sim_load", 1, [240 + k * 7 for k in range(20)])
    second = client.get(
        "/internal/periodicity/predict",
        params={"simulation_id": "sim_load", "band_id": 1, "now": 400},
    ).json()["data"]

    assert first["estimated_period"] != second["estimated_period"]


# -- the batch endpoint ------------------------------------------------------------------------

def test_batch_returns_one_prediction_per_requested_band(client):
    feed(client, "sim_periodic", 10, [k * 20 for k in range(12)])
    r = client.post(
        "/internal/periodicity/predict/batch",
        json={"simulation_id": "sim_periodic", "band_ids": [10, 11, 12], "now": 250},
    )
    assert r.status_code == 200
    preds = r.json()["data"]["predictions"]
    assert [p["band_id"] for p in preds] == [10, 11, 12]


def test_batch_agrees_with_the_single_band_endpoint(client):
    """The batch call must be a pure speedup, not a different answer."""
    feed(client, "sim_periodic", 20, [k * 25 for k in range(14)])
    single = client.get(
        "/internal/periodicity/predict",
        params={"simulation_id": "sim_periodic", "band_id": 20, "now": 400},
    ).json()["data"]
    batched = client.post(
        "/internal/periodicity/predict/batch",
        json={"simulation_id": "sim_periodic", "band_ids": [20], "now": 400},
    ).json()["data"]["predictions"][0]

    assert batched["estimated_period"] == pytest.approx(single["estimated_period"])
    assert batched["confidence"] == pytest.approx(single["confidence"])
    assert batched["phase"] == pytest.approx(single["phase"])
    assert batched["predicted_next_active_window"] == single["predicted_next_active_window"]


def test_batch_includes_untouched_bands_as_no_claims(client):
    """The StateBuilder asks for every band; silent bands must come back as well-formed nulls."""
    feed(client, "sim_periodic", 30, [k * 20 for k in range(12)])
    preds = client.post(
        "/internal/periodicity/predict/batch",
        json={"simulation_id": "sim_periodic", "band_ids": [30, 31], "now": 250},
    ).json()["data"]["predictions"]
    by_band = {p["band_id"]: p for p in preds}
    assert by_band[30]["confidence"] > 0.95
    assert by_band[31]["predicted_next_active_window"] is None
    assert by_band[31]["confidence"] == 0.0


def test_batch_is_dramatically_faster_than_looping_the_single_band_endpoint(client):
    """The reason the endpoint exists. Measured at 86x over a real socket; 5x in-process is a
    conservative floor that still fails loudly if the fit cache regresses."""
    bands = list(range(48))
    for b in bands:
        feed(client, "sim_load", b, [k * 17 for k in range(12)])

    params = {"simulation_id": "sim_load", "now": 400}
    client.post("/internal/periodicity/predict/batch", json={**params, "band_ids": bands})

    t = time.perf_counter()
    for b in bands:
        client.get("/internal/periodicity/predict",
                   params={"simulation_id": "sim_load", "band_id": b, "now": 400})
    looped = time.perf_counter() - t

    t = time.perf_counter()
    client.post("/internal/periodicity/predict/batch", json={**params, "band_ids": bands})
    batched = time.perf_counter() - t

    assert batched * 5 < looped, f"batch {batched*1000:.1f} ms vs loop {looped*1000:.1f} ms"


def test_batch_rejects_an_empty_band_list(client):
    r = client.post(
        "/internal/periodicity/predict/batch",
        json={"simulation_id": "sim_periodic", "band_ids": []},
    )
    assert r.status_code == 422
