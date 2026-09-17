"""FastAPI service -- API_CONTRACT.md Section 5, port 8600 (Ai-ml-2 Levels 1, 3, 6).

Every route returns the Section 1 envelope: ``{success, data|error, requestId}``. Errors map to
the documented codes -- 422 VALIDATION_ERROR, 404 RESOURCE_NOT_FOUND, 500 otherwise.

Called only by the Backend. Never calls Ai-ml-1, never calls the Frontend.
"""

from __future__ import annotations

import time
from contextlib import asynccontextmanager
from typing import Any

from fastapi import APIRouter, FastAPI, HTTPException, Query, Request, Response
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from periodicity.config import default_config
from periodicity.contract import (
    BandPrediction,
    BatchPredictRequest,
    BatchPredictResponse,
    ErrorBody,
    ErrorEnvelope,
    HealthResponse,
    PredictResponse,
    ResetRequest,
    ResetResponse,
    StateResponse,
    SuccessEnvelope,
    UpdateRequest,
    UpdateResponse,
    new_request_id,
)
from periodicity.service import PeriodicityService
from periodicity.utils import logging as jlog

log = jlog.get_logger(__name__)

config = default_config()
service = PeriodicityService(config)


@asynccontextmanager
async def lifespan(_: FastAPI):
    jlog.configure()
    log.info("ml-periodicity ready", extra={"port": 8600, "service": "Ai-ml-2"})
    yield


app = FastAPI(
    lifespan=lifespan,
    title="Ai-ml-2 Periodicity Estimator",
    version="1.0.0",
    description=(
        "Statistical periodicity/inter-arrival predictor for the Intelligent RF Spectrum Scan "
        "Strategy prototype. Simulation-only: synthetic detection timestamps, no real RF."
    ),
)
router = APIRouter(prefix="/internal")


def ok(data: Any, request_id: str | None = None) -> JSONResponse:
    return JSONResponse(
        content=SuccessEnvelope(data=data, requestId=request_id or new_request_id()).model_dump(
            mode="json"
        )
    )


def fail(status: int, code: str, message: str, details: dict | None = None) -> JSONResponse:
    return JSONResponse(
        status_code=status,
        content=ErrorEnvelope(
            error=ErrorBody(code=code, message=message, details=details or {})
        ).model_dump(mode="json"),
    )


# -- cross-cutting ---------------------------------------------------------------------------

@app.middleware("http")
async def correlation_and_timing(request: Request, call_next):
    """Correlation-ID passthrough (NFR-008) plus timing on the prediction path.

    This service sits ahead of Ai-ml-1 in the Backend's per-step critical path, so its latency
    comes out of the same NFR-002 budget rather than having one of its own.
    """
    jlog.clear_correlation()
    jlog.set_correlation(
        request_id=request.headers.get("X-Request-Id"),
        simulation_id=request.headers.get("X-Simulation-Id"),
    )
    started = time.perf_counter()
    response: Response = await call_next(request)
    elapsed_ms = (time.perf_counter() - started) * 1000.0
    response.headers["X-Response-Time-Ms"] = f"{elapsed_ms:.2f}"
    return response


@app.exception_handler(RequestValidationError)
async def on_validation_error(request: Request, exc: RequestValidationError):
    details = {".".join(str(p) for p in e["loc"][1:]): e["msg"] for e in exc.errors()}
    return fail(422, "VALIDATION_ERROR", "Request failed validation", details)


@app.exception_handler(HTTPException)
async def on_http_error(request: Request, exc: HTTPException):
    code = "RESOURCE_NOT_FOUND" if exc.status_code == 404 else "REQUEST_FAILED"
    return fail(exc.status_code, code, str(exc.detail))


@app.exception_handler(Exception)
async def on_unhandled(request: Request, exc: Exception):
    log.warning("unhandled error", extra={"path": request.url.path, "error": str(exc)})
    return fail(500, "INTERNAL_ERROR", "Unexpected error in the periodicity estimator")


# -- Section 5 endpoints ----------------------------------------------------------------------

@router.get("/health")
def health() -> JSONResponse:
    return ok(HealthResponse().model_dump())


@router.post("/periodicity/update")
def update(body: UpdateRequest) -> JSONResponse:
    """Called by the Backend on every confirmed detection event."""
    service.update(body.simulation_id, body.band_id, body.detection_timestamp)
    # Acknowledged even when the timestamp was a duplicate: the Backend told us something true,
    # and a retry must not look like a failure.
    return ok(UpdateResponse(acknowledged=True).model_dump())


@router.get("/periodicity/predict")
def predict(
    simulation_id: str = Query(...),
    band_id: int = Query(..., ge=0),
    now: float | None = Query(
        None, description="Current simulation time. Defaults to the last detection seen."
    ),
) -> JSONResponse:
    """Prediction for one band -- what the Backend's StateBuilder calls before every decision."""
    at = now
    if at is None:
        seen = service.buffers.snapshot(simulation_id, band_id)
        at = seen[-1] if seen else 0.0

    prediction = service.predict(simulation_id, band_id, float(at))
    payload = PredictResponse(**prediction.to_contract()).model_dump(mode="json")
    # phase is not in the Section 5 response shape, but the Backend needs it for the state
    # vector's periodicity_phase and would otherwise have to recompute it from the window.
    payload["phase"] = service.phase(simulation_id, band_id, float(at))
    return ok(payload)


@router.post("/periodicity/predict/batch")
def predict_batch(body: BatchPredictRequest) -> JSONResponse:
    """Every band's prediction in one round trip -- what the StateBuilder should call.

    Looping the single-band GET costs N HTTP round trips per scheduler step; at 64 bands that
    measured ~193 ms against a 50 ms per-step budget, of which the estimator's own work was
    0.13 ms. This collapses it to one.
    """
    at = body.now
    if at is None:
        at = service.latest_detection(body.simulation_id, body.band_ids)

    predictions = [
        BandPrediction(band_id=band_id, phase=phase, **prediction.to_contract())
        for band_id, prediction, phase in service.predict_many(
            body.simulation_id, body.band_ids, float(at)
        )
    ]
    return ok(BatchPredictResponse(predictions=predictions).model_dump(mode="json"))


@router.get("/periodicity/state")
def state(
    simulation_id: str = Query(...),
    band_id: int = Query(..., ge=0),
    now: float | None = Query(None),
) -> JSONResponse:
    """Raw buffer plus current estimate, for debugging."""
    return ok(StateResponse(**service.state(simulation_id, band_id, now)).model_dump(mode="json"))


@router.post("/periodicity/reset")
def reset(body: ResetRequest) -> JSONResponse:
    """Clear a simulation's buffers. Called on simulation reset."""
    cleared = service.reset(body.simulation_id)
    return ok(ResetResponse(acknowledged=True, cleared_bands=cleared).model_dump())


app.include_router(router)
