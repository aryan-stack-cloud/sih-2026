#### G1 / G1b efficiency at the live horizons (mean of ratios over A-G; Scenario B alone)

| horizon | mean ratio [95%] | G1 | Scenario B ratio [95%] | G1b |
|---|---|---|---|---|
| 80 | 1.255 [1.206, 1.311] | PASS | 1.392 [1.242, 1.560] | PASS |
| 160 | 1.186 [1.149, 1.228] | FAIL | 1.297 [1.192, 1.413] | FAIL |

#### G2 no loss on longer runs (lower end >= 1.00 at 400, >= 0.97 at full)

| horizon | ratio [95%] | pass |
|---|---|---|
| 400 | 1.072 [1.046, 1.099] | PASS (>= 1.00) |
| full | 1.017 [1.001, 1.034] | PASS (>= 0.97) |

#### G3 detection (mean new - today, pp; lower end: Pd >= -1.0, HPDR >= -2.0)

| metric | horizon | diff [95%] | pass |
|---|---|---|---|
| pd | 80 | +2.34 [+1.81, +2.89] | PASS |
| pd | 160 | +2.07 [+1.51, +2.65] | PASS |
| pd | 400 | +1.14 [+0.58, +1.70] | PASS |
| pd | full | +0.64 [+0.24, +1.03] | PASS |
| hpdr | 80 | +2.84 [+0.97, +4.56] | PASS |
| hpdr | 160 | +2.29 [+0.59, +3.85] | PASS |
| hpdr | 400 | -0.38 [-2.08, +1.11] | FAIL |
| hpdr | full | -1.43 [-3.08, +0.01] | FAIL |

#### G4 per-scenario efficiency ratio (point [95%]); upper end >= 0.95 in every cell

| horizon | A | B | C | D | E | F | G | pass |
|---|---|---|---|---|---|---|---|---|
| 80 | 1.08 [1.02,1.15] | 1.39 [1.24,1.56] | 1.07 [1.01,1.15] | 1.23 [1.13,1.35] | 1.19 [1.13,1.25] | 1.36 [1.12,1.66] | 1.46 [1.38,1.57] | PASS |
| 160 | 1.02 [0.95,1.10] | 1.30 [1.19,1.41] | 1.06 [0.99,1.13] | 1.21 [1.12,1.29] | 1.17 [1.13,1.21] | 1.16 [0.99,1.36] | 1.39 [1.29,1.49] | PASS |
| 400 | 0.98 [0.94,1.03] | 1.21 [1.13,1.31] | 1.04 [0.99,1.10] | 1.03 [0.96,1.10] | 1.06 [1.01,1.10] | 1.03 [0.92,1.14] | 1.14 [1.08,1.21] | PASS |

#### G5 coverage: distinct bursts, mean new - today (lower end >= -3.0 pp) and per scenario (upper end must not be below -10 pp)

| horizon | mean diff [95%] | mean ok | worst scenario upper end | per-scenario ok |
|---|---|---|---|---|
| 80 | -0.40 [-1.58, +0.76] | PASS | -1.7 | PASS |
| 160 | +0.76 [-0.31, +1.82] | PASS | -1.0 | PASS |
| 400 | +1.20 [+0.06, +2.38] | PASS | -0.1 | PASS |
| full | -1.14 [-2.58, +0.28] | PASS | -2.8 | PASS |

VERDICT b_poly2: FAIL   G1=FAIL  G1b=FAIL  G2=ok  G3=FAIL  G4=ok  G5=ok
