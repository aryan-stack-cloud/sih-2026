### ppo_new vs ppo, profile B

#### E1 efficiency: mean over the 7 scenarios of eff(new)/eff(today); lower end >= 1.20 at 80/160/400

| horizon | ratio | 95% interval | pass |
|---|---|---|---|
| 80 | 1.606 | [1.511, 1.725] | PASS |
| 160 | 1.602 | [1.517, 1.705] | PASS |
| 400 | 1.620 | [1.539, 1.718] | PASS |
| full (E3, >= 0.99) | 1.663 | [1.596, 1.744] | PASS |

#### E2 detection and B1 coverage guards: lower end of mean (new - today) >= -1.0 pp

| metric | horizon | difference pp | 95% interval | gated | pass |
|---|---|---|---|---|---|
| pd | 80 | +4.99 | [+4.30, +5.78] | yes | PASS |
| pd | 160 | +5.30 | [+4.71, +5.95] | yes | PASS |
| pd | 400 | +5.72 | [+5.10, +6.39] | yes | PASS |
| pd | full | +6.31 | [+5.77, +6.92] | yes | PASS |
| hpdr | 80 | +4.67 | [+2.98, +6.39] | yes | PASS |
| hpdr | 160 | +5.79 | [+4.54, +7.14] | yes | PASS |
| hpdr | 400 | +5.40 | [+4.05, +6.87] | yes | PASS |
| hpdr | full | +6.64 | [+5.28, +8.25] | yes | PASS |
| bursts | 80 | +0.78 | [-0.59, +2.22] | yes | PASS |
| bursts | 160 | +1.69 | [+0.60, +2.76] | yes | PASS |
| bursts | 400 | +1.24 | [+0.29, +2.17] | yes | PASS |
| bursts | full | +4.37 | [+3.52, +5.24] | yes | PASS |

#### E4 per-scenario efficiency ratio (point [95% interval]); gate: upper end >= 0.95 in every cell

| horizon | A | B | C | D | E | F | G | pass |
|---|---|---|---|---|---|---|---|---|
| 80 | 1.35 [1.25,1.47] | 1.85 [1.55,2.29] | 1.13 [1.03,1.25] | 1.47 [1.29,1.69] | 1.46 [1.33,1.61] | 2.51 [2.03,3.10] | 1.46 [1.27,1.69] | PASS |
| 160 | 1.37 [1.26,1.48] | 1.83 [1.57,2.16] | 1.16 [1.10,1.24] | 1.50 [1.35,1.68] | 1.48 [1.35,1.60] | 2.36 [1.92,2.91] | 1.52 [1.39,1.68] | PASS |
| 400 | 1.34 [1.24,1.46] | 1.75 [1.53,2.06] | 1.21 [1.15,1.29] | 1.51 [1.36,1.68] | 1.56 [1.44,1.69] | 2.45 [2.02,2.96] | 1.52 [1.42,1.63] | PASS |

VERDICT ppo_new (profile B): PASS
