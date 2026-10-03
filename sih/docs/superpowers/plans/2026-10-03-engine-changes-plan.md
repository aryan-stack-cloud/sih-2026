# Engine changes: implementation plan

Spec: `sih/docs/superpowers/specs/2026-10-03-engine-changes-design.md` (binding). Clone: `C:/w/eng`,
branch `feat/engine-index-bandit-threat`. Tasks 1-4 are Python (Ai-ml-1), 5 is Java (Backend), 6 is
Frontend. The lead (not an implementer) edits `API_CONTRACT.md`, runs the confirmation evaluation and
the budget tuning run.

All paths below are relative to `C:/w/eng/sih` unless they start with `C:/`.

## Task 1: Index coverage-budget pass-through (Python)

**Files.** Modify `Ai-ml-1-Scheduler-Engine/ml/agents/index_agent.py` and
`Ai-ml-1-Scheduler-Engine/scripts/train_all.py`. Create
`Ai-ml-1-Scheduler-Engine/ml/tuning/index_budget.py`,
`Ai-ml-1-Scheduler-Engine/ml/configs/index_budgets.json`,
`Ai-ml-1-Scheduler-Engine/tests/test_index_budget.py`.

**Background.** Index derives its revisit deadline in `IndexAgent.from_scenario` as
`cycle / COVERAGE_BUDGET` (module constant 0.5, `index_agent.py` around lines 230-232).
`ml/configs/index_tuned_B.json` holds a tuned `coverage_budget`, but `scripts/train_all.py` (the
`algo == "index"` branch) builds the agent from the weights and `rho_min` only, so the budget is
dropped and every registered Index model uses 0.5. A saved Index model persists its `deadline_s`
(`IndexAgent.save`/`load`), so serving needs nothing else.

**Requirements.**
1. `IndexAgent.from_scenario(scenario, **overrides)` accepts `coverage_budget` as an override. Pop it
   before building the agent. Deadline precedence: an explicit `deadline_s` override wins, then
   `coverage_budget`, then the module constant `COVERAGE_BUDGET`. A budget outside `(0, 1]` raises
   `ValueError("coverage_budget must lie in (0, 1], got <value>")`. Set `agent.coverage_budget` on the
   returned instance to the budget that determined the deadline: the override when given, else the
   module constant `COVERAGE_BUDGET` (0.5), and `None` when the deadline came from an explicit
   `deadline_s`. Do NOT change the value of `COVERAGE_BUDGET`.
2. `IndexAgent` defines `describe()` twice (around lines 281 and 564); the later definition is the
   effective one. Add `"coverage_budget": self.coverage_budget` to the effective one. Do not remove
   or merge the duplicate (out of scope). Give `__init__` a line `self.coverage_budget = None` so the
   attribute always exists.
3. New module `ml/tuning/index_budget.py` with exactly these public names:
   - `BUDGETS_PATH`: `Path(__file__).resolve().parents[1] / "configs" / "index_budgets.json"`.
   - `load_budgets(path=None) -> dict[str, float]`: returns `{}` when the file is missing; otherwise
     reads `{"budgets": {"A": 0.35, ...}}` and returns that mapping. Each value must be a float in
     `(0, 1]` and each key one of `ml.utils.config.SCENARIO_IDS`, else `ValueError` naming the entry.
   - `budget_for(scenario_id: str, budgets: dict[str, float]) -> float | None`: the scenario's budget,
     or `None` when absent.
4. `ml/configs/index_budgets.json` initial content: a `"_comment"` string explaining that
   `scripts/tune_index_budget.py` writes this file and that scenarios not listed keep the 0.5
   default, plus `"budgets": {}`.
5. `scripts/train_all.py`, `algo == "index"` branch: `budget = budget_for(scenario_id, load_budgets())`.
   Pass `coverage_budget=budget` to `IndexAgent.from_scenario` only when `budget is not None`. Record
   the effective budget in `summary["hyperparams"]["coverage_budget"]` (`budget` if not None else the
   module default `COVERAGE_BUDGET`). Leave the weights and `rho_min` handling unchanged.

**Tests** (`tests/test_index_budget.py`, at least 8 cases, no network, no live registry; the root
`conftest.py` already points `ML_CHECKPOINT_DIR` at a temp directory):
- default: `IndexAgent.from_scenario(load_scenario("B"))` has `describe()["coverage_budget"] == 0.5`
  and a `deadline_slots` value consistent with `cycle / 0.5`.
- `coverage_budget=0.25` yields a deadline about twice the default one (assert the ratio within
  rounding, deriving the expectation from `from_scenario`'s own formula) and `describe()["coverage_budget"] == 0.25`.
- explicit `deadline_s` beats `coverage_budget`, and `describe()["coverage_budget"] is None`.
- budgets 0, -0.1 and 1.5 raise `ValueError`.
- `load_budgets` on a missing path returns `{}`; on a temp file it parses; it rejects a value of 1.2
  and an unknown scenario key.
- `budget_for` returns `None` for a scenario that is not in the mapping.
- a `train_all` level test: import `train_one` from `scripts/train_all.py` (use
  `importlib.util.spec_from_file_location` if `scripts` is not a package), monkeypatch
  `ml.tuning.index_budget.load_budgets` to return `{"B": 0.25}`, call
  `train_one("index", "B", timesteps=0, eval_episodes=1)`, and assert the returned/registered model's
  recorded hyperparameters contain `coverage_budget == 0.25`. If `train_one` imports `load_budgets`
  at module import time, patch the name in `train_all`'s namespace instead.

**Commands.** From `C:/w/eng/sih/Ai-ml-1-Scheduler-Engine`:
`python -m pytest tests/test_index_budget.py tests/test_index_agent_scenario.py tests/test_index_agent.py -q -p no:cacheprovider`

## Task 2: Bandit window scoring (Python)

**Files.** Modify `Ai-ml-1-Scheduler-Engine/ml/agents/bandit_agent.py`,
`Ai-ml-1-Scheduler-Engine/ml/training/trainer.py`, `Ai-ml-1-Scheduler-Engine/ml/inference/inference.py`.
Create `Ai-ml-1-Scheduler-Engine/tests/test_bandit_window.py`.

**Background.** The receiver covers K adjacent bands (wrapping), and the action names the start band.
`BanditAgent.q_values` returns one value per start band computed from that band alone, and
`BanditAgent.learn` updates only that band. The tested prototype (from the review) is:
`q(a) = mean over the K bands of the window of (phi_b . w + bias_b)`, and on learning,
`phi = mean of the window's feature rows`, `pred = phi . w + mean of the window's biases`,
`err = reward/reward_scale - pred`, `w += lr * err * phi`, `bias[window] += bias_lr * err`,
`visit_counts[window] += 1`. With K = 1 this is exactly today's agent.

**Requirements.**
1. `BanditAgent.__init__` gains `bandwidth_k: int = 1` (place it after `rng`, keyword-friendly).
   Validate `1 <= bandwidth_k <= num_bands`, else `ValueError`. Build
   `self._windows = (np.arange(n)[:, None] + np.arange(k)[None, :]) % n` (shape `(n, k)`).
2. `q_values(observation)`: `band_q = self._band_features(observation) @ self.weights + self.band_bias`;
   return `band_q[self._windows].mean(axis=1)`.
3. `learn(...)`: implement the window update above. The action is the start band
   (`action % num_bands` is already guaranteed by the caller).
4. `hyperparams()` adds `"bandwidth_k": self.bandwidth_k`. `load()` already passes the saved
   hyperparameters to the constructor, so a checkpoint saved without the key loads with K = 1 (today's
   behaviour). Do not change the npz layout otherwise.
5. `trainer.train()`: for `algorithm == "bandit"` only, set `merged["bandwidth_k"]` to
   `int((cfg.get("receiver") or {}).get("bandwidth_k", 1))` before `build_agent` (unless the caller
   already supplied one). It is then persisted in the registry's recorded hyperparameters through
   `merged`. Do not pass it for `q_learning`, `dqn` or `ppo`.
6. `inference._cold_agent`: for `policy == "bandit"`, derive K the same way `IndexAgent` does there
   (`load_scenario(scenario_id if scenario_id in SYNTHETIC_SCENARIOS else "D")`, `receiver.bandwidth_k`)
   and call `build_agent("bandit", num_bands, None, bandwidth_k=K)`. Other policies unchanged.

**Tests** (`tests/test_bandit_window.py`, at least 7 cases):
- K = 1 equivalence: for 50 random observations and a sequence of 100 random `learn` calls, a K=1
  `BanditAgent` produces the same q-values and weights as an inline reference implementation of the
  OLD formulas (copy them into the test), to `1e-12`.
- K = 2: for a hand-built observation, `q_values[a]` equals the mean of band `a` and band `a+1`'s
  individual values, including the wrap-around action `n-1`.
- K = 2 `learn`: both window bands' biases move by `bias_lr * err`, both visit counts increase by 1, and
  bands outside the window are untouched.
- `bandwidth_k` outside `[1, n]` raises `ValueError`.
- `save`/`load` round trip preserves `bandwidth_k` and the q-values.
- legacy load: save a K=1 agent, rewrite the saved npz's `hyperparams` JSON without the `bandwidth_k`
  key (`np.load` then `np.savez`), load it, and assert `bandwidth_k == 1`.
- `train("bandit", <scenario dict with receiver.bandwidth_k = 2>, episode_count=1, eval_episodes=1)`
  returns an agent with `bandwidth_k == 2` and `summary["hyperparams"]["bandwidth_k"] == 2`.

**Commands.** From `C:/w/eng/sih/Ai-ml-1-Scheduler-Engine`:
`python -m pytest tests/test_bandit_window.py tests/test_agents.py tests/test_api.py -q -p no:cacheprovider`
(`test_agents.py` and `test_api.py` must still pass; fix any assertion that listed the exact
hyperparameter dict only if it genuinely must now include `bandwidth_k`).

## Task 3: Threat-aware training environment (Python)

**Files.** Modify `Ai-ml-1-Scheduler-Engine/ml/environments/environment.py`. Create
`Ai-ml-1-Scheduler-Engine/tests/test_threat_aware_env.py`.

**Background.** `StateBuilder.band_priority_weight` (a float32 array, 1.0 per band) feeds the state
vector's priority column (`weight / 2.0`). The ground truth has `ground_truth.priority[t][band]`
(1.0 normal, 2.0 high, for the emitter active on that band at step t). The rule to mirror in the
Backend: after each scan, decay every weight toward its base value by a constant factor, then for each
detected band set the weight to the priority of the emitter that was detected there. Only bands that
yielded a detection reveal their priority, so nothing is leaked.

**Requirements.**
1. `EWEnvironment.__init__` gains `threat_aware: bool = False` and `priority_decay: float = 0.998`
   (validate `0 < priority_decay <= 1`), stored as attributes. `make_env` reads
   `config.get("threat_aware", False)` and `config.get("priority_decay", 0.998)` unless the caller's
   `overrides` already supply them.
2. In `reset()`: capture `self._base_priority = self.state_builder.band_priority_weight.copy()` and,
   when `threat_aware`, restore `band_priority_weight` to that base copy.
3. In `step()`, immediately after the periodicity features are set (`set_periodicity`) and before the
   history entry, when `self.threat_aware`: call a new method
   `_observe_priority(t, outcome.detected_bands)`:
   `w = band_priority_weight; w[:] = base + (w - base) * priority_decay`; then for each detected band
   `b`, `w[b] = float(self.ground_truth.priority[t][b])`.
4. With `threat_aware=False` no code path may touch `band_priority_weight`: observations and rewards
   must be identical to today's for the same seed and actions.

**Tests** (`tests/test_threat_aware_env.py`, at least 6 cases):
- flag off: after 200 round-robin steps the priority weights are all exactly the base values.
- flag on with `high_priority_fraction=1.0` (`make_env({**load_scenario("B"), "high_priority_fraction": 1.0}, seed=7, threat_aware=True)`):
  after a round-robin sweep for 300 steps at least one band's weight is greater than 1.0, and no
  weight ever exceeds 2.0 or falls below 1.0.
- `_observe_priority` directly: after `reset`, set `env.ground_truth.priority[0, 3] = 2.0`, call
  `env._observe_priority(0, [3])` -> weight 3 is 2.0; with `priority_decay=0.5`, calling
  `env._observe_priority(1, [])` twice gives 1.5 then 1.25.
- `reset()` restores the base weights between episodes.
- flag on does not change the reward or the first observation of an episode versus flag off (same
  seed, same actions) before any detection has happened (compare step 0 outputs).
- `make_env(config)` honours `config["threat_aware"] = True`.
- invalid `priority_decay` (0, 1.5) raises `ValueError`.

**Commands.** From `C:/w/eng/sih/Ai-ml-1-Scheduler-Engine`:
`python -m pytest tests/test_threat_aware_env.py tests/test_environment.py tests/test_reproducibility.py -q -p no:cacheprovider`

## Task 4: Index budget tuning tool (Python)

**Files.** Modify `Ai-ml-1-Scheduler-Engine/ml/tuning/index_budget.py` (created by Task 1). Create
`Ai-ml-1-Scheduler-Engine/scripts/tune_index_budget.py` and
`Ai-ml-1-Scheduler-Engine/tests/test_index_budget_selection.py`. Task 1 must be complete first.

**Background.** The spec's decision D2 fixes the selection rule. The repo's runner API:
`ml.evaluation.runner.run_policy(scenario, agent_factory, seeds=[...])` returns
`{"summary": {...pooled metrics...}}` with keys `pd`, `run_intercept_rate`, `ait_censored`,
`scan_efficiency`. `scripts/compare.py` shows how the fixed sweep is built
(`build_agent("baseline", bands, {"stride": K, "mode": "round_robin"})`) and how Index is built
(`IndexAgent.from_scenario(scenario, weights=..., rho_min=...)`).

**Requirements.**
1. In `ml/tuning/index_budget.py` add
   `choose_budget(candidates: dict[float, dict[str, float]], sweep: dict[str, float], margin: float = 0.0, default: float = 0.5) -> float`
   where each metrics dict has `pd` and `run_intercept_rate` (fractions in [0, 1]). Rule: feasible
   budgets are those whose `run_intercept_rate >= sweep["run_intercept_rate"] - margin`; among them take
   the highest `pd`; budgets whose `pd` is within 0.001 of the best count as tied and the LARGER budget
   wins; if no budget is feasible return `default`.
2. `scripts/tune_index_budget.py` CLI (argparse, `sys.path` fix like `compare.py`):
   `--scenarios A,B,C,D,E,F,G` (default all), `--budgets 0.5,0.35,0.25,0.2184,0.15,0.1`,
   `--seeds 2000-2009` (inclusive range or comma list), `--workers 1`, `--out` (default
   `BUDGETS_PATH`), `--dry-run` (print, do not write). For each scenario it evaluates the fixed sweep
   and Index (weights and `rho_min` from `ml/configs/index_tuned_B.json`, as `train_all.py` does) at each
   budget on the SAME seeds, using `run_policy`, then calls `choose_budget`. With `--workers > 1` use a
   `ProcessPoolExecutor` over `(scenario, budget)` jobs (a module-level worker function so it pickles
   on Windows). Output JSON: `{"_comment": ..., "rule": <one-sentence rule text>, "tuning_seeds": [...],
   "budgets": {scenario: chosen}, "table": {scenario: {"sweep": {...}, "<budget>": {...}}}}`; only
   `budgets` is read by `load_budgets`, and `load_budgets` must ignore the other keys.
3. Print a compact per-scenario table (budget, Pd, distinct bursts, intercept time) and the choice.

**Tests** (`tests/test_index_budget_selection.py`, at least 6 pure-function cases for `choose_budget`):
highest feasible Pd wins; an infeasible budget with the highest Pd is skipped; ties within 0.001 pick
the larger budget; nothing feasible returns the default; margin 0 is strict; the sweep's own coverage
equal to a candidate's is feasible. Add one CLI smoke test that runs `scripts/tune_index_budget.py` via
`subprocess` with `--scenarios B --budgets 0.5,0.25 --seeds 2000-2000 --dry-run` and asserts exit code
0 and that its stdout names the chosen budget (use `sys.executable`; allow up to 180 seconds).

**Commands.** From `C:/w/eng/sih/Ai-ml-1-Scheduler-Engine`:
`python -m pytest tests/test_index_budget_selection.py tests/test_index_budget.py -q -p no:cacheprovider`

## Task 5: Threat-aware plumbing in the Backend (Java)

**Files (all under `Backend/`).** Modify `src/main/java/com/rfscheduler/ml/StateBuilder.java`,
`service/SimulationRunner.java`, `service/SimulationService.java`, `experiments/ExperimentService.java`,
`dto/Requests.java`, `domain/SimulationEntity.java`, `domain/ExperimentEntity.java`,
`controller/SimulationController.java`, `controller/ExperimentController.java`. Create
`src/main/resources/db/migration/V3__threat_aware.sql` and tests under `src/test/java/com/rfscheduler/`.
(Packages: `com.rfscheduler.<package>`; files are in `Backend/src/main/java/com/rfscheduler/<package>/`.)

**Background.** The Backend builds the StateVector for Ai-ml-1 with `StateBuilder`, whose
`bandPriorityWeight` array is initialised to 1.0 and never changed (`setBandPriorityWeight` has no
caller). The rule from spec decision D5: after each scan, decay every weight toward 1.0 by 0.998, then
for each detected band set its weight to the priority of the emitter active there
(`GroundTruth.priorityAt(t, band)`). Requests use camelCase JSON (`durationSteps`); responses are
hand-built snake_case maps (`duration_steps`). JPA runs with `ddl-auto: validate` and Flyway owns the
schema (migrations V1, V2 exist).

**Requirements.**
1. `StateBuilder`: add `public static final double PRIORITY_DECAY = 0.998;` (comment: equals the
   Python environment's `priority_decay` default), `public void resetPriorityWeights()` (all 1.0),
   `public void decayPriorityWeights(double decay)` (`w = 1 + (w - 1) * decay`) and
   `public void observePriority(int band, double priority)` (sets the weight; ignore priorities below
   1.0). `reset()` also calls `resetPriorityWeights()`.
2. `SimulationRunner.RunRequest`: add a component `boolean threatAware`. Keep every existing
   constructor shape working (the 7-argument and 8-argument ones used by tests and services) with
   `threatAware = false`; keep `withoutPeriodicity()` preserving the flag. In the step loop, right after
   `stateBuilder.update(scanned, outcome.detectedBands());`, when `request.threatAware()`:
   `stateBuilder.decayPriorityWeights(StateBuilder.PRIORITY_DECAY);` then for each band in
   `outcome.detectedBands()`: `stateBuilder.observePriority(band, truth.priorityAt(t, band));`.
   Nothing changes when the flag is false.
3. Persistence: `V3__threat_aware.sql` adds `threat_aware BOOLEAN NOT NULL DEFAULT FALSE` to both
   `simulations` and `experiments` (SQL both PostgreSQL and H2 accept, like V1/V2). Add a `threatAware`
   boolean to `SimulationEntity` and `ExperimentEntity` mapped with
   `@Column(name = "threat_aware", nullable = false)`, with `isThreatAware()`/`setThreatAware(boolean)`.
4. API: `Requests.CreateSimulation`, `Requests.UpdateSimulation` and `Requests.CreateExperiment` each gain
   an optional `Boolean threatAware` (null means false / unchanged). Keep the old canonical arity
   available through an extra constructor so existing callers compile. `SimulationService.create`,
   `SimulationService.update` and `ExperimentService.create` take the new value; keep old overloads
   delegating with `false`/`null` if anything else calls them. `SimulationService.start` and
   `ExperimentService.execute` pass `entity.isThreatAware()` into the `RunRequest`.
5. Responses: `SimulationController.summary` and the experiment summary map include
   `"threat_aware": <boolean>`; the experiment results payload includes `"threat_aware"` next to its
   other top-level fields (`seeds`, `episodes`, `duration_steps`).

**Tests** (JUnit 5 + Mockito, like the existing tests; at least 8 cases):
- `StateBuilder`: initial weights 1.0; `observePriority(2, 2.0)` then `decayPriorityWeights(0.5)` gives
  1.5 for band 2 and 1.0 elsewhere; `reset()` restores 1.0; priority below 1.0 is ignored.
- Runner, flag on: use a stub `MlSchedulerClient` that records every `state` map it receives and returns
  round-robin bands (see `EndToEndSimulationTest` and `NoCompatibleModelFallbackTest` for how clients
  are stubbed), run a short simulation of scenario A or D with `threatAware = true` and a policy that
  uses the ML client, and assert that at least one later state has a `band_priority_weight` above 1.0
  and none exceeds 2.0. Same run with the flag off: every state's `band_priority_weight` is 1.0.
- Request records: a `CreateSimulation` JSON body without `threatAware` deserialises with
  `threatAware == null`; with `"threatAware": true` it is true (use Spring's `JsonMapper`/`ObjectMapper`
  the way other tests do, or a `@JsonTest`).
- Migration: following `SimulationModelMigrationTest`, assert V3 applies and the `threat_aware` column
  exists on both tables with default false.
- Controller/service level: creating a simulation with `threatAware=true` and reading it back returns
  `threat_aware: true` in the summary map; default is false.

**Commands.** From `C:/w/eng/sih/Backend` (Git Bash; the Maven wrapper is not present, use the installed
Maven): `export PATH="/c/Users/This PC/tools/apache-maven-3.9.16/bin:$PATH" && mvn -B -q -Dtest='StateBuilder*Test,ThreatAware*Test,SimulationModelMigrationTest,EndToEndSimulationTest,LiveSimulationStepTest' -Dsurefire.failIfNoSpecifiedTests=false test`
then, once, the whole quick suite:
`mvn -B -q -Dtest='!PeriodicityAcceptanceTest' -Dsurefire.failIfNoSpecifiedTests=false test`
(`PeriodicityAcceptanceTest` needs live services; never run it). With `-q` Maven prints nothing on
success; check `target/surefire-reports/*.txt` for the counts and report them.

## Task 6: Threat-aware toggle in the Frontend

**Files (all under `Frontend/src/`).** Modify `types/contract.ts`, `services/api/client.ts`,
`pages/DemoPage.tsx`, `pages/SimulationsPage.tsx`, and `styles.css` only if a new rule is unavoidable.

**Background.** The Backend (Task 5) accepts an optional boolean `threatAware` on `POST /simulations`,
`PUT /simulations/{id}` and `POST /experiments`, and returns `threat_aware` on simulations and
experiments. The control must be an explicit, labelled choice, off by default. Today only the Index
policy responds to it; the label must say so honestly.

**Requirements.**
1. Types: `CreateSimulationRequest.threatAware?: boolean`; `Simulation.threat_aware?: boolean`;
   `Experiment.threat_aware?: boolean`. `createExperiment`'s body type gains `threatAware?: boolean`.
2. `DemoPage`: a checkbox in the mission controls, label "Threat-aware", with a visible hint under or
   beside it: "Use the threat level of emitters already intercepted. Only the Index policy responds."
   State `threatAware` defaults to false, is disabled while a run is in progress, and is passed as
   `threatAware` to both `api.createSimulation` and `api.createExperiment` in `runDemo`. Replay
   (`runDemo(replay)`) must reuse the value used for that run (add it to the `DemoWorlds` record).
   When on, the status line and the results `sampleCaption` mention "threat-aware".
3. `SimulationsPage`: if it has a create form, add the same labelled checkbox (default off) and pass
   `threatAware`; if the page lists simulations, show "threat-aware" as a small tag when
   `threat_aware` is true. Do not redesign the page.
4. Accessibility: the checkbox has a real `<label>`; the hint is associated with it
   (`aria-describedby`). Reuse existing classes (`field`, `note`); add CSS only if there is no existing
   class that fits, using the existing colour tokens.
5. No change to anything else. The build must stay clean.

**Verification.** From `C:/w/eng/sih/Frontend`: `npm run build` (this runs `tsc -b && vite build`) with
no TypeScript errors. Do not stage `tsconfig.tsbuildinfo` or `dist/`. There is no unit-test framework in
this package and adding one is out of scope; describe in your report how you checked the wiring (for
example by reading the request body construction), and list the exact lines where `threatAware` is
sent.
