"""Pydantic models for API_CONTRACT.md -- Sections 1 and 5.

THIS FILE IS A MIRROR, NOT A SOURCE. ``API_CONTRACT.md`` is the single source of truth and is
copied byte-identically into all four domain folders. Change it there first, propagate to all
four copies in the same commit, and tell the Backend owner. Do not let this file drift ahead of
the contract -- the response shape here is consumed directly by the Backend's StateBuilder and
forwarded into Ai-ml-1's state vector, so a renamed field breaks the scheduler silently.
"""

from __future__ import annotations

from typing import Any, Literal, Optional
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field


def new_request_id() -> str:
    return f"req_{uuid4().hex[:8]}"


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


# -- Section 5: Backend <-> Ai-ml-2 ---------------------------------------------------------

class UpdateRequest(BaseModel):
    """``POST /internal/periodicity/update`` -- one confirmed detection event."""

    model_config = ConfigDict(extra="forbid")

    simulation_id: str
    band_id: int = Field(ge=0)
    detection_timestamp: float = Field(ge=0)


class UpdateResponse(BaseModel):
    acknowledged: bool = True


class ActiveWindowModel(BaseModel):
    start: float
    end: float


class PredictResponse(BaseModel):
    """``GET /internal/periodicity/predict``.

    ``predicted_next_active_window`` is null when there is no usable estimate. That is a
    well-formed "no claim", not an error: the Backend calls this for *every* band before every
    scheduler decision, including bands holding non-periodic emitters (Ai-ml-2 Level 7).
    """

    predicted_next_active_window: Optional[ActiveWindowModel] = None
    estimated_period: Optional[float] = None
    confidence: float = Field(ge=0.0, le=1.0)


class BatchPredictRequest(BaseModel):
    """``POST /internal/periodicity/predict/batch``.

    The endpoint the Backend's StateBuilder should use: one round trip per scheduler step
    instead of one per band. See "Why the batch endpoint exists" in API_CONTRACT.md Section 5.
    """

    model_config = ConfigDict(extra="forbid")

    simulation_id: str
    band_ids: list[int] = Field(min_length=1, max_length=1024)
    now: Optional[float] = None


class BandPrediction(PredictResponse):
    """One band's prediction inside a batch response."""

    band_id: int = Field(ge=0)
    phase: float = Field(default=0.0, ge=0.0, lt=1.0)


class BatchPredictResponse(BaseModel):
    predictions: list[BandPrediction] = Field(default_factory=list)


class ResetRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    simulation_id: str


class ResetResponse(BaseModel):
    acknowledged: bool = True
    cleared_bands: int = 0


class StateResponse(BaseModel):
    """``GET /internal/periodicity/state`` -- raw buffer plus current estimate, for debugging."""

    simulation_id: str
    band_id: int
    timestamps: list[float] = Field(default_factory=list)
    inter_arrivals: list[float] = Field(default_factory=list)
    activations: int = 0
    detections_retained: int = 0
    detections_total: int = 0
    estimate: dict[str, Any] = Field(default_factory=dict)
    prediction: dict[str, Any] = Field(default_factory=dict)


class HealthResponse(BaseModel):
    status: Literal["ok"] = "ok"
