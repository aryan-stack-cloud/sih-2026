### bandit_new vs bandit, profile E

#### E1 efficiency: mean over the 7 scenarios of eff(new)/eff(today); lower end >= 1.20 at 80/160/400

| horizon | ratio | 95% interval | pass |
|---|---|---|---|
| 80 | 1.665 | [1.569, 1.778] | PASS |
| 160 | 1.486 | [1.397, 1.591] | PASS |
| 400 | 1.201 | [1.148, 1.254] | FAIL |
| full (E3, >= 0.99) | 1.044 | [1.002, 1.090] | PASS |

#### E2 detection and B1 coverage guards: lower end of mean (new - today) >= -1.0 pp

| metric | horizon | difference pp | 95% interval | gated | pass |
|---|---|---|---|---|---|
| pd | 80 | +6.59 | [+5.70, +7.50] | yes | PASS |
| pd | 160 | +6.50 | [+5.47, +7.52] | yes | PASS |
| pd | 400 | +4.28 | [+3.36, +5.16] | yes | PASS |
| pd | full | +2.27 | [+1.38, +3.20] | yes | PASS |
| hpdr | 80 | +5.71 | [+3.16, +8.49] | yes | PASS |
| hpdr | 160 | +3.11 | [+0.53, +5.67] | yes | PASS |
| hpdr | 400 | -0.30 | [-2.91, +2.38] | yes | FAIL |
| hpdr | full | -5.46 | [-8.37, -2.80] | yes | FAIL |
| bursts | 80 | -11.56 | [-13.08, -10.04] | reported | FAIL |
| bursts | 160 | -12.99 | [-14.54, -11.46] | reported | FAIL |
| bursts | 400 | -12.79 | [-14.39, -11.23] | reported | FAIL |
| bursts | full | -16.82 | [-18.37, -15.26] | reported | FAIL |

#### E4 per-scenario efficiency ratio (point [95% interval]); gate: upper end >= 0.95 in every cell

| horizon | A | B | C | D | E | F | G | pass |
|---|---|---|---|---|---|---|---|---|
| 80 | 1.20 [1.02,1.39] | 2.02 [1.77,2.30] | 1.05 [0.97,1.13] | 1.58 [1.38,1.79] | 1.52 [1.36,1.69] | 2.55 [2.07,3.19] | 1.73 [1.53,1.97] | PASS |
| 160 | 1.12 [0.95,1.30] | 1.71 [1.49,1.94] | 0.79 [0.67,0.90] | 1.49 [1.30,1.69] | 1.37 [1.26,1.48] | 2.20 [1.77,2.77] | 1.73 [1.56,1.92] | FAIL |
| 400 | 1.09 [0.92,1.25] | 1.45 [1.31,1.59] | 0.90 [0.74,1.05] | 1.18 [1.00,1.38] | 1.15 [1.08,1.23] | 1.29 [1.17,1.43] | 1.34 [1.26,1.42] | PASS |

VERDICT bandit_new (profile E): FAIL
