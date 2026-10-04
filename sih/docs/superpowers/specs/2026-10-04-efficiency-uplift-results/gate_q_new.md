### q_new vs q, profile E

#### E1 efficiency: mean over the 7 scenarios of eff(new)/eff(today); lower end >= 1.20 at 80/160/400

| horizon | ratio | 95% interval | pass |
|---|---|---|---|
| 80 | 1.382 | [1.316, 1.456] | PASS |
| 160 | 1.323 | [1.263, 1.389] | PASS |
| 400 | 1.302 | [1.256, 1.350] | PASS |
| full (E3, >= 0.99) | 1.277 | [1.237, 1.318] | PASS |

#### E2 detection and B1 coverage guards: lower end of mean (new - today) >= -1.0 pp

| metric | horizon | difference pp | 95% interval | gated | pass |
|---|---|---|---|---|---|
| pd | 80 | +4.54 | [+3.60, +5.49] | yes | PASS |
| pd | 160 | +3.96 | [+2.99, +4.92] | yes | PASS |
| pd | 400 | +4.07 | [+3.35, +4.77] | yes | PASS |
| pd | full | +3.92 | [+3.23, +4.61] | yes | PASS |
| hpdr | 80 | +2.68 | [+0.24, +5.14] | yes | PASS |
| hpdr | 160 | +3.24 | [+0.90, +5.62] | yes | PASS |
| hpdr | 400 | +3.23 | [+0.55, +5.70] | yes | PASS |
| hpdr | full | +4.12 | [+1.69, +6.10] | yes | PASS |
| bursts | 80 | -6.13 | [-7.64, -4.60] | reported | FAIL |
| bursts | 160 | -5.19 | [-7.11, -3.36] | reported | FAIL |
| bursts | 400 | -6.15 | [-7.82, -4.53] | reported | FAIL |
| bursts | full | -5.27 | [-7.13, -3.47] | reported | FAIL |

#### E4 per-scenario efficiency ratio (point [95% interval]); gate: upper end >= 0.95 in every cell

| horizon | A | B | C | D | E | F | G | pass |
|---|---|---|---|---|---|---|---|---|
| 80 | 1.32 [1.17,1.48] | 1.02 [0.91,1.14] | 1.30 [1.14,1.48] | 1.69 [1.48,1.93] | 1.61 [1.46,1.75] | 1.28 [1.09,1.54] | 1.44 [1.20,1.69] | PASS |
| 160 | 1.40 [1.27,1.54] | 1.04 [0.95,1.13] | 1.31 [1.18,1.46] | 1.63 [1.39,1.91] | 1.58 [1.46,1.71] | 1.04 [0.88,1.20] | 1.27 [1.11,1.45] | PASS |
| 400 | 1.37 [1.27,1.46] | 1.04 [0.97,1.11] | 1.33 [1.20,1.48] | 1.47 [1.29,1.69] | 1.58 [1.48,1.69] | 1.06 [0.99,1.12] | 1.27 [1.16,1.39] | PASS |

VERDICT q_new (profile E): PASS
