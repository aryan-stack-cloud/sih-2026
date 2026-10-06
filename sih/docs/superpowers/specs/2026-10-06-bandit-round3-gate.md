# Bandit round 3: priority-aware repair of the r2a_f HPDR loss — pre-registered procedure and gate

Status: **pre-registered**. Committed before any V2 (24000–24019) or C2 (22000–22019) run.
Tuning seeds T (20000–20019) may be looked at; V2 and C2 have never been used.

## Why round 3

Round 2 (`2026-10-05-efficiency-round2-gate.md`) validated three Bandit finalists on V
(23000–23019). The strongest, `r2a_f` (poly_degree 2, align_window, phase_fourier),
passed efficiency (mean ratio 1.42/1.30 at 80/160 steps, B 1.52/1.46) and coverage,
but failed G3: full-length mean HPDR difference −2.13 pp [95%: −3.80, −0.64],
guard requires lower end ≥ −2.0 pp. `b_poly2` and `b_blr40_al` failed G1 and G3.

Diagnosis: `r2a_f` uses poly_degree 2 over the first 5 band features only
(time_since_last_scan, ewma, consecutive_misses, phase, confidence). Feature 5,
`band_priority_weight`, enters only linearly, so the policy cannot express
"high priority AND likely active" interactions. HP emitters (priority > 1.0) are
rare; an efficiency-tuned camping policy neglects them on long runs, which is
exactly where the HPDR loss appears (short-horizon HPDR was +6.6/+4.0 pp).

Owner request (6 Oct 2026): "Improve the Bandit model itself, validate efficiency,
detection and coverage through a sandbox Backend, and activate it only after it
passes. Tell me before each live-stack step."

## Rulings (each with the cost if it is wrong)

| # | Ruling | Cost if wrong |
|---|---|---|
| S1 | Same metric as rounds 1–2: listening efficiency = useful scans / total scans; "+20%" is relative (new / reference ≥ 1.20). Horizons 80/160 for the claim, 400/full for no-regression. | If the owner meant another metric the headline misleads; Pd, HPDR, bursts reported alongside. |
| S2 | Reference = today's live Bandit (unchanged since `ee2ee6f`, active `model_bandit_0496bb32` on B). | A claim vs any other reference overstates the user-visible gain. |
| S3 | Round-3 tolerances = round-2 tolerances (Pd −1 pp, HPDR −2 pp, bursts −3 pp, full-length ratio 0.97 at lower bound). They permit small losses; they do not prove equality. | If the owner wants strict zero-loss, a neutral candidate can still fail. |
| S4 | V2 = seeds 24000–24019 (fresh, never observed). V (23000–23019) is tainted and never reused as validation. C2 = 22000–22019 remains the single confirmation. | Reusing V would overstate confidence; using fresh V2 costs one more 2800-episode run. |
| S5 | Sandbox Backend validation is required in addition to offline Python: paired worlds through a sandbox engine over HTTP (`/internal/decide` + `/internal/learn`, learn=True, explore=False, fresh agent per world) on ports that never touch the live stack (engine :8501, backend :8081). | Offline-only validation previously missed serving-path effects (cf. served-session fix `17cb1f5`, torch nondeterminism). Skipping it risks another silent mismatch. |

## Seed sets

| Set | Seeds | Worlds per scenario | Use |
|---|---|---|---|
| T (tuning) | 20000–20019 | 20 | screening of the fixed pool below; free to look at |
| V2 (validation) | 24000–24019 | 20 | gate run for finalists; never used before this file |
| C2 (reserve) | 22000–22019 | 20 | single confirmation of the chosen model; never used before |
| V (tainted) | 23000–23019 | 20 | round-2 validation; must not be used for selection or validation in round 3 |

Training seeds are the registry's own (1042 upward), disjoint from T, V, V2, C2.

## Arms

Every arm runs like a fresh Backend simulation: serving periodicity estimator,
`learn=True, explore=False`, one fresh agent per world, same worlds per arm (paired);
horizons 80, 160, 400, full (2000–3000).

* `sweep`: fixed round-robin sweep (stride K).
* `bandit today`: the live registry's Bandit models.
* candidates: fixed pool below (backbone = `r2a_f`: poly_degree 2, align_window true,
  phase_fourier true; each adds priority expressiveness and/or a coverage protector).

## Fixed candidate pool (round 3)

| Label | Adds to `r2a_f` backbone | Rationale |
|---|---|---|
| `r3_p6` | `poly_features: 6` (quadratics include priority) | priority × activity interactions |
| `r3_p6_c1` | `poly_features: 6` + `cov_beta: 1.0` | + training-time staleness reward |
| `r3_p6_k06` | `poly_features: 6` + `age_bonus: 0.06` | + decision-time staleness nudge |
| `r3_p6_c1_k06` | `poly_features: 6` + `cov_beta: 1.0` + `age_bonus: 0.06` | both protectors |
| `r3_c1` | `cov_beta: 1.0` (poly stays 5) | isolates shaping effect |
| `r3_p7_c1` | `poly_features: 7` + `cov_beta: 1.0` | priority + tuning-cost interactions |
| `r3_p6_c2` | `poly_features: 6` + `cov_beta: 2.0` | stronger shaping if 1.0 under-protects |

All trained 20 episodes on seeds 1042–1061 per scenario (same as round 2), default
epsilon schedule, learning_rate 0.05, bias_learning_rate 0.05, reward_scale 10.0,
optimistic_init 0.5. No other options change. Pool is fixed at pre-registration;
no labels may be added after seeing V2.

## Selection (on T only)

Predicted-pass rule (same form as round 2, point estimates on T):
R80, R160 ≥ 1.25; B ratio at 80 and 160 ≥ 1.25; R400 ≥ 1.05; Rfull ≥ 1.014;
dPd ≥ 0.0 pp, dHPDR ≥ +0.7 pp, dBursts ≥ −1.5 pp at 80/160/400/full;
no scenario cell at 80/160/400 below 0.95.
Violation = sum of normalised shortfalls (scales: 0.05, 0.05, 0.03, 0.02, 0.5, 1.0, 0.75, 0.05).
**Finalists = up to two candidates with the lowest violation** (ties: larger
min(R80, R160)). If none is within 1.0 of zero violation, no finalist advances and
round 3 stops with a negative screening report.

## Gate (on V2; same procedure once on C2 for the chosen model)

Paired bootstrap, 4000 resamples, 95%, seed 20261003, worlds resampled independently
per scenario; "lower end" = 2.5% point.

| # | Check | Passes when |
|---|---|---|
| G1 | efficiency at live horizons | lower end of mean-over-scenarios ratio ≥ 1.20 at 80 and 160 |
| G1b | efficiency on Scenario B (Dashboard default) | lower end of B ratio ≥ 1.20 at 80 and 160 |
| G2 | no loss on longer runs | lower end ≥ 1.00 at 400 and ≥ 0.97 at full |
| G3 | detection | lower end of mean diff (new − today) Pd ≥ −1.0 pp and HPDR ≥ −2.0 pp at 80/160/400/full |
| G4 | no hidden regression | every scenario at 80/160/400: upper end of ratio ≥ 0.95 |
| G5 | coverage (distinct bursts) | lower end of mean diff ≥ −3.0 pp at all horizons; no scenario cell upper end below −10 pp |

PASS = every check. Among finalists passing on V2, the one with larger min(R80, R160)
is chosen; it is ported via `train_all.py` into a sandbox registry, checked for
prototype/engine parity, evaluated once on C2, and additionally validated through the
sandbox engine over HTTP on paired V2 worlds (Scenario B + one 32-band scenario,
80/160 steps, serving path, 0 fallbacks required). If none passes, no C2 run is made
and the report says so.

## Live activation (only after a C2 + sandbox PASS)

Each step announced before running: (1) backup live registry; (2) merge round-3
branch `--no-ff` (only if engine code changed; recipe-only changes need no merge);
(3) import the confirmed model into the live registry and activate Scenario B
(plus scenarios the gate covers); (4) restart the live engine :8500; (5) paired
live Backend check + Dashboard check + latency probe. Rollback: stop engine,
restore registry backup, revert merge, restart engine.
