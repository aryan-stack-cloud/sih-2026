#### G1 / G1b efficiency at the live horizons (mean of ratios over A-G; Scenario B alone)

| horizon | mean ratio [95%] | G1 | Scenario B ratio [95%] | G1b |
|---|---|---|---|---|
| 80 | 1.418 [1.331, 1.527] | PASS | 1.521 [1.373, 1.692] | PASS |
| 160 | 1.301 [1.256, 1.354] | PASS | 1.463 [1.383, 1.551] | PASS |

#### G2 no loss on longer runs (lower end >= 1.00 at 400, >= 0.97 at full)

| horizon | ratio [95%] | pass |
|---|---|---|
| 400 | 1.121 [1.092, 1.152] | PASS (>= 1.00) |
| full | 1.008 [0.989, 1.028] | PASS (>= 0.97) |

#### G3 detection (mean new - today, pp; lower end: Pd >= -1.0, HPDR >= -2.0)

| metric | horizon | diff [95%] | pass |
|---|---|---|---|
| pd | 80 | +3.92 [+3.15, +4.69] | PASS |
| pd | 160 | +3.73 [+3.12, +4.36] | PASS |
| pd | 400 | +1.92 [+1.30, +2.53] | PASS |
| pd | full | +0.28 [-0.22, +0.78] | PASS |
| hpdr | 80 | +6.56 [+4.25, +8.32] | PASS |
| hpdr | 160 | +4.00 [+2.07, +5.73] | PASS |
| hpdr | 400 | +0.54 [-1.24, +2.00] | PASS |
| hpdr | full | -2.13 [-3.80, -0.64] | FAIL |

#### G4 per-scenario efficiency ratio (point [95%]); upper end >= 0.95 in every cell

| horizon | A | B | C | D | E | F | G | pass |
|---|---|---|---|---|---|---|---|---|
| 80 | 1.17 [1.10,1.24] | 1.52 [1.37,1.69] | 1.15 [1.07,1.23] | 1.36 [1.25,1.48] | 1.24 [1.17,1.31] | 2.08 [1.54,2.78] | 1.41 [1.31,1.51] | PASS |
| 160 | 1.11 [1.04,1.18] | 1.46 [1.38,1.55] | 1.12 [1.03,1.22] | 1.25 [1.15,1.36] | 1.26 [1.21,1.32] | 1.55 [1.32,1.85] | 1.35 [1.28,1.43] | PASS |
| 400 | 1.05 [1.00,1.10] | 1.25 [1.17,1.34] | 1.06 [0.97,1.13] | 1.08 [0.99,1.17] | 1.10 [1.08,1.13] | 1.10 [0.97,1.22] | 1.21 [1.15,1.27] | PASS |

#### G5 coverage: distinct bursts, mean new - today (lower end >= -3.0 pp) and per scenario (upper end must not be below -10 pp)

| horizon | mean diff [95%] | mean ok | worst scenario upper end | per-scenario ok |
|---|---|---|---|---|
| 80 | -1.19 [-2.33, -0.09] | PASS | -0.8 | PASS |
| 160 | +0.33 [-0.76, +1.41] | PASS | -0.6 | PASS |
| 400 | +0.66 [-0.28, +1.61] | PASS | -0.3 | PASS |
| full | +2.03 [+0.65, +3.31] | PASS | +1.3 | PASS |

VERDICT r2a_f: FAIL   G1=ok  G1b=ok  G2=ok  G3=FAIL  G4=ok  G5=ok
