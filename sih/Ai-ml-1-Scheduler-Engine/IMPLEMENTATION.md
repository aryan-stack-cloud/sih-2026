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

---

# SCT scheduler — Search, Confirm, Track

Implements `docs/superpowers/specs/2026-09-11-sct-scheduler-solution.md` inside this service. The
design argument and its literature are in that document and its companion
`2026-09-11-smart-scan-strategy-design.md`; this section records what was built, what measurement
changed, and what the numbers actually are.

Everything below was written test-first. Four design decisions were rejected by their own tests
and rewritten; all four are recorded here rather than quietly corrected, because each is a mistake
a reader would otherwise make again.

## Why a new policy at all

The contextual bandit passes the MVP gate and loses the problem statement's stated primary
objective. SIH26055 asks to "minimise intercept time and ensure a high interception rate". On
scenario B the bandit reports a run intercept rate of 0.14 against round-robin's 0.41, and an
interception ratio of 0.71 — it never sees 29% of the emitters at all.

That is structural, not a tuning failure. A scalar reward paying per detection buys *density*, so
the policy camps on the busiest bands. Intercept time and interception ratio are **coverage**
objectives with deadline structure, and the `w5_redundant` sweep above walks that Pareto frontier
monotonically, which is the proof that no weight buys both.

So coverage stops being a penalty term and becomes a constraint.

## What was added

| Module | Purpose |
|---|---|
| `ml/scheduling/deadlines.py` | Revisit deadlines derived from intercept-time theory, the staleness barrier, the hard override, and the receiver-sizing feasibility check |
| `ml/belief/occupancy.py` | Two-state occupancy belief with the imperfect-sensing POMDP update, plus information gain |
| `ml/belief/kernel_learning.py` | Per-band transition kernels learned from hits and misses, with the detector's ROC undone |
| `ml/environments/detection_model.py` | Energy-detector ROC, and the dwell-length decision as a value rate |
| `ml/scheduling/sync_guard.py` | Three-distance-theorem lockout test, continued-fraction diagnosis, noble-ratio revisit selection |
| `ml/scheduling/index_policy.py` | The index, its named-term breakdown, window selection, deadline override |
| `ml/agents/index_agent.py` | `policy_type: "index"` — the above, wired, plus floor mixing and the slow loop |
| `ml/agents/ctmc_floor.py` | `policy_type: "ctmc"` — the randomised floor, and baseline arm B4 |
| `ml/evaluation/phase_sweep.py` | Phase-independent probability of intercept, by cross-correlation |
| `ml/tuning/objective.py` | What "better" means, as a score against round-robin on identical seeds |
| `ml/agents/base.py`, `ml/evaluation/runner.py` | `observe()` hook: hits and misses, not a scalar reward |
| `scripts/coverage_frontier.py` | Walks the coverage-versus-value dial so the operating point is a documented trade |
| `scripts/phase_sweep.py` | Phase-independent PI per policy, including the min-max worst case |
| `scripts/tune_index.py` | Differential-evolution search over the six index scalars, validated on hold-out seeds |
| `scripts/sync_trap_demo.py` | The synchronisation trap, three policies side by side |

Contract changes are additive and are in all five copies of `API_CONTRACT.md`: `policy_type` gains
`index` and `ctmc`, `StateVector.bands[]` gains five optional fields, `DecideResponse` gains an
optional `index_breakdown`. `exclude_none` on the decide response keeps it byte-identical for every
policy that produces no breakdown, which is what makes "additive" true rather than merely intended.

## Six things measurement rejected

**1. The deadline term belonged inside the division, not after it.** The first draft added the
staleness barrier to the rate, reasoning that a constraint multiplier is not value. But the value
terms carry units of "per second" and a bare barrier is dimensionless, so the barrier only outbid
value in the last few percent before the deadline — far too late to drain a queue of stale bands
through a receiver that serves one at a time. Staleness overran a 29-slot deadline by ten slots.
Dividing it too makes the whole index one rate; the barrier starts winning at about 40% of the
deadline and coverage stays ahead. It still dominates any finite value, because it diverges.

**2. A bounded zero-mean dither cannot break a synchronisation lockout.** The spec proposed
dithering the revisit *interval* with a golden Kronecker sequence. The partial sums of a centred
low-discrepancy sequence stay O(log n), so the accumulated timing perturbation never reaches a full
emitter period: 200 dithered looks against a two-second emitter at a one-second revisit left 42% of
the phase circle uncovered. Breaking a lockout means moving the **ratio** onto a noble number,
which is what `golden_revisit` does. The negative result is a test so it is not "fixed" back.

**3. The agent has to know which receiver it is driving.** The first end-to-end comparison ran the
index with library-default receiver parameters against a scenario that specifies its own, so the
Bayesian update used a false-alarm rate two orders of magnitude too small and a wrong `P_d`. A
belief updated through the wrong ROC is confidently wrong, and the value term went flat — the index
scored within 2% of round-robin on everything. `IndexAgent.from_scenario` derives `P_d`, `P_fa`,
bandwidth, slot and retune from the scenario's receiver block. That one change took Pd from +2% to
+43% over baseline.

**4. A fixed transition kernel was costing about half the achievable gain.** With `p01` and `p10`
frozen at a prior nobody had measured, an unobserved band drifted toward the wrong stationary
value. Learning them per band moved scenario B from "+11.5% Pd for −0.9% run intercept rate" to
"+21.2% Pd for +0.7%" — from a trade into a clean win. The estimator has to undo the detector's own
ROC to do it: on this receiver a raw count of detections over looks is biased upward by a 6.7%
false-alarm rate and downward by a 16% miss rate, and both errors are large enough to matter.

**5. The randomised floor was switched off during every evaluation.** It was gated on the same
flag that disables epsilon-greedy exploration, which is right for a value-learning agent and wrong
here: the floor is not exploration, it is the structural guarantee that bounds worst-case behaviour
against an emitter no model predicts. Every scenario number measured before this fix described a
policy carrying no such bound. In the synchronisation trap it was the difference between
intercepting the emitter and reporting a flawless sweep at exactly zero detection.

**6. "Characterised" meant the wrong thing, twice.** The floor's share of the receiver's time is
the fraction of the spectrum still uncharacterised, so that definition decides how much of every
episode is spent on uninformed random search. Defining it as *mean* periodicity confidence left the
floor taking 61% of every episode for ever, because that mean plateaued at 0.22. Defining it per
band was worse, at 72 to 89%. The reason is the interesting part: periodicity confidence only rises
for cleanly periodic emitters, so a band holding a random emitter never earns it and an *empty*
band never earns it either -- though an empty band is the most thoroughly characterised thing in
the spectrum. Scoring empty bands as unknown sent the floor's looks to the one place with nothing
to find. Characterisation is now evidence-based, so watching a band is what retires it, and the
floor settles at its 10% minimum after a few hundred steps.

A seventh, smaller one: the index ignored `periodicity_phase` and `periodicity_confidence` entirely,
which are the features scenario B exists to reward. `effective_belief` now fuses them into the
occupancy belief, confidence-weighted. Phase is circular, so due-ness is `0.5 (1 + cos 2πφ)` — the
emitter is on us near phase 0 *and* near phase 1, not only at the top of the cycle.

## Results

**Every number below is measured on hold-out seeds** -- episodes 8 through 13 of each scenario,
which took no part in choosing any setting. That distinction is not pedantry here. Two claims
made earlier in this work survived selection seeds and failed hold-out, and both were reported
before the check rather than after.

Scenario B, 20 evaluation seeds for the bandit column, 6 hold-out seeds for the rest, 2000 steps,
identical spectrum per seed. `index` runs at the shipped defaults.

| Metric | round-robin | bandit | **index** | ctmc floor |
|---|---|---|---|---|
| Pd | 0.1092 | **0.3375** | 0.1334 | 0.1043 |
| HPDR | 0.1162 | **0.2875** | 0.1381 | 0.1008 |
| Scan efficiency | 0.1953 | **0.5470** | 0.2376 | 0.1876 |
| Interception ratio | 0.9667 | 0.7100 | 0.9667 | 0.9850 |
| Run intercept rate | **0.3994** | 0.1409 | 0.3814 | 0.3470 |
| AIT censored | **1202** | 1718 | 1238 | 1307 |

### The trade, stated plainly

Across four scenarios at budget 0.50, percentages against round-robin on hold-out seeds:

| Scenario | Pd | HPDR | Scan eff | Interception ratio | Run intercept | AIT censored |
|---|---|---|---|---|---|---|
| A — Mostly Fixed | +20.1% | +20.9% | +19.6% | **+5.5%** | −5.1% | −9.5% |
| B — Mostly Periodic | +22.2% | +18.8% | +21.7% | 0.0% | −4.5% | −3.0% |
| C — Frequency-Agile | +2.9% | **−6.0%** | +2.2% | **+2.9%** | −12.1% | −6.9% |
| D — Mixed Environment | +20.6% | +24.2% | +20.4% | 0.0% | 0.0% | 0.0% |

**The index buys detection with run coverage.** It is not a dominance and earlier drafts of this
document claimed one. Detection rises 3 to 22%, scan efficiency 2 to 22%, and emitter reach never
falls. Run intercept rate falls by up to 12%.

For scale: the contextual bandit's trade on the same problem is +214% detection for −66% run
intercept rate and −26% interception ratio, which is a different part of the frontier entirely.

Scenario C is the weak case and the reason is the theory rather than a defect. Frequency-agile
emitters have no learnable phase structure, so the index has nothing to exploit and pays the
coverage cost anyway. Clarkson & Pollington predict exactly this, and it is worth saying so rather
than burying a negative HPDR in an average.

### Why run intercept rate cannot be held

Held-out measurement at budgets 0.8, 0.7, 0.6 and 0.5 shows round-robin ahead on run intercept rate
in every scenario at every budget, and looser budgets make it *worse* rather than better.

That is not a tuning failure. Run intercept rate rewards catching the *start* of an activation run,
which a perfectly uniform sweep maximises by construction, so any deviation to chase value costs
it. It is the metric round-robin was born to win.

This is why the tuning objective's veto is interception ratio alone. A constraint no non-trivial
policy can satisfy encodes the baseline, not an operating intent. Run intercept rate and censored
intercept time stay inside the weighted sum at five to one against gains.

### Choosing the coverage budget

`COVERAGE_BUDGET` is the fraction of receiver time the guaranteed coverage cycle may consume.
`scripts/coverage_frontier.py` walks it. Above 0.5 the deadline is tight enough that the override
fires constantly and drags the schedule toward a fixed rotation, costing detection *and* coverage.
Below 0.4 the policy starts buying detection with coverage in the direction the bandit takes far
too far. 0.5 is the best measured compromise and remains a mission parameter rather than a
constant.

### The synchronisation trap

The one scenario where the difference is categorical rather than incremental.
`python scripts/sync_trap_demo.py`, four seeds:

| Policy | Pd | Emitters intercepted | AIT censored |
|---|---|---|---|
| round-robin sweep | 0.000 | 0.000 | 800.0 |
| randomised floor | 0.150 | 1.000 | 680.0 |
| index | 0.080 | 1.000 | 736.0 |

An 8-band sweep visits band b when `t mod 8 == b`; an emitter in band 5 illuminating one step in
eight at phase 3 is visible only when `t mod 8 == 3`. The two never meet. The sweep is not slow
here, it is blind, and it cannot tell that from an empty band. Both other policies escape.

Pure random beats the index on this scenario, which is Clarkson & Pollington in measurement rather
than in a citation: one emitter with unknown parameters is exactly the regime their theorem covers.
The index's claim here is narrow and it is the right one -- the floor is what keeps it out of the
lockout.

### A bootstrapping threshold, and where it points

Detection on the trap ranges from 0.08 to 1.00 across deadline settings. Tracing it:

| Deadline | Periodicity locks on at | Detections in 800 steps | Pd |
|---|---|---|---|
| 133 ms | step 43 | 100 | 1.000 |
| 160 ms | never | 13 | 0.080 |
| 200 ms | step 435 | 12 | 0.130 |
| 267 ms | step 635 | 19 | 0.230 |

The outcome turns on whether the first few detections arrive close enough together for the
periodicity estimator to fit a period at all. Once it locks on, tracking is genuine and catches
every activation.

**This is a measured argument for the Ai-ml-2 upgrade in solution spec Section 3.2.** The training
stand-in fits a median inter-arrival over detections alone and needs four with consistent gaps;
thirteen scattered detections in 800 steps cannot produce that. The specified estimator evaluates a
likelihood over hits *and misses*, which fits from far sparser evidence -- exactly this regime.

The trigger dither (`ml/scheduling/deadlines.py`) narrows the spread from 12.5x to 8.3x and cannot
close it, because the dominant factor is the estimator rather than the schedule's own periodicity.
It is kept because it is correct on its own terms and costs nothing, and the test says plainly that
it is not the mechanism behind this scenario.

### Tuning

`scripts/tune_index.py` optimises the six index scalars with differential evolution against the
objective in `ml/tuning/objective.py`, which compares to round-robin on identical seeds. **Nothing
optimises a proxy reward.**

The search never scores itself. Its first run reported +1.84 against a +0.41 default on its own
three search seeds; on eight hold-out seeds the same configuration scored +0.53, and the gap was
the fit. Every reported number now comes from seeds the search never saw, and a configuration that
does not beat the shipped defaults there is rejected with a message saying so.

## What is not built yet

Named so the gaps are not mistaken for oversights.

The **threat classifier** is the largest. The index currently reads the operator-set
`band_priority_weight` where the design calls for a threat score learned from emitter character.
That is blocked on the environment rather than on effort: it emits band occupancy, not pulse
descriptor words, so there are no PRI, pulse-width or angle-of-arrival features to classify. It
needs either a richer environment or the Turing replay path.

Also outstanding: per-band SNR estimation, the GA offline oracle (baseline arm B5), and the six
purpose-built scenarios of solution spec Section 11.3. The sync guard is implemented and tested but
not yet wired into the agent's revisit planning, because that needs a period estimate the contract
does not carry; the randomised floor supplies the aperiodicity in the meantime and needs no period
estimate at all.
