# Ai-ml-1 — Scheduler Engine (Bandit → Q-Learning → DQN/PPO)

Python microservice that owns the scan-decision policy. It is called **only** by the Backend, via
the internal contract in `../API_CONTRACT.md` §4. It never talks to the Frontend or to Ai-ml-2
directly — periodicity features arrive already merged into the `StateVector` the Backend sends.
Scope reminder: simulation-only decision-making over synthetic data; no real RF hardware.

## Stack

Python 3.11+, FastAPI (internal REST per §4), Gymnasium-compatible environment interface
(interoperable with Stable-Baselines3 for the V2 escalation), NumPy, and (V2 only) PyTorch or
Stable-Baselines3 for DQN/PPO. Structured JSON logging with the same correlation IDs the Backend
uses (`simulation_id`, `training_run_id`).

## Folder structure to generate

```
ml/
  environments/   environment.py, state.py, action_space.py, reward.py   # Gymnasium-compatible
  agents/         bandit_agent.py, q_learning_agent.py, dqn_agent.py, ppo_agent.py
  algorithms/     shared exploration/exploitation strategies (epsilon-greedy, decay schedules)
  features/       band_feature_builder.py   # NOTE: periodicity_estimator.py lives in Ai-ml-2, not here
  training/       trainer.py, hyperparameter configs (YAML per algorithm)
  evaluation/     evaluator.py, metrics comparison helpers
  inference/      inference.py — low-latency decision API backing /internal/decide
  checkpoints/    versioned weights / Q-tables (gitignored, mounted as a Docker volume)
  experiments/    scenario configs (A–G) as YAML
  visualization/  reward curves, Q-value heatmaps (offline analysis only, not served)
  configs/        default hyperparameters per algorithm
  utils/          seeding, logging, reproducibility helpers
  model_registry.py   # registration, versioning, activation/rollback
```

## Algorithm ladder (Section 10.1 — build in this order, do not skip ahead)

| Algorithm | Tier | Training time | Interpretability |
|---|---|---|---|
| Multi-Armed Bandit (contextual) | **MVP — build first** | Minutes | High |
| Tabular Q-Learning | V1 | Tens of minutes | Medium |
| Deep Q-Network (DQN) | V2 — stretch | Hours, GPU preferred | Low |
| PPO | V2 — research extension | Hours, GPU preferred | Low |

Do not start DQN/PPO before the bandit demonstrably beats the open-loop baseline on Scenario A/B
— this is an explicit scope-creep risk called out in the PRD (Section 24).

## State / Action / Reward (implement exactly as received — do not reshape)

- **State** — the `StateVector` JSON defined in `API_CONTRACT.md` §4. Treat `periodicity_phase`
  and `periodicity_confidence` as opaque input features; this service does not compute them.
- **Action** — MVP/V1: `{ "next_band": int }`. V2 (DQN/PPO) may add `{ "dwell_time": int }` once
  dwell-time control is justified by MVP results.
- **Reward** — a scalar float arrives pre-computed from the Backend via `/internal/learn`
  (Equation 10.1, Section 10.3). This service consumes it; it does not compute it itself.

## Episode / exploration definitions (Section 10.4)

Episode = one full simulation run of fixed duration T, terminal at t=T. Exploration: ε-greedy for
bandit/Q-Learning with per-episode decay; entropy-regularized policy for PPO. Exploitation:
argmax expected reward (bandit/Q-Learning) or policy-network sampling (DQN/PPO). Checkpoint model
weights / Q-table every N episodes and on best-validation-reward. Every trained model registered
with algorithm, hyperparameters, training-data seed range, and evaluation metrics.

---

## Build Plan — 10 Levels

### Level 1 — Service scaffold
FastAPI app boots, `/internal/health` returns `{"status":"ok"}`, Dockerfile + docker-compose entry
on port 8500 (per `API_CONTRACT.md` §7), structured logging with correlation-ID passthrough.
**DoD:** `docker-compose up ml-scheduler` boots standalone; health check passes.

### Level 2 — Gymnasium environment shell
`environments/environment.py` implements a Gymnasium-compatible env whose `state`/`action`/
`reward` shapes match `API_CONTRACT.md` §4 exactly (not an internally-invented shape). Unit tests
confirm the env can be stepped with a random policy without crashing.
**DoD:** `env.step()`/`env.reset()` round-trip cleanly against the shared StateVector schema.

### Level 3 — Contextual bandit agent (MVP)
`agents/bandit_agent.py`: per-band value estimates, ε-greedy exploration with decay. Wire to
`inference/inference.py`.
**DoD:** Bandit trains on a synthetic reward stream and its band-value estimates converge in unit
tests.

### Level 4 — `/internal/decide` + `/internal/learn` endpoints
Implement both endpoints from `API_CONTRACT.md` §4 against the bandit agent, decision latency
<50ms per step (NFR-002).
**DoD:** Contract test hitting `/internal/decide` with a fixture StateVector returns a valid
action within the latency budget.

### Level 5 — Training pipeline + model registry
`training/trainer.py` runs full episodes against the scenario configs (A–G) checked into
`experiments/`. `model_registry.py` persists versioned checkpoints with metadata. `/internal/train`
(async job) and `/internal/train/{job_id}/status` implemented.
**DoD:** A training job launched via the endpoint completes and registers a versioned model.

### Level 6 — Evaluation + `/internal/models/*`
`evaluation/evaluator.py` computes Pd, Pfa, AIT, latency, HPDR against a fixed evaluation seed
set. `/internal/models`, `/internal/models/{id}`, `/internal/models/{id}/activate`,
`/internal/models/{id}/evaluate` implemented.
**DoD:** Bandit measurably beats a random baseline on Scenario A/B on these metrics — this is the
MVP acceptance gate (Section 22, Phase 4).

### Level 7 — Tabular Q-Learning (V1 escalation)
`agents/q_learning_agent.py`, small state/action space per MVP scope, fixed seeds + checkpointing
for training stability. Selectable via the `policy` field in `/internal/decide`.
**DoD:** Q-Learning trains reproducibly given a fixed seed and can be selected/evaluated exactly
like the bandit through the same endpoints.

### Level 8 — Reproducibility & regression tests
Given identical seed + config, training and inference output is bit-for-bit reproducible
(NFR-006, mirrored into ML-specific test suite). Regression thresholds guard against silent
performance drops across scenarios A–G.
**DoD:** CI test suite (mirrors Backend's TEST-030–034) passes: reward validation, policy sanity
checks, run-to-run reproducibility, regression thresholds, distribution-shift check.

### Level 9 — DQN/PPO (V2 stretch — only after Level 6 gate is met)
`agents/dqn_agent.py`, `agents/ppo_agent.py` via Stable-Baselines3, `(next_band, dwell_time)`
action space, GPU-optional training. Explicitly gated behind an architecture-review checkpoint
per the PRD's scope-creep risk mitigation (Section 24) — do not build this level unless directed.
**DoD:** DQN/PPO selectable through the same `/internal/decide` contract with no Backend changes
required; inference latency <150ms (NFR-002).

### Level 10 — Hardening & observability
≥80% unit-test coverage on agent/reward/state logic (NFR-007). Correlation IDs on every log line.
Dependency-vulnerability scan (pip-audit) in CI. Load test confirms decision latency budgets hold
under concurrent simulation load (NFR-004: ≥5 concurrent simulations).
**DoD:** CI blocks below 80% coverage; latency budgets verified under NFR-004 concurrency target.
