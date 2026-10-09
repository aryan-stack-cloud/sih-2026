# Round 3 screening (T = seeds 20000–20019, 20 paired worlds per scenario/horizon)

Reference = live registry Bandit checkpoints (read-only `resolve` + `load_agent`;
Scenario B reference is `model_bandit_0496bb32`). Candidates trained 20 episodes on
seeds 1042–1061, evaluated with a fresh deepcopy of the trained weights per world
(`learn=True, explore=False`), pooled counts, point estimates. Serving periodicity
estimator (Ai-ml-2 code in-process). No V2/C2 world was observed.

| Candidate | Adds to r2a_f backbone | R80 / R160 | B80 / B160 | dPd 80/160/400/full | dHPDR 80/160/400/full | dBursts 80/160/400/full | viol |
|---|---|---|---|---|---|---|---|
| `r3_p6_c1_k06` | poly_features 6 + cov 1.0 + age 0.06 | 1.39 / 1.25 | 1.33 / 1.25 | +3.1/+2.6/+1.2/−0.2 | +4.1/+1.6/+0.3/−1.8 | +0.5/+1.2/+3.8/+2.7 | 4.05 |
| `r3_p7_c1` | poly_features 7 + cov 1.0 | 1.42 / 1.27 | 1.39 / 1.26 | +3.5/+3.0/+1.7/+0.1 | +3.4/+0.9/−0.6/−1.6 | −1.7/−0.5/+1.6/+1.9 | 4.10 |
| `r3_p6` | poly_features 6 | 1.39 / 1.25 | 1.38 / 1.34 | +3.1/+2.8/+1.7/+0.2 | +4.2/+1.3/−0.1/−2.6 | −0.9/−0.4/+1.3/+0.6 | 4.34 |
| `r3_p6_k06` | poly_features 6 + age 0.06 | 1.46 / 1.26 | 1.31 / 1.13 | +3.8/+2.9/+2.1/+0.3 | +5.9/+1.7/+0.4/−1.0 | −1.4/−0.1/−0.6/−0.0 | 4.42 |
| `r3_p6_c1` | poly_features 6 + cov 1.0 | 1.46 / 1.28 | 1.42 / 1.36 | +3.8/+3.1/+1.9/−0.1 | +4.2/+1.6/−0.7/−2.8 | −2.8/−1.6/+0.2/+0.2 | 8.04 |
| `r3_c1` | cov 1.0 | 1.37 / 1.22 | 1.22 / 1.12 | +2.9/+2.1/+1.3/−0.2 | +3.9/+0.3/+0.3/−2.1 | +0.1/+1.0/+2.0/+2.0 | 8.83 |
| `r3_p6_c2` | poly_features 6 + cov 2.0 | 1.39 / 1.22 | 1.30 / 1.19 | +3.0/+2.1/+0.9/−0.4 | +3.7/+0.5/−1.9/−1.9 | −0.0/+0.6/+2.3/+3.3 | 9.16 |

R = mean over A–G of per-scenario pooled efficiency ratios (new/live); B = Scenario B
ratio; d* = mean over A–G of pooled percentage-point differences; viol = pre-registered
predicted-pass shortfall (bars R80/R160/B80/B160 ≥ 1.25, R400 ≥ 1.05, Rfull ≥ 1.014,
dPd ≥ 0.0, dHPDR ≥ +0.7, dBursts ≥ −1.5, no cell < 0.95). Stop rule: no finalist unless
one is within 1.0 of zero violation. Best is 4.05 → no finalist advances.

Illustrative T-only bootstrap (4000 resamples, tuning data — NOT a gate):
`r3_p6_c1_k06` R160 1.253 [1.211, 1.298], B160 1.247 [1.142, 1.360],
HPDR-full −1.80 [−3.31, −0.19]; `r3_p7_c1` R160 1.274 [1.227, 1.322],
B160 1.257 [1.066, 1.466], HPDR-full −1.63 [−2.99, −0.38].
Both would fail G1b (B160 lower end ≥ 1.20) and G3 (HPDR-full lower end ≥ −2.0)
on fresh worlds with high probability — V2 confirmation is not justified.

## Methodology corrections during screening (T only, V2/C2 untouched)

1. First screening run reused one agent object across horizons/worlds (online-learning
   weights accumulated across the 20 tuning worlds and across horizons). Ratios
   collapsed (R160 ≈ 1.0 for all). Fixed to a fresh deepcopy of the post-training
   weights per world, matching deployment (`_fresh_session_copy` semantics) and the
   round-2 "one fresh agent per world" rule. All numbers above use the fixed harness.
2. First ranking compared candidate mean-of-rates against live pooled counts, which
   overstated full-length HPDR losses (−5 to −6 pp). Fixed to pooled counts on both
   arms (same estimator as the gate bootstrap). Full-HPDR points are −1.0 to −2.8 pp.
3. EcoQoS throttling: background-shell workers ran at ~0 CPU until exempted via
   `SetProcessInformation(ProcessPowerThrottling)`; 8 workers then finished 56
   train+eval jobs in ~14 min. Live services were never restarted or reconfigured.

## Side observation (single-run, unconfirmed)

A freshly trained default-recipe Bandit beat the live Scenario B checkpoint on T at
80 steps (0.305 vs 0.239, ratio 1.27) but not at 160 (1.05). One training draw each —
this may be retraining noise or live-checkpoint staleness (live weights predate the
state-builder/serving fixes). It is NOT a confirmed gain and must not be presented
as one; a multi-draw retraining study would be needed.
