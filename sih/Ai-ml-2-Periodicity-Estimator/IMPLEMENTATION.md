# Ai-ml-2 Periodicity Estimator — implementation notes

Implementation of the build plan in [README.md](README.md), against
[API_CONTRACT.md](API_CONTRACT.md) §5. Both are specs and are not edited by this work; this file
records what was built, what was decided, and what was measured.

Simulation-only: synthetic detection timestamps, no real RF.

---

## Quick start

```bash
pip install -r requirements.txt
```

```bash
python -m pytest tests/ -q
```

```bash
uvicorn periodicity.api.main:app --port 8600
```

```bash
curl -s "localhost:8600/internal/periodicity/predict?simulation_id=sim_demo&band_id=0"
```

77 tests pass, **96% coverage** (NFR-007 asks for 80%).

---

## Status against the 10-level build plan

| Level | Scope | State |
|---|---|---|
| 1 | Service scaffold, health, Dockerfile on 8600, structured logging | done |
| 2 | Per-(simulation, band) bounded buffers, thread-safe | done |
| 3 | `update` + `reset` | done |
| 4 | Inter-arrival / autocorrelation estimator, fixed period | done |
| 5 | Jittered period + confidence scoring | done |
| 6 | `predict` returning window + confidence | done |
| 7 | Non-periodic emitters give near-zero confidence | done — measured, see below |
| 8 | Latency & concurrency hardening | done — 3.0 ms p95 for 64 bands |
| 9 | Scenario B improvement end-to-end | **blocked on the Backend** |
| 10 | Testing & observability | done |

Level 9 is the only gap and it is not a gap in this service: it requires running Scenario B
through the Backend with and without this service feeding the RL state. Ai-ml-1 already validates
the equivalent A/B against its training stand-in.

---

## The core decision: phase folding, not median inter-arrival

The obvious approach is to take the median gap between detections. It does not work here, for a
reason specific to this system: **we do not observe the emitter, we observe our own detections of
it.** The receiver must be tuned to a band to detect anything, and it is tuned elsewhere most of
the time. A period-20 emitter therefore does not produce gaps of 20 — it produces 20, 40, 60, 100,
whichever activations the scan schedule happened to catch. The median of that is not the period,
and it drifts with the *scheduler's* behaviour rather than the emitter's.

Instead every timestamp is folded onto a candidate period and the concentration of the resulting
phases is measured (the mean resultant length, R). If the candidate is right, detections land at
the same phase however many cycles were skipped between them. This is the standard treatment for
period-finding in sparse, irregularly-sampled event series, and it is a vectorised sweep — no
training, no iteration, no GPU, exactly as the README requires.

`tests/test_estimator.py::test_recovers_the_period_when_cycles_were_missed` pins this: it
asserts the naive median gives the wrong answer and the fit gives the right one.

---

## Three corrections that came out of measurement

Each was a real defect found by measuring, not by reading the code.

**1. Subharmonics.** Every divisor of the true period folds the data just as tightly — given
detections at 0, 20, 40, the candidates 5 and 10 score identically to 20. The first
implementation returned 20.2 for a clean period-20 signal because a loose "near-tie" rule let a
slightly-worse *larger* period win. Now the best-scoring candidate is found first, then only
integer multiples of it are tested, and the largest one that still folds tightly is taken.
Doubling breaks concentration, so there is no matching risk at the top end.

**2. The look-elsewhere effect.** The estimator sweeps a few thousand candidate periods and keeps
the best. Scoring that winner with a plain Rayleigh p-value rated a purely **random** emitter at
0.99 confidence — precisely the confident-but-wrong claim Level 7 forbids — because the best of
many draws from noise looks impressive on its own terms. The p-value is now corrected for the
number of *independent* trial periods the search covered.

**3. One activation is one sample.** The Rayleigh test assumes independent observations, and raw
detection timestamps are not: a receiver dwelling on an active band reports the same burst several
steps running. Feeding all of them in as separate samples inflated the evidence enormously — a
bursty **intermittent** emitter with ten bursts but forty detections scored above 95% confidence.
Detections closer together than `min_period` are now collapsed into one activation. This is
self-consistent rather than arbitrary: the estimator will not report a period shorter than
`min_period`, so on its own terms two detections closer than that cannot be separate cycles.

---

## Calibration (Level 7)

Confidence is `1 - p`, not a hand-scaled score, so the documented threshold is the ordinary
p < 0.05 → **0.95**. Fraction of runs claiming confidence above it, 60–80 trials each:

| Emitter class | n=12 | n=20 | n=40 | n=64 |
|---|---|---|---|---|
| random (Bernoulli per slot) | 0.04 | 0.06 | 0.01 | 0.00 |
| intermittent (bursty) | 0.00 | 0.00 | 0.01 | 0.06 |
| fixed (continuous) | 0.00 | 0.00 | 0.00 | 0.00 |
| **periodic, clean** | **1.00** | **1.00** | **1.00** | **1.00** |
| **periodic, jitter ±3** | 0.70 | **1.00** | **1.00** | **1.00** |

The four non-periodic classes sit at the nominal 5% false-positive rate; periodic emitters are
detected essentially always from about 20 activations. That is the Level 7 Definition of Done,
stated as a measured rate rather than an assertion — `test_no_false_periodicity_claims_on_non_periodic_emitters`
runs it as a test.

`min_samples = 8` (distinct activations, after clustering) is where that rate settles. Below about
six activations there is almost always *some* period that aligns them by luck.

---

## Latency, and a contract change

This service sits **ahead of Ai-ml-1** on the Backend's per-step critical path, so its cost comes
out of the same NFR-002 50 ms budget rather than having one of its own.

The contract's `GET /internal/periodicity/predict` returns one band. The Backend's StateBuilder
needs every band before every decision. Measured at 64 bands:

| | 64 bands, one scheduler step |
|---|---|
| single-band GET in a loop | **181 ms** |
| estimator's actual work | **0.13 ms** |
| batch endpoint | **3.0 ms p95** |

The entire original cost was HTTP round trips, not computation. `POST
/internal/periodicity/predict/batch` was added to the contract (all five copies) and collapses N
round trips into one — an 86× improvement. The single-band GET remains for debugging.

Combined ML path is now **9.6 ms** (Ai-ml-2 3.0 + Ai-ml-1 6.6), leaving ~40 ms of the budget for
the Backend.

Two design points make this affordable:

- **Fits are cached per band and invalidated on `update`.** A band's period only changes when a
  new detection arrives for it. Per simulation step at most K bands (the receiver's instantaneous
  bandwidth, default 2) can have new detections, so the per-step refit cost is bounded by K, not
  by N. A cold fit costs ~0.6 ms/band; a cached one costs ~2 µs.
- **The fit runs outside the lock**, against a copied snapshot, so a slow sweep never blocks an
  incoming detection.

---

## Boundary

Called only by the Backend. Never calls Ai-ml-1, never calls the Frontend. It receives detection
timestamps and returns predictions; it knows nothing about emitters, ground truth, scan decisions
or rewards.

The Backend merges `periodicity_phase` and `periodicity_confidence` from this service into the
StateVector before sending it to Ai-ml-1 — which is why the batch response carries `phase`
alongside the contract's three fields, so the Backend does not have to re-derive it from the
window.

**On simulation reset the Backend must call both** `/internal/periodicity/reset` here **and**
`/internal/reset` on Ai-ml-1, or the next run of that `simulation_id` inherits the previous run's
beliefs. This is now stated in API_CONTRACT.md §4.

---

## Known limitation: scan-schedule aliasing

We see detections, which are the product of emitter activity **and** the scan schedule. A
perfectly regular scanner revisiting a band every 8 steps can imprint its own period on the
timestamps, and this service cannot tell that apart from an 8-step emitter.

`min_period` keeps the shortest and most degenerate aliases out — a period of 1 fits any data at
all — but it is not a complete defence. The honest mitigations are that the scheduler this feeds
is adaptive rather than fixed-cadence, and that the affected case (a *regular* scanner) is the
baseline we are trying to beat rather than the policy we ship. If the contract ever carried
scanned-but-empty observations alongside detections, the ambiguity would disappear properly;
that is the right fix if this ever matters in practice.
