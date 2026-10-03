# Engine changes: per-scenario Index budget, Bandit window scoring, threat-aware mode

Status: approved by the project owner on 3 Oct 2026 ("do both a and b"). Evidence: the project review
`project-review-2026-10-03` (Traycer artifact), sections 2.3, 2.8 and 2.9.

## Problem

The 3 Oct review measured three engine-level gaps with paired experiments (20 fresh worlds per
scenario, seeds 3000-3019):

1. **Index runs with an untuned patience setting.** Index forces a revisit of any band left unvisited
   for `cycle / coverage_budget`. `IndexAgent.from_scenario` hard-codes `coverage_budget = 0.5` (a
   21-step deadline on Scenario B). `ml/configs/index_tuned_B.json` holds a tuned 0.2184 (48 steps)
   that `scripts/train_all.py` never passes on. The tuned value raises Pd by 2.1 to 8.2 pp and scan
   efficiency by 9 to 15 pp over the served one on all seven scenarios, but it costs 1.3 to 1.9 pp
   of distinct bursts on A, C, E and G. It was tuned on B only.
2. **The Bandit scores half of what it chooses.** The receiver always covers K=2 adjacent bands, but
   `BanditAgent` values an action from its first band alone and credits the step reward to that band
   alone. Scoring the whole window raised distinct bursts by 9.3 pp on B (A +7.7) with no significant
   loss on the other scenarios.
3. **Threat level is invisible to every policy.** The simulators give each emitter a priority (1.0
   normal, 2.0 high) but report `band_priority_weight = 1.0` for every band, so Index's threat term is
   a constant. A real receiver learns an emitter's threat once it intercepts it. Feeding that back
   (decaying toward 1.0) raised high-priority detection by 5.5 to 9.9 pp for Index on all seven
   scenarios, at a cost of up to 4 pp of distinct bursts. Only Index uses the number; Bandit, Q-learning,
   DQN and PPO ignore it.

## Decisions (binding for the plan)

| # | Decision | Why |
|---|---|---|
| D1 | `IndexAgent.COVERAGE_BUDGET` stays 0.5 in code. Per-scenario budgets live in `ml/configs/index_budgets.json` and are applied by `scripts/train_all.py` when it registers Index. A scenario missing from the file keeps 0.5. | Existing callers and tests keep today's behaviour; only registered models change. |
| D2 | Budgets are chosen by a pre-registered rule on tuning seeds 2000-2009: among candidate budgets whose distinct-burst rate is not below the fixed sweep's (margin 0, matching the promise made to the owner: never below the sweep), take the one with the highest Pd (ties within 0.001 go to the larger budget); if none qualifies, keep 0.5. (Amended before the official tuning run: the first draft allowed a 1 pp margin, which would have let Index fall below the sweep on Scenarios E and G.) | Coverage is the statement's primary objective; Pd is the tie-breaker. |
| D3 | The Bandit gains a `bandwidth_k` hyperparameter (default 1). With K=1 it is bit-for-bit today's agent, so existing checkpoints load unchanged. Training passes the scenario's K. | Backward-compatible; new models carry K in their saved hyperparameters. |
| D4 | Threat-aware mode is **off by default** in every layer. It is a per-simulation and per-experiment boolean (`threatAware` in requests, `threat_aware` in responses). With it off, behaviour is identical to today. | It trades coverage for threat detection, so it must be an explicit, labelled choice. |
| D5 | Observed priority decays toward 1.0 with factor 0.998 per step (half-life about 350 steps). A band's weight becomes the priority of the emitter active on it when a detection occurs. The Java Backend and the Python training environment implement the identical rule. | Matches the tested prototype. |
| D6 | The Python training environment mirrors the rule behind a `threat_aware` flag (default False). Training and serving agree. | Avoids a train/serve mismatch. |

## Confirmation gate (run by the lead before anything merges)

Fresh seeds 4000-4019 (20 worlds per scenario, nobody has used them), paired bootstrap, 95% intervals.
Variants: fixed sweep, Index as served today (budget 0.5), Index with the per-scenario budget, Bandit as
trained today, Bandit with window scoring, Index with the per-scenario budget plus threat-aware mode.

Pass rules, fixed now:

1. Per-scenario Index budget: Pd and scan efficiency are higher than Index at 0.5 on all seven scenarios
   (interval excludes zero), and distinct bursts are never significantly below the fixed sweep.
2. Bandit window scoring: no significant loss of Pd or high-priority detection on any scenario versus
   today's Bandit, and distinct bursts higher on Scenario B.
3. Threat-aware mode: high-priority detection higher on all seven scenarios for Index; |change in Pd|
   at most 1.5 pp; with the flag off, results are identical to the same code without the flag.

An item that fails stays out of the merge. The lead reports numbers either way.

## Out of scope

Thompson sampling arm, Q-learning window scoring, DQN/PPO changes, the Judge view v2 work (separate
branch `feat/judge-view-v2`), editing `API_CONTRACT.md` (the lead updates all five copies).

## Confirmation results (4 Oct 2026)

Run by the lead on a snapshot of the branch, in-process, with an isolated model registry and Ai-ml-2's serving
estimator supplying the periodicity features (the same path the Backend serves). Fresh seeds 4000-4019 (20 worlds
per scenario, never used before), one trained agent per arm, paired bootstrap with 95% intervals (fixed bootstrap
seed 20261003). A star marks an interval that excludes zero. Gains are in percentage points (pp) unless noted;
intercept time is in steps (lower is better).

#### Rule 1: per-scenario Index budget (idx_ship vs idx_today; coverage vs the sweep)

| Scenario | Pd gain (pp) | Scan efficiency gain (pp) | Distinct bursts vs sweep (pp) | Intercept time vs sweep (steps) | Pass |
|---|---|---|---|---|---|
| A | +5.0 [+4.6, +5.5] * | +17.4 [+16.1, +18.5] * | +1.4 [-1.6, +5.0] | -27.8 [-99.6, +31.9] | PASS |
| B | +11.0 [+10.1, +11.9] * | +18.0 [+16.7, +19.3] * | +5.1 [+2.8, +7.1] * | -102.1 [-142.2, -56.1] * | PASS |
| C | +4.0 [+3.8, +4.2] * | +16.3 [+15.5, +17.1] * | -0.9 [-2.9, +1.2] | +16.8 [-23.8, +57.4] | PASS |
| D | +6.2 [+5.5, +7.0] * | +21.2 [+19.0, +23.4] * | +2.6 [+0.4, +4.9] * | -79.1 [-146.6, -11.1] * | PASS |
| E | +2.2 [+2.1, +2.3] * | +14.2 [+13.7, +14.7] * | +1.9 [+0.9, +3.0] * | -57.7 [-89.8, -25.7] * | PASS |
| F | +11.9 [+10.8, +13.0] * | +16.1 [+14.7, +17.6] * | +10.5 [+8.0, +13.0] * | -209.7 [-259.2, -159.6] * | PASS |
| G | +1.2 [+1.0, +1.3] * | +4.5 [+3.9, +5.0] * | +0.2 [-0.9, +1.3] | -6.6 [-38.1, +25.5] | PASS |

#### Rule 2: Bandit window scoring (bandit_ship vs bandit_today)

| Scenario | Pd (pp) | HPDR (pp) | Distinct bursts (pp) | Intercept time (steps) | Pass |
|---|---|---|---|---|---|
| A | -0.1 [-0.8, +0.5] | -4.1 [-8.3, -0.5] * | +5.7 [+2.0, +10.4] * | -114.2 [-207.7, -40.3] * | FAIL |
| B | -0.7 [-2.2, +1.1] | +0.9 [-4.0, +7.3] | +6.4 [-0.5, +14.2] | -128.5 [-283.0, +9.3] | FAIL |
| C | -0.2 [-0.7, +0.3] | -0.8 [-2.6, +0.9] | +4.1 [+2.9, +5.3] * | -82.7 [-105.9, -58.2] * | PASS |
| D | -0.4 [-1.2, +0.4] | -1.7 [-3.1, -0.0] * | +1.1 [-0.2, +2.5] | -34.0 [-74.4, +6.2] | FAIL |
| E | +0.2 [-0.2, +0.5] | -0.6 [-1.6, +0.3] | -0.1 [-1.2, +1.3] | +1.5 [-40.1, +34.8] | PASS |
| F | +1.6 [-1.3, +4.7] | +1.0 [-4.0, +8.4] | -2.0 [-6.5, +3.0] | +40.8 [-60.4, +130.1] | PASS |
| G | +0.4 [-0.1, +1.0] | +1.5 [+0.1, +2.8] * | +0.4 [-0.6, +1.4] | -11.0 [-40.9, +19.4] | PASS |

#### Rule 3: threat-aware mode (idx_ship_threat vs idx_ship)

| Scenario | HPDR (pp) | Pd (pp) | Distinct bursts (pp) | Intercept time (steps) | Pass |
|---|---|---|---|---|---|
| A | +15.5 [+11.4, +20.6] * | +0.6 [-0.1, +1.2] | -8.1 [-12.2, -3.6] * | +163.2 [+71.4, +244.2] * | PASS |
| B | +10.6 [+5.7, +16.3] * | +0.2 [-0.6, +1.1] | +0.5 [-3.0, +4.3] | -9.2 [-85.4, +60.9] | PASS |
| C | +6.0 [+4.1, +7.8] * | -0.2 [-0.4, +0.1] | -1.3 [-2.5, -0.1] * | +25.4 [+1.3, +49.0] * | PASS |
| D | +7.8 [+5.9, +9.9] * | +0.2 [-0.2, +0.5] | -2.2 [-4.3, -0.1] * | +65.9 [+3.4, +127.9] * | PASS |
| E | +5.7 [+4.3, +7.3] * | +0.1 [-0.0, +0.3] | -3.6 [-4.5, -2.7] * | +107.9 [+82.5, +133.6] * | PASS |
| F | +9.0 [+3.5, +16.9] * | +0.3 [-0.5, +1.1] | -0.2 [-2.1, +1.8] | +5.0 [-36.3, +41.6] | PASS |
| G | +4.3 [+3.7, +5.0] * | +0.4 [+0.1, +0.6] * | -0.8 [-1.4, -0.2] * | +25.3 [+5.2, +42.4] * | PASS |

#### Flag off equals no flag (idx_ship_flagoff vs idx_ship, per-episode rows identical)

A: identical, B: identical, C: identical, D: identical, E: identical, F: identical, G: identical

#### What the tuned budget costs against Index as served today (idx_ship minus idx_today)

| Scenario | Distinct bursts: tuned vs today (pp) | Intercept time: tuned vs today (steps) | HPDR: tuned vs today (pp) |
|---|---|---|---|
| A | -2.6 [-4.6, -0.6] * | +52.8 [+12.1, +91.3] * | +6.8 [+4.4, +9.2] * |
| B | -2.2 [-4.8, +0.1] | +44.5 [-1.7, +96.1] | +12.5 [+9.0, +16.5] * |
| C | -4.1 [-5.5, -2.6] * | +82.2 [+51.3, +110.6] * | +4.3 [+2.6, +5.8] * |
| D | -3.5 [-5.2, -1.7] * | +104.2 [+51.9, +156.0] * | +6.0 [+3.8, +8.3] * |
| E | -0.8 [-1.4, -0.2] * | +23.9 [+6.6, +42.3] * | +2.7 [+2.1, +3.4] * |
| F | +3.8 [+2.2, +5.5] * | -76.7 [-110.8, -44.6] * | +14.4 [+8.9, +18.7] * |
| G | -0.4 [-1.0, +0.2] | +11.0 [-5.3, +28.9] | +1.0 [+0.7, +1.3] * |

### Outcome

| Item | Rule | Result | Merge |
|---|---|---|---|
| 1. Per-scenario Index budget | Pd and scan efficiency higher than Index at 0.5 on all seven scenarios; distinct bursts never significantly below the sweep | **PASS** (7 of 7) | in |
| 2. Bandit window scoring | no significant loss of Pd or high-priority detection; distinct bursts higher on B | **FAIL**: high-priority detection fell on A (-4.1 pp) and D (-1.7 pp); the B gain (+6.4 pp) was not significant | out: reverted in 9968e09, code kept at 2f528b7 |
| 3. Threat-aware mode (off by default) | high-priority detection higher on all seven; change in Pd within 1.5 pp; flag off identical to no flag | **PASS** (7 of 7); flag off identical on all seven | in, as a labelled option |

Today's arms are unchanged: Index at the 0.5 default and the first-band Bandit, re-run on the branch snapshot,
reproduce master's per-episode results exactly on all seven scenarios.

Budgets written by the official tuning run (`scripts/tune_index_budget.py`, seeds 2000-2009, margin 0, serving
evaluator): A 0.15, B 0.1, C 0.15, D 0.1, E 0.2184, F 0.1, G 0.35. The lead's independent sweep (a separate
harness) selected the same values.

What the numbers mean for the claims: the tuned budget raises Pd, scan efficiency and high-priority detection on
every scenario and never leaves Index significantly below the sweep on distinct bursts, but against Index as
served today it gives back some coverage (distinct bursts down 2.6 to 4.1 pp and intercept time up 24 to 104 steps
on A, C, D and E; it improves both on F). Threat-aware mode raises high-priority detection by 4 to 16 pp at a cost
of up to 8.1 pp of distinct bursts (Scenario A) and up to 163 steps of intercept time.
