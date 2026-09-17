"""Pydantic models for API_CONTRACT.md -- Sections 1, 4 and 6.

THIS FILE IS A MIRROR, NOT A SOURCE. ``API_CONTRACT.md`` is the single source of truth and is
copied byte-identically into all four domain folders. If a field has to change, change it in
``API_CONTRACT.md`` first, propagate it to all four copies in the same commit, and tell the
Backend owner -- do not let this file drift ahead of the contract, or the Backend will send a
StateVector this service silently mis-reads.

Field names, types and enum values below are transcribed from the contract verbatim.
"""

from __future__ import annotations

from typing import Any, Literal, Optional
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field

# -- Section 6: shared enums and ID formats ------------------------------------------------

BehaviorClass = Literal["fixed", "periodic", "agile", "random", "intermittent"]
PolicyType = Literal["baseline", "bandit", "q_learning", "dqn", "ppo"]
DetectionType = Literal["TP", "FN", "FP", "TN"]
ScenarioId = Literal["A", "B", "C", "D", "E", "F", "G"]
LearningPolicy = Literal["bandit", "q_learning", "dqn", "ppo"]

SIMULATION_ID_PATTERN = r"^sim_[0-9a-f]{8}$"
EXPERIMENT_ID_PATTERN = r"^exp_[0-9a-f]{8}$"
MODEL_ID_PATTERN = r"^model_(baseline|bandit|q_learning|dqn|ppo)_[0-9a-f]{8}$"


def new_request_id() -> str:
    return f"req_{uuid4().hex[:8]}"


def new_model_id(algorithm: str) -> str:
    return f"model_{algorithm}_{uuid4().hex[:8]}"


def new_decision_id() -> str:
    return f"dec_{uuid4().hex[:8]}"


# -- Section 1: standard envelope ----------------------------------------------------------

class ErrorBody(BaseModel):
    code: str
    message: str
    details: dict[str, Any] = Field(default_factory=dict)


class SuccessEnvelope(BaseModel):
    success: Literal[True] = True
    data: Any = None
    requestId: str = Field(default_factory=new_request_id)


class ErrorEnvelope(BaseModel):
    success: Literal[False] = False
    error: ErrorBody
    requestId: str = Field(default_factory=new_request_id)


# -- Section 4: StateVector ----------------------------------------------------------------

class BandState(BaseModel):
    """One band's ML-001 features.

    ``periodicity_phase`` and ``periodicity_confidence`` are populated by the Backend from
    Ai-ml-2 before the StateVector reaches us. This service treats them as opaque inputs and
    never computes them (Ai-ml-1 README, "State / Action / Reward").
    """

    model_config = ConfigDict(extra="forbid")

    band_id: int = Field(ge=0)
    time_since_last_scan: int = Field(ge=0)
    recent_detection_rate_ewma: float = Field(ge=0.0, le=1.0)
    consecutive_misses: int = Field(ge=0)
    periodicity_phase: float = Field(ge=0.0, le=1.0)
    periodicity_confidence: float = Field(ge=0.0, le=1.0)
    band_priority_weight: float = Field(ge=0.0)
    tuning_cost_to_band: int = Field(ge=0)


class ReceiverState(BaseModel):
    model_config = ConfigDict(extra="forbid")

    tuned_bands: list[int] = Field(default_factory=list)
    dwell_remaining_ms: int = Field(default=0, ge=0)
    tuning_delay_countdown_ms: int = Field(default=0, ge=0)


class StateVector(BaseModel):
    model_config = ConfigDict(extra="forbid")

    bands: list[BandState] = Field(min_length=1)
    receiver: ReceiverState = Field(default_factory=ReceiverState)


class Action(BaseModel):
    model_config = ConfigDict(extra="forbid")

    next_band: int = Field(ge=0)
    dwell_time: Optional[int] = Field(default=None, ge=0)


# -- Section 4: request/response bodies ----------------------------------------------------

class DecideRequest(BaseModel):
    simulation_id: str
    state: StateVector
    policy: LearningPolicy
    model_id: Optional[str] = None


class DecideResponse(BaseModel):
    action: Action
    model_id: str
    decision_id: str


class LearnRequest(BaseModel):
    simulation_id: str
    decision_id: str
    state: StateVector
    action: Action
    reward: float
    next_state: Optional[StateVector] = None


class LearnResponse(BaseModel):
    acknowledged: bool = True


class TrainRequest(BaseModel):
    algorithm: LearningPolicy
    scenario: ScenarioId
    hyperparams: dict[str, Any] = Field(default_factory=dict)
    episode_count: Optional[int] = Field(default=None, ge=1)
    seed_range: Optional[tuple[int, int]] = None


class TrainResponse(BaseModel):
    job_id: str


class TrainStatusResponse(BaseModel):
    status: Literal["running", "done", "failed"]
    progress: float = Field(ge=0.0, le=1.0)
    detail: dict[str, Any] = Field(default_factory=dict)


class EvaluateRequest(BaseModel):
    scenario: ScenarioId
    episode_count: int = Field(default=20, ge=1)


class ModelMetadata(BaseModel):
    model_config = ConfigDict(protected_namespaces=())

    model_id: str
    algorithm: PolicyType
    scenario: Optional[str] = None
    version: int = 1
    active: bool = False
    created_at: str
    hyperparams: dict[str, Any] = Field(default_factory=dict)
    seed_range: Optional[list[int]] = None
    metrics: dict[str, Any] = Field(default_factory=dict)


class HealthResponse(BaseModel):
    status: Literal["ok"] = "ok"
