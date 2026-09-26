# v6 — 40s cinematic problem-introduction (refined remake of v5, NO SOLUTION)

Same story and rules as v5 (one guard, 15 dark rooms, a torch that only ever flashes where
he isn't looking → the EW receiver problem), rebuilt for quality. v1–v5 are untouched.

## What changed vs v5

| | v5 | v6 |
|---|---|---|
| World | flat 2D grid of 15 boxes in a vignette | real 3D night compound (Three.js): brutalist 5×3 block with real rooms, furniture, glass, stencilled numbers, lot, fence, street lamps, distant city, moon, stars, fog |
| Light | CSS glows | physically lit: moonlight, sodium practicals, searchlight with shadows + volumetric beam, torch spotlight with dust motes, bloom, ACES tone map |
| Guard's observation | cyan square outline | a searchlight on the guard post — one lit window at a time |
| Camera | near-static | motivated cinematic shots: push-ins, interior, over-the-shoulder, drone, montage cuts, one continuous tilt-to-flatten |
| Transition | bars fade in | the 15 windows physically unfold into the 15 bands; the searchlight beam *becomes* the receiver scan; the booth becomes a dish |
| EW view | 15 flat bars | spectrum instrument 2–18 GHz (from the project's own spec), live noise floor, spikes, scan read-head, RX readout |
| Text | 12–14px labels, beam overlapped the statement | video-scale HUD (20–46px), letterbox bars for the story, no overlaps (checked) |
| Voice | Kokoro am_adam (its lowest-graded voice) | Kokoro am_michael, loudness-matched to −19 LUFS, lines split to land on picture beats |
| Sound | ffmpeg sine drone + 3 clicks | custom score synced to picture (drone, pad, heartbeat, sting, cold chord, scan pulse, freeze) + a full SFX stem; score carved under the voice |
| Encode | ~1 Mbps | 23 Mbps delivery encode (x264 slow, CRF 15, 1080p30), grain/dither in the float pipeline against banding |

## Storyboard — 40.0s, 1920×1080

| Scene | Time | Beat |
|---|---|---|
| 01 Establish | 0–5 | Wide night push on the compound; 15 zone brackets flick on; "GUARD POST · 1 OBSERVER". Letterboxed 2.33:1. |
| 02 Unknown activity | 5–10 | Hooded silhouette slips through the side door → inside Room 07 the torch clicks on → over-the-shoulder from the booth: window 07 goes dark as the guard looks up. "ACTIVITY DETECTED · ORIGIN UNKNOWN". |
| 03 Sequential observation | 10–15 | Searchlight strikes; beam steps Room 01 → 02 → 03 → 04. Search-order strip in the lower bar. |
| 04 The miss | 15–21 | Beam holds 04; Room 10's torch flashes and dies; beam moves on 05, 06, 07; intruder leaves by the side door. "ROOM 10 · NEVER OBSERVED". |
| 05 Repeats | 21–27 | Montage: 03 vs 08, 12 vs 05, 07 vs 14, then four rapid flashes; beam always arrives to darkness. "FLASHES 9 · SEEN 0". |
| 06 Transition | 27–32 | Crane up + tilt-to-flatten; the world dims; windows become outlines and unfold into 15 bands; room 12's flash lands as an RF burst; booth → receiver dish; letterbox retracts. |
| 07 Mapping | 32–36 | Building → RF environment · Rooms → frequency bands · Intruder → unknown / agile emitter · Flashlight → RF transmission · Guard's observation → receiver scan. Scan steps one band at a time. |
| 08 The problem | 36–40 | Scan on 11, burst on 13; scan arrives to nothing; MISSED + ghost of the burst; freeze; the problem statement. |

## Voiceover (Kokoro am_michael @0.95)

- 0.70 "One guard. Fifteen dark rooms. All of them, his to watch."
- 5.10 "Somewhere inside, an intruder." · 6.95 "Invisible, until his torch flicks on."
- 10.15 "So the guard searches, room by room. He can only look at one at a time."
- 15.15 "He's watching room four." · 18.00 "Room ten. Gone, before he looks."
- 21.10 "Room three, while he watches eight. Twelve, while he watches five. Every time, too late."
- 27.50 "The building is the radio spectrum. Every room, a frequency band."
- 32.10 "The intruder, an unknown emitter. The guard, the receiver."
- 35.86 "The signal was there." — MISSED lands in the pause — "The receiver was looking elsewhere."

## Delivered (verified 2026-09-24)

- `v6-problem-intro-cinematic.mp4` — H.264 1920×1080, 30 fps, 40.000 s, 23.2 Mbps; AAC 48 kHz stereo, −17.8 LUFS integrated, −1.5 dBFS peak; poster embedded as cover art (film frames untouched).
- `v6-poster.jpg` — the frozen MISSED end frame · `v6-contact-sheet.jpg` — scene midpoints pulled from the final MP4.
- `npx hyperframes check`: 0 errors · layout 0 issues · motion 0 · contrast 92/92 WCAG AA. Remaining warnings are structural (one shared WebGL canvas, so no sub-compositions) plus ANGLE shader-compiler notes.
- A 60 fps render was attempted first; its encode exceeded HyperFrames' 16-minute ffmpeg limit on a shared CPU, so the delivered cut is 30 fps.

## Accuracy note

v6 follows the v5 spec: 15 rooms → 15 bands, the receiver scanning one band at a time, and an axis labelled 2–18 GHz (the coverage stated in `sih/docs/superpowers/specs/2026-09-11-sct-scheduler-solution.md`). The simulator's headline scenarios differ: they use 16 index-based bands, and the receiver hears K = 2 contiguous bands per step. Re-cut v6 if the video must match the code exactly.

## Rebuilding

- Picture: `composition/index.html` (Three.js world + HUD, all state a pure function of time).
- Sound: `python composition/audio-src/build_audio.py` regenerates the score + SFX stems; cue times mirror the picture schedules.
- Checks: `npx hyperframes check` from `composition/`.
