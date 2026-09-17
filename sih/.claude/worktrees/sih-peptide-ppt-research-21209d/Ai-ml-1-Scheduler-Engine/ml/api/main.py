"""FastAPI service -- API_CONTRACT.md Section 4, port 8500 (Ai-ml-1 Levels 1, 4, 5, 6).

Every route returns the Section 1 envelope: ``{success, data|error, requestId}``. Errors map to
the documented codes -- 422 VALIDATION_ERROR, 404 RESOURCE_NOT_FOUND, 409/500 otherwise.

This service is called only by the Backend. It never calls Ai-ml-2 and never calls the Frontend.
"""

from __future__ import annotations

import time
from contextlib import asynccontextmanager
from typing import Any

from fastapi import APIRouter, FastAPI, Header, HTTPException, Request, Response
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from ml.contract import (
    DecideRequest,
    DecideResponse,
    ErrorBody,
    ErrorEnvelope,
    EvaluateRequest,
    HealthResponse,
    LearnRequest,
    LearnResponse,
    SuccessEnvelope,
    TrainRequest,
    TrainResponse,
    TrainStatusResponse,
    new_request_id,
)
from ml.inference.inference import InferenceEngine
from ml.model_registry import ModelRegistry
from ml.training.jobs import JobRegistry
from ml.utils import logging as jlog

log = jlog.get_logger(__name__)

registry = ModelRegistry()
engine = InferenceEngine(registry)
jobs = JobRegistry()


@asynccontextmanager
async def lifespan(_: FastAPI):
    jlog.configure()
    log.info("ml-scheduler ready", extra={"port": 8500, "service": "Ai-ml-1"})
    yield
    jobs.shutdown()


app = FastAPI(
    lifespan=lifespan,
    title="Ai-ml-1 Scheduler Engine",
    version="1.0.0",
    description=(
        "Scan-decision policy service for the Intelligent RF Spectrum Scan Strategy prototype. "
        "Simulation-only: no real RF hardware, no interception, no jamming, no weapon control."
    ),
)
router = APIRouter(prefix="/internal")


def ok(data: Any, request_id: str | None = None) -> JSONResponse:
    envelope = SuccessEnvelope(data=data, requestId=request_id or new_request_id())
    return JSONResponse(content=envelope.model_dump(mode="json"))


def fail(status: int, code: str, message: str, details: dict | None = None, request_id: str | None = None):
    envelope = ErrorEnvelope(
        error=ErrorBody(code=code, message=message, details=details or {}),
        requestId=request_id or new_request_id(),
    )
    return JSONResponse(status_code=status, content=envelope.model_dump(mode="json"))


# -- cross-cutting -------------------------------------------------------------------------

@app.middleware("http")
async def correlation_and_timing(request: Request, call_next):
    """Attach the Backend's correlation IDs to every log line, and time the decision path."""
    jlog.clear_correlation()
    jlog.set_correlation(
        request_id=request.headers.get("X-Request-Id"),
        simulation_id=request.headers.get("X-Simulation-Id"),
        training_run_id=request.headers.get("X-Training-Run-Id"),
    )
    started = time.perf_counter()
    response: Response = await call_next(request)
    elapsed_ms = (time.perf_counter() - started) * 1000.0
    response.headers["X-Response-Time-Ms"] = f"{elapsed_ms:.2f}"
    if request.url.path.endswith("/decide"):
        # NFR-002: < 50 ms per decision for bandit/Q-Learning, < 150 ms for DQN.
        log.info("decide latency", extra={"latency_ms": round(elapsed_ms, 3)})
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
    return fail(500, "INTERNAL_ERROR", "Unexpected error in the scheduler engine")


# -- Section 4 endpoints ---------------------------------------------------------------------

@router.get("/health")
def health() -> JSONResponse:
    return ok(HealthResponse().model_dump())


@router.post("/decide")
def decide(body: DecideRequest, x_request_id: str | None = Header(default=None)) -> JSONResponse:
    """Return the next band to scan for one simulation step."""
    try:
        action, model_id, decision_id = engine.decide(
            body.simulation_id, body.state, body.policy, body.model_id
        )
    except KeyError:
        return fail(404, "RESOURCE_NOT_FOUND", f"model {body.model_id} is not registered")
    except ValueError as exc:
        return fail(422, "VALIDATION_ERROR", str(exc))

    payload = DecideResponse(action=action, model_id=model_id, decision_id=decision_id)
    return ok(payload.model_dump(mode="json"), x_request_id)


@router.post("/learn")
def learn(body: LearnRequest, x_request_id: str | None = Header(default=None)) -> JSONResponse:
    """Apply one Backend-computed reward. No-op for policies that do not learn online."""
    acknowledged = engine.learn(
        body.simulation_id, body.decision_id, body.state, body.action, body.reward, body.next_state
    )
    return ok(LearnResponse(acknowledged=acknowledged).model_dump(), x_request_id)


@router.post("/reset")
def reset(payload: dict) -> JSONResponse:
    """Drop cached online-learning sessions for a simulation (called on simulation reset)."""
    simulation_id = payload.get("simulation_id")
    if not simulation_id:
        return fail(422, "VALIDATION_ERROR", "simulation_id is required",
                    {"simulation_id": "field required"})
    return ok({"cleared_sessions": engine.reset(simulation_id)})


@router.post("/train")
def train_endpoint(body: TrainRequest) -> JSONResponse:
    """Launch an async training job; returns a job_id immediately."""
    from ml.training.trainer import train as run_training

    def task(progress=None) -> dict:
        result = run_training(
            algorithm=body.algorithm,
            scenario=body.scenario,
            hyperparams=body.hyperparams,
            episode_count=body.episode_count,
            seed_range=body.seed_range,
            progress=progress,
        )
        meta = registry.register(
            result["agent"],
            algorithm=body.algorithm,
            scenario=body.scenario,
            hyperparams=result["summary"].get("hyperparams"),
            seed_range=list(body.seed_range) if body.seed_range else None,
            metrics=_metric_subset(result["summary"]),
        )
        return {"model_id": meta.model_id, "metrics": _metric_subset(result["summary"])}

    job_id = jobs.submit(task)
    return ok(TrainResponse(job_id=job_id).model_dump())


@router.get("/train/{job_id}/status")
def train_status(job_id: str) -> JSONResponse:
    job = jobs.get(job_id)
    if job is None:
        return fail(404, "RESOURCE_NOT_FOUND", f"job {job_id} not found")
    detail = dict(job.detail)
    if job.status == "done" and job.result:
        detail.update(job.result)
    if job.error:
        detail["error"] = job.error
    return ok(
        TrainStatusResponse(status=job.status, progress=job.progress, detail=detail).model_dump()
    )


@router.get("/models")
def list_models(algorithm: str | None = None, active: bool | None = None) -> JSONResponse:
    return ok([m.model_dump(mode="json") for m in registry.list(algorithm=algorithm, active=active)])


@router.get("/models/{model_id}")
def get_model(model_id: str) -> JSONResponse:
    try:
        return ok(registry.get(model_id).model_dump(mode="json"))
    except KeyError:
        return fail(404, "RESOURCE_NOT_FOUND", f"model {model_id} not found")


@router.post("/models/{model_id}/activate")
def activate_model(model_id: str) -> JSONResponse:
    """Promote a model. Deactivates the previous active model of the same algorithm."""
    try:
        return ok(registry.activate(model_id).model_dump(mode="json"))
    except KeyError:
        return fail(404, "RESOURCE_NOT_FOUND", f"model {model_id} not found")


@router.post("/models/{model_id}/evaluate")
def evaluate_model(model_id: str, body: EvaluateRequest) -> JSONResponse:
    """Run evaluation episodes and return the Section 12 metrics summary."""
    from ml.training.trainer import evaluate as run_eval

    try:
        agent = registry.load_agent(model_id)
    except KeyError:
        return fail(404, "RESOURCE_NOT_FOUND", f"model {model_id} not found")

    summary = run_eval(agent, body.scenario, episodes=body.episode_count)
    registry.update_metrics(model_id, _metric_subset(summary))
    return ok(summary)


def _metric_subset(summary: dict) -> dict:
    """The metrics the contract names for a model: Pd, Pfa, AIT, latency, HPDR."""
    keys = (
        "pd", "pfa", "ait", "median_latency", "hpdr", "interception_ratio",
        "scan_efficiency", "cumulative_reward_mean", "episodes", "decision_latency_ms_mean",
    )
    return {k: summary[k] for k in keys if k in summary}


app.include_router(router)
