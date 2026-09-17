"""The SCT additions to API_CONTRACT.md Sections 4 and 6.

Every change is additive: no endpoint removed, no existing field's meaning altered. That is what
lets the four folders adopt independently instead of needing a flag-day. These tests pin the
"additive" part down, because a required field slipped in here would break the Backend silently.
"""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from ml.agents.base import POLICY_TYPES
from ml.contract import BandState, DecideRequest, DecideResponse, StateVector

LEGACY_BAND = {
    "band_id": 0,
    "time_since_last_scan": 12,
    "recent_detection_rate_ewma": 0.42,
    "consecutive_misses": 3,
    "periodicity_phase": 0.71,
    "periodicity_confidence": 0.85,
    "band_priority_weight": 1.0,
    "tuning_cost_to_band": 1,
}

SCT_FIELDS = {
    "revisit_deadline": 28,
    "staleness_ratio": 0.43,
    "threat_score": 0.62,
    "occupancy_belief": 0.31,
    "sync_risk": 0.0,
}


# -- backward compatibility ----------------------------------------------------------------------

def test_a_backend_that_has_not_adopted_the_new_fields_still_validates():
    """The whole point of additive: an un-upgraded Backend keeps working."""
    band = BandState(**LEGACY_BAND)
    assert band.revisit_deadline == 0
    assert band.threat_score == pytest.approx(0.5)
    assert band.occupancy_belief == pytest.approx(0.5)
    assert band.staleness_ratio == pytest.approx(0.0)
    assert band.sync_risk == pytest.approx(0.0)


def test_a_zero_revisit_deadline_means_no_deadline_not_an_immediate_one():
    """Documented default. Read the other way it would make every legacy band permanently overdue."""
    assert BandState(**LEGACY_BAND).revisit_deadline == 0


# -- the new fields ------------------------------------------------------------------------------

def test_the_sct_band_fields_round_trip():
    band = BandState(**LEGACY_BAND, **SCT_FIELDS)
    assert band.revisit_deadline == 28
    assert band.threat_score == pytest.approx(0.62)
    assert band.sync_risk == pytest.approx(0.0)


def test_threat_score_is_distinct_from_the_operator_set_priority_weight():
    """One is learned from emitter character, the other is set by hand. Conflating them loses both."""
    band = BandState(**{**LEGACY_BAND, "band_priority_weight": 2.0}, **{**SCT_FIELDS, "threat_score": 0.1})
    assert band.band_priority_weight == pytest.approx(2.0)
    assert band.threat_score == pytest.approx(0.1)


def test_probabilities_outside_the_unit_interval_are_rejected():
    for field in ("threat_score", "occupancy_belief", "sync_risk"):
        with pytest.raises(ValidationError):
            BandState(**LEGACY_BAND, **{**SCT_FIELDS, field: 1.5})


def test_staleness_ratio_may_exceed_one_because_a_band_can_be_overdue():
    band = BandState(**LEGACY_BAND, **{**SCT_FIELDS, "staleness_ratio": 3.2})
    assert band.staleness_ratio == pytest.approx(3.2)


def test_unknown_band_fields_are_still_rejected():
    """extra=forbid stays on: a typo must fail loudly, not be silently dropped."""
    with pytest.raises(ValidationError):
        BandState(**LEGACY_BAND, threat_scores=0.5)


# -- policy enum ---------------------------------------------------------------------------------

def test_the_policy_enum_gained_index_and_ctmc():
    assert "index" in POLICY_TYPES
    assert "ctmc" in POLICY_TYPES


def test_no_existing_policy_was_removed():
    for legacy in ("baseline", "bandit", "q_learning", "dqn", "ppo"):
        assert legacy in POLICY_TYPES


def test_decide_accepts_the_index_policy():
    request = DecideRequest(
        simulation_id="sim_00000001",
        state=StateVector(bands=[BandState(**LEGACY_BAND, **SCT_FIELDS)]),
        policy="index",
    )
    assert request.policy == "index"


# -- explainability ------------------------------------------------------------------------------

def test_the_decide_response_can_carry_an_index_breakdown():
    response = DecideResponse(
        action={"next_band": 3, "dwell_time": 20},
        model_id="model_index_0000abcd",
        decision_id="dec_0000abcd",
        index_breakdown={
            "value": 0.31,
            "information": 0.02,
            "novelty": 0.0,
            "deadline": 1.4,
            "elapsed_s": 0.015,
        },
    )
    assert response.index_breakdown["deadline"] == pytest.approx(1.4)


def test_the_index_breakdown_is_optional():
    response = DecideResponse(
        action={"next_band": 3},
        model_id="model_bandit_0000abcd",
        decision_id="dec_0000abcd",
    )
    assert response.index_breakdown is None
