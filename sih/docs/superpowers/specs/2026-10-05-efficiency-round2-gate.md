# Efficiency round 2 (Bandit and Q-learning): pre-registered procedure and gate

Status: **pre-registered**. This file is committed before any validation run (seeds V) and before any reserve run (seeds C2).
Everything in the "Tuning" sections below was done on the tuning seeds T, which are allowed to be looked at.

## Why a second round

Round 1 (`2026-10-04-efficiency-uplift-gate.md`, merged as `13c90d5`) passed for Q-learning, DQN and PPO and failed for the Bandit.
The project owner's reply after the rollout (5 Oct 2026): "the listining efficinecy is not increased of the bandit or any model".
The facts behind it (paired worlds C1, Scenario B = the Dashboard's default, listening efficiency %, original model -> live now):

| Model | 80 steps | 160 steps | Reason |
|---|---|---|---|
| Bandit | 20.8 -> 20.8 | 26.5 -> 26.5 | the round-1 Bandit failed its gate and was not shipped |
| Q-learning | 42.9 -> 43.8 | 47.5 -> 49.2 | already close to what any "park on the best window" policy reaches (about 60% on B, 50% on F) |
| DQN | 33.9 -> 44.1 | 37.0 -> 47.3 | |
| PPO | 19.8 -> 36.6 | 20.3 -> 37.1 | |

Owner approval (5 Oct 2026): "Go: run round 2 offline. Pick a milder Bandit recipe on a validation set and confirm it once on the
reserve worlds (seeds 22000-22019). Try periodicity-timed switching for Q-learning on Scenarios B and F. Report before touching master
or the live stack."

## Rulings (each with the cost if it is wrong)

| # | Ruling | Cost if wrong |
|---|---|---|
| S1 | Same metric as round 1: listening efficiency = useful scans / total scans (the Dashboard's number); "+20%" is relative (new / reference >= 1.20). | If the owner meant something else the headline does not answer it; Pd, HPDR and distinct bursts are reported next to it. |
| S2 | The Bandit claim is made at the Dashboard's live horizons **80 and 160 steps** (mean over the seven scenarios A-G of the per-scenario ratio, and separately on Scenario B, the default). At 400 steps and full length the claim is only "no regression". This is a weaker claim than round 1's (which also asked +20% at 400 steps), by design: the screened Bandit family did not reach +20% at 400 steps without camping. | The Bandit would be +20% only for runs up to 160 steps; longer runs look as before. |
| S3 | Reference for the Bandit = today's live Bandit (unchanged since `ee2ee6f`). Reference for Q-learning = the ORIGINAL Q-learning the owner saw before round 1 (live registry backup `C:\w\backup\ml-checkpoints-live-pre-efficiency-20261004`) for the owner-facing claim, and the LIVE round-1 Q-learning for the no-regression checks. | A claim against the live round-1 model would be weaker than what the owner sees. |
| S4 | Non-inferiority margins are one noise half-width of the round-1 intervals (Pd 1.0 pp, HPDR 2.0 pp, full-length efficiency ratio 0.97, distinct bursts 3.0 pp), not the round-1 value of 1.0 pp for HPDR: the HPDR half-width measured in round 1 is 2.6-2.8 pp at every horizon, so a 1.0 pp margin makes the test a coin flip for a candidate with zero true change and is only passed by candidates that improve HPDR significantly. A candidate with a true HPDR loss of 2.5 pp or more still fails with high probability. Chosen here, before any V or C2 run. | If the owner wants the strict 1.0 pp margin for HPDR, a Bandit that is neutral on HPDR cannot pass. |

## Seed sets

| Set | Seeds | Worlds per scenario | Use |
|---|---|---|---|
| T (tuning) | 20000-20019 | 20 | screening of candidates (also used in round 1); free to look at |
| V (validation) | 23000-23019 | 20 | choose among the finalists, with the gate's own procedure; never used before |
| C2 (reserve) | 22000-22019 | 20 | the confirmation, **once per final model**; never used before |

Training seeds are the registry's own (1042 upward), disjoint from T, V and C2.

## Arms

Every arm runs exactly like a fresh Backend simulation: serving periodicity estimator, `learn=True, explore=False`, one fresh agent per
world, the same worlds for every arm (paired); horizons 80, 160, 400 and full length (2000-3000).

* `sweep`: fixed round-robin sweep (stride K).
* `bandit today`: the live registry's Bandit models (unchanged files).
* `q original`: the ORIGINAL Q-learning models (registry backup). `q live`: the round-1 Q-learning models (live registry).
* candidates: see below.

## Bandit procedure

1. **Pool (fixed now)**: the 46 complete Bandit candidate labels screened in round 1 (every one except the failed round-1 recipe `b6_e4c2_ep30`), plus the 14 round-2
   variants listed in the next section. Two decision-time levers are new in round 2 (prototype-tested on T before this file was written):
   `age_bonus` (a bonus `age_bonus * mean staleness of the window's bands` added to the action score at decision time, not learned; it keeps
   coverage directly instead of through the learned reward) and `phase_fourier` (confidence-weighted cosine and sine of the periodicity phase of
   the band and of the next band as extra features, so a linear score can express "about to switch on").
2. **Predicted-pass rule on T** (point estimates, computed by `r2_rank.py` in the artifact's `experiments/`): a candidate is judged by the total
   normalised shortfall against: R80, R160 >= 1.25; Scenario B ratio at 80 and 160 >= 1.25; R400 >= 1.05; full-length ratio >= 1.014;
   dPd >= 0.0 pp, dHPDR >= +0.7 pp, d(distinct bursts) >= -1.5 pp at 80/160/400/full; no scenario ratio at 80/160/400 below 0.95 (each threshold is
   the gate threshold plus the half-width of its interval, so a candidate on the threshold would pass the gate about half the time).
   **Finalists = the three candidates with the lowest total shortfall** (ties: larger min(R80, R160)).
3. **Validation**: the finalists are evaluated on V against `bandit today` and `sweep` with the gate below (the same bootstrap). Among the finalists that
   PASS the gate on V, the one with the largest min(R80, R160) is chosen. If none passes, no Bandit recipe is chosen, no reserve world is used for the
   Bandit, and the report says so.
4. **Final model**: the chosen recipe is ported into the engine's options (with tests), trained by `scripts/train_all.py` into a sandbox registry, checked
   against the prototype for decision-for-decision parity, and evaluated once on C2 with the gate below.

## Bandit gate (on C2; the same procedure on V)

Paired bootstrap, 4000 resamples, 95%, seed 20261003, worlds resampled independently per scenario; "lower end" = the 2.5% point.

| # | Check | Passes when |
|---|---|---|
| G1 | efficiency at the live horizons | lower end of mean-over-scenarios ratio >= 1.20 at 80 steps and at 160 steps |
| G1b | efficiency on Scenario B (the Dashboard default) | lower end of the Scenario B ratio >= 1.20 at 80 and at 160 steps |
| G2 | no loss on longer runs | lower end of the ratio >= 1.00 at 400 steps and >= 0.97 at full length |
| G3 | detection | lower end of the mean difference (new minus today) in Pd >= -1.0 pp and in HPDR >= -2.0 pp, at 80, 160, 400 and full length |
| G4 | no hidden regression | in every scenario at 80, 160 and 400 steps the upper end of the ratio is >= 0.95 |
| G5 | coverage (distinct bursts) | lower end of the mean difference >= -3.0 pp at all four horizons, and in no scenario at any horizon is the upper end of the difference below -10 pp |

PASS = every check passes.

## Q-learning on Scenarios B and F ("periodicity-timed switching")

The registry holds one Q-learning model per scenario, so a variant can be registered for B and F only. Variants are options of the tabular agent's state
(finer periodicity-phase bins, three confidence bins, the next band's phase in the key, phase merged while confidence is lowest, finer age bins) on top of
the round-1 recipe. The screening on T decides whether anything is worth confirming.

**Q gate** (C2, Scenarios B and F only; paired with the same worlds; evaluated only for a finalist chosen on V by the same rule as the Bandit's):

| # | Check | Passes when |
|---|---|---|
| Q1 | owner-facing efficiency | lower end of the ratio versus the ORIGINAL Q-learning >= 1.20 in each of the four cells B and F at 80 and 160 steps |
| Q2 | no loss against the live model | lower end of the ratio versus the LIVE Q-learning >= 0.98 at 80, 160, 400 steps and >= 0.97 at full length, on B and on F |
| Q3 | detection and coverage versus the LIVE model | mean over B and F: Pd lower end >= -1.0 pp, HPDR lower end >= -2.0 pp, distinct bursts lower end >= -3.0 pp, at all four horizons |

If no Q-learning variant reaches the Q1 bar on T with a margin, nothing is confirmed on C2 and the report states the best result and the ceiling analysis instead.

## Frozen before validation (5 October 2026)

The candidate inventory contains 60 complete Bandit labels. The exact pool, training settings, source expressions and checkpoint
SHA-256 hashes are in `2026-10-05-efficiency-round2-results/round2_frozen_selection.json`; the inventory count above corrects
the draft's count of 45. No validation or reserve worlds have been observed at this point.

The saved ranking selects, in order: `r2a_f`, `b_poly2`, `b_blr40_al`. The last arm uses the original round-1 checkpoint
with the observation-based alignment wrapper, exactly as it was screened. Validation runs all three against the same Bandit reference
and sweep on V. Passing is still required before choosing a candidate for reserve confirmation. Rounded-shortfall ties use the
existing selector's precision of 0.001; neither thresholds nor finalist count change.

Q-learning timing, training-horizon and training-seed replication screens on T have completed. Even allowing a separate recipe
for B and F, the best minimum of the 80/160-step point ratios versus original Q-learning is 1.078 on B (`r2q_ep160`)
and 1.150 on F (`r2q_e8c1`). Neither reaches 1.20 with a margin. Therefore no Q-learning finalist goes to V or C2.
This is a negative screening result, not evidence that all possible Q-learning methods are capped there.

Round-2 tolerances are Pd -1 pp, HPDR -2 pp, distinct bursts -3 pp, and full efficiency ratio 0.97 at the lower confidence bound.
These allow small losses; they do not establish exact equality or universal absence of regression. The rationale in S4 was a design
choice informed by round-1 intervals, not a measured power calculation. The original round-1 stricter gate remains a separate result.

## Outcome: validation complete, no reserve confirmation

All three frozen finalists failed V. `r2a_f` passed the efficiency and coverage checks, including Scenario B ratios 1.521 / 1.463
at 80 / 160 steps, but full-length mean high-priority detection changed -2.13 pp [95%: -3.80, -0.64], failing G3.
`b_poly2` failed G1, G1b and G3; `b_blr40_al` failed G1 and G3. Therefore no Bandit model was selected and no C2 run was made.
Q-learning had already failed its tuning prerequisite. Reserve seeds 22000-22019 remain unused by round 2.

The new opt-in Bandit options are committed as `b9525e3` on `feat/efficiency-round2`; the default recipe is unchanged.
Relevant tests: 82 option/alignment checks plus 28 existing agent/served-session checks, all passed. The validated 140 V files contain
2,800 correctly paired episodes, and frozen candidate checkpoint hashes are unchanged. Details and full gate reports are in
`2026-10-05-efficiency-round2-results/round2_result.md`. Raw evidence and reproducible harness/checkpoints are saved in the local
Traycer artifact `efficiency-round2-2026-10-05`. No merge, push, live registry change, activation or service restart was performed.
