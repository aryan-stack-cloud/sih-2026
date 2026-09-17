# API_CONTRACT.md — Single Source of Truth

> **This file is copied verbatim into `Frontend/`, `Backend/`, `Ai-ml-1-Scheduler-Engine/`, and
> `Ai-ml-2-Periodicity-Estimator/`.**
> Every coding agent (e.g. Antigravity) working on any one of the four folders should treat this
> file as the non-negotiable contract for how the domains talk to each other. If a change to an
> endpoint, event, or schema is ever needed, it must be made **here first**, then propagated to
> all four copies in the same commit. Do not let any one domain invent its own shape for a
> shared endpoint.

Source PRD: `Intelligent RF Spectrum Scan Strategy — Product Requirements & Technical Design
Specification v1.0`. Scope reminder: **simulation-only**, no real RF hardware, no interception,
no jamming, no weapon control.

---

## 0. Domain Map

| Domain | Folder | Role | Talks to |
|---|---|---|---|
| Frontend | `Frontend/` | React/TS dashboard (test-harness build first, real UI later) | Backend only (REST + WS) |
| Backend | `Backend/` | Spring Boot system of record, orchestration, WebSocket hub | Frontend, Ai-ml-1, Ai-ml-2, Postgres, Redis |
| Ai-ml-1 | `Ai-ml-1-Scheduler-Engine/` | Bandit / Q-Learning / DQN / PPO scan-decision policy | Backend only (internal REST) |
| Ai-ml-2 | `Ai-ml-2-Periodicity-Estimator/` | Statistical periodicity/inter-arrival predictor, feeds RL state | Backend only (internal REST) |

The Backend is the **only** service the Frontend ever calls. The Backend is the **only** service
that calls Ai-ml-1 and Ai-ml-2. Ai-ml-1 and Ai-ml-2 never call each other directly — the Backend's
`StateBuilder` assembles the full state vector (simulation features + periodicity features) before
sending it to Ai-ml-1's `/internal/decide`. This keeps every domain independently testable and
independently deployable, and it is the seam every coding agent must respect.

---

## 1. Standard Envelope (all public + internal REST responses)

```json
// success
{ "success": true, "data": { }, "requestId": "req_019a" }

// error
{ "success": false, "error": { "code": "SIMULATION_NOT_FOUND", "message": "...", "details": {} }, "requestId": "req_019a" }
```

- Validation errors → HTTP 422, `error.code = "VALIDATION_ERROR"`, `error.details` = field → message map.
- Not found → HTTP 404, `error.code = "RESOURCE_NOT_FOUND"`.
- All other domain errors → HTTP 409/500 with a specific `error.code`.

---

## 2. Public REST API (Backend ⇄ Frontend)

Base path: `/api/v1`

| Method | Endpoint | Purpose |
|---|---|---|
| POST | `/simulations` | Create simulation (`name`, `bands`, `duration_steps`, `seed`) → `201 { id, status: "draft" }` |
| GET | `/simulations` | Paginated list, filter by `status` |
| GET | `/simulations/{id}` | Detail |
| PUT | `/simulations/{id}` | Update config (only while `status=draft`) |
| DELETE | `/simulations/{id}` | Delete, cascades scan/detection events |
| POST | `/simulations/{id}/start` | Enqueue simulation worker job |
| POST | `/simulations/{id}/stop` | Persist partial state |
| POST | `/simulations/{id}/reset` | Reset to t=0, clears history |
| POST | `/emitters` | Create emitter (`behavior_class` enum: `fixed`\|`periodic`\|`agile`\|`random`\|`intermittent`) |
| GET/PUT/DELETE | `/emitters/{id}` | Standard CRUD |
| GET | `/receiver/status` | Tuned bands, dwell remaining |
| PUT | `/receiver/config` | `bandwidth_k`, `dwell_ms`, `tuning_delay`, `threshold` |
| POST | `/receiver/scan` | Manual single-step scan (debug) → `Observation` |
| GET | `/scheduler/status` | Current policy + step count |
| PUT | `/scheduler/config` | Select policy: `baseline`\|`bandit`\|`q_learning`\|`dqn`\|`ppo` |
| POST | `/scheduler/start` / `/scheduler/stop` | Start/stop scheduling loop |
| GET | `/scheduler/decision` | Latest decision + state vector (debug) |
| GET | `/scheduler/history` | Paginated decision log |
| POST | `/models/train` | Launch training job (async) → `job_id` |
| GET | `/models` | List, filter by `algorithm`/`active` |
| GET | `/models/{id}` | Detail + metrics |
| POST | `/models/{id}/activate` | Promote to active scheduler model |
| POST | `/models/{id}/evaluate` | Run evaluation episodes → metrics summary |
| POST | `/experiments` | Define experiment (scenario A–G + policy list) |
| GET | `/experiments` | List |
| GET | `/experiments/{id}` | Detail |
| POST | `/experiments/{id}/run` | Execute baseline + ML runs (async, WS progress) |
| POST | `/experiments/{id}/stop` | Cancel a running experiment |
| GET | `/experiments/{id}/results` | Comparison results: Pd/Pfa/latency per policy |
| GET | `/metrics/live?simulationId=` | Live metrics (polling fallback for WS) |
| GET | `/metrics/{experimentId}` | Stored metrics for an experiment |
| GET | `/metrics/compare?ids[]=` | Compare ≥2 experiments |
| GET | `/health` / `/ready` / `/metrics` | No auth required; Prometheus format on `/metrics` |

Auth (V1+): Bearer JWT on all routes except `/health`, `/ready`. MVP demo runs unauthenticated on
a trusted local network (see `Backend/README.md` Level 9).

---

## 3. WebSocket Contract (Backend ⇄ Frontend)

| Property | Value |
|---|---|
| Endpoint | `/ws/v1/simulations/{simulationId}` |
| Lifecycle | Client connects after simulation creation → server sends `connection_ack` → client may `subscribe` to channels: `spectrum`, `scheduler`, `metrics`, `training` |
| Event types | `spectrum_update`, `scan_decision`, `detection_event`, `metrics_update`, `training_progress`, `error` |
| Heartbeat | Server ping every 15s; client must pong within 10s or connection closes |
| Reconnection | Client exponential backoff 1s→30s cap; server replays last known state snapshot |
| Backpressure | `spectrum_update` coalesced to ≤10/s per connection; drops intermediate frames, never the latest |
| Error frame | `{"type":"error","code":"SIM_NOT_RUNNING","message":"..."}` |

Frontend clients MUST implement reconnect + coalescing tolerance from day one, even in the
test-only build — this is the behavior most likely to break "seamless connection" if skipped.

---

## 4. Internal REST — Backend ⇄ Ai-ml-1 (Scheduler Engine)

Base path: `/internal` on the Ai-ml-1 service (default port `8500`).

| Method | Endpoint | Request | Response |
|---|---|---|---|
| POST | `/internal/decide` | `{ "simulation_id", "state": StateVector, "policy": "bandit"\|"q_learning"\|"dqn"\|"ppo", "model_id"? }` | `{ "action": { "next_band": int, "dwell_time"?: int }, "model_id", "decision_id" }` |
| POST | `/internal/learn` | `{ "simulation_id", "decision_id", "state", "action", "reward": float, "next_state" }` | `{ "acknowledged": true }` (no-op for baseline, called by Backend after every step) |
| POST | `/internal/train` | `{ "algorithm", "scenario", "hyperparams": {}, "episode_count", "seed_range": [start,end] }` | `{ "job_id" }` (async) |
| GET | `/internal/train/{job_id}/status` | — | `{ "status": "running"\|"done"\|"failed", "progress": 0-1 }` |
| GET | `/internal/models` | Query: `algorithm?`, `active?` | List of model metadata |
| GET | `/internal/models/{id}` | — | Model detail + eval metrics |
| POST | `/internal/models/{id}/activate` | — | Deactivates previous active model of same algorithm |
| POST | `/internal/models/{id}/evaluate` | `{ "scenario", "episode_count" }` | Metrics summary (Pd, Pfa, AIT, latency, HPDR) |
| POST | `/internal/reset` | `{ "simulation_id" }` | `{ "cleared_sessions": int }` — drops Ai-ml-1's cached online-learning session for that simulation. Called by the Backend on simulation reset, alongside Ai-ml-2's `/internal/periodicity/reset` |
| GET | `/internal/health` | — | `{ "status": "ok" }` |

### StateVector shape (ML-001, shared verbatim by Backend's StateBuilder and Ai-ml-1)

```json
{
  "bands": [
    {
      "band_id": 0,
      "time_since_last_scan": 12,
      "recent_detection_rate_ewma": 0.42,
      "consecutive_misses": 3,
      "periodicity_phase": 0.71,
      "periodicity_confidence": 0.85,
      "band_priority_weight": 1.0,
      "tuning_cost_to_band": 1
    }
  ],
  "receiver": { "tuned_bands": [2], "dwell_remaining_ms": 0, "tuning_delay_countdown_ms": 0 }
}
```
`periodicity_phase` and `periodicity_confidence` are populated by the Backend from Ai-ml-2's
`/internal/periodicity/predict` response before the state vector is sent to Ai-ml-1. Ai-ml-1 never
calls Ai-ml-2 directly.

Ai-ml-1 is stateless with respect to *simulation* state — every `/internal/decide` carries the
full StateVector — but it does keep one thing per `simulation_id`: the online-learning agent
instance, because the Backend calls `/internal/learn` after every step and the bandit's per-band
estimates are built up across a run. `/internal/reset` is what clears it. A simulation reset must
call both `/internal/reset` (Ai-ml-1) and `/internal/periodicity/reset` (Ai-ml-2), or the next run
of that `simulation_id` inherits the previous run's beliefs.

### Reward (ML-003 / Equation 10.1) — computed by Backend, passed to `/internal/learn`

`r(t) = w1·D(t) + w2·P(t)·D(t) − w3·L(t) − w4·F(t) − w5·C(t) − w6·M(t)`
Weights `w1..w6` are config-driven and logged per experiment (see `Backend/README.md` Level 5).

---

## 5. Internal REST — Backend ⇄ Ai-ml-2 (Periodicity Estimator)

Base path: `/internal` on the Ai-ml-2 service (default port `8600`).

| Method | Endpoint | Request | Response |
|---|---|---|---|
| POST | `/internal/periodicity/update` | `{ "simulation_id", "band_id", "detection_timestamp" }` | `{ "acknowledged": true }` — called by Backend on every confirmed detection event |
| GET | `/internal/periodicity/predict?simulation_id=&band_id=` | — | `{ "predicted_next_active_window": {"start": t, "end": t}, "estimated_period": float, "confidence": 0-1 }` |
| POST | `/internal/periodicity/predict/batch` | `{ "simulation_id", "band_ids": [int], "now"? }` | `{ "predictions": [ { "band_id", "predicted_next_active_window", "estimated_period", "confidence", "phase" } ] }` — **the endpoint the StateBuilder should use.** See the note below |
| GET | `/internal/periodicity/state?simulation_id=&band_id=` | — | Raw inter-arrival buffer + current estimate, for debugging |
| POST | `/internal/periodicity/reset` | `{ "simulation_id" }` | Clears estimator state for a simulation (used on simulation reset) |
| GET | `/internal/health` | — | `{ "status": "ok" }` |

### Why the batch endpoint exists

The Backend's `StateBuilder` needs a periodicity prediction for **every band** before **every**
scheduler decision. Calling the single-band `GET` in a loop means N round trips per simulation
step, and that is what dominates: measured at 64 bands, 64 sequential calls cost ~193 ms while
the estimator's own work is ~0.13 ms. The entire cost is HTTP overhead, and it blows NFR-002's
50 ms per-step budget on its own — before Ai-ml-1 is even called.

`POST /internal/periodicity/predict/batch` collapses those N round trips into one. The
single-band `GET` remains for debugging and for the `/internal/periodicity/state` workflow.

Note also that a band's fit only changes when a new detection arrives for it, so Ai-ml-2 caches
per-band fits and invalidates on `update`. Per step, at most K bands (the receiver's
instantaneous bandwidth) can have new detections, so the per-step refit cost is bounded by K,
not by N.

---

## 6. Shared Enums & IDs (must match byte-for-byte across all four domains)

```
behavior_class:  fixed | periodic | agile | random | intermittent
policy_type:     baseline | bandit | q_learning | dqn | ppo
detection_type:  TP | FN | FP | TN
scenario_id:     A | B | C | D | E | F | G
simulation_id:   string, format "sim_<8-hex>"
experiment_id:   string, format "exp_<8-hex>"
model_id:        string, format "model_<algorithm>_<8-hex>"
```

## 7. Docker Compose Ports (must match across all READMEs)

| Service | Container port | Host port |
|---|---|---|
| frontend | 5173 | 5173 |
| api (Backend) | 8080 | 8080 |
| ml-scheduler (Ai-ml-1) | 8500 | 8500 |
| ml-periodicity (Ai-ml-2) | 8600 | 8600 |
| db (Postgres) | 5432 | 5432 |
| redis | 6379 | 6379 |

Any coding agent adding a new endpoint, event, or field must update this file's copy in **all
four folders**, not just the one it's currently working in.
