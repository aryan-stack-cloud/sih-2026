# Judge view v2: explain the decision, deliver the trace, race on the same spectrum

Status: approved by the project owner on 3 Oct 2026 ("do both a and b"). Evidence and wireframe: the
project review `project-review-2026-10-03` (Traycer artifact), section 3. The wireframe (built from
real simulator frames, Scenario B seed 3002) is the visual reference for layout and tone.

## Problem

1. **The scheduler's reasoning is computed and discarded.** `IndexAgent` records why it chose a window
   (`last_breakdown`: value, information, novelty, deadline, elapsed_s; `last_source`: floor or index)
   and `DecideResponse.index_breakdown` exists in the contract, but `InferenceEngine.decide` never
   returns it, so nothing reaches the UI.
2. **The decision trace is decimated by a copy-paste bug.** `SimulationEventPublisher.onStep` reads one
   `last` timestamp and uses the same condition for `spectrum_update` and `scan_decision`, so decisions
   are dropped whenever spectrum frames are (43 of 160 steps in a measured run). The class comment
   promises that decisions on detection steps bypass the gate; the code does not.
3. **A red error banner flashes at the start of every run.** `DemoPage` calls `pollLive` the moment
   the simulation id is set, before `startSimulation`; the Backend answers 409 `SIM_NOT_RUNNING`, and
   `pollLive` stores it as `error`, which `App.tsx` renders as an alert for about a second.
4. **The page cannot show the sweep and the policy on the same spectrum.** It watches one live run;
   the sweep only runs inside a hidden 10-episode experiment.
5. **Nothing shows whether listening time followed the signals.** `useful_scans` and per-band
   activity are not exposed per band.

## Decisions (binding for the plan)

| # | Decision | Why |
|---|---|---|
| D1 | `/internal/decide` gains `decision_source` (`"floor"`, `"index"` or `"deadline"`) for the Index policy; `index_breakdown` is populated for Index. Both are absent for every other policy (`exclude_none` stays). All numbers are finite (`+inf` is clamped to 1e6, NaN becomes 0). | Additive; old Backends see no change. |
| D2 | `InferenceEngine.decide` keeps returning a 3-tuple. A new `decide_explained` returns a 4-tuple whose last item is the explanation dict; `main.py` uses it. | No existing caller or test breaks. |
| D3 | `scan_decision` frames carry optional `decision_source` and `index_breakdown` (only when the ML service supplied them). `GET /scheduler/decision` carries them too. | One shape for the live trace and the debug view. |
| D4 | `scan_decision` gets its own gate state. It is emitted when its own 100 ms gate fires (the gate path updates its timestamp) OR when the step has a detection or a false alarm (the bypass path never updates the timestamp). Spectrum and decision gates therefore fire on the same steps, so every spectrum frame has a decision with the same `t`, and every detection step has one too. | Honours the existing Javadoc; keeps paired display; bounded traffic. |
| D5 | Per-band counters live in `LiveSimulation` (all steps, not gated): `looks[b]` (steps band b was scanned), `active[b]` (steps band b was transmitting), `heard[b]` (steps band b was detected) and `useful[b]` (steps band b was scanned while transmitting; added after the first acceptance run so the race readouts can show listening efficiency live: when a run ends `sum(heard)/sum(active)` equals `metrics.pd` and `sum(useful)/sum(looks)` equals `metrics.scan_efficiency`). Exposed as `per_band` in `snapshot()` (so in `GET /metrics/live` and the `connection_ack` snapshot). | The streamed frames are decimated and would bias attention-vs-activity, and the `metrics` object only arrives when a run ends. |
| D6 | `pollLive` treats `SIM_NOT_RUNNING` as "not started yet": no error, no state change. Every other error still surfaces. | Fixes the banner without hiding real failures. |
| D7 | The race runs two live simulations with the same seed, scenario and duration: the challenger (watched through the existing store) and the fixed sweep (watched by `RacePanel` through its own `useRunWatcher`). Both are paced with the same step delay of at least 100 ms (the frame-gate interval), so every step of both runs reaches the browser and rows can be matched by step; faster presets are raised to 100 ms during a race. Pacing spaces the EMITTED frames by the delay, measured from the previous emission, so compute time inside a step is absorbed and the two runs stay in step (a post-step sleep let an Index run drift about 8% behind the sweep; a step-period variant dropped about a third of the frames at the 100 ms gate). A failure of the sweep run degrades to the single waterfall with a visible note; it never fails the demo. | Keeps the global store untouched; synchronised pacing is the only way two live runs line up. |
| D8 | Pure logic (frame window, decision pairing, attention shares and match score) lives in `Frontend/src/lib/*.ts` without framework imports so it can be tested with Node's built-in runner (`node --test`, TypeScript type stripping, no new dependency). | The package has no test framework; none is added. |
| D9 | Visual language: the existing EW Console tokens only (`--intercepted`, `--missed`, `--false-alarm`, `--listened`, `--electric`, `--ground`, `--panel`, `--ink*`; gold stays scarce). Colour is never the only cue; charts have a text/table alternative; `prefers-reduced-motion` is honoured; layouts stack below 900 px. | Matches `Frontend/PRODUCT.md`. |

## Contract changes (the lead applies them to all five `API_CONTRACT.md` copies)

| Where | Change |
|---|---|
| Section 3, `scan_decision` | optional `decision_source`, `index_breakdown`; emission rule D4 |
| Section 2, `GET /scheduler/decision` | same two optional fields inside `decision` |
| Section 2, `GET /metrics/live` and the snapshot | `per_band: {looks: int[N], active: int[N], heard: int[N], useful: int[N]}` |
| Section 4, `POST /internal/decide` response | `decision_source`; breakdown keys and finiteness |

## Panel behaviours

**Why this band?** Shows, for the newest displayed step: the listened window ("bands 09-10 of 16",
1-based like the hero card), the decision type (Search = floor, Priority = index, Coverage = deadline),
bars for the Index terms `value`, `information`, `deadline` (and `novelty` when non-zero) with their
numbers, and the step reward with its terms (`D`, `P`, `L`, `F`, `C`, `M`). For policies without a
breakdown it says so in one sentence and still shows the reward terms.

**Attention vs activity.** Per band, the share of looks next to the share of transmissions, plus one
score: the overlap `sum_b min(lookShare_b, activeShare_b)` ("listening followed activity: 62%"). A text
table is available for assistive technology.

**Race.** Two columns (stacked on narrow screens): fixed sweep and the chosen challenger. Each shows its
step counter, spectrum heard, interceptions, listening efficiency, and its waterfall. The spectrum is
identical because the seeds are.

## Acceptance (checked by the lead on a second stack, ports 8501/8601/8081/5174)

1. A full run shows no red banner at any time.
2. With Index selected, "Why this band?" shows a decision type and terms that change over the run.
3. Both race waterfalls advance together and show the same transmissions.
4. Attention-vs-activity bars are populated and the score is plausible (sweep close to the overlap of a
   uniform distribution with the activity distribution).
5. Backend quick suite, Ai-ml-1 targeted tests and `npm run build` are green.

## Out of scope

Belief dials, the learning-curve panel, the real frequency axis, changing the waterfall's 0-based ruler,
the engine changes (separate branch `feat/engine-index-bandit-threat`).

## Acceptance results (4 Oct 2026)

Checked by the lead on a second stack built from the merged tree (Ai-ml-1 :8501, Ai-ml-2 :8601, Backend :8081,
Frontend :5174) with a copy of the model registry, in a real browser (Playwright, Chrome) and with a Node
WebSocket probe.

| # | Acceptance item | Result |
|---|---|---|
| 1 | A full run shows no red banner at any time | Pass: the alert region was polled every ~150 ms through full runs (Index, Q-learning, Bandit); 0 alerts, 0 page errors. The browser console still logs the swallowed 409 of the pre-start poll. |
| 2 | "Why this band?" shows a decision type and terms that change over the run | Pass: Search, Coverage and Priority all appear (Index is mostly Search and Coverage for its first ~200 steps); 151 to 119 distinct `value` terms per 160-step run; policies without a breakdown say so and still show the reward terms. |
| 3 | Both race waterfalls advance together and show the same transmissions | Pass after two fixes found by this check: lock-step runs (Index and sweep at 31/31, 61/61, 91/92, 122/122, 152/152, 160/160 steps after 3/6/9/12/15 s) and 160 of 160 frames at 100 ms. |
| 4 | Attention-vs-activity bars populated, score plausible | Pass: 51 to 62% for Index and 52% for the Bandit; the uniform-listening overlap computed by hand from the same counters is about 49%. |
| 5 | Backend quick suite, Ai-ml-1 tests and `npm run build` green | Pass: Backend 91/91, Frontend 39/39 with a clean build, Python suite green. |

Defects the acceptance run found and the fixes: the live readouts showed dashes for most of a run (the `metrics`
object only arrives at the end) -> `per_band.useful` and `liveReadouts`; "Done." appeared while the paced race was
still playing -> `waitForRunsToFinish` (capped at 90 s); a step-period pacing change dropped a third of the frames
at the Backend's 100 ms gate -> pacing by emission spacing; the screen-reader table of the attention panel made
the page scroll sideways at 390 px -> wrapped in a clipped block (checked at 320, 390 and 768 px).

Version skew: the new Frontend against the current master Backend (no `per_band`, no decision fields) completes
a run with no alerts or page errors; "Why this band?" falls back to its no-breakdown sentence, the attention
panel stays on "Waiting for the run to start", and the race readouts fill in from the final metrics.
