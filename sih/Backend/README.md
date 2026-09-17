# Backend — Spring Boot System of Record

Build this **complete** — it is the only service the Frontend talks to, and the only service
that talks to the two ML microservices. See `../API_CONTRACT.md` in this folder for the exact
contract you must implement and call. Scope reminder: simulation-only, no real RF hardware.

## Stack

Java 21 + Spring Boot 3 (Web MVC, Data JPA, WebSocket, Validation; Spring Security added at
Level 9). PostgreSQL as system of record, Flyway for migrations. Redis (Spring Data Redis) for
WebSocket pub/sub fan-out and the async job queue for training/experiment runs. Layers:
`Controller → Service → Repository → Entity`, DTOs as Java `record`s validated with
`jakarta.validation`, a `@RestControllerAdvice` mapping domain exceptions to the standard error
envelope, structured JSON logs via SLF4J + Logback with correlation IDs on every line.

## Folder structure to generate

```
backend/src/main/java/com/rfscheduler/
  controller/   # one @RestController per resource
  config/       # WebSocketConfig, SecurityConfig, RedisConfig, OpenApiConfig
  domain/       # JPA @Entity classes
  dto/          # request/response records + MapStruct mappers
  service/      # SimulationService, SchedulerService, MetricsService, ExperimentService
  repository/   # Spring Data JPA repositories
  simulation/   # SimulationClock, Spectrum, Emitter, EmitterBehavior
  receiver/     # Receiver, Scanner, DetectionEngine
  scheduler/    # BaselineScheduler + MLSchedulerClient (HTTP client to Ai-ml-1)
  metrics/      # Pd/Pfa/latency/efficiency calculators
  experiments/  # ExperimentRunner, comparison logic
  websocket/    # WebSocketHandler, session + topic management
  exception/    # domain exceptions + advice
backend/src/main/resources/   # application.yml, db/migration/ (Flyway)
backend/src/test/java/        # unit + integration (Testcontainers + Postgres)
```

## Core entities

`SimulationClock`, `Spectrum`, `FrequencyBand`, `Emitter`, `EmitterBehavior` (strategy per
class: fixed / periodic / agile / random / intermittent), `Signal`, `Receiver`, `Scanner`,
`DetectionEngine`, `GroundTruthGenerator` (never given to the scheduler — used only for scoring).

Simulation loop per step:
```
spectrum.advance(t)
action = scheduler.decide(state)          // calls Ai-ml-1 /internal/decide, or BaselineScheduler
observation = scanner.execute(action, receiver, spectrum)
event = detection_engine.evaluate(observation, threshold)
reward = reward_fn(event, action, state)
state = state_builder.update(state, action, observation, event)  // merges Ai-ml-2 periodicity features
metrics.record(t, action, observation, event, reward)
scheduler.learn(state, action, reward)    // calls Ai-ml-1 /internal/learn; no-op for baseline
```

## Database schema (Flyway migrations)

`simulations(id, name, seed, bands, duration, status, created_at)` ·
`emitters(id, simulation_id FK, behavior_class, band, period, priority)` ·
`receiver_configs(id, simulation_id FK, bandwidth_k, dwell_ms, tuning_delay, threshold)` ·
`scan_events(id, simulation_id FK, t, band, policy_type, dwell_used)` ·
`detection_events(id, scan_event_id FK, type, latency_ms)` ·
`scheduler_decisions(id, scan_event_id FK, state_vector JSONB, action, reward, model_id FK)` ·
`models(id, algorithm, version, hyperparams JSONB, active, created_at)` ·
`experiments(id, scenario, baseline_id, ml_run_id, expected_outcome)`.

## Reward function (implement exactly — Equation 10.1)

`r(t) = w1·D(t) + w2·P(t)·D(t) − w3·L(t) − w4·F(t) − w5·C(t) − w6·M(t)`
Weights are config-driven, logged per experiment. `D`=true detection, `P`=priority multiplier,
`L`=latency penalty, `F`=false alarm flag, `C`=redundant-scan penalty, `M`=missed-opportunity
penalty on a high-priority unscanned active band.

## Metrics engine (Section 12 — implement all, unit-test against hand-computed cases)

Pd = TP/(TP+FN) · Pfa = FP/(FP+TN) · AIT = mean(t_detect − t_active_start) · per-event latency ·
Interception Ratio · Scan Efficiency · Cumulative Reward · High-Priority Detection Rate ·
Precision · Recall · F1 · Coverage · Miss Rate.

## The 7 experiment scenarios (Section 13) — seed these as fixture configs

A: 80% fixed, 16 bands, 10 emitters, 2000 steps · B: 70% periodic, 16 bands, 10 emitters, 2000
steps · C: 70% agile, 24 bands, 12 emitters, 2000 steps · D: even split, 24 bands, 15 emitters,
3000 steps · E: high-density mixed, 32 bands, 30 emitters, 3000 steps · F: sparse, 32 bands, 5
emitters, 2000 steps · G: rapidly changing, 24 bands, 15 emitters, 3000 steps. Each: ≥20
episodes/policy, shared seed set across baseline and ML for fair comparison.

---

## Build Plan — 10 Levels

### Level 1 — Repo & scaffold
Spring Boot project bootstrapped, Postgres + Redis wired via docker-compose, Flyway running an
empty baseline migration, CI pipeline green on an empty test suite, `/health` and `/ready`
return 200.
**DoD:** `docker-compose up` boots api + db + redis; `GET /health` → `200`.

### Level 2 — Simulation engine core
`SimulationClock`, `Spectrum`, `FrequencyBand`, `Emitter`, all 5 `EmitterBehavior` classes,
`GroundTruthGenerator`. Given identical seed + config, output is bit-for-bit reproducible
(NFR-006).
**DoD:** Unit tests assert correct ground truth per emitter class against hand-computed tables.

### Level 3 — Receiver model
`Receiver`, `Scanner` enforcing instantaneous bandwidth `K`, dwell time, tuning/switching delay
per Section 9.1/9.2. Tuning delay must fully elapse before a newly tuned band yields a valid
observation.
**DoD:** Scan/tune/dwell mechanics verified against the formal definitions table (Section 9.1).

### Level 4 — Baseline scanner + detection engine
`BaselineScheduler` (round-robin, configurable fixed-order), `DetectionEngine` applying
threshold/noise model to produce TP/FN/FP/TN.
**DoD:** Round-robin scanner produces a deterministic scan order for a given seed.

### Level 5 — Metrics engine + reward function
Implement every metric in Section 12 and the reward function (Equation 10.1) with configurable,
logged weights.
**DoD:** All formulas unit-tested against hand-computed cases; reward logged per experiment.

### Level 6 — Public REST API (mocked ML)
Implement every endpoint in `API_CONTRACT.md` §2. `SchedulerService` calls a **mock**
`MLSchedulerClient` (hardcoded/random decisions) and a **mock** periodicity client so the API
surface is fully testable before Ai-ml-1/Ai-ml-2 exist.
**DoD:** All §2 endpoints implemented, contract tests passing, standard envelope + error format
everywhere (§1).

### Level 7 — WebSocket hub
Implement `API_CONTRACT.md` §3 exactly: endpoint, event types, heartbeat, reconnection replay,
coalescing to ≤10/s, error frames. Redis pub/sub fans events out across instances.
**DoD:** Load test confirms ≤250ms end-to-end delivery under ≤10 concurrent viewers (NFR-003);
coalescing verified under load.

### Level 8 — Real ML integration
Swap the Level 6 mocks for real HTTP clients hitting Ai-ml-1 (`API_CONTRACT.md` §4) and Ai-ml-2
(§5). `StateBuilder` merges simulation-side features with Ai-ml-2's periodicity prediction before
calling Ai-ml-1's `/internal/decide`. Model registry endpoints (`/models/*`) proxy to Ai-ml-1.
**DoD:** Full experiment run (baseline vs. bandit) succeeds end-to-end via API without manual DB
intervention.

### Level 9 — Security, auth, checkpointing
Bearer JWT on all routes except `/health`/`/ready` (MVP demo may stay unauthenticated on a
trusted local network — document which mode is active). Input validation on every DTO (422 on
violation). Rate limiting (Bucket4j, e.g. 60 req/min/client) on write endpoints. Simulation state
checkpointed at least every 500 steps (NFR-005). Audit log on model-activation and config-change
endpoints. Dependency allow-list review confirming no RF-hardware-capable dependency exists
(NFR-010).
**DoD:** Security checklist (Section 17) passes review; checkpoint/resume tested by killing the
worker mid-run.

### Level 10 — Testing, observability, demo polish
≥80% unit-test coverage on core logic (simulation, reward, metrics). Integration suite
(API+DB+worker round-trip, WS delivery), ML-specific reproducibility/regression tests,
end-to-end demo workflow test, performance tests against NFR-001/002/003. Structured logs with
correlation IDs on every simulation/experiment/training-run. Prometheus `/metrics`. The scripted
3–5 minute demo (Section 20.4) runs reliably twice in a row.
**DoD:** CI blocks merges below 80% coverage or on failed integration/E2E suites; demo rehearsed
twice successfully.
