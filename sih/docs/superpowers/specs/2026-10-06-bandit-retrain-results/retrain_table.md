# Retraining study results: 6 default-recipe draws vs live

Training: default `ml/configs/bandit.yaml`, seeds 1042–1061, 20 episodes, agent RNG
seeded 5000+i (reproducible draws). Eval: fresh deepcopy per world, `learn=True,
explore=False`, paired worlds, serving estimator. Reference = live registry Bandit
checkpoints (read-only).

## V2 selection (seeds 24000–24019, pooled point estimates vs live)

| Draw | R80 / R160 | B80 / B160 | dHPDR full | dBursts full |
|---|---|---|---|---|
| draw0 | 1.126 / 1.099 | 1.159 / 1.206 | +0.1 | −0.8 |
| draw1 | 0.970 / 1.030 | 0.997 / 1.129 | −0.5 | −0.1 |
| draw2 | 0.966 / 0.995 | 0.963 / 1.080 | −0.5 | −0.9 |
| draw3 | 0.949 / 0.964 | 1.060 / 1.142 | −0.5 | −0.5 |
| draw4 | 1.094 / 1.064 | **1.173** / 1.253 | −0.7 | −1.5 |
| draw5 | 1.109 / 1.115 | 1.075 / 1.225 | −1.0 | −0.5 |

Selected = draw4 (largest B80, per pre-registration). Spread across draws (R80
0.95–1.13, B80 0.96–1.17) shows training noise is large — the T observation that
motivated this study sits inside draw luck, not above it.

## C2 confirmation (seeds 22000–22019, single run, paired bootstrap 4000/95%)

draw4 vs live:

| Check | Result | Bar |
|---|---|---|
| R80 1.079 [1.033, 1.133] / B80 1.255 [1.120, 1.405] | G1 FAIL (R80 lower 1.033 < 1.05) | B80 ≥ 1.10, R80 ≥ 1.05 |
| R160 1.025 [0.999, 1.056] / B160 1.267 [1.178, 1.367] | G2 FAIL (R160 lower 0.999 < 1.00) | both ≥ 1.00 |
| R400 1.014 [0.991, 1.037] / Rfull 0.992 [0.977, 1.006] | G3 FAIL (R400 lower 0.991 < 1.00) | 1.00 / 0.97 |
| Pd +0.7/+0.8/+0.7/−0.1; HPDR +2.0/+1.3/+0.9/+0.2 (all lower ends ≥ guards) | G4 PASS | Pd −1.0, HPDR −2.0 |
| Bursts −1.0/−1.9/−1.8/−0.1 (all lower ends ≥ −3.0) | G5 PASS | −3.0, no cell < −10 |

**VERDICT: FAIL** (G1/G2/G3 on mean ratios; detection and coverage pass).

## Reading

The draw IS better than live on Scenario B on fresh worlds (B80 1.255, B160 1.267,
both lower ends clear of 1.10) — the Dashboard default would show roughly +25%.
But the mean over A–G misses every bar by 0.001–0.02: retraining does not
systematically lift the policy, it re-rolls the dice, and this roll was B-lucky.
The gate's mean criteria fail, so per the pre-registration there is no sandbox run
and no live activation. C2 is spent for this study; no re-confirmation.

Per-world evidence: `C:\w\r3\retrain_worlds_V2.json`, `C:\w\r3\live_ref_V2.json`,
`C:\w\r3\c2_worlds.json`, `C:\w\r3\c2_gate_draw4.md`. Selected weights:
`C:\w\r3\agents\draw4\{A..G}.npz` (kept, unregistered).
