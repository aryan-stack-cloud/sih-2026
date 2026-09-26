---
workflow: general-video
flow: automation
storyboard: no
message: "The challenge is not having a receiver — it is deciding where and when that limited receiver looks while unknown signals appear unpredictably across a wide spectrum."
destination: presentation-screen
aspect: 1920x1080
language: en
audience: technical defense / technology presentation panel
length: 40s
angle: problem-only analogy → EW mapping (no solution)
narration: minimal
---

## Intent

v6 is a refined, higher-quality remake of v5 (`../../v5-problem-intro/`), the 40-second
cinematic problem-introduction for the Smart Scan Strategy presentation. The request was
"remake the video with more refining and better quality". v5's content spec (below) still
governs; v6 upgrades the craft: a real 3D night world (Three.js) instead of a flat box grid,
realistic lighting (moonlight, sodium lamps, a searchlight with volumetric beam and shadows,
torch light inside real rooms), smooth motivated camera moves, a true morph of the 15 rooms
into 15 frequency bands, video-scale HUD typography, a custom score synced to picture, a
better narrator voice, and a high-bitrate delivery encode.

Tone: serious, cinematic, technically believable, restrained. First ~27s a simple human
story anyone understands; final ~13s progressively transform it into the EW problem.

## Customizations

- Letterboxed (≈2.33:1) analogy that opens to full 16:9 when the world becomes technical.
- Searchlight on the guard post = "narrow observation beam": one window lit at a time.
- Spectrum axis 2–18 GHz, grounded in `sih/docs/superpowers/specs/2026-09-11-sct-scheduler-solution.md` ("250 MHz channels over 2–18 GHz").
- Custom synthesized score + bundled SFX (HeyGen signed out; MusicGen deps missing → offline synthesis).
- Narrator: Kokoro `am_michael` (v5 used `am_adam`, Kokoro's lowest-graded voice).

## Notes — the governing content spec (from the user's v5 request)

- 0–5 establish: large building at night, ~15 dark rooms as a grid of observation zones, ONE guard at a surveillance position outside, slow push.
- 5–10 unknown activity: silhouetted intruder enters a room, brief torch flash; cut between dark room, flash, guard outside; guard doesn't know which room.
- 10–15 sequential observation: guard's POV, rooms 1→2→3→4→5…, one room observed at a time, narrow observation beam.
- 15–21 the miss: guard observes Room 4 while the torch flashes in Room 10; flash gone before he reaches it; he keeps scanning; intruder leaves. Serious, not comedic.
- 21–27 repeats: montage — 3 while watching 8, 12 while watching 5, 7 while watching 14; each time too late; accelerating.
- 27–32 transition: camera pulls up, rooms MORPH into a horizontal spectrum of bands; flashes → RF bursts; guard → EW receiver.
- 32–36 mapping labels: Building → RF Environment · Rooms → Frequency Bands · Intruder → Unknown / Agile Emitter · Flashlight → RF Transmission · Guard's Observation → Receiver Scan. Receiver scans one band at a time.
- 36–40 the problem: emitter bursts on one band while receiver is on another; receiver arrives, signal gone; subtle red MISSED; freeze; statement: "Detecting agile and unknown emitters across a wide frequency spectrum with limited receiver observation time."
- Do NOT show the solution, multiple guards, a smart guard, AI/ML/DQN/RL/algorithms/optimization, or how it is solved.
- Minimal on-screen text; visuals carry the explanation.
- Keep v1–v5 untouched; new cut is saved as v6.
