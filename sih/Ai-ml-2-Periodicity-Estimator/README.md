# Ai-ml-2 — Periodicity Estimator

Python microservice implementing the "hybrid predictor + scheduler" architecture from PRD Section
11.1: a lightweight, interpretable statistical estimator of each band's periodic-emitter timing,
kept deliberately **separate** from the RL policy (Ai-ml-1) so it can be unit-tested and
data-efficient on its own. It is called **only** by the Backend, via `../API_CONTRACT.md` §5. It
never talks to the Frontend or to Ai-ml-1 directly. Scope reminder: simulation-only, synthetic
detection timestamps only.

## Why this is its own service, not folded into the RL state or into Ai-ml-1

Per PRD Section 11.1: RL requires far more samples to learn periodicity implicitly than a
closed-form estimator (slower convergence for MVP timeline), and a full learned periodicity
classifier is overkill for the defined emitter classes. The chosen design — a statistical
inter-arrival estimator feeding the RL state as additional features — gives the best
interpretability/data-efficiency trade-off and isolates periodicity estimation for independent
unit testing. Do not merge this logic into Ai-ml-1's codebase even though both are "ML"; the
Backend's `StateBuilder` is what stitches their outputs together (see `../Backend/README.md`
Level 8).

## Stack

Python 3.11+, FastAPI (internal REST per §5), NumPy/SciPy for autocorrelation and inter-arrival
statistics. No GPU, no deep learning — this is intentionally a classical statistics service.

## Folder structure to generate

```
periodicity/
  estimator/       periodicity_estimator.py   # autocorrelation / inter-arrival fit per band
  buffers/          per-(simulation_id, band_id) detection-timestamp ring buffers
  inference/        prediction.py — backing /internal/periodicity/predict
  api/              FastAPI routers implementing API_CONTRACT.md §5
  tests/            unit tests against hand-computed inter-arrival sequences
  configs/          buffer size, minimum-samples-before-prediction, confidence thresholds
  utils/            seeding, logging, correlation-ID passthrough
```

## Core object

`PeriodicityEstimator` tracks each `(simulation_id, band_id)` pair's detection timestamps and
fits a simple autocorrelation/inter-arrival estimate of period length and phase. Output:
`predicted_next_active_window` (a `{start, end}` time range) and a `confidence` score. This is
exposed to the Backend's `StateBuilder` as additional RL-state features (`periodicity_phase`,
`periodicity_confidence` in `API_CONTRACT.md` §4) — it is never a standalone decision-maker.

## Endpoints to implement (verbatim from `API_CONTRACT.md` §5)

- `POST /internal/periodicity/update` — called by the Backend on every confirmed detection event;
  appends a timestamp to that band's buffer and re-fits the estimate incrementally.
- `GET /internal/periodicity/predict` — returns the current prediction for a band; this is what
  the Backend's `StateBuilder` calls before every `/internal/decide` call to Ai-ml-1.
- `GET /internal/periodicity/state` — raw buffer + current estimate, for debugging.
- `POST /internal/periodicity/reset` — clears a simulation's buffers (called on simulation reset).
- `GET /internal/health`.

---

## Build Plan — 10 Levels

### Level 1 — Service scaffold
FastAPI app boots, `/internal/health` returns `{"status":"ok"}`, Dockerfile + docker-compose entry
on port 8600 (per `API_CONTRACT.md` §7), structured logging with correlation-ID passthrough.
**DoD:** `docker-compose up ml-periodicity` boots standalone; health check passes.

### Level 2 — Detection-timestamp buffer
Per-`(simulation_id, band_id)` ring buffer of detection timestamps, bounded size (config-driven),
thread/process-safe for concurrent simulations (NFR-004: ≥5 concurrent simulations).
**DoD:** Buffer correctly accumulates and bounds timestamps across concurrent simulation IDs in
unit tests.

### Level 3 — `/internal/periodicity/update` + `/internal/periodicity/reset`
Wire the buffer to the update/reset endpoints exactly as specified in §5.
**DoD:** Posting a sequence of detection events for a band is reflected in
`/internal/periodicity/state` immediately after.

### Level 4 — Inter-arrival / autocorrelation estimator (fixed-period case)
`periodicity_estimator.py`: fit period length and phase for a constant-period periodic emitter
from its inter-arrival buffer. Start with the simplest case (Emitter class "periodic", constant
`Tperiod`) before handling jitter.
**DoD:** Unit tests against hand-computed constant-period sequences recover the true period and
phase within a defined tolerance.

### Level 5 — Jittered period + confidence scoring
Extend the estimator to periodic emitters with jittered periods; produce a `confidence` score
that degrades gracefully with jitter and with too few samples.
**DoD:** Confidence score is low (below a documented threshold) when fewer than the configured
minimum-samples are available, and improves monotonically as more consistent samples arrive.

### Level 6 — `/internal/periodicity/predict`
Implement the prediction endpoint returning `predicted_next_active_window` and `confidence`
exactly per §5's response shape (this shape is consumed directly by the Backend's StateBuilder —
do not rename fields).
**DoD:** Contract test: given a fixture buffer of a known periodic sequence, the endpoint returns
a next-active-window that contains the true next activation time.

### Level 7 — Non-periodic emitter behavior (graceful null case)
Confirm behavior for fixed-frequency, agile, random, and intermittent emitters: the estimator
should report low/near-zero confidence rather than a false periodic prediction — this matters
because the Backend feeds this into the RL state for *every* band, not just periodic ones.
**DoD:** Unit tests confirm no false-positive high-confidence periodicity claims on the four
non-periodic behavior classes.

### Level 8 — Latency & concurrency hardening
Ensure prediction latency is negligible relative to the scheduler's decision budget (this service
sits on the Backend's critical path before every `/internal/decide` call to Ai-ml-1, per NFR-002's
50ms/step budget). Confirm correctness under ≥5 concurrent simulations, ≥64 bands each (NFR-004).
**DoD:** Load test confirms prediction latency stays low enough that it doesn't push the combined
Backend→Ai-ml-2→Ai-ml-1 round trip over the scheduler's per-step latency budget.

### Level 9 — Improved detection latency on Scenario B (acceptance gate)
Validate against PRD Definition-of-Done item 8: "periodic-emitter prediction measurably improves
detection latency on Scenario B" — run Scenario B (70% periodic) end-to-end with and without this
service's predictions feeding the RL state (via the Backend + Ai-ml-1) and confirm the
improvement.
**DoD:** Documented before/after detection-latency comparison on Scenario B shows a measurable
improvement when this service's output is included in the state vector.

### Level 10 — Testing & observability
≥80% unit-test coverage on estimator logic (NFR-007). Correlation IDs on every log line.
Dependency-vulnerability scan (pip-audit) in CI. Reproducibility: identical detection-timestamp
sequence + config yields identical prediction (mirrors NFR-006).
**DoD:** CI blocks below 80% coverage; reproducibility test passes across repeated runs with the
same fixture input.
