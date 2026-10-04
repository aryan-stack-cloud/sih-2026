### dqn_new vs dqn, profile B

#### E1 efficiency: mean over the 7 scenarios of eff(new)/eff(today); lower end >= 1.20 at 80/160/400

| horizon | ratio | 95% interval | pass |
|---|---|---|---|
| 80 | 1.347 | [1.237, 1.568] | PASS |
| 160 | 1.375 | [1.259, 1.654] | PASS |
| 400 | 1.399 | [1.271, 1.696] | PASS |
| full (E3, >= 0.99) | 1.431 | [1.301, 1.761] | PASS |

#### E2 detection and B1 coverage guards: lower end of mean (new - today) >= -1.0 pp

| metric | horizon | difference pp | 95% interval | gated | pass |
|---|---|---|---|---|---|
| pd | 80 | +3.91 | [+2.75, +5.10] | yes | PASS |
| pd | 160 | +4.51 | [+3.27, +5.85] | yes | PASS |
| pd | 400 | +4.66 | [+3.36, +6.03] | yes | PASS |
| pd | full | +5.23 | [+3.94, +6.53] | yes | PASS |
| hpdr | 80 | +2.74 | [+0.06, +5.42] | yes | PASS |
| hpdr | 160 | +3.11 | [+0.53, +6.05] | yes | PASS |
| hpdr | 400 | +3.42 | [+0.70, +6.36] | yes | PASS |
| hpdr | full | +4.75 | [+2.20, +7.65] | yes | PASS |
| bursts | 80 | +5.85 | [+4.24, +7.43] | yes | PASS |
| bursts | 160 | +6.19 | [+4.61, +7.76] | yes | PASS |
| bursts | 400 | +7.65 | [+6.22, +9.05] | yes | PASS |
| bursts | full | +11.13 | [+9.65, +12.57] | yes | PASS |

#### E4 per-scenario efficiency ratio (point [95% interval]); gate: upper end >= 0.95 in every cell

| horizon | A | B | C | D | E | F | G | pass |
|---|---|---|---|---|---|---|---|---|
| 80 | 1.06 [0.98,1.17] | 1.30 [1.13,1.54] | 1.15 [1.03,1.28] | 1.10 [0.97,1.28] | 1.49 [1.31,1.73] | 2.18 [1.50,3.57] | 1.13 [0.99,1.29] | PASS |
| 160 | 1.04 [0.96,1.13] | 1.28 [1.10,1.50] | 1.20 [1.08,1.33] | 1.15 [1.01,1.32] | 1.48 [1.31,1.68] | 2.30 [1.56,3.95] | 1.18 [1.05,1.33] | PASS |
| 400 | 1.03 [0.95,1.12] | 1.21 [1.05,1.43] | 1.19 [1.09,1.31] | 1.12 [0.99,1.30] | 1.45 [1.31,1.64] | 2.56 [1.72,4.36] | 1.23 [1.10,1.39] | PASS |

VERDICT dqn_new (profile B): PASS
