# Intelligent RF Spectrum Scan Strategy — Build Scaffold

Simulation-only research prototype. **No real RF hardware, no interception, no jamming, no
weapon control** — every signal, emitter, and detection exists only inside a synthetic,
deterministic-by-seed simulation. This scaffold turns the PRD into four independently-buildable
folders that a coding agent (e.g. Antigravity) can be pointed at one at a time — or all at once —
and produce a working, interoperating system.

## Folders

| Folder | What it builds | Give to the agent when... |
|---|---|---|
| `Backend/` | Complete Spring Boot system of record: simulation engine, receiver model, baseline scanner, REST + WebSocket API, Postgres schema, orchestration of the two ML services | Build this **first** — everything else depends on its contract |
| `Ai-ml-1-Scheduler-Engine/` | Bandit → Q-Learning → DQN/PPO scan-decision policy microservice | Build in parallel with Backend once `API_CONTRACT.md` is stable |
| `Ai-ml-2-Periodicity-Estimator/` | Statistical inter-arrival/periodicity predictor microservice | Build in parallel with Backend once `API_CONTRACT.md` is stable |
| `Frontend/` | **Test-harness only** — minimal, unstyled React/TS app that exercises every REST + WS endpoint. Deliberately ugly; real UX design is a later pass | Build last, or in parallel purely to validate the contract end-to-end |

Every folder contains:
1. Its own `README.md` — a **10-level build plan** (Level 1 → Level 10), each level with scope,
   deliverables, and a Definition of Done, so an agent can be handed one level at a time.
2. A copy of `API_CONTRACT.md` — the canonical, byte-identical contract every domain must honor.

## Recommended order of operations

1. Hand `Backend/README.md` + `API_CONTRACT.md` to the agent. Build through Level 6 (APIs stubbed,
   in-memory or Postgres-backed, calling **mock** ML services).
2. Hand `Ai-ml-1-Scheduler-Engine/README.md` and `Ai-ml-2-Periodicity-Estimator/README.md` to the
   agent (same or separate sessions) — they only need `API_CONTRACT.md` §4/§5, not the Backend's
   internals.
3. Point the Backend at the real ML services (swap the mocks) — Backend Level 8 (Integration).
4. Hand `Frontend/README.md` to the agent to build the test harness against the now-real Backend.
5. Run the Level 9/10 phases (Testing, Demo polish) across all four in whatever order the team
   finds convenient — they're independent by this point.

## Why this split works

The PRD's own architecture (Section 15.1, ADR-06) already isolates the Python ML ecosystem behind
an internal REST boundary from the Spring Boot domain layer, and further isolates the periodicity
estimator as a "hybrid predictor feeding RL state" rather than a decision-maker (Section 11.1).
This scaffold just turns those two seams into two separate deliverable folders, plus the
frontend/backend seam the PRD already specifies via REST + WebSocket (Section 15.3–15.4).

## Non-goals (apply to every folder, every level)

- No control of real RF hardware or SDR devices.
- No real-world signal interception, direction-finding, or geolocation.
- No jamming, spoofing, electronic-attack, or countermeasure functionality.
- No weapon-system targeting, cueing, or fire-control integration.
- No classified, export-controlled, or operationally sensitive data or waveforms.

If any generated code path would touch a physical radio, network capture, or hardware driver,
stop and flag it — it is out of scope by design (NFR-010).
