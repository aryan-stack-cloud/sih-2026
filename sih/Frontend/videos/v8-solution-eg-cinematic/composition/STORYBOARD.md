---
format: 1920x1080
duration: 40s
message: "Many possible frequencies, limited receiver observation: signals appear while the receiver is looking elsewhere."
arc: Establish → Intruder + torch → Sequential check (2 rooms at a time) → Meanwhile / too late → It keeps happening → Building becomes the spectrum → The ES problem + the open question
audience: SIH26055 judges / technical defence presentation panel
mode: autonomous
style: 2D night-noir cartoon (hand-built SVG puppets, masked practical lights) → the app's own EW instrument (Waterfall.tsx aperture, status colours). Ice-white = observation, warm amber = signal / "transmitting, not heard", green = heard.
architecture: "monolithic multi-scene merge — one shared SVG art kit (building, guard, thief, room) generated at init, five scene sections on one paused GSAP timeline; 2.5D parallax camera on the exterior world"
---

Rhythm: slow establish (hold) · 3-cut intruder reveal (side door → Room 10 torch → guard unaware, rack focus) · methodical stepping · split-screen MEANWHILE (held) · too-late reveal · accelerating flashes (the log fills) · ONE continuous morph (windows fly into 16 bands, letterbox retracts) · stepped mapping callouts · clean instrument · statement lines · open question.

Technical grounding (checked in source, see BRIEF.md § Notes): 16 rooms = 16 bands (scenarios A/B); the guard's light covers 2 adjacent rooms = K = 2 contiguous bands; route 01–02 → 03–04 → … = open-loop round-robin with stride K; the light blanks briefly on each move = 3 ms retune dead time in a 10 ms step.

## Frame 1 — Establish

- scene: Night compound. Four-storey block, 16 dark windows with small plates 01–16, moon, tree line. Foreground left: uniformed guard seated at his post (desk lamp, logbook, radio, a pivoting spotlight, off). Slow push + lateral drift across the facade.
- duration: 7s (0.0–7.0)
- status: animated
- src: index.html#s1
- transition_in: exposure ramp from black
- blueprint: camera-journey (sub-shape B, cursorless flight — leg 1 slow push)
- rules: multi-phase-camera (steady push + micro-drift), sine-wave-loop (guard breathing, star twinkle, cloud drift), ambient-glow-bloom (moon halo, desk lamp)
- voiceover: s1 "One guard. Sixteen dark rooms. And every one of them is his to watch."

## Frame 2 — The intruder

- scene: (a) low side shot: hooded intruder with a small backpack and an unlit torch creeps along the side wall, checks behind him, slips through the fire door. (b) Inside ROOM 10: moonlit blind stripes, desks, cabinet; he lifts the torch — click — a warm cone sweeps, the lit layer is revealed only inside the beam, glints on glass and a monitor, dust in the beam. (c) Guard close-up at his desk, sharp; behind him the facade is soft, and Room 10's window glows warm for a moment; he is writing in the logbook and never looks up.
- duration: 8s (7.0–15.0)
- status: animated
- src: index.html#s2
- transition_in: hard cuts
- rules: depth-of-field-blur (rack focus in 2c), ambient-glow-bloom (torch bloom), sine-wave-loop (dust motes)
- voiceover: s2a "Somewhere inside, an intruder is moving." · s2b "The only thing that gives him away is his torch."

## Frame 3 — Sequential observation + meanwhile

- scene: (a) over-the-shoulder: the guard switches the spotlight on; the lit patch covers ROOMS 01–02, blanks while it swings, lands on 03–04; route strip 16 cells, 2 lit. (b) Split screen: left "GUARD LOOKING · ROOMS 03–04 ✓" (lit, empty), right "THIEF ACTIVE · ROOM 10 ⚠" (torch sweeping), centre "MEANWHILE". (c) Facade: the light keeps its route 05–06 → 07–08 → 09–10: Room 10 is dark and empty; a warm flash is already in Room 15.
- duration: 9.8s (15.0–24.8)
- status: animated
- src: index.html#s3
- transition_in: cut
- rules: ai-tracking-box (observation brackets, adapted to ice-white L-corners), discrete-text-sequence (LOOKING · ROOMS 0N–0M), chart-scrub-readout (route strip read head)
- voiceover: s3a "So the guard checks the rooms in order. Two at a time." · s3b "He's watching rooms three and four. The torch is in room ten." · s3c "By the time he gets there, it's gone."

## Frame 4 — It keeps happening

- scene: Flat facade. The light steps faster on its fixed route; warm flashes pop and die in rooms it is not on (03, 14, 06, 10, 01, 12 …), two happen to fall inside the light (green SEEN). A room log under the building fills like a waterfall: amber = active and not seen. Tally ACTIVITY 14 · SEEN 2 (the log is computed from the same events as the flashes). Labels: MANY POSSIBLE EVENTS vs LIMITED OBSERVATION · 2 ROOMS AT A TIME.
- duration: 6.2s (24.8–31.0)
- status: animated
- src: index.html#s4
- transition_in: continuous (same facade)
- rules: waterfall-entry (log rows), discrete-text-sequence (tally), multi-phase-camera (slow push, micro-shake at the peak)
- voiceover: s4a "It keeps happening. Always in a room he isn't watching." · s4b "Too many rooms. Too little time to look."

## Frame 5 — The building becomes the spectrum

- scene: Letterbox retracts. Walls dissolve; the 16 windows fly (row by row) into one row of 16 frequency bands; the light patch on two windows becomes the receiver aperture over two bands; the last torch glow becomes an RF burst; the room log becomes the waterfall. Chips: ROOM → FREQUENCY BAND · TORCH LIGHT → RF EMISSION · INTRUDER → UNKNOWN, AGILE EMITTER · GUARD → ES RECEIVER · LOOKING AT 2 ROOMS → TUNED TO 2 BANDS · FIXED ROUTE → ROUND-ROBIN SWEEP. Then the clean instrument: aperture steps round-robin, bursts land where it is not; spec line N = 16 BANDS · K = 2 HEARD AT ONCE · 10 ms STEP · 3 ms RETUNE. Statement: "Many possible frequencies. / Limited receiver observation. / Signals can appear while the receiver is looking elsewhere." Final line: "So how does it decide where to look — and when?"
- duration: 9s (31.0–40.0)
- status: animated
- src: index.html#s5
- transition_in: continuous morph (no cut)
- blueprint: zoom-out-workspace-reveal (one decelerating re-scope of the whole) · titlecard-reveal (statement hold)
- rules: svg-path-draw (axis + leader lines), chart-scrub-readout (aperture = read head), waterfall-entry (statement lines), depth-of-field-blur (instrument dims under the statement)
- voiceover: s5a "Now swap the building for the radio spectrum." · (statement read in silence) · s6 "So how does it decide where to look, and when?"
- poster: 39.6
