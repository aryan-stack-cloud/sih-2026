---
format: 1920x1080
duration: 40s
message: "The challenge is not having a receiver — it is deciding where and when that limited receiver looks while unknown signals appear unpredictably across a wide spectrum."
arc: Establish → Unknown signal → Sequential search → The miss → It keeps happening → Pull back → Mapping → The EW problem (frozen)
audience: technical defense / technology presentation panel
mode: autonomous
style: cinematic night thriller → EW instrument; ice-white = observation, amber = signal, red = miss
architecture: "monolithic multi-scene merge — one continuous Three.js world (hf-seek) + HTML HUD phases on one paused GSAP timeline"
---

Rhythm: slow-establish · 3-cut reveal · methodical steps · HELD miss · accelerating montage (hard cuts) · ONE continuous tilt-to-flatten morph · stepped mapping · freeze.
Letterboxed 2.33:1 for the human story; bars retract when the world becomes technical (S6).

## Frame 1 — Establish

- scene: Night compound. Brutalist block, 15 dark windows stenciled 01–15, lone guard booth with an unlit searchlight; slow cinematic push.
- duration: 5s
- status: animated
- src: index.html
- transition_in: fade from black (exposure ramp)
- blueprint: camera-journey (sub-shape B, cursorless flight — leg 1 slow push)
- rules: multi-phase-camera (steady push + micro-drift), ai-tracking-box (zone brackets derived per frame from projected window corners), sine-wave-loop (camera micro-drift, rooftop aviation light blink)
- voiceover: "One guard. Fifteen dark rooms. All of them, his to watch."

One observer, many hidden zones. HUD brackets flick on over all 15 windows, then fade.

## Frame 2 — Unknown activity

- scene: Hooded silhouette slips through the side door → inside Room 07 (silhouette against the window, the night lot beyond) the torch clicks on and sweeps → reaction shot: guard looks up, every window dark.
- duration: 5s
- status: animated
- src: index.html
- transition_in: cut
- rules: ambient-glow-bloom (torch bloom + window glow), multi-phase-camera (slow creep inside Room 07); reaction shot is an over-the-shoulder silhouette from inside the booth
- voiceover: "Somewhere inside, an intruder." / "Invisible, until his torch flicks on."

Detectable only while it emits. "ACTIVITY · ORIGIN UNKNOWN".

## Frame 3 — Sequential observation

- scene: Over-the-shoulder behind the searchlight: beam powers on, lands Room 01 → 02 → 03 → 04; one window lit, fourteen dark.
- duration: 5s
- status: animated
- src: index.html
- transition_in: cut
- rules: ai-tracking-box (observation bracket follows the lit window), discrete-text-sequence (OBSERVING · ROOM 0N), chart-scrub-readout (15-cell strip read head in the lower letterbox)
- voiceover: "So the guard searches, room by room. He can only look at one at a time."

## Frame 4 — The miss

- scene: Wide diagonal; beam holds Room 04 while Room 10 flashes and dies; beam steps on 05, 06, 07; the intruder leaves by the side door unseen.
- duration: 6s
- status: animated
- src: index.html
- transition_in: cut
- blueprint: camera-journey (leg 2 — hold while the content acts)
- rules: ai-tracking-box (ice bracket on beam, amber bracket on the flash), multi-phase-camera (slow push)
- voiceover: "He's watching room four." / "Room ten. Gone, before he looks."

The signal existed; the observer looked elsewhere. Serious, held.

## Frame 5 — It keeps happening

- scene: Accelerating montage of hard cuts — 03 vs 08, 12 vs 05, 07 vs 14, then four rapid flashes — the beam always arrives to darkness. Tally: FLASHES 7 · SEEN 0.
- duration: 6s
- status: animated
- src: index.html
- transition_in: hard cuts (tempo-matched)
- rules: ai-tracking-box (beam + flash brackets), discrete-text-sequence (FLASHES n · SEEN 0 tally)
- voiceover: "Room three, while he watches eight. Twelve, while he watches five. Every time, too late."

## Frame 6 — Pull back

- scene: Camera cranes up and flattens to frontal; the lot falls away; windows become glowing outlines, then slide into one row of 15 frequency bands; a lingering flash becomes an RF burst; booth + searchlight become a receiver dish whose beam is the scan.
- duration: 5s
- status: animated
- src: index.html
- transition_in: continuous camera (no cut)
- blueprint: zoom-out-workspace-reveal (one decelerating pull-back re-scopes the whole) + camera-journey (tilt-to-flatten)
- rules: 3d-camera-flight (tilt-to-flatten, rooms travel in z as they unfold into bands)
- voiceover: "The building is the radio spectrum. Every room, a frequency band."

Letterbox retracts: the human story becomes the instrument.

## Frame 7 — Mapping

- scene: EW spectrum 2–18 GHz, noise floor, receiver scan window stepping band by band; agile emitter bursts on bands it never shares with the scan; five mapping callouts appear and clear.
- duration: 4s
- status: animated
- src: index.html
- transition_in: continuous
- rules: chart-scrub-readout (scan window = read head, readout on index change), waterfall-entry (callout arrivals), svg-path-draw (leader lines)
- voiceover: "The intruder, an unknown emitter. The guard, the receiver."

## Frame 8 — The actual problem

- scene: Scan on band 11, burst on band 13; scan arrives, burst gone; subtle red MISSED with the ghost of the vanished burst; freeze; the problem statement.
- duration: 4s
- status: animated
- src: index.html
- transition_in: continuous
- blueprint: titlecard-reveal (one restrained move, still hold)
- rules: chart-scrub-readout (scan read head + RX readout); the freeze dims and desaturates every band except the miss
- voiceover: "The signal was there. The receiver was looking elsewhere."
- poster: 39.9

"Detecting agile and unknown emitters across a wide frequency spectrum with limited receiver observation time." No solution, no AI.
