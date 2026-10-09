# B-only Bandit study: ship draw4's Scenario B gain — pre-registered gate

Status: **pre-registered**. Committed before any V3 (25000–25019) or C3 (26000–26019) run.
Base: `feat/bandit-retrain-study` tip. No engine code changes; the candidate is existing
weights, frozen below.

## Motivation

The retraining study's draw4 (default recipe, agent RNG seed 5004) confirmed on the
spent reserve C2, Scenario B: efficiency 1.255 [1.120, 1.405] at 80 steps and 1.267
[1.178, 1.367] at 160 steps vs the live B checkpoint, detection and coverage guards
passing — while mean-over-scenarios missed the full gate by 0.001–0.02. The registry
serves per-scenario models (`ModelRegistry.resolve` prefers the newest same-scenario
model), and Scenario B is the Dashboard default the owner looks at. This study asks the
narrow question: does draw4 beat live **on B** on fresh worlds, without B-local
regression? One validation (V3) plus one confirmation (C3), both pre-registered here.

This is not testing-until-pass: the candidate, gate, seeds, and single-confirmation
rule are fixed here, before any V3/C3 world is observed. V2 selected the draw, C2
confirmed B at +25% twice consistently (V2 B80 1.173 → C2 B80 1.255); V3/C3 test whether
it replicates a third/fourth time under a binding gate.

## Rulings (each with the cost if it is wrong)

| # | Ruling | Cost if wrong |
|---|---|---|
| S1 | Candidate = draw4's EXACT Scenario B weights (SHA-256 frozen below, saved at `C:\w\r3\agents\draw4\B.npz`). No retraining, no tuning — the artifact that already confirmed twice. | If the file corrupts, the hash check catches it; re-running needs a new study, not a quiet re-train. |
| S2 | Scope is Scenario B ONLY. Other scenarios keep their live models; activation impact is B-confined (see S4). | A B-only win says nothing about A/C–G; claiming more would need the full gate draw4 already failed. |
| S3 | Bar is 1.15 at 80/160 (not 1.10): the claimed effect is ~1.26, so a real effect clears 1.15 with margin; a lucky draw does not clear it twice more. | If the true effect is 1.10–1.15, this gate fails a useful model; that conservatism is the price of two prior failures. |
| S4 | Activation is per-algorithm BUT resolve is per-scenario: registering draw4-B and activating it deactivates `model_bandit_0496bb32` (today's only active Bandit, also B) and draw4-B becomes B's server as newest-active same-scenario model. All other scenarios keep resolving to their current newest same-scenario models — verified, not assumed, before announcing activation complete. | If resolve preferred otherwise, other scenarios could shift servers; the verification step catches it and triggers rollback. |
| S5 | C3 (26000–26019) is fresh reserve for this study only: exactly ONE confirmation run. A fail ends the study; no re-confirmation, no V4. | Re-spending reserve until a pass would manufacture significance. |

## Frozen candidate

- File: `C:\w\r3\agents\draw4\B.npz` (default recipe, 20 episodes on seeds 1042–1061, agent RNG 5004)
- SHA-256: `4cd0fd9497d406ed7bce407e1fddcb3b851fa88ccfe50457499c0b9c05734cf8`
- Reference: live `model_bandit_0496bb32` (read-only)

## Arms and procedure (V3; identical once on C3)

Scenario B only, horizons 80/160/400/full (2000 steps), 20 paired worlds, fresh session
(deepcopy of weights) per world, `learn=True, explore=False`, serving estimator.
Bootstrap: 4000 resamples, 95%, seed 20261003, worlds resampled (single scenario).

## B-only gate (on V3; same procedure once on C3)

| # | Check | Passes when (lower = 2.5% point) |
|---|---|---|
| B1 | B efficiency at live horizons | lower end of B80 AND B160 ratios ≥ 1.15 |
| B2 | no B long-run regression | lower end ≥ 1.00 at B400 and ≥ 0.97 at Bfull |
| B3 | B detection | lower ends Pd ≥ −1.0 pp, HPDR ≥ −2.0 pp at 80/160/400/full |
| B4 | B coverage | lower ends distinct bursts ≥ −3.0 pp at all horizons |

## Outcome: FAIL on V3 (6 October 2026)

V3 (25000–25019): B80 1.178 [1.088, 1.284], B160 1.143 [1.039, 1.255] → B1 FAIL;
B2 PASS; B3 FAIL (HPDR-full −2.34 [−8.11, +2.42]); B4 FAIL (bursts −3.0 to −3.6,
lowers −5.0 to −5.8). Per the single-confirmation rule there is NO C3 run — C3
(26000–26019) stays pristine. No sandbox, no live steps. Details in
`2026-10-06-bandit-b-only-results/b_v3_gate.md`. The B-effect replicated in direction
a third time but not at gate strength, and B-local burst losses are a genuine cost.

PASS = every check. V3 PASS → one C3 confirmation. C3 PASS → sandbox serving check
(register frozen weights into sandbox registry, parity-hash vs frozen SHA, paired
B experiments at 80/160 through sandbox engine :8501 + sandbox Backend :8081 with 0
fallbacks and offline-matching decisions) → live activation, each step announced
before running: (1) backup live registry; (2) import draw4-B into live registry;
(3) activate draw4-B, verify per-scenario resolution unchanged outside B; (4) restart
live engine :8500; (5) paired live B check + Dashboard check + latency probe.
Rollback: stop engine, restore registry backup, re-activate `model_bandit_0496bb32`,
restart engine.
