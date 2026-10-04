# Efficiency uplift for the four main models: pre-registered gate

Status: **pre-registered**. This file is committed before any confirmation run (seeds C1) and before the final models were trained. Request (project owner, 4 Oct 2026): "increase the efficieny at least by 20 percent more of all the
models the main models like bandit , q learning , dqn , ppo  do whatever you like to".

## Interpretation (rulings, each with the cost if it is wrong)

| # | Ruling | Cost if wrong |
|---|---|---|
| R1 | "Efficiency" is listening (scan) efficiency: useful scans / total scans, the share of receiver looks that land on a transmitting band (the Dashboard's efficiency). | If the owner meant Pd or distinct bursts, the headline number does not answer the question; both are reported next to it. |
| R2 | "At least 20 percent more" is **relative**: new / today >= 1.20 (not +20 percentage points). | An absolute +20 pp is out of reach for most cells (see the ceilings); a relative +20% is the reading under which the request can be met at all. |
| R3 | "Today" is the model the live registry serves for each (policy, scenario) at commit `ee2ee6f`, resolved with `ModelRegistry.resolve`, evaluated on the same worlds as the candidate. | If the owner meant "20% above the fixed sweep", today's four models already clear it at 160+ steps; the sweep is reported next to every number. |
| R4 | The claim is made at the demo horizons **80, 160 and 400 steps** (the Dashboard runs 80-160 steps live; 400 is the first length at which the learned models settle). Headline per horizon: mean over the seven scenarios A-G of the per-scenario ratio (each scenario counts equally); the claim holds when the lower end of the paired 95% bootstrap interval is >= 1.20. | At full length (2000-3000 steps) +20% is not reachable for every cell: a clairvoyant policy that knows the whole spectrum's previous step reaches 94/60/78/80/86/45/71% on A-G (a fixed best window reaches 97/60/69/78/94/50/61%), and today's Bandit and Q-learning already sit at 44-78%. Full length is therefore reported and guarded, not required to be +20%. |
| R5 | Detection must not be bought with efficiency: for every model and every horizon (80, 160, 400, full) the mean-over-scenarios difference (new minus today) in Pd and in high-priority detection (HPDR) has a lower interval end >= -1.0 pp, and full-length efficiency's lower end is >= 0.99 of today's. Distinct bursts (coverage, the problem statement's primary objective) are gated only where the chosen recipe kept them on the tuning seeds and are reported everywhere. | A model could look 20% better by camping on the busiest band; Q-learning and DQN already camp (distinct bursts 22% against the sweep's 34%). If the owner wants coverage gated for the Bandit and Q-learning too, their +20% at 400 steps is not reachable in the screened model family. |
| R6 | Per-scenario cells are reported with their intervals. The only per-cell gate is E4 below (no cell significantly more than 5% under today's); a +20% per cell is not required. | A single scenario can be only a few percent better than today's; the table shows it. |

## Seed sets (new, never used before)

| Set | Seeds | Worlds per scenario | Use |
|---|---|---|---|
| T (tuning/screening) | 20000-20019 | 20 | choose the recipe of each model; the baseline numbers of today's models below |
| C1 (confirmation) | 21000-21019 | 20 | the gate; looked at once, after this file is committed |
| C2 (reserve) | 22000-22019 | 20 | only if C1 fails and the owner approves a second attempt |

Training seeds are the registry's own (`base + 1000 + i` = 1042 upward, extended for DQN/PPO); they are disjoint from T, C1, C2.
Exploratory runs before this gate (on seeds 6000-7019, 12000-14019 and the smoke seeds 15000-15002) informed the idea of
neighbour alignment and are not reused.

## Today's models on the tuning seeds (listening efficiency %, mean over the seven scenarios, 20 paired worlds each)

| Arm | 80 steps | 160 | 400 | full length |
|---|---|---|---|---|
| fixed sweep | 26.8 | 27.0 | 27.0 | 26.9 |
| Bandit | 30.9 | 38.2 | 48.3 | 56.7 |
| Q-learning | 40.9 | 45.1 | 49.0 | 52.9 |
| DQN | 41.5 | 43.7 | 45.9 | 46.5 |
| PPO | 29.4 | 31.1 | 32.2 | 34.1 |
| Index (for reference) | 27.3 | 27.6 | 32.0 | 49.5 |

The +20% targets at 80/160/400 steps are therefore Bandit 37.1/45.8/58.0, Q-learning 49.1/54.1/58.8, DQN 49.8/52.4/55.1 and PPO 35.3/37.3/38.6.

## One recipe per model, and what is gated

The levers that raise efficiency (looking at busy bands and at both bands of the window) can spend coverage (time on bands that
are quiet right now). On the tuning seeds every recipe was screened for both effects, and the selection (below) picked, per model,
the recipe with the highest weakest-demo-horizon uplift that keeps Pd, HPDR, full-length efficiency and every scenario where they
are. Two outcomes were possible and both are pre-registered:

* the chosen recipe **also keeps distinct bursts** on the tuning seeds (DQN and PPO): the coverage check B1 is part of its gate;
* the chosen recipe **spends distinct bursts** (Bandit and Q-learning: no screened recipe reached +20% at 400 steps without it): B1
  is reported with its numbers, not gated, and the report states the cost next to the gain.

## Arms

| Arm | What | How it is built |
|---|---|---|
| sweep | fixed round-robin sweep, stride K | `build_agent("baseline", ...)` |
| today | the registered model of each (policy, scenario) | live registry, live checkout at `ee2ee6f`, `ModelRegistry.resolve`, a fresh agent per world |
| new | the recipes below | Bandit and Q-learning trained by `scripts/train_all.py` of branch `feat/efficiency-boost` into a sandbox registry; DQN and PPO are the screened artifacts (trained by the same trainer functions with the same hyperparameters) registered into the same sandbox registry with `align_window` set; loaded with `ModelRegistry.resolve`, a fresh agent per world |

Every arm is run exactly as a fresh Backend simulation would be: the serving periodicity estimator, `learn=True, explore=False`,
one fresh agent per world, the same worlds for every arm (paired).

## Recipes (chosen on the tuning seeds T, before any confirmation run)

All four are the engine's own options (`ml/agents/*`, `ml/configs/*.yaml` of this branch), trained by the engine's trainer with the
registry's training seeds. Every option defaults to the original behaviour; the numbers on T are in the report.

| Model | Recipe | Screened candidate |
|---|---|---|
| Bandit | pairwise products of all seven band features (`poly_degree 2`, `poly_features 7`), the next band's time-since-scan / detection EWMA / consecutive misses as extra features that also enter the products (`neighbor_features [0,1,2]`, `poly_neighbor`), `align_window`, `eff_beta 4`, `cov_beta 2`, 30 training episodes | `b6_e4c2_ep30` |
| Q-learning | six EWMA bins (edges 0.05 0.15 0.3 0.5 0.75), the next band's EWMA in the key (edges 0.15 0.4), `align_window`, `eff_beta 4`, `cov_beta 2`, 80 training episodes of mixed length (80, 160, 400, full) | `q4_e4c2` |
| DQN | the permutation-equivariant policy (hidden 64), reward x0.1, `cov_beta 3`, `align_window`, 100,000 base timesteps (scaled with the band count as before) | `dqn_eq_c3` + alignment |
| PPO | the permutation-equivariant policy (hidden 64), reward x0.1, `cov_beta 10`, `align_window`, 100,000 base timesteps (scaled as before) | `ppo_eq_c10` + alignment |

`align_window` = when the receiver window is two bands wide, take the window `(a-1, a)` instead of `(a, a+1)` when band `a-1`'s detection
EWMA is higher than band `a+1`'s (the target band `a` stays in the window either way). `eff_beta` adds `eff_beta * detected bands / scanned bands`
to the reward the learner sees; `cov_beta` adds `cov_beta * mean staleness (age/32, capped at 1) of the scanned bands`.



## Selection rule (on the tuning seeds T, per model)

1. Candidates are the recipes screened on T (listed in the results section of the final report, all of them, including the ones that
   were not chosen).
2. A candidate is *feasible* when, on T and as point estimates over the seven scenarios: Pd and HPDR differences versus today are
   >= -0.5 pp at 80, 160, 400 and full length; full-length efficiency ratio >= 0.99; and no scenario's efficiency ratio at 80/160/400
   is below 0.95. A feasible candidate that also has distinct-burst differences >= -0.5 pp at all four horizons is *coverage-keeping*.
3. Among the feasible candidates the one with the highest weakest-demo-horizon efficiency ratio wins; ties within 0.01 go to the
   smaller `eff_beta`, then the larger `cov_beta`. (Applying the same rule to the coverage-keeping candidates alone finds none for the
   Bandit and Q-learning; for DQN and PPO the winner is coverage-keeping.)

## Gate (on the confirmation seeds C1; the headline numbers are computed once)

For each algorithm the verdict is PASS only if all of these hold; each is evaluated with the paired bootstrap
(4,000 resamples, 95% percentile, generator seed 20261003, worlds resampled independently per scenario):

* **E1 efficiency**: mean over the seven scenarios of eff(new)/eff(today) has a lower interval end >= 1.20 at each of 80, 160 and 400 steps.
* **E2 detection**: the mean-over-scenarios differences (new minus today) in Pd and in HPDR have a lower end >= -1.0 pp at 80, 160, 400 and full length.
* **E3 full length**: the same efficiency ratio at full length has a lower end >= 0.99.
* **E4 no hidden regression**: in every scenario at 80, 160 and 400 steps the upper end of the efficiency ratio's interval is >= 0.95 (no cell is significantly more than 5% below today's).
* **B1 coverage** (gated for DQN and PPO, whose chosen recipes kept coverage on T; reported for Bandit and Q-learning): the mean-over-scenarios difference in distinct bursts has a lower end >= -1.0 pp at all four horizons.

A failed check is reported with its numbers and nothing is relaxed afterwards; a model that fails does not ship. If C1 fails for a
model, a second attempt needs the owner's approval and uses C2.

## Procedure and what is touched

Screening, selection and confirmation are offline harness runs on this clone's code; the live registry is only read. Nothing is
merged to `master`, no model is registered in the live registry and the live stack is not touched until the owner has seen the
report and said which models to register.

