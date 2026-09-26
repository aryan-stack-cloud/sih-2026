# v7 — "solution eg": 40 s problem introduction (guard → ES receiver)

An alternate cut of the problem intro, following the user's "40-SECOND INTRODUCTION TO THE
PROBLEM — VIDEO IDEATION" storyboard. Problem only: no scheduler, no AI, no smarter guard. It
ends on the question the solution section answers: *so how does it decide where to look — and when?*

v1–v6 are untouched. The composition lives in `composition/` (HyperFrames).

## Storyboard as built (40.0 s, 1920×1080)

| Time | Beat | On screen |
|---|---|---|
| 0–7 | Establish | Night compound, four-storey block with 16 dark rooms (plates 01–16), uniformed guard at his post (booth, desk, logbook, desk lamp, pivoting spotlight). Slow push. A small figure slips toward the side fire door. |
| 7–9.8 | Intruder | Low side shot: hooded intruder (beanie, face covered, small backpack, unlit torch) creeps along the wall, glances back, slips through the fire door. |
| 9.8–12.8 | The torch | Inside **Room 10**: he raises the torch — click — a warm cone with dust, the lit layer revealed only inside the beam, glints on the monitor. Through the window, far away, the guard's desk lamp. |
| 12.8–15 | Unaware | Guard close-up writing in the logbook; behind him Room 10's window glows warm for a moment (rack focus to it and back). He never looks up. |
| 15–18.2 | Sequential check | Over the shoulder: he switches on the spotlight; it covers **rooms 01–02**, blanks while it swings, lands on **03–04**. Readout: FIXED ROUTE 01–02 › 03–04 › … |
| 18.2–22.4 | Meanwhile | Split screen: GUARD LOOKING · Rooms 03–04 ✓ (nothing there) / THIEF ACTIVE · Room 10 ⚠ (unseen). Through Room 10's window, the guard's light points somewhere else. |
| 22.4–24.8 | Too late | The light keeps its route 05–06 → 07–08 → 09–10: Room 10 is dark and empty; the torch is already in Room 15. |
| 24.8–31 | It keeps happening | Wide: the light steps faster on the same route; the torch flicks on in rooms it is not on. A ROOM LOG fills (amber = activity not seen, green = seen, grey = looked, empty). Tally ACTIVITY 14 · SEEN 2. MANY POSSIBLE EVENTS vs LIMITED OBSERVATION · 2 rooms at a time. |
| 31–32.6 | Transformation | Letterbox retracts, walls dissolve, the 16 windows fly into 16 frequency bands, the room log becomes the waterfall, the lit pair becomes the receiver aperture, the torch glow becomes an RF burst. |
| 32.4–35.5 | Mapping | Room → frequency band · Torch light → RF emission · Intruder → unknown, agile emitter · Guard → ES receiver · Looking at 2 rooms → tuned to 2 bands · Fixed route → round-robin sweep. |
| 35.5–40 | The problem | Clean instrument (spectrum + waterfall + aperture stepping, emitters bursting where it is not). "Many possible frequencies. / Limited receiver observation. / Signals can appear while the receiver is looking elsewhere." + "So how does it decide where to look — and when?" |

## Technical details corrected against the source

| Storyboard said | Source says | Used |
|---|---|---|
| ~15 rooms | Scenarios A/B: **16 bands** (`Backend/.../simulation/ScenarioLibrary.java`; explainer PDF: 16–32 by scenario) | 16 rooms → 16 bands |
| guard sees one room at a time | Receiver hears **K = 2 contiguous bands** per step (`receiver/ReceiverConfig.defaults()`, `receiver/Receiver.java`) | light covers 2 adjacent rooms; 2 of 16 = 12.5 % |
| checks Room 01 → 02 → 03 … | Baseline = open-loop **round-robin, stride K**, ignores feedback (`scheduler/BaselineScheduler.java`) | 01–02 → 03–04 → 05–06 … same route every time |
| looking at a room | **10 ms** step, **3 ms** retune dead time, 4 ms min dwell (`ReceiverConfig.defaults()`) | light blanks on every move; spec line in the ending |
| thief moves room to room | emitter classes fixed / periodic / **agile** / random / **intermittent** (`simulation/EmitterBehavior.java`) | intruder → unknown, agile emitter; the ending adds periodic / intermittent / random emitters |
| "RF receiver" | SIH26055: *ML-based **Electronic Support (ES) receiver** scheduler* | guard → ES receiver |
| signals appear while it looks elsewhere | *"two dimensional search problem … adjusting receiver's frequency at correct time"*, *"absence of prior reliable intelligence"* | right band **and** right time; no tip-off |

The room log and the ending waterfall are computed from one event list, the same one the facade
flashes use, and they reuse the app's own waterfall semantics and colours
(`Frontend/src/components/Waterfall.tsx`: heard / transmitting, not heard / listened, nothing there).
No GHz axis is drawn: the 16-band scenarios are index-based in the code.

## Audio

- Narration: Kokoro `af_heart` @ 0.94, offline (HeyGen signed out). 10 lines, ~28.8 s of speech.
- Score: synthesized offline (`composition/tools/make_audio.py`): drone → heartbeat → stepping ticks →
  riser → clean instrument chord. Carved under the `voiceover` group (strength 0.8).
- SFX: bundled Pixabay-licensed clicks, whooshes, glitch and impact (media-use skill) plus synthesized
  footsteps, door, servo ticks and data ticks.
