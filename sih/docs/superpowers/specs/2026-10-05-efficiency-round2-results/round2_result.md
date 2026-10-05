# Round-2 offline result

All three Bandit finalists FAIL validation. No model selected; reserve seeds 22000–22019 remain unused by round 2. No Q-learning finalist met the tuning prerequisite.

## Scenario B: listening efficiency on validation worlds

| Bandit arm | 80 steps | 160 steps | 400 steps | Full |
|---|---|---|---|---|
| `bandit` | 22.56% | 27.64% | 36.99% | 46.96% |
| `r2a_f` | 34.31% | 40.44% | 46.29% | 51.21% |
| `b_poly2` | 31.41% | 35.86% | 44.91% | 51.28% |
| `b_blr40_al` | 29.91% | 36.58% | 43.44% | 49.25% |

## Finalist verdicts

| Arm | Mean ratio 80 / 160 | Scenario B ratio 80 / 160 | Full-run mean HPDR difference [95%], pp | Failed checks |
|---|---|---|---|---|
| `r2a_f` | 1.418 / 1.301 | 1.521 / 1.463 | -2.13 [-3.80, -0.64] | G3 |
| `b_poly2` | 1.255 / 1.186 | 1.392 / 1.297 | -1.43 [-3.08, +0.01] | G1, G1b, G3 |
| `b_blr40_al` | 1.179 / 1.177 | 1.325 / 1.323 | -1.07 [-2.64, +0.37] | G1, G3 |

Validation: seeds 23000–23019, 20 paired worlds per scenario and horizon, 140 result files / 2,800 evaluation episodes. All expected files, seed identities, short-run lengths and frozen candidate hashes checked. Bandit reference IDs match tuning; live checkpoint bytes match the pre-rollout backup.

The strongest candidate passes efficiency and distinct-burst guards, but full-run high-priority detection fails even the relaxed round-2 margin. This result does not pass the full gate and is not a reserve confirmation.

Q-learning: best weaker-horizon tuning ratios versus original are 1.078 on B and 1.150 on F, permitting different recipes. Phase variants did not solve the short-run target. No claim of a universal algorithm ceiling is justified. Ground-truth oracle diagnostics are for ceilings only and were never inputs to a candidate policy.

Verified 110 relevant tests (82 options/alignment and 28 agents/served-session). Engine/prototype parity compares three combinations, all learned parameters and 120 greedy actions per case. Experimental code and reports remain on feat/efficiency-round2; defaults and live deployments unchanged.
