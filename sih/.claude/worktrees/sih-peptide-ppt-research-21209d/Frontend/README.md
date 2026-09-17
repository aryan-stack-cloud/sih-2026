# Frontend — Test Harness Only (NOT the final UI)

**Explicit scope note for whoever builds this (human or agent):** this build is a functional
test harness, not a product UI. Minimal styling, no design system, no polish — every screen just
needs to prove that every endpoint and WebSocket event in `../API_CONTRACT.md` works end-to-end.
It will be thrown away and redesigned later (see `Backend/README.md`'s Section 16 page list for
what the *real* dashboard will eventually look like — do not build that yet).

## Stack

React 18 + TypeScript + Vite. Plain HTML elements / unstyled `<div>`s and `<table>`s are fine —
default browser styling or a single trivial CSS reset is enough. Zustand for the WebSocket/
simulation store (still needed even in the test build, since reconnect/coalescing behavior must
be exercised). Typed REST client generated or hand-written directly against `API_CONTRACT.md` §2.

**Do not** pull in Tailwind, Recharts, or any design tooling at this stage — that's Level 10+ /
the future redesign pass. A plain `<pre>{JSON.stringify(...)}</pre>` dump is an acceptable way to
show data in this build.

## Folder structure to generate

```
frontend/src/
  app/            # routing, providers
  pages/          # one flat page per resource group (see Levels below) — no nested design system
  services/api/   # typed REST clients, one file per resource, mirroring API_CONTRACT.md §2
  services/websocket/  # connection manager: connect, subscribe, reconnect w/ backoff, dispatch
  store/          # Zustand store: simulations, scheduler, metrics, ws connection state
  types/          # TS types mirroring API_CONTRACT.md schemas & enums exactly
frontend/tests/
```

## Non-negotiable behaviors (even in the test build)

- WebSocket client must implement exponential backoff reconnect (1s→30s cap) and must tolerate
  event coalescing without breaking (§3 of the contract) — this is the part most likely to be
  skipped in a "quick test UI" and it's exactly the part worth testing early.
- Every REST call must surface the standard envelope's `error.code` and `error.message` visibly
  (a raw text dump is fine) so a broken Backend contract is obvious, not silently swallowed.
- Every enum (`behavior_class`, `policy_type`, `detection_type`, `scenario_id`) must be typed from
  `API_CONTRACT.md` §6, not re-invented.

---

## Build Plan — 10 Levels

### Level 1 — Project scaffold
Vite + React + TS project boots, `npm run dev` serves an empty page, typed API client folder
structure created (empty stubs), `.env.example` with `VITE_API_BASE_URL` and `VITE_WS_BASE_URL`.
**DoD:** `npm run dev` serves a blank page with no console errors; env vars documented.

### Level 2 — Simulations CRUD test page
One flat page: a form to POST `/simulations` (bands, duration, seed), a table listing GET
`/simulations`, click-through to GET `/simulations/{id}`, buttons for PUT/DELETE.
**DoD:** Can create, list, view, edit, and delete a simulation entirely from the UI.

### Level 3 — Lifecycle controls
Buttons wired to `/simulations/{id}/start`, `/stop`, `/reset`. Raw status text shown, no
visualization yet.
**DoD:** Status text changes correctly across start/stop/reset against a running Backend.

### Level 4 — Emitters & receiver test page
Flat CRUD form/table for `/emitters` (behavior_class dropdown from the shared enum), a form for
`PUT /receiver/config`, a button for `POST /receiver/scan` (debug) that dumps the raw
`Observation` JSON.
**DoD:** Can create emitters of all 5 behavior classes and see a manual scan's raw JSON response.

### Level 5 — Scheduler test page
Dropdown to `PUT /scheduler/config` (policy select from shared enum), start/stop buttons, a
polling or WS-fed raw dump of `GET /scheduler/decision` and `GET /scheduler/history`.
**DoD:** Switching policy and starting the scheduler visibly changes the raw decision dump.

### Level 6 — WebSocket harness
Connect to `/ws/v1/simulations/{id}`, subscribe to all four channels, render a raw scrolling log
of every event type received (`spectrum_update`, `scan_decision`, `detection_event`,
`metrics_update`, `training_progress`, `error`). Implement reconnect-with-backoff and verify it by
killing the Backend mid-session.
**DoD:** Event log updates live; killing and restarting the Backend triggers visible reconnect
without a page reload.

### Level 7 — Models & training test page
Form for `POST /models/train`, table for `GET /models`, buttons for `/activate` and `/evaluate`,
raw dump of training progress via the `training_progress` WS event.
**DoD:** Can launch a training job and watch its raw progress update live.

### Level 8 — Experiments test page
Form for `POST /experiments` (scenario A–G + policy list), run/stop buttons, raw JSON dump of
`GET /experiments/{id}/results`.
**DoD:** Can run a full baseline-vs-ML experiment and see raw comparison numbers.

### Level 9 — Metrics test page
Raw dumps of `GET /metrics/live`, `GET /metrics/{experimentId}`, and `GET /metrics/compare`
(multi-select of experiment IDs). No charts required — tables/JSON are fine.
**DoD:** All three metrics endpoints are exercised and their numbers cross-checked once manually
against the Backend's hand-computed test cases.

### Level 10 — Contract regression pass
Write a lightweight scripted pass (manual checklist or Playwright, whichever the agent's session
supports) that hits every endpoint and every WS event type once, confirming the response shape
matches `API_CONTRACT.md` exactly. Document any drift found back into `API_CONTRACT.md` in all
four folders, not just this one.
**DoD:** Every endpoint in §2 and every event in §3 has been exercised at least once from this
harness with a passing result. This build is now ready to be handed off and rebuilt as the real
dashboard (Section 16 pages) in a follow-up project.
