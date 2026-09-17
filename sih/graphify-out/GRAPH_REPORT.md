# Graph Report - sih  (2026-09-12)

## Corpus Check
- 165 files · ~83,408 words
- Verdict: corpus is large enough that graph structure adds value.

## Summary
- 1906 nodes · 4082 edges · 95 communities (87 shown, 8 thin omitted)
- Extraction: 93% EXTRACTED · 7% INFERRED · 0% AMBIGUOUS · INFERRED: 271 edges (avg confidence: 0.85)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `c4c3c3e9`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- Emitter
- periodicity/api/main.py
- ExperimentEntity
- WebSocketHub
- BufferStore
- test_turing_replay.py
- ApiResponse
- test_periodicity_boundary.py
- SimulationEntity
- estimate_period
- Ai-ml-2-Periodicity-Estimator/tests/test_api.py
- .run
- client.ts
- test_agents.py
- SimulationService
- load_scenario
- service.py
- package.json
- RewardFunction
- contract.ts
- test_environment.py
- Ai-ml-1-Scheduler-Engine/tests/test_api.py
- ml/api/main.py
- Ai-ml-1 Scheduler Engine — implementation notes
- test_prediction.py
- SimulationController
- useStore
- inference.py
- ml/utils/logging.py
- compilerOptions
- Agent
- make_env
- environment.py
- EpsilonSchedule
- test_acceptance.py
- Build Plan — 10 Levels
- EWEnvironment
- ModelRegistry
- periodicity_estimator.py
- BanditAgent
- org.springframework.http.ResponseEntity
- GroundTruth
- DeepRLAgent
- QLearningAgent
- .start
- Build Plan — 10 Levels
- Receiver
- Build Plan — 10 Levels
- DemoPage.tsx
- WebSocketConfig
- StateBuilder
- runner.py
- EstimatorConfig
- API_CONTRACT.md — Single Source of Truth
- API_CONTRACT.md — Single Source of Truth
- API_CONTRACT.md — Single Source of Truth
- MlPeriodicityClient
- StateBuilder
- BaselineScanner
- SimulationConnection
- ApiException
- SimulationRunner.java
- PeriodicityAcceptanceTest.java
- make_seed_bundle
- MlSchedulerClient
- Running the system
- .degradesGracefully
- SimulationClock
- RewardContext
- Intelligent RF Spectrum Scan Strategy — Build Scaffold
- RfSchedulerApplication
- .delete
- CLAUDE.md
- com.rfscheduler:rf-scheduler-backend

## God Nodes (most connected - your core abstractions)
1. `ApiResponse` - 51 edges
2. `SimulationService` - 41 edges
3. `estimate_period()` - 40 edges
4. `SimulationEntity` - 40 edges
5. `MlSchedulerClient` - 40 edges
6. `Agent` - 36 edges
7. `EWEnvironment` - 36 edges
8. `ExperimentEntity` - 36 edges
9. `BanditAgent` - 35 edges
10. `make_env()` - 32 edges

## Surprising Connections (you probably didn't know these)
- `fail()` --uses--> `ErrorBody`  [INFERRED]
  Ai-ml-2-Periodicity-Estimator/periodicity/api/main.py → Ai-ml-1-Scheduler-Engine/ml/contract.py
- `ok()` --uses--> `SuccessEnvelope`  [INFERRED]
  Ai-ml-2-Periodicity-Estimator/periodicity/api/main.py → Ai-ml-1-Scheduler-Engine/ml/contract.py
- `fail()` --uses--> `ErrorEnvelope`  [INFERRED]
  Ai-ml-2-Periodicity-Estimator/periodicity/api/main.py → Ai-ml-1-Scheduler-Engine/ml/contract.py
- `health()` --uses--> `HealthResponse`  [INFERRED]
  Ai-ml-2-Periodicity-Estimator/periodicity/api/main.py → Ai-ml-1-Scheduler-Engine/ml/contract.py
- `test_observation_shape_matches_the_declared_space()` --uses--> `StateBuilder`  [INFERRED]
  Ai-ml-1-Scheduler-Engine/tests/test_environment.py → Ai-ml-1-Scheduler-Engine/ml/environments/state.py

## Import Cycles
- None detected.

## Communities (95 total, 8 thin omitted)

### Community 0 - "Emitter"
Cohesion: 0.05
Nodes (69): _allocate_classes(), _assign_bands(), build_emitters(), Emitter, ndarray, _randomize_params(), Emitter behavior classes (PRD Section 8.3). Five strategy objects, one per…, Instantiate a scenario emitter population from a behavior-class mix. ``mix``… (+61 more)

### Community 1 - "periodicity/api/main.py"
Cohesion: 0.06
Nodes (63): correlation_and_timing(), fail(), health(), lifespan(), ok(), on_http_error(), on_unhandled(), on_validation_error() (+55 more)

### Community 2 - "ExperimentEntity"
Cohesion: 0.10
Nodes (4): ExperimentEntity, Progress, jakarta.persistence.Entity, jakarta.persistence.Table

### Community 3 - "WebSocketHub"
Cohesion: 0.19
Nodes (9): Override, SimulationWebSocketHandler, WebSocketHub, org.springframework.stereotype.Component, org.springframework.web.socket.CloseStatus, org.springframework.web.socket.handler.TextWebSocketHandler, org.springframework.web.socket.TextMessage, org.springframework.web.socket.WebSocketSession (+1 more)

### Community 4 - "BufferStore"
Cohesion: 0.06
Nodes (35): BufferKey, BufferStore, DetectionBuffer, Per-(simulation_id, band_id) detection-timestamp ring buffers (Ai-ml-2 Level…, Thread-safe collection of per-(simulation_id, band_id) buffers., A copy of one band's history, so the estimator can fit without holding the lock., Clear every band of one simulation. Called on simulation reset., Bounded history of ACTIVATION START times for one band of one simulation. THE… (+27 more)

### Community 5 - "test_turing_replay.py"
Cohesion: 0.08
Nodes (45): build_occupancy(), build_replay_ground_truth(), download_pulse_trains(), extract_pdw_features(), load_replay_scenario(), map_frequencies_to_bands(), _match(), _normalise() (+37 more)

### Community 6 - "ApiResponse"
Cohesion: 0.15
Nodes (8): ModelController, SchedulerController, ApiResponse, EvaluateModel, TrainModel, SuppressWarnings, com.fasterxml.jackson.annotation.JsonInclude, org.springframework.web.bind.annotation.GetMapping

### Community 7 - "test_periodicity_boundary.py"
Cohesion: 0.07
Nodes (27): LocalPeriodicityProvider, NullPeriodicityProvider, PeriodicityProvider, ndarray, Where ``periodicity_phase`` and ``periodicity_confidence`` come from. READ THIS…, Debug view, mirroring Ai-ml-2's ``/internal/periodicity/state`` shape., Supplies the two periodicity features for every band at time t., Returns ``(phase, confidence)``, each shape ``(num_bands,)``, values in [0, 1]. (+19 more)

### Community 8 - "SimulationEntity"
Cohesion: 0.14
Nodes (3): SimulationEntity, Scenario, org.springframework.transaction.annotation.Transactional

### Community 9 - "estimate_period"
Cohesion: 0.08
Nodes (35): Train against an EWEnvironment. This is the only place the policy changes., estimate_period(), independent_trials(), How many *independent* periods the search effectively tried. Candidate periods…, Fit a period to one band's detection history., _false_positive_rate(), gen_agile(), gen_fixed() (+27 more)

### Community 10 - "Ai-ml-2-Periodicity-Estimator/tests/test_api.py"
Cohesion: 0.08
Nodes (31): clean_state(), client(), feed(), fixture, TestClient, Contract tests against API_CONTRACT.md Section 5 (Ai-ml-2 Levels 1, 3, 6, 8)., These names are consumed verbatim by the Backend's StateBuilder., The Backend asks for every band before every decision, not just the interesting… (+23 more)

### Community 11 - ".run"
Cohesion: 0.07
Nodes (20): RewardContext, RewardFunction, RewardResult, RewardWeights, DetectionOutcome, BaselineScheduler, Mode, FIXED_ORDER (+12 more)

### Community 12 - "client.ts"
Cohesion: 0.12
Nodes (32): activateModel(), ApiRequestError, compareExperiments(), createExperiment(), createSimulation(), deleteSimulation(), evaluateModel(), experimentMetrics() (+24 more)

### Community 13 - "test_agents.py"
Cohesion: 0.11
Nodes (27): observation(), ndarray, parametrize, Agent behavior: convergence, exploration, checkpointing (Ai-ml-1 Levels 3, 7)., Two bands with identical features must share one table entry, or the table…, The bootstrap term is what the bandit cannot represent. optimistic_init must be…, A minimal observation with a chosen detection-rate profile., Open loop means open loop -- feedback must not change the scan order. (+19 more)

### Community 14 - "SimulationService"
Cohesion: 0.14
Nodes (12): HealthController, ExperimentService, ExperimentRepository, SimulationRepository, SimulationRunner, SimulationService, org.slf4j.Logger, org.springframework.core.task.TaskExecutor (+4 more)

### Community 15 - "load_scenario"
Cohesion: 0.12
Nodes (28): null_periodicity_env(), Same scenario with the periodicity features pinned to zero. Used for the PRD…, evaluate(), Any, SB3 path. Trains on one seed's environment for total_timesteps. A single…, Score a trained agent on a scenario's evaluation seeds. Online learning stays…, Train one policy on one scenario and evaluate it on held-out seeds. Mirrors the…, train() (+20 more)

### Community 16 - "service.py"
Cohesion: 0.10
Nodes (16): PeriodEstimate, The fitted period for one band, or an explicit "no claim"., phase_at(), Prediction, Fraction of the cycle elapsed at ``now``, in [0, 1). This is the…, The Section 5 predict response, plus diagnostics the state endpoint exposes., PeriodicityService, The estimator service: buffers + fitting + a cache, behind the Section 5… (+8 more)

### Community 17 - "package.json"
Cohesion: 0.07
Nodes (28): dependencies, react, react-dom, zustand, description, devDependencies, @types/react, @types/react-dom (+20 more)

### Community 18 - "RewardFunction"
Cohesion: 0.13
Nodes (30): DetectionOutcome, Per-band detection classification for one step, plus the derived reward inputs., Reward function -- PRD Equation 10.1 / ML-003. r(t) = w1*D(t) + w2*P(t)*D(t) -…, w1..w6 of Equation 10.1. Non-negative by definition., Computes r(t) and reports each term of Equation 10.1 separately., RewardFunction, RewardWeights, context() (+22 more)

### Community 19 - "contract.ts"
Cohesion: 0.12
Nodes (25): API_BASE, ConnectionCallbacks, ConnectionState, StoreState, ApiEnvelope, ApiError, BEHAVIOR_CLASSES, BehaviorClass (+17 more)

### Community 20 - "test_environment.py"
Cohesion: 0.09
Nodes (19): StateVector, Configurable receiver parameters (PRD Section 9.2)., Whether a step that retunes can still yield a valid observation., ReceiverConfig, Convenience for the inference path: StateVector JSON -> agent input vector., vector_from_contract(), parametrize, EWEnvironment: Gymnasium conformance, contract shape, receiver physics (Ai-ml-1… (+11 more)

### Community 21 - "Ai-ml-1-Scheduler-Engine/tests/test_api.py"
Cohesion: 0.07
Nodes (17): client(), decide_body(), fixture, parametrize, TestClient, Contract tests against API_CONTRACT.md Section 4 (Ai-ml-1 Levels 1, 4, 5, 6).…, extra='forbid' is what catches Backend/Ai-ml-1 contract drift at the boundary., /internal/models/{id}/activate: 'deactivates previous active model of same… (+9 more)

### Community 22 - "ml/api/main.py"
Cohesion: 0.06
Nodes (66): activate_model(), correlation_and_timing(), decide(), evaluate_model(), fail(), get_model(), health(), learn() (+58 more)

### Community 23 - "Ai-ml-1 Scheduler Engine — implementation notes"
Cohesion: 0.04
Nodes (44): 0. Domain Map, 1. Standard Envelope (all public + internal REST responses), 2. Public REST API (Backend ⇄ Frontend), 3. WebSocket Contract (Backend ⇄ Frontend), 4. Internal REST — Backend ⇄ Ai-ml-1 (Scheduler Engine), 5. Internal REST — Backend ⇄ Ai-ml-2 (Periodicity Estimator), 6. Shared Enums & IDs (must match byte-for-byte across all four domains), 7. Docker Compose Ports (must match across all READMEs) (+36 more)

### Community 24 - "test_prediction.py"
Cohesion: 0.15
Nodes (23): next_activation(), predict(), Half-width of the predicted window, from the circular spread of the fit., The first predicted activation strictly after ``now``. Anchored on…, Build the Section 5 prediction for one band at time ``now``., window_halfwidth(), clean(), parametrize (+15 more)

### Community 25 - "SimulationController"
Cohesion: 0.14
Nodes (15): ExperimentController, MetricsController, SimulationController, CreateExperiment, CreateSimulation, ManualScan, ReceiverConfigRequest, Requests (+7 more)

### Community 26 - "useStore"
Cohesion: 0.16
Nodes (17): App(), Tab, TABS, ExperimentsPage(), HEADLINE, HealthPanel(), LiveSimulationPage(), ModelsPage() (+9 more)

### Community 27 - "inference.py"
Cohesion: 0.08
Nodes (15): new_decision_id(), ActionSpaceSpec, Action space (ML-002 / API_CONTRACT.md Section 4). MVP and V1 -- bandit and…, Describes the action space and converts between agent actions and contract…, Agent action -> ``(next_band, dwell_time)``; dwell is None in the MVP space., Agent action -> the ``action`` object of ``/internal/decide``., The contract's ``action`` object -> an agent action., InferenceEngine (+7 more)

### Community 28 - "ml/utils/logging.py"
Cohesion: 0.19
Nodes (10): lifespan(), FastAPI, configure(), get_logger(), JsonFormatter, Logger, LogRecord, Structured JSON logging with correlation-ID passthrough (NFR-008). Every log… (+2 more)

### Community 29 - "compilerOptions"
Cohesion: 0.09
Nodes (22): compilerOptions, esModuleInterop, isolatedModules, jsx, lib, module, moduleResolution, noEmit (+14 more)

### Community 30 - "Agent"
Cohesion: 0.08
Nodes (23): Agent, ndarray, Path, Common agent interface. Every policy -- baseline, bandit, Q-Learning, DQN --…, Base class for scan-decision policies., Choose the next band to tune to., Consume one (s, a, r, s') transition. No-op for policies that do not learn., Hook for per-episode exploration decay and any per-episode counters. (+15 more)

### Community 31 - "make_env"
Cohesion: 0.19
Nodes (21): make_env(), Build an EWEnvironment from a scenario config dict…, Run one full episode and score it. ``learn=False`` gives a clean evaluation…, run_episode(), env(), fixture, parametrize, Reproducibility and regression guards (NFR-006, Ai-ml-1 Level 8,… (+13 more)

### Community 32 - "environment.py"
Cohesion: 0.10
Nodes (15): EWEnvironment -- the Gymnasium environment (Ai-ml-1 README, Level 2). One…, DetectionEngine, Observation, ndarray, Receiver, Scanner and DetectionEngine (PRD Section 9). The receiver is what…, Holds instantaneous bandwidth, dwell time, tuning delay and detection threshold., Point the receiver at a new block. Returns True if this was an actual retune., Integer cost of reaching ``band`` from the current tuning, for the StateVector. (+7 more)

### Community 33 - "EpsilonSchedule"
Cohesion: 0.12
Nodes (13): Contextual multi-armed bandit -- the MVP scheduler (PRD Section 10.1, Ai-ml-1…, epsilon_greedy(), EpsilonSchedule, ndarray, Shared exploration/exploitation strategies (Ai-ml-1 README, ml/algorithms/).…, Per-episode epsilon decay. ``mode="exponential"`` eps = max(end, start *…, Argmax with probability 1-eps, uniform random otherwise. Ties in the argmax are…, With optimistic init every arm starts tied; argmax would freeze on band 0. (+5 more)

### Community 34 - "test_acceptance.py"
Cohesion: 0.26
Nodes (17): parametrize, random_baseline(), The MVP acceptance gate (Ai-ml-1 Level 6 DoD / PRD Phase 4 sign-off). Ai-ml-1…, Pins the known trade-off so it stays honest and visible. With instantaneous…, Same policy, same seeds, same spectrum -- only the two Ai-ml-2 columns differ.…, The Level 6 / Phase 4 criterion, against the reference the spec names., The harder reference: the legacy open-loop scanner this project exists to…, A policy that simply lowered its bar would win Pd and lose the point. (+9 more)

### Community 35 - "Build Plan — 10 Levels"
Cohesion: 0.05
Nodes (38): 0. Domain Map, 1. Standard Envelope (all public + internal REST responses), 2. Public REST API (Backend ⇄ Frontend), 3. WebSocket Contract (Backend ⇄ Frontend), 4. Internal REST — Backend ⇄ Ai-ml-1 (Scheduler Engine), 5. Internal REST — Backend ⇄ Ai-ml-2 (Periodicity Estimator), 6. Shared Enums & IDs (must match byte-for-byte across all four domains), 7. Docker Compose Ports (must match across all READMEs) (+30 more)

### Community 36 - "EWEnvironment"
Cohesion: 0.13
Nodes (10): ndarray, EWEnvironment, GroundTruth, ndarray, ReceiverConfig, RewardWeights, The current state as the API_CONTRACT.md Section 4 StateVector., Bandwidth-constrained scan scheduling over a synthetic RF spectrum. (+2 more)

### Community 37 - "ModelRegistry"
Cohesion: 0.18
Nodes (12): new_model_id(), ModelRegistry, Any, Path, Model registry -- registration, versioning, activation and rollback (Ai-ml-1…, Rehydrate a registered model into a ready-to-serve agent., Versioned store of trained scheduler models., Persist a trained agent and record its metadata. (+4 more)

### Community 38 - "periodicity_estimator.py"
Cohesion: 0.13
Nodes (19): cluster_activations(), _mean_phase(), _no_estimate(), _prefer_fundamental(), ndarray, Periodicity estimation from sparse detection timestamps (Ai-ml-2 Levels 4, 5,…, p-value of the Rayleigh test of circular uniformity, for ONE pre-specified…, Confidence that this concentration is real, corrected for the look-elsewhere… (+11 more)

### Community 39 - "BanditAgent"
Cohesion: 0.17
Nodes (8): BanditAgent, ndarray, Path, Online least-squares update on the chosen arm only. Bandit semantics: we…, The learned rule, in words. Useful for the demo and for sanity-checking…, Linear contextual bandit with shared feature weights and per-band value…, Slice the observation into ``(num_bands, FEATURE_DIM)``. Layout is fixed by…, New episode: keep the learned rule, forget which band was which. The shared…

### Community 40 - "org.springframework.http.ResponseEntity"
Cohesion: 0.26
Nodes (10): ApiError, GlobalExceptionHandler, org.springframework.http.converter.HttpMessageNotReadableException, org.springframework.http.ResponseEntity, org.springframework.web.bind.annotation.ExceptionHandler, org.springframework.web.bind.annotation.RestControllerAdvice, org.springframework.web.bind.MethodArgumentNotValidException, org.springframework.web.bind.MissingServletRequestParameterException (+2 more)

### Community 41 - "GroundTruth"
Cohesion: 0.05
Nodes (9): MetricsSummary, MetricsEngine, Emitter, EmitterBehavior, EmitterFactory, Emitter, GroundTruth, GroundTruth (+1 more)

### Community 42 - "DeepRLAgent"
Cohesion: 0.22
Nodes (5): DeepRLAgent, Any, Path, Wraps an SB3 DQN or PPO model behind the shared Agent interface., No-op. SB3 owns its own replay/rollout buffer; see the module docstring.

### Community 43 - "QLearningAgent"
Cohesion: 0.25
Nodes (5): ndarray, Path, QLearningAgent, Tabular Q-Learning over discretised per-band context., One discretised context key per band. Features are already normalised to [0, 1].

### Community 44 - ".start"
Cohesion: 0.11
Nodes (6): RunResult, StepFrame, LiveSimulation, StepListener, Override, SimulationEventPublisher

### Community 45 - "Build Plan — 10 Levels"
Cohesion: 0.10
Nodes (19): Backend — Spring Boot System of Record, Build Plan — 10 Levels, Core entities, Database schema (Flyway migrations), Folder structure to generate, Level 10 — Testing, observability, demo polish, Level 1 — Repo & scaffold, Level 2 — Simulation engine core (+11 more)

### Community 46 - "Receiver"
Cohesion: 0.10
Nodes (5): Receiver, ReceiverConfig, Scenario, Scenario, ScenarioLibrary

### Community 47 - "Build Plan — 10 Levels"
Cohesion: 0.12
Nodes (15): Build Plan — 10 Levels, Folder structure to generate, Frontend — Test Harness Only (NOT the final UI), Level 10 — Contract regression pass, Level 1 — Project scaffold, Level 2 — Simulations CRUD test page, Level 3 — Lifecycle controls, Level 4 — Emitters & receiver test page (+7 more)

### Community 48 - "DemoPage.tsx"
Cohesion: 0.18
Nodes (12): ComparisonTable(), LiftChart(), LiftRow, CellState, classify(), FILL, Waterfall(), DemoPage() (+4 more)

### Community 49 - "WebSocketConfig"
Cohesion: 0.20
Nodes (10): CorsConfig, Override, Override, WebSocketConfig, org.springframework.context.annotation.Configuration, org.springframework.web.servlet.config.annotation.CorsRegistry, org.springframework.web.servlet.config.annotation.WebMvcConfigurer, org.springframework.web.socket.config.annotation.EnableWebSocket (+2 more)

### Community 50 - "StateBuilder"
Cohesion: 0.13
Nodes (10): ndarray, StateBuilder -- the ML-001 state vector, in both of its representations. This…, Fold one step of scan outcomes into the per-band features. Called after the…, Inject the two features this service does not compute. At inference these…, The StateVector JSON exactly as the Backend sends and expects it., Rebuild a StateBuilder from an incoming StateVector. This is the inference…, Divisors that map raw contract values into roughly [0, 1] for the agents. The…, Tracks the ML-001 per-band features across a simulation run. (+2 more)

### Community 51 - "runner.py"
Cohesion: 0.21
Nodes (12): aggregate(), EpisodeMetrics, Any, Aggregate across episodes. Rates are recomputed from pooled counts rather than…, One episode's scoring. Field names are what the Backend surfaces via…, Episode runner shared by training, evaluation and the comparison scripts. One…, Run a policy across a scenario's episode seeds and aggregate the results., Train on one seed block, then evaluate greedily on the scenario's held-out eval… (+4 more)

### Community 52 - "EstimatorConfig"
Cohesion: 0.16
Nodes (9): default_config(), EstimatorConfig, Path, Estimator configuration (Ai-ml-2 README, ``configs/``). Buffer size, minimum-…, Tunables for the periodicity estimator., Load from YAML, falling back to the defaults above., Process-wide config, overridable by ``PERIODICITY_CONFIG`` for the Docker…, ActiveWindow (+1 more)

### Community 53 - "API_CONTRACT.md — Single Source of Truth"
Cohesion: 0.15
Nodes (12): 0. Domain Map, 1. Standard Envelope (all public + internal REST responses), 2. Public REST API (Backend ⇄ Frontend), 3. WebSocket Contract (Backend ⇄ Frontend), 4. Internal REST — Backend ⇄ Ai-ml-1 (Scheduler Engine), 5. Internal REST — Backend ⇄ Ai-ml-2 (Periodicity Estimator), 6. Shared Enums & IDs (must match byte-for-byte across all four domains), 7. Docker Compose Ports (must match across all READMEs) (+4 more)

### Community 54 - "API_CONTRACT.md — Single Source of Truth"
Cohesion: 0.15
Nodes (12): 0. Domain Map, 1. Standard Envelope (all public + internal REST responses), 2. Public REST API (Backend ⇄ Frontend), 3. WebSocket Contract (Backend ⇄ Frontend), 4. Internal REST — Backend ⇄ Ai-ml-1 (Scheduler Engine), 5. Internal REST — Backend ⇄ Ai-ml-2 (Periodicity Estimator), 6. Shared Enums & IDs (must match byte-for-byte across all four domains), 7. Docker Compose Ports (must match across all READMEs) (+4 more)

### Community 55 - "API_CONTRACT.md — Single Source of Truth"
Cohesion: 0.15
Nodes (12): 0. Domain Map, 1. Standard Envelope (all public + internal REST responses), 2. Public REST API (Backend ⇄ Frontend), 3. WebSocket Contract (Backend ⇄ Frontend), 4. Internal REST — Backend ⇄ Ai-ml-1 (Scheduler Engine), 5. Internal REST — Backend ⇄ Ai-ml-2 (Periodicity Estimator), 6. Shared Enums & IDs (must match byte-for-byte across all four domains), 7. Docker Compose Ports (must match across all READMEs) (+4 more)

### Community 56 - "MlPeriodicityClient"
Cohesion: 0.23
Nodes (3): BandPeriodicity, SuppressWarnings, MlPeriodicityClient

### Community 58 - "BaselineScanner"
Cohesion: 0.20
Nodes (5): BaselineScanner, ndarray, Path, Deterministic open-loop sweep. Given a seed and config, the scan order is fixed., test_fixed_order_requires_a_band_order()

### Community 59 - "SimulationConnection"
Cohesion: 0.24
Nodes (3): SimulationConnection, wsUrl(), WsChannel

### Community 61 - "SimulationRunner.java"
Cohesion: 0.15
Nodes (6): ScanDecision, DetectionEngine, DetectionOutcome, Observation, Observation, Scanner

### Community 62 - "PeriodicityAcceptanceTest.java"
Cohesion: 0.16
Nodes (9): AppConfig, MlProperties, SimulationProperties, MetricsSummary, PeriodicityAcceptanceTest, org.springframework.boot.context.properties.ConfigurationProperties, org.springframework.boot.context.properties.EnableConfigurationProperties, org.springframework.context.annotation.Bean (+1 more)

### Community 63 - "make_seed_bundle"
Cohesion: 0.28
Nodes (8): make_generator(), make_seed_bundle(), Seeding helpers. NFR-006 requires that, given an identical seed and…, The three independent generators a simulation run needs., A generator for one concern, independent of every other stream from the same…, SeedBundle, test_seed_bundle_is_reproducible(), test_seed_streams_are_independent_of_each_other()

### Community 65 - "Running the system"
Cohesion: 0.18
Nodes (10): 1. Ai-ml-1 — scan-decision policy, 2. Ai-ml-2 — periodicity estimator, 3. Backend, 4. Frontend, Databases, Known environment issue: Java 25 on Windows, Known open issue: periodicity does not yet help, Reading the results honestly (+2 more)

### Community 68 - "RewardContext"
Cohesion: 0.48
Nodes (4): DetectionOutcome, C(t): "cost of rescanning a band with no new information" (PRD Equation 10.1).…, Everything Equation 10.1 needs that is not in the DetectionOutcome itself., RewardContext

### Community 69 - "Intelligent RF Spectrum Scan Strategy — Build Scaffold"
Cohesion: 0.33
Nodes (5): Folders, Intelligent RF Spectrum Scan Strategy — Build Scaffold, Non-goals (apply to every folder, every level), Recommended order of operations, Why this split works

### Community 70 - "RfSchedulerApplication"
Cohesion: 0.60
Nodes (3): RfSchedulerApplication, org.springframework.boot.autoconfigure.SpringBootApplication, org.springframework.scheduling.annotation.EnableAsync

## Knowledge Gaps
- **193 isolated node(s):** `BufferKey`, `com.rfscheduler:rf-scheduler-backend`, `ReceiverConfigRequest`, `ManualScan`, `ROUND_ROBIN` (+188 more)
  These have ≤1 connection - possible missing edges or undocumented components.
- **8 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `fail()` connect `periodicity/api/main.py` to `ml/api/main.py`?**
  _High betweenness centrality (0.041) - this node is a cross-community bridge._
- **Why does `DeepRLAgent` connect `DeepRLAgent` to `estimate_period`, `EWEnvironment`, `ModelRegistry`, `Agent`?**
  _High betweenness centrality (0.032) - this node is a cross-community bridge._
- **Why does `ok()` connect `periodicity/api/main.py` to `ml/api/main.py`?**
  _High betweenness centrality (0.029) - this node is a cross-community bridge._
- **What connects `BufferKey`, `com.rfscheduler:rf-scheduler-backend`, `ReceiverConfigRequest` to the rest of the system?**
  _193 weakly-connected nodes found - possible documentation gaps or missing edges._
- **Should `Emitter` be split into smaller, more focused modules?**
  _Cohesion score 0.051201671891327065 - nodes in this community are weakly interconnected._
- **Should `periodicity/api/main.py` be split into smaller, more focused modules?**
  _Cohesion score 0.06057945566286216 - nodes in this community are weakly interconnected._
- **Should `ExperimentEntity` be split into smaller, more focused modules?**
  _Cohesion score 0.09986504723346828 - nodes in this community are weakly interconnected._