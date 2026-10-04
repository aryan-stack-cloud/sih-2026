### Efficiency of today's models and of the fixed sweep on the tuning seeds (listening efficiency %, mean over the seven scenarios)

| arm | 80 steps | 160 | 400 | full length |
|---|---|---|---|---|
| fixed sweep | 26.8 | 27.0 | 27.0 | 26.9 |
| Bandit | 30.9 | 38.2 | 48.3 | 56.7 |
| Q-learning | 40.9 | 45.1 | 49.0 | 52.9 |
| DQN | 41.5 | 43.7 | 45.9 | 46.5 |
| PPO | 29.4 | 31.1 | 32.2 | 34.1 |
| Index (reference) | 27.3 | 27.6 | 32.0 | 49.5 |

### The chosen recipes on the tuning seeds (new / today, mean over the seven scenarios, 95% paired interval)

| model | candidate | 80 steps | 160 | 400 | full | eff % today -> new at 80 / 160 / 400 |
|---|---|---|---|---|---|---|
| Bandit | `b6_e4c2_ep30` | 1.91 [1.81, 2.02] | 1.57 [1.50, 1.65] | 1.28 [1.23, 1.32] | 1.10 [1.07, 1.14] | 30.9 -> 53.3 / 38.2 -> 57.5 / 48.3 -> 61.4 |
| Q-learning | `q4_e4c2` | 1.35 [1.29, 1.42] | 1.33 [1.28, 1.38] | 1.28 [1.24, 1.33] | 1.23 [1.19, 1.27] | 40.9 -> 54.8 / 45.1 -> 59.9 / 49.0 -> 62.5 |
| DQN | `dqn_eq_c3_al` | 1.34 [1.25, 1.53] | 1.35 [1.24, 1.54] | 1.32 [1.22, 1.49] | 1.39 [1.26, 1.69] | 41.5 -> 50.4 / 43.7 -> 53.8 / 45.9 -> 55.8 |
| PPO | `ppo_eq_c10_al` | 1.52 [1.45, 1.61] | 1.55 [1.49, 1.63] | 1.61 [1.55, 1.69] | 1.70 [1.63, 1.78] | 29.4 -> 43.4 / 31.1 -> 45.4 / 32.2 -> 47.5 |

### Guards of the chosen recipes on the tuning seeds (mean over scenarios of new minus today, pp)

| model | metric | 80 | 160 | 400 | full |
|---|---|---|---|---|---|
| Bandit | Pd | +8.2 | +7.3 | +5.0 | +2.8 |
| Bandit | HPDR | +10.6 | +5.6 | +2.9 | +0.2 |
| Bandit | distinct bursts | -10.7 | -10.6 | -9.1 | -11.6 |
| Q-learning | Pd | +4.0 | +3.9 | +3.4 | +3.1 |
| Q-learning | HPDR | +5.7 | +6.0 | +4.6 | +6.0 |
| Q-learning | distinct bursts | -3.8 | -2.6 | -2.5 | -2.7 |
| DQN | Pd | +3.4 | +3.9 | +3.8 | +4.4 |
| DQN | HPDR | +3.4 | +5.0 | +5.0 | +6.1 |
| DQN | distinct bursts | +5.6 | +5.7 | +6.7 | +10.3 |
| PPO | Pd | +4.4 | +4.9 | +5.4 | +6.2 |
| PPO | HPDR | +5.0 | +6.0 | +6.3 | +6.8 |
| PPO | distinct bursts | +0.6 | +0.1 | +1.0 | +3.9 |

### Window alignment alone on today's registered models (tuning seeds; no retraining)

| model | 80 steps | 160 | 400 | Pd diff pp (400) | bursts diff pp (400) |
|---|---|---|---|---|---|
| Bandit | 1.11 [1.08, 1.14] | 1.10 [1.07, 1.13] | 1.07 [1.05, 1.09] | +1.0 | +1.0 |
| Q-learning | 1.17 [1.13, 1.21] | 1.16 [1.12, 1.20] | 1.19 [1.15, 1.23] | +2.4 | -2.8 |
| DQN | 1.03 [1.01, 1.05] | 1.06 [1.03, 1.10] | 1.04 [1.01, 1.07] | +0.5 | +0.1 |
| PPO | 1.11 [1.08, 1.14] | 1.13 [1.10, 1.16] | 1.15 [1.12, 1.19] | +1.4 | +0.4 |
