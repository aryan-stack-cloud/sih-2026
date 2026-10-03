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
