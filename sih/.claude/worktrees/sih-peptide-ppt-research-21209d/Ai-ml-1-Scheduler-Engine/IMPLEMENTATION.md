# Ai-ml-1 Scheduler Engine — implementation notes

Implementation of the build plan in [README.md](README.md), against the contract in
[API_CONTRACT.md](API_CONTRACT.md). `README.md` and `API_CONTRACT.md` are the specs and are not
edited by this work; this file records what was built, what was decided, and what the results
actually are.

Simulation-only. No real RF hardware, no interception, no jamming, no weapon control.

---

## Quick start

```bash
pip install -r requirements.txt
```

```bash
python -m pytest tests/ -q
```

```bash
python scripts/compare.py --scenario B --policies random,baseline,bandit --episodes 20
```

```bash
uvicorn ml.api.main:app --port 8500
```

Then, against a running service:

```bash
curl -s -X POST localhost:8500/internal/decide -H "Content-Type: application/json" -d @tests/fixtures/state_vector.json
```

Skip the training-heavy tests during inner-loop work:

```bash
python -m pytest tests/ -q -m "not slow"
```

---

## Status against the 10-level build plan

| Level | Scope | State |
|---|---|---|
| 1 | Service scaffold, `/internal/health`, Dockerfile, structured logging | done |
| 2 | Gymnasium environment matching the §4 shapes | done |
| 3 | Contextual bandit (MVP) | done |
| 4 | `/internal/decide` + `/internal/learn`, <50 ms | done — warm p95 **6.6 ms** over HTTP |
| 5 | Training pipeline + model registry, async `/internal/train` | done |
| 6 | Evaluation + `/internal/models/*`, **MVP acceptance gate** | done — gate passes, with a caveat below |
| 7 | Tabular Q-Learning (V1) | done |
| 8 | Reproducibility & regression tests | done |
| 9 | DQN/PPO (V2 stretch, gated) | built and verified, off by default |
| 10 | Hardening & observability | 87% coverage, correlation IDs, latency verified |

167 tests pass, 1 skipped (the gated Turing download).

### Measured decision latency (NFR-002)

Measured over real HTTP against `uvicorn` on :8500, not in-process — the two differ by more than
an order of magnitude and only the socket number is the one NFR-002 governs.

| Case | p50 | p95 | Notes |
|---|---|---|---|
| Warm, same simulation | 5.6 ms | **6.6 ms** | the steady state; budget is 50 ms |
| New `simulation_id` | 7.0 ms | 8.1 ms | builds a session, copies the active model |
| First decide after boot | — | ~260 ms | one-time per process: registry read + checkpoint load |

The cold start is once per process, not per simulation. If the Backend's first step of a demo
must stay inside budget, hit `/internal/decide` once at startup to warm it.

An earlier draft of this file claimed 0.26 ms/step. That figure was the in-process agent decision
time inside the evaluation loop and did **not** include the HTTP hop, pydantic validation, or
session lookup. Plan the team's latency budget against 6.6 ms — Ai-ml-2's prediction call sits on
the same per-step critical path, ahead of this one.

---

## Results

Scenario B (70% periodic, 16 bands, 10 emitters), 5 evaluation seeds, 1000 steps.
All policies see an identical spectrum per seed.

| Metric | random | round-robin | bandit |
|---|---|---|---|
| Pd | 0.1037 | 0.1067 | **0.3454** |
| Pfa | 0.0690 | 0.0682 | 0.0703 |
| HPDR | 0.1085 | 0.1014 | **0.3748** |
| Scan efficiency | 0.190 | 0.198 | **0.573** |
| AIT (detected runs) | 2.46 | 2.34 | **0.59** |
| Run intercept rate | 0.340 | **0.413** | 0.174 |
| Censored AIT | 660.7 | **587.8** | 826.1 |

Scenario A (80% fixed): Pd 0.106 → **0.249**, HPDR 0.105 → **0.573**, scan efficiency
0.426 → **0.917**.

**The gate passes.** Ai-ml-1 Level 6 asks for the bandit to beat a *random* baseline on Pd, Pfa,
AIT, latency and HPDR; PRD Phase 4 asks for Pd specifically. It clears all of them on both A
and B — `scripts/compare.py` prints the pass/fail.

### Where the learned policy loses

It does not win everything, and the demo should say so rather than being asked about it.

The bandit reports a **lower run intercept rate** (0.174 vs 0.413) and a **worse censored AIT**
than the round-robin sweep. This is a genuine resource-constraint frontier, not a metric artifact:
with instantaneous bandwidth K=2 over 16 bands, a scheduler can either spread thin and catch the
*start* of many short activation runs, or concentrate and observe far more active spectrum. The
sweep takes the first option; Equation 10.1 pushes the learned policy toward the second.

`w5_redundant` moves along that frontier, and does so monotonically:

| `w5_redundant` | Pd | Censored AIT | Run intercept rate | Interception ratio |
|---|---|---|---|---|
| 0.5 | 0.357 | 827 | 0.173 | 0.425 |
| **3.0 (default)** | 0.338 | 812 | 0.188 | 0.725 |
| 8.0 | 0.259 | 703 | 0.297 | 0.900 |
| 20.0 | 0.154 | 577 | 0.423 | 1.000 |

The default trades a little Pd for a large gain in emitter coverage. Reward weights are
config-driven per scenario (`ml/experiments/scenario_*.yaml`), so this is the team's call to
retune per mission, exactly as PRD Section 24 anticipates.

`tests/test_acceptance.py::test_learned_policy_trades_run_coverage_for_density` asserts this
weakness. If a future change makes the learned policy win on coverage too, that test fails — and
this section needs updating rather than silently going stale.

---

## Two measurement traps worth knowing about

Both were found by measurement, and both would have produced confident, wrong demo claims.

**1. Raw AIT is conditioned on detection succeeding.** PRD Section 12 defines AIT as an average
over detections, so it only counts activation runs a policy actually caught. A policy that
intercepts *more* runs will usually post a *worse* AIT — the extra runs it caught are the hard,
late ones the weaker policy missed entirely. Read alone, raw AIT ranks the better policy lower.

`ait_censored` is reported alongside it: undetected runs are charged the full episode length, so
the average is defined over every run. Use raw `ait` to describe how fast a policy reacts when it
does intercept; use `ait_censored` to compare two policies. This is what the PRD Definition-of-Done
item 8 comparison is read against.

**2. Pd and Pfa are counted over different populations,** deliberately. Pd counts every band at
every step, so a band that was active and never looked at is a false negative — otherwise a
scanner that stared at one band forever would report a perfect Pd, which is the exact failure mode
this project exists to fix. Pfa counts *scanned* bands only, because an unscanned band cannot raise
a false alarm; counting idle unscanned bands as true negatives would drive Pfa to zero for every
policy. Both rules are pinned by tests in `tests/test_metrics.py`.

---

## Design decisions

**The environment serializes to the contract.** `ml/environments/state.py` is the load-bearing
file: `StateBuilder` exposes the same per-band state as a flat float32 vector (what agents and
Stable-Baselines3 consume) and as the exact §4 `StateVector` JSON (what the Backend sends). The API
converts at the boundary and nowhere else, so a model trained offline reads features identically at
inference. `tests/test_environment.py` asserts the round-trip is exact.

**Action space stays `Discrete(N)`.** An action names `next_band`; the receiver then observes the
contiguous block of K bands starting there. That is what "K bands observable per step" means
physically (PRD §9.2) and it keeps the space `Discrete(N)` rather than `C(N, K)` — which is what
makes a tabular bandit or Q-table tractable at N=32, and it is the shape the contract already
specifies.

**Tuning delay costs integration time, not a coin flip.** A step that retunes gets
`step_ms - tuning_delay_ms` of observation; below the dwell minimum it yields nothing, otherwise
effective SNR scales by `sqrt(observe_ms / step_ms)`. A hard on/off switching cost would make
retuning either free or fatal and the agent would learn a degenerate policy either way.

**Three RNG streams per seed** — ground truth, detection noise, policy exploration. This gives
NFR-006 reproducibility *and* the property Section 13 needs: every policy sees a bit-identical
spectrum, so a comparison isolates the scheduling decision. Asserted in
`tests/test_reproducibility.py`.

**The bandit shares feature weights and resets per-band biases each episode.** `q(s,a) = w·φ_a + b_a`.
The shared `w` learns the transferable rule from every arm at once, so it converges in a handful of
episodes; `b_a` captures what is idiosyncratic about each band and is the interpretable "per-band
value estimate" Level 3 asks for. But `b_a` is reset at episode start, because emitters sit on
different bands every seed — carrying it forward made the agent camp on bands that were busy during
training and silent at evaluation, scoring *worse than round-robin* while looking like a trained
policy.

**Evaluation runs with online learning on, exploration off.** That is what deployment does: the
Backend calls `/internal/decide` then `/internal/learn` on every step of a live simulation. Freezing
the policy after training would score it in a mode it never actually runs in. Exploration stays off
so the numbers are the policy's own and the run is deterministic given a seed.

### Two reward readings that were changed after measurement

Both are in `ml/environments/reward.py` with the reasoning inline.

**L(t) is charged only on the first detection of an activation run.** Charging stale latency every
step made the reward fight the metric it serves — AIT counts one latency per run while Pd rewards
every active cell observed — and it pushed the agent off emitters it had correctly found.

**C(t) counts re-detecting an already-intercepted run as "no new information."** The literal PRD
wording is "cost of rescanning a band with no new information." Reading that as merely "found
nothing" leaves camping completely unpenalised: a band that pays out every step never looks wasted.
The policy then maximises detection density on a handful of loud bands and never discovers the rest
of the spectrum — Pd and scan efficiency look excellent while the interception mission quietly
fails. This is the change that made `w5_redundant` a working coverage knob.

---

## Contract compliance

`ml/contract.py` mirrors API_CONTRACT.md §1/§4/§6 as pydantic models with `extra="forbid"`, so
Backend/Ai-ml-1 drift fails loudly at the boundary instead of being silently dropped.
**It is a mirror, not a source** — change `API_CONTRACT.md` first, propagate to all four folders in
the same commit, and tell the Backend owner.

| Endpoint | State |
|---|---|
| `POST /internal/decide` | implemented, warm p95 6.6 ms over HTTP |
| `POST /internal/learn` | implemented; consumes the Backend's reward, never recomputes it |
| `POST /internal/train`, `GET /internal/train/{job_id}/status` | implemented, async; `detail.phase` is `training` then `evaluating` |
| `GET /internal/models`, `/models/{id}`, `POST /models/{id}/activate`, `/evaluate` | implemented |
| `GET /internal/health` | implemented |
| `POST /internal/reset` | **added** — clears online-learning sessions on simulation reset |

`/internal/reset` is not in the contract. It is needed because this service keeps a per-simulation
online-learning session (the bandit's per-band estimates build up over a run and must survive
between `/internal/decide` calls), and those need clearing when the Backend resets a simulation.
**This needs adding to `API_CONTRACT.md` in all four folders, or dropping.** Flagging rather than
assuming — it is the Backend owner's call. Nothing else here departs from the contract.

`tests/fixtures/state_vector.json` was captured from a real environment run, so contract tests
exercise the shape the Backend will actually send.

### The Ai-ml-2 boundary

This service **never** computes periodicity and never calls Ai-ml-2. `periodicity_phase` and
`periodicity_confidence` arrive already merged into the StateVector by the Backend's `StateBuilder`.

`ml/features/periodicity_provider.py` does contain a `LocalPeriodicityProvider`, and it is marked
**TRAINING-ONLY** and unreachable from `ml/api/`. It exists because standalone training has no
Backend and no Ai-ml-2 in the loop: with those two features pinned at zero for every training
episode, the agent would learn they carry no signal and then ignore them at inference, when they
suddenly do — quietly defeating PRD Definition-of-Done item 8. If periodicity estimation needs
improving, improve it in Ai-ml-2.

---

## Scenarios

`ml/experiments/scenario_{a..g}.yaml`, transcribed from PRD Section 13 (bands / emitters / duration
/ mix / ≥20 episodes). Scenario G adds behavior-class churn via `emitter_params`.

---

## The gated DQN/PPO path

Built, verified, and off by default. `scripts/train_agent.py --algo dqn` refuses without `--force`
and prints the gate. SB3 trains against the *same* `EWEnvironment`, so a DQN result is comparable to
a bandit result by construction.

At 6,000 timesteps DQN scores Pd 0.144 against the bandit's 0.242 — which is the PRD's own argument
for the ladder (Section 26: "DQN as MVP — longer training, GPU dependency, low interpretability").
Deep RL needs far more training to pay off here.

One structural difference: SB3 learns from its own rollouts, so `/internal/learn` cannot feed it
transitions one at a time. `Agent.learn` is a no-op for these agents and they are served read-only
after offline training — which is why switching policy needs no Backend change.

---

## Turing replay (optional, off by default)

`ml/data/turing_replay.py` binds the Alan Turing Institute's synthetic radar dataset to the
environment as an alternative ground-truth source.

Two practical facts that shaped the code, and that differ from how the dataset is usually described:
the repo is **gated** (needs `HF_TOKEN` from an account that has accepted the terms), and it ships
as **~2,750 raw HDF5 files**, not a tabular dataset — so `load_dataset(..., streaming=True)` does
not give you named columns. The working path is `hf_hub_download` on individual `.h5` files plus
`h5py`, with field names discovered at runtime since the schema is not ours to pin.

`build_replay_ground_truth` bins PDW centre frequencies into N bands and quantises time-of-arrival
into simulation steps, producing exactly the `(T, N)` occupancy table `GroundTruth` already speaks:

```bash
HF_TOKEN=... python -c "from ml.data.turing_replay import load_replay_scenario; e=load_replay_scenario(); e.reset(); print(e.ground_truth.summary())"
```

Every agent, metric and endpoint works unchanged — only the ground-truth source is swapped. The
pure transforms are tested offline with synthetic PDWs; the download test is marked `turing` and
skips without a token.

PRD Section 25 assumes synthetic-only data, so this stays an explicitly-labelled extension. Nothing
in the training or evaluation path imports it.

---

## Deployment

`Dockerfile` and `docker-compose.ml-scheduler.yml` — port 8500 per §7, non-root user, healthcheck
on `/internal/health`, checkpoints on a named volume shared with the Backend
(`ML_CHECKPOINT_DIR`).
