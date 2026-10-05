#### G1 / G1b efficiency at the live horizons (mean of ratios over A-G; Scenario B alone)

| horizon | mean ratio [95%] | G1 | Scenario B ratio [95%] | G1b |
|---|---|---|---|---|
| 80 | 1.179 [1.127, 1.240] | FAIL | 1.325 [1.237, 1.416] | PASS |
| 160 | 1.177 [1.141, 1.221] | FAIL | 1.323 [1.225, 1.433] | PASS |

#### G2 no loss on longer runs (lower end >= 1.00 at 400, >= 0.97 at full)

| horizon | ratio [95%] | pass |
|---|---|---|
| 400 | 1.094 [1.072, 1.118] | PASS (>= 1.00) |
| full | 1.025 [1.006, 1.044] | PASS (>= 0.97) |

#### G3 detection (mean new - today, pp; lower end: Pd >= -1.0, HPDR >= -2.0)

| metric | horizon | diff [95%] | pass |
|---|---|---|---|
| pd | 80 | +1.64 [+1.12, +2.10] | PASS |
| pd | 160 | +2.10 [+1.59, +2.60] | PASS |
| pd | 400 | +1.48 [+1.04, +1.91] | PASS |
| pd | full | +0.48 [-0.04, +1.01] | PASS |
| hpdr | 80 | +2.16 [+0.47, +3.49] | PASS |
| hpdr | 160 | +1.36 [-0.19, +2.75] | PASS |
| hpdr | 400 | +0.19 [-1.29, +1.48] | PASS |
| hpdr | full | -1.07 [-2.64, +0.37] | FAIL |

#### G4 per-scenario efficiency ratio (point [95%]); upper end >= 0.95 in every cell

| horizon | A | B | C | D | E | F | G | pass |
|---|---|---|---|---|---|---|---|---|
| 80 | 1.02 [0.97,1.07] | 1.33 [1.24,1.42] | 1.08 [1.03,1.14] | 1.19 [1.12,1.26] | 1.08 [1.03,1.15] | 1.30 [1.00,1.70] | 1.25 [1.16,1.33] | PASS |
| 160 | 1.01 [0.96,1.06] | 1.32 [1.22,1.43] | 1.09 [1.03,1.16] | 1.18 [1.13,1.24] | 1.09 [1.06,1.14] | 1.28 [1.09,1.55] | 1.26 [1.21,1.31] | PASS |
| 400 | 1.07 [1.02,1.13] | 1.17 [1.10,1.26] | 1.06 [0.99,1.12] | 1.08 [1.03,1.14] | 1.06 [1.03,1.10] | 1.06 [1.00,1.13] | 1.15 [1.09,1.21] | PASS |

#### G5 coverage: distinct bursts, mean new - today (lower end >= -3.0 pp) and per scenario (upper end must not be below -10 pp)

| horizon | mean diff [95%] | mean ok | worst scenario upper end | per-scenario ok |
|---|---|---|---|---|
| 80 | -0.09 [-1.22, +0.99] | PASS | -0.0 | PASS |
| 160 | +0.37 [-0.51, +1.26] | PASS | +0.4 | PASS |
| 400 | +0.87 [-0.13, +1.91] | PASS | +1.7 | PASS |
| full | -0.80 [-2.17, +0.51] | PASS | -2.4 | PASS |

VERDICT b_blr40_al: FAIL   G1=FAIL  G1b=ok  G2=ok  G3=FAIL  G4=ok  G5=ok
