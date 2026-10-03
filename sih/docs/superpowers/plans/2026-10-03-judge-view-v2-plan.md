# Judge view v2: implementation plan

Spec: `sih/docs/superpowers/specs/2026-10-03-judge-view-v2-design.md` (binding). Visual reference:
`sih/docs/superpowers/specs/2026-10-03-judge-view-v2-wireframe.html` (open it as a file; read its CSS for
tone, spacing and bar styles; do not copy its data). Clone: `C:/w/jv2`, branch `feat/judge-view-v2`.
Task 1 is Python (Ai-ml-1), Tasks 2-4 are Java (Backend), Tasks 5-7 are Frontend. The lead (not an
implementer) edits `API_CONTRACT.md` and does the end-to-end run.

All paths below are relative to `C:/w/jv2/sih` unless they start with `C:/`.

Streams run in parallel on disjoint directories: Python (Task 1), Java (Tasks 2, 3, 4 in order),
Frontend (Tasks 5, 6, 7 in order). Field names and shapes are fixed by the spec so streams do not wait
for each other.

## Task 1: Decision explanation from Ai-ml-1 (Python)

**Files.** Modify `Ai-ml-1-Scheduler-Engine/ml/agents/index_agent.py`,
`Ai-ml-1-Scheduler-Engine/ml/inference/inference.py`, `Ai-ml-1-Scheduler-Engine/ml/api/main.py`,
`Ai-ml-1-Scheduler-Engine/ml/contract.py`. Create
`Ai-ml-1-Scheduler-Engine/tests/test_decide_explanation.py`.

**Background.** `IndexAgent.select_action` sets `self.last_source` to `"floor"` (random search floor draw)
or `"index"` and `self.last_breakdown` to `{value, information, novelty, deadline, elapsed_s}` for the
chosen start band (`_breakdown_for`), but `apply_deadline_override` can then replace the chosen bands
with overdue ones without `last_source` saying so. `InferenceEngine.decide` returns
`(action, model_id, decision_id)` and `main.py::decide` builds `DecideResponse` from it with
`exclude_none=True`; `DecideResponse.index_breakdown` exists but is never filled.

**Requirements.**
1. `IndexAgent.select_action`: capture `selected = list(bands)` just before `apply_deadline_override`;
   after it, when `list(bands) != selected` set `self.last_source = "deadline"`. Allowed values are
   exactly `"floor"`, `"index"`, `"deadline"`. Nothing else about action selection may change (the
   chosen action for a given state must be identical to today's).
2. `InferenceEngine.decide_explained(simulation_id, state, policy, model_id=None, scenario_id=None)` returns
   `(action, resolved_model, decision_id, explanation)`. `explanation` is `{}` unless the session agent has
   a non-empty `last_breakdown` (only `IndexAgent`), in which case it is
   `{"index_breakdown": {...}, "decision_source": agent.last_source}`. Breakdown values must be finite
   floats rounded to 6 decimals: `+inf` becomes `1e6`, `-inf` becomes `-1e6`, NaN becomes `0.0`.
   `decide(...)` keeps its exact 3-tuple signature and return value by delegating to `decide_explained`.
   Read `last_breakdown`/`last_source` immediately after `select_action` for that call.
3. `ml/contract.py`: `DecideResponse.decision_source: Optional[Literal["floor", "index", "deadline"]] = None`
   with a docstring saying it is populated by the Index policy only. Update the `index_breakdown`
   docstring to say values are finite and that `deadline` is clamped to 1e6 when a band is overdue.
4. `ml/api/main.py::decide`: use `engine.decide_explained`; build
   `DecideResponse(action=action, model_id=model_id, decision_id=decision_id, **explanation)`. Keep
   `exclude_none=True`, so other policies' responses are byte-identical to today's.

**Tests** (`tests/test_decide_explanation.py`, at least 7 cases; look at `tests/test_api.py` for how the
FastAPI test client and a valid 16-band StateVector are built):
- `POST /internal/decide` with `policy="index"` returns `index_breakdown` with exactly the keys
  `value, information, novelty, deadline, elapsed_s`, every value a finite number, and `decision_source`
  in the allowed set; the whole response body passes `json.dumps(..., allow_nan=False)`.
- the same request with `policy="bandit"` and `policy="baseline"` contains neither key.
- `decide(...)` still returns a 3-tuple and `decide_explained(...)` returns a 4-tuple for the same inputs.
- `IndexAgent` unit test: a fresh agent built with `IndexAgent.from_scenario(load_scenario("B"))` after
  `start_episode(0)` reports `last_source` in `{"floor", "index"}`; after setting
  `agent.time_since_last_scan[:] = 10_000` and calling `select_action` on a neutral observation,
  `last_source == "deadline"` and the breakdown is still finite.
- the action chosen for a fixed observation and seed is the same as before the change (compare against an
  agent whose `apply_deadline_override` is wrapped, or against a recorded value computed on the unmodified
  logic path: build two agents, one normal and one where the new bookkeeping is monkeypatched out, and
  assert equal actions over 50 steps).
- a clamped value: monkeypatch `agent.last_breakdown = {"deadline": float("inf"), "value": float("nan")}`
  and assert the explanation holds `1e6` and `0.0`.

**Commands.** From `C:/w/jv2/sih/Ai-ml-1-Scheduler-Engine`:
`python -m pytest tests/test_decide_explanation.py tests/test_api.py tests/test_index_agent.py tests/test_index_agent_scenario.py tests/test_observe_hook.py -q -p no:cacheprovider`

## Task 2: Own rate gate for `scan_decision` (Java)

**Files.** Modify `Backend/src/main/java/com/rfscheduler/websocket/SimulationEventPublisher.java`. Create
`Backend/src/test/java/com/rfscheduler/websocket/SimulationEventPublisherTest.java`.

**Background.** `onStep` reads `Long last = lastSpectrumEmit.get(simulationId)` once, updates the map
only inside the spectrum branch, and reuses the same condition for the `scan_decision` branch, so the two
frame types are dropped together. The class comment says decisions on detection steps bypass the gate;
the code does not do that. `SimulationRunner.StepFrame` is a record (10 components); build instances
directly in tests.

**Requirements.**
1. Add a second constructor `SimulationEventPublisher(WebSocketHub hub, java.util.function.LongSupplier nowMs)`
   for tests and make the Spring-visible constructor the one-argument one (annotate it with
   `@Autowired` if Spring needs the hint with two constructors); the one-argument constructor delegates
   with `System::currentTimeMillis`.
2. Keep `lastSpectrumEmit` for the spectrum gate and add `lastDecisionEmit` (a `ConcurrentHashMap`) with a
   constant `MIN_DECISION_INTERVAL_MS = 100`. Rules in `onStep`:
   - spectrum frame: exactly today's gate.
   - `scan_decision`: compute `decisionGateOpen = lastDecision == null || now - lastDecision >= MIN_DECISION_INTERVAL_MS`
     and `hasEvent = !frame.detectedBands().isEmpty() || !frame.falseAlarmBands().isEmpty()`. Emit when
     `decisionGateOpen || hasEvent`. Update `lastDecisionEmit` ONLY when `decisionGateOpen` (so a bypass
     emission never shifts the gate and the decision gate stays in lock-step with the spectrum gate).
   - `detection_event`: unchanged.
3. `onComplete` and `onError` remove both gate entries.
4. Rewrite the class Javadoc so it states what the code now does (both gates, the bypass, the pairing
   property) and remove the sentence that no longer holds. The `scan_decision` payload fields stay exactly
   as they are in this task (Task 3 adds fields); switch `Map.of(...)` to a `LinkedHashMap` only if you
   need to, preserving key order `t, action, model_id, reward, reward_terms, valid_observation`.

**Tests** (mock `WebSocketHub` with Mockito, `ArgumentCaptor` on `broadcast(simId, channel, frame)`, a
mutable fake clock; at least 7 cases):
- 30 steps 10 ms apart with no detections: spectrum and scan_decision frames are emitted for the same
  step indices (0, 10, 20), nothing else.
- a detection step that falls between gate openings emits a `scan_decision` and a `detection_event` but no
  `spectrum_update`, and the following gate openings are unchanged (still 10, 20 relative to the start).
- a false-alarm-only step also bypasses.
- at 100 ms or more per step, every step emits both frames.
- after `onComplete`, the same simulation id starts fresh: its first step emits both frames.
- the `scan_decision` payload still has exactly the original six keys for a frame without extras.
- two simulation ids gate independently.

**Commands.** From `C:/w/jv2/sih/Backend`:
`export PATH="/c/Users/This PC/tools/apache-maven-3.9.16/bin:$PATH" && mvn -B -q -Dtest='SimulationEventPublisherTest,LiveSimulationStepTest,EndToEndSimulationTest' -Dsurefire.failIfNoSpecifiedTests=false test`
then, once at the end: `mvn -B -q -Dtest='!PeriodicityAcceptanceTest' -Dsurefire.failIfNoSpecifiedTests=false test`
(never run `PeriodicityAcceptanceTest`; it needs live services). With `-q` nothing prints on success;
read `target/surefire-reports/*.txt` for the counts and report them.

## Task 3: Carry the decision explanation end to end (Java)

**Files.** Modify `Backend/src/main/java/com/rfscheduler/ml/ScanDecision.java`, `ml/MlSchedulerClient.java`,
`service/SimulationRunner.java`, `websocket/SimulationEventPublisher.java`,
`controller/SchedulerController.java`; add tests next to the existing ones under
`Backend/src/test/java/com/rfscheduler/`. Task 2 must be complete first (same publisher file).

**Requirements.**
1. `ScanDecision` gains trailing components `Map<String, Double> indexBreakdown` and `String decisionSource`
   (nullable). Keep the current five-argument constructor (both new values null) and the
   `local(int, String)` factory working.
2. `MlSchedulerClient.decide`: when `data` contains `index_breakdown` (a JSON object), convert it to a
   `Map<String, Double>` (skip entries whose value is not a number); when it contains `decision_source`
   (a string), take it. Absent or null means null. Nothing else about the method changes.
3. `SimulationRunner.StepFrame` gains trailing components `String decisionSource` and
   `Map<String, Double> indexBreakdown`, and keeps a constructor with the current 10-argument shape
   (both null) so existing code and tests compile. In the step loop, build the frame with
   `decision.decisionSource()` and `decision.indexBreakdown()` (fallback decisions have nulls).
4. `SimulationEventPublisher`: the `scan_decision` payload additionally contains `"decision_source"` and
   `"index_breakdown"` only when non-null (after the original six keys, in that order).
5. `SchedulerController.latestDecision`: `decision` additionally contains `decision_source` and
   `index_breakdown` when non-null.

**Tests** (at least 6 cases):
- client parse: stub the HTTP layer exactly like `MlSchedulerPayloadTest` does; a response with
  `index_breakdown` {value, information, novelty, deadline, elapsed_s} and `decision_source: "index"`
  yields a `ScanDecision` carrying both; a response without them yields nulls; a non-numeric breakdown
  entry is skipped.
- publisher: a frame with extras produces a `scan_decision` frame containing both extra keys; a frame
  without extras contains neither.
- `StepFrame` old 10-argument constructor still works and leaves both new values null.
- `SchedulerController.latestDecision` includes the two fields when the latest frame has them and omits
  them otherwise (Mockito-stub `SimulationService.liveState`).

**Commands.** As Task 2 (focused classes first, then the quick suite once at the end).

## Task 4: Per-band attention counters (Java)

**Files.** Modify `Backend/src/main/java/com/rfscheduler/service/SimulationService.java`. Create
`Backend/src/test/java/com/rfscheduler/service/LiveSimulationPerBandTest.java` (same package as
`SimulationService`, since `LiveSimulation`'s constructor is package-private).

**Requirements.**
1. `LiveSimulation` gets the band count: constructor `LiveSimulation(String simulationId, int numBands)`;
   `start()` passes `sim.getBands()`. Keep a one-argument constructor only if something else needs it
   (then `per_band` is simply absent for it).
2. `record(frame)` increments three `AtomicIntegerArray`s (or `int[]` guarded the same way the other
   counters are): `looks[b]` for each band in `frame.scannedBands()`, `active[b]` for each band in
   `frame.activeBands()`, `heard[b]` for each band in `frame.detectedBands()`; ignore indices outside
   `[0, numBands)`. This runs for every step (it is not gated).
3. `snapshot()` adds `"per_band"`: `{"looks": [...], "active": [...], "heard": [...]}` as `List<Integer>`s
   (copies, not live views). Put it after `counters`.

**Tests** (at least 4 cases): counts after a hand-built sequence of `StepFrame`s; out-of-range band
indices are ignored; the snapshot lists are copies (mutating the returned list does not change later
snapshots); `snapshot()` before any step has all-zero arrays of length `numBands`.

**Commands.** As Task 2.

## Task 5: Frontend plumbing: types, store, 409 fix, run watcher, tested helpers

**Files (under `Frontend/`).** Modify `src/types/contract.ts`, `src/store/useStore.ts`, `package.json`
(add only the script `"test": "node --test"`; the form with a directory argument does not run on this Node). Create `src/lib/frameWindow.ts`,
`src/hooks/useRunWatcher.ts`, `tests/frameWindow.test.ts`.

**Background.** Node 24 runs TypeScript test files directly (type stripping, no dependency). Tests live in
`Frontend/tests/` (outside `tsconfig`'s `include: ["src"]`) and import helpers with an explicit `.ts`
extension. Therefore `src/lib/frameWindow.ts` must have NO runtime imports (only `import type`, which
are erased) and use only erasable TypeScript (no enums, no parameter properties).

**Requirements.**
1. `types/contract.ts`: `WsFrame` gains `decision_source?: "floor" | "index" | "deadline"` and
   `index_breakdown?: Record<string, number>`; add `export interface PerBandCounters { looks: number[]; active: number[]; heard: number[]; }`
   and `LiveSnapshot.per_band?: PerBandCounters`.
2. `lib/frameWindow.ts` (pure): `export const FRAME_WINDOW = 40;` the `SpectrumFrame` interface (moved from
   the store, same fields); `appendSpectrumFrame(frames, frame)` (adds the frame built from a
   `spectrum_update` WsFrame and keeps the last `FRAME_WINDOW`); `applyFalseAlarms(frames, frame)` (for a
   `detection_event` with `false_alarm_bands`, sets them on the frame with the same `t`; returns the same
   array reference when nothing changes); `export const DECISION_WINDOW = 64;`
   `appendDecision(decisions, frame)` (keeps the last `DECISION_WINDOW`); and
   `decisionForStep(decisions, t)`: the decision whose `t` equals `t`; else the latest one with `t` at or
   below the requested step; else `null`. Use `import type { WsFrame } from "../types/contract"`.
3. `store/useStore.ts`: import the helpers instead of the inline logic (identical behaviour for the
   spectrum and false-alarm handling); re-export the type with `export type { SpectrumFrame }` so existing
   imports (`Waterfall`) keep working; add `decisions: WsFrame[]` to the state (reset in `watch` and
   `unwatch`, appended on `scan_decision` next to the existing `lastDecision`, which stays).
4. `pollLive`: in the `catch`, when the error is an `api.ApiRequestError` whose `code === "SIM_NOT_RUNNING"`,
   do nothing (no `error`, no state change); every other error behaves as before.
5. `hooks/useRunWatcher.ts`: `useRunWatcher(simulationId: string | null, pollMs = 1500)` returns
   `{ frames, live, decisions, connection }`. It opens a `SimulationConnection` for the id, applies
   `connection_ack` snapshots as REPLACEMENTS, `spectrum_update`, `detection_event`, `scan_decision`
   and `metrics_update` the way the store does (using the helpers), polls `api.liveMetrics(id)` every
   `pollMs` (ignoring `SIM_NOT_RUNNING`, ignoring other errors silently but keeping the last good
   snapshot), resets all state when the id changes, and closes the connection and the timer on unmount or
   id change. No store access.

**Tests** (`tests/frameWindow.test.ts`, at least 8 cases with `node:test` and `node:assert/strict`):
the window caps at 40 and keeps the newest; frames keep `t` order of arrival; false alarms attach to the
matching `t` only and return the same array when nothing matches; `appendDecision` caps at 64;
`decisionForStep` exact match, latest-at-or-below fallback, `null` when empty or when every decision is
newer than the step.

**Commands.** From `C:/w/jv2/sih/Frontend`: `npm run test` then `npm run build`. Report both outputs.
Do not stage `tsconfig.tsbuildinfo` or `dist/`.

## Task 6: "Why this band?" and "Attention vs activity" panels

**Files (under `Frontend/`).** Create `src/components/WhyThisBand.tsx`, `src/components/AttentionActivity.tsx`,
`src/lib/attention.ts`, `tests/attention.test.ts`. Modify `src/pages/DemoPage.tsx`, `src/styles.css`.
Task 5 must be complete first.

**Requirements.**
1. `lib/attention.ts` (pure, same constraints as Task 5): `attentionShares(perBand)` returns
   `{ looks: number[]; active: number[]; total: {looks: number; active: number} }` with each array
   normalised to sum 1 (all zeros when the total is zero); `matchScore(perBand)` returns
   `sum_b min(lookShare_b, activeShare_b)` in `[0, 1]` (0 when either total is zero).
2. `AttentionActivity` props: `{ perBand?: PerBandCounters; bands: number; policyLabel: string }`. Renders
   a titled panel ("Attention vs activity"), one sentence of explanation, the match score as a large
   percentage ("62% of listening time followed the activity" style wording), and per band a diverging
   mini bar chart: activity share going up (`--missed` family is reserved for MISSED transmissions, so use
   `--electric` for activity) and look share going down (`--listened`), band labels 01..N (1-based).
   `role="img"` with a concise `aria-label`, plus a visually hidden `<table>` with looks, active and heard
   per band. Empty state when `perBand` is undefined or all zero: "Waiting for the run to start."
3. `WhyThisBand` props: `{ decision: WsFrame | null; bands: number; policyLabel: string; k?: number }`
   (`k` defaults to 2). Shows: the window ("Listening to bands 09-10 of 16", 1-based, wrapping at the top
   so the last band pairs with 01), a decision-type chip (`decision_source` "floor" -> "Search: random
   floor keeps sampling where little is known", "index" -> "Priority: highest score this step",
   "deadline" -> "Coverage: this band had waited too long"), bars with numbers for the `index_breakdown`
   terms `value` ("Expected catch"), `information` ("Information gain"), `deadline` ("Waiting too long")
   and `novelty` only when non-zero (bar lengths relative to the largest shown term; all-zero shows a one
   line note), and the reward line from `decision.reward` and `decision.reward_terms` (labels: D
   detection, P priority, L delay, F false alarm, C repeat look, M missed threat; unknown keys verbatim).
   For decisions without a breakdown it says "This policy scores bands from learned weights and does not
   expose per-term scores." and still shows the reward line. `null` decision: "Waiting for the first
   decision."
4. `DemoPage` integration: below the existing `.spectrum-panel`, add a section grid (class `judge-grid`,
   two columns, stacked below 900 px) holding `WhyThisBand` (decision = `decisionForStep(decisions,
   <t of the newest frame in waterfallFrames>)`, falling back to `lastDecision`; `decisions` and
   `lastDecision` come from `useStore()`) and `AttentionActivity` (`live?.per_band`). The policy label is
   `CHALLENGER_LABELS[challenger]`. Do not change the hero, tiles or comparison sections.
5. CSS: new classes only, using existing tokens, matching the wireframe's panel look; honour
   `prefers-reduced-motion` (no transitions needed); text must stay readable at 100% zoom on a dark
   background (contrast at least 4.5:1 for body text).

**Tests** (`tests/attention.test.ts`, at least 6 cases): shares sum to 1; zero totals give zeros and a
0 score; identical distributions score 1; disjoint distributions score 0; a known 4-band example with the
expected score computed by hand (put the arithmetic in a comment); `matchScore` ignores `heard`.

**Commands.** From `C:/w/jv2/sih/Frontend`: `npm run test` then `npm run build`. Report both outputs.

## Task 7: Race on the identical spectrum

**Files (under `Frontend/`).** Create `src/components/RacePanel.tsx`, `src/lib/raceAlign.ts` and
`tests/raceAlign.test.ts`. Modify `src/pages/DemoPage.tsx`, `src/styles.css`. Tasks 5 and 6 must be complete first.

**Requirements.**
1. `RacePanel` props:
   `{ bands: number; reference: { label: string; simulationId: string | null }; challenger: { label: string; frames: SpectrumFrame[]; live: LiveSnapshot | null }; note?: string }`.
   It calls `useRunWatcher(reference.simulationId)` for the sweep and renders two columns (class
   `race-grid`, stacked below 900 px). Each column: the label, "step N" (from `live.t`), three small
   readouts (spectrum heard `live.metrics.pd` as a percentage, interceptions `live.counters.detections`,
   listening efficiency `live.metrics.scan_efficiency`; "—" until available), and a `Waterfall`
   (`frames`, `bands`). Rows are aligned: `alignFrames(challengerFrames, referenceFrames)` from the new pure
   module `lib/raceAlign.ts` returns the two frame lists restricted to the `t` values present in BOTH (order
   preserved, at most the last 40); until the two runs share a `t`, each column shows its own frames. The run
   that is ahead is simply trimmed to the slower one's progress. A caption states that both columns show the
   same transmissions (same seed) and that rows are matched by step.
   When `note` is set show it as a status line and render only the challenger column.
2. `DemoPage.runDemo`: after the challenger simulation is created and started, create the reference
   simulation with the same `name` prefix, `bands`, `durationSteps`, `seed`, `scenario` and
   `policy: "baseline"`, start it, and set `referenceSimulationId` state. Pace both runs with the same
   step delay: `raceSpeedMs = Math.max(speedMs, 100)` (a faster preset is raised to 100 ms, the Backend's
   frame-gate interval, so every step of both runs reaches the browser), applied with
   `api.setSimulationSpeed` to both (best-effort, as the existing code does). Show a one-line note
   next to the speed control while a race runs: "Race pacing: 100 ms per step so both runs stay in step." `changeSpeed` updates both while running. Any failure
   creating or starting the reference run is caught: set `raceNote` to "Race view unavailable: <reason>"
   and carry on exactly as today (the demo must never fail because of the reference run). `cancelDemo`
   stops the reference run too (best-effort). Clear `referenceSimulationId`/`raceNote` at the start of a
   run.
3. Render `RacePanel` in place of the single waterfall inside `.spectrum-panel` once a reference id or a
   note exists; otherwise keep today's single `Waterfall`. The challenger's frames and live snapshot are
   the store's (`frames`, `live`); the hero aperture and tiles are unchanged.
4. `DemoPage` must not open a second socket for the challenger: only the reference run is watched by the
   hook.
5. Accessibility: the two columns are labelled regions (`role="group"` with `aria-label`), counters are
   text, and the existing waterfall alternatives are reused as they are.

**Tests** (`tests/raceAlign.test.ts`, at least 5 cases): only common `t` values survive in both outputs; order is
preserved; the window caps at 40 newest; disjoint inputs return the inputs unchanged (so each column keeps
its own frames); empty inputs return empty arrays.

**Verification.** `npm run build` clean and `npm run test` green. Describe in your report how the
race degrades when the reference simulation fails and where in `runDemo` that is handled.
