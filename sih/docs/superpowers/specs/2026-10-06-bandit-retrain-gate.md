# Bandit retraining study: is the live checkpoint just an unlucky draw? — pre-registered procedure and gate

Status: **pre-registered**. Committed before any V2 (24000–24019) or C2 (22000–22019) run.
Base branch: `feat/bandit-round3` tip (round-3 context); this study changes no engine code.

## Motivation

Round-3 screening (see `2026-10-06-bandit-round3-results/round3_screening_table.md`) found,
on tuning worlds T, that a freshly trained DEFAULT-recipe Bandit beat the live Scenario B
checkpoint (`model_bandit_0496bb32`) 1.27× at 80 steps (0.305 vs 0.239) but only 1.05× at
160 steps — one training draw each, so possibly retraining noise or live-checkpoint
staleness (live weights predate the state-builder/serving fixes). This study tests whether
retraining the UNCHANGED default recipe systematically recovers short-run efficiency.

## Rulings (each with the cost if it is wrong)

| # | Ruling | Cost if wrong |
|---|---|---|
| S1 | Same default recipe (`ml/configs/bandit.yaml`), same training data (seeds 1042–1061, 20 episodes), same epsilon schedule. Only the agent RNG differs per draw (seeded 5000+i, reproducible). This isolates training noise from recipe changes. | If the live weakness is data/estimator drift rather than noise, all draws look like live and the study correctly reports nothing. |
| S2 | D = 6 draws. Enough to see spread (luck vs systematic); small enough for ~1 h CPU. | With 6 draws the best-of-6 on V2 is selection-biased upward; the independent C2 confirmation (below) is what counts, not V2. |
| S3 | V2 (24000–24019, pristine) selects exactly ONE draw (largest B80 point ratio) and estimates the effect. C2 (22000–22019, pristine) confirms that ONE draw exactly once with the gate below. No other C2 run for this study. | Any second peek at C2 invalidates the confirmation; a failed study must not re-spend C2. |
| S4 | Reference throughout = the live registry Bandit checkpoints (read-only). The user-visible comparison. | A fresh-default reference would hide staleness; live is the honest baseline. |
| S5 | Claim is modest on purpose: retraining recovery at 80 steps, no regression elsewhere. Bars below (not 1.20 — same recipe, no new capability claimed). | If the owner expects +20%, this study cannot deliver it; routes 1/3 from round 3 remain the +20% paths. |

## Arms and horizons

Fresh session per world (deepcopy of post-training weights), `learn=True, explore=False`,
serving periodicity estimator, paired worlds; horizons 80, 160, 400, full.

* `bandit-live`: live registry Bandit per scenario.
* `draw0..draw5`: default recipe, agent RNG seeded 5000+i.

## Selection (on V2 only)

For each draw: pooled mean-over-A–G efficiency ratios R80/R160 and B80/B160 vs live,
pooled diffs. **Selected = draw with the largest B80 point ratio.** Ties: larger R80.
Report all six draws (spread = evidence about noise vs systematic shift).

## Confirmation gate (on C2, selected draw vs live; paired bootstrap 4000/95%/seed 20261003)

| # | Check | Passes when |
|---|---|---|
| G1 | 80-step recovery | lower end of B80 ratio ≥ 1.10 AND lower end of mean R80 ≥ 1.05 |
| G2 | no 160-step regression | lower ends of B160 and mean R160 ≥ 1.00 |
| G3 | no long-run regression | lower ends ≥ 1.00 at 400 steps and ≥ 0.97 at full length |
| G4 | detection | lower ends Pd ≥ −1.0 pp, HPDR ≥ −2.0 pp at 80/160/400/full |
| G5 | coverage | lower ends distinct bursts ≥ −3.0 pp at all horizons; no scenario cell upper end below −10 pp |

PASS = every check. On PASS: register the selected draw's exact weights into a sandbox
registry, parity-check vs the validated weights, run paired serving-path experiments
through a sandbox engine (:8501) + sandbox Backend (:8081, separate H2) on B and one
32-band scenario at 80/160 steps (0 fallbacks required, decisions match offline), and
only then propose live activation — each live step (backup, import, activate B,
restart :8500, verify) announced before running. On FAIL: no sandbox, no live steps,
report stands, C2 stays spent-for-this-study (no re-confirmation).
