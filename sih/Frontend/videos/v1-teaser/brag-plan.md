# Brag Plan: PUSHPAK — Spectrum Scan Scheduler

## What is this app?
A live demonstrator where a machine-learned Electronic Support receiver — one that can only hear two bands of the spectrum at a time — decides in real time where to listen next, and races that decision live against a fixed sweep on the identical simulated spectrum.

## The angle
The product's own strongest material is a number, not a metaphor: on a "synchronization trap" scenario, a classic fixed sweep scores **exactly 0.000 detection** — it never once looks where the signal is — while the learned scheduler escapes it and holds a 0.967 interception ratio. The video's job is to make a viewer watch the receiver's aperture (a hard bracket on the waterfall) fail to cover the spectrum, then watch the comparison prove it wasn't a fluke. Specific to this project, not generic: it's an SDR waterfall recreated as the hero, not a dashboard mockup.

## Hook (first 2-3 seconds)
The product's own standfirst line, split for weight: "A RECEIVER THAT CAN HEAR TWO BANDS AT A TIME." beat, then "LEARNING WHERE TO LISTEN." Full-bleed deep indigo ground, nothing else on screen — the constraint stated before anything else.

## Key moments (the middle)
- The receiver's aperture — a bracket labeled LISTENING — sliding across the waterfall's band axis while cells stream downward beneath it in real intercepted/missed/idle color.
- The fixed sweep's exact failure: "0.000 DETECTION" slammed in rose, immediately countered by the learned policy's "0.967" in gold — the specific, verifiable stat from the product's own evidence, not a rounded marketing number.
- The head-to-head lift chart: 2-3 metric bars sweeping out from a zero line, gold reading better, proving the claim on the same seeds rather than asserting it.

## Outro / punchline
The PUSHPAK gold "P" mark and wordmark slam in on the beat. Tagline: "Learning where to listen." Beneath it, small but legible: "SIMULATION ONLY — NO REAL RF." The honesty is part of the brand, not a disclaimer bolted on.

## User flow worth showing
Pulled directly from the Dashboard page's own three-beat structure (`DemoPage.tsx`): press **Run the demo** → watch the receiver work live on the waterfall → read what it achieved (the metric tiles) → see it measured against the fixed sweep it replaces (the head-to-head chart). Scenes 2-4 of the storyboard are this flow, not a landing-page recreation.

## Tone
- Preset: cinematic
- Creative direction: an instrument-panel trailer — the spectrum as a dramatic, high-stakes surface, shot like the product's own SDR waterfall rather than generic dashboard furniture.
- Interpretation: dramatic reveals over quick cuts, full-bleed scenes, large type holding its moment before the next beat lands. Restraint stays in the copy (short declaratives, real numbers) even as the visuals go big — nothing overclaims beyond what the product's own evidence supports.

## Format: landscape — 1920x1080
## Duration: ~21.5s target

## Visual identity (from the project)
- Background: `#0b1020` (ground), panels `#141b2e` / `#1b2440`
- Accent: `#e8b84b` brand gold (on-gold ink `#241a05`) — reserved for brand/outro moments only, never used as a data color
- Text: `#e6eaf5` primary ink, `#8a93ad` muted
- Data/status hues (used only on the waterfall and chart, never as general accents): intercepted `#0f9e73`, missed `#c87a18`, false-alarm `#d8425f`
- Display font: Archivo (hook lines, stat callouts, wordmark)
- Body font: JetBrains Mono (readouts, band-axis numbers, the LISTENING tag, chart labels) — the product's own instrument voice
- Strongest visual element: the spectrum waterfall (`Waterfall.tsx`) — frequency across, time down, newest row at top, with the receiver's aperture drawn as a bracket threaded continuously down through the scrolled history, not floating over just the newest row

## Share copy (draft)
PUSHPAK: a receiver that can only hear two bands at once — watch it learn where to listen, live, against a fixed sweep that goes fully blind (0.000 detection) in a sync trap. Simulation-only scan scheduler, built for SIH26055.

## Audio direction
- Role: cinematic support — a restrained low bed, no melodrama, matched to a control-room mood
- Music: `happy-beats-business-moves-vol-12-by-ende-dot-app.mp3` — "steady and clean," the bundled track recommended for cinematic/polished. 109.96 BPM.
- Music treatment: enters under the hook at low volume (~0.28), a gentle swell into the claim reveal, sustained under the comparison, settles under the outro and fades by the last frame.
- Music cue guidance: bundled preset read (`music-cues.json`/`.md` for vol-12). Three strong-cue locks used out of the preset's list: **8.74s** (0.99, the "0.000 DETECTION" slam), **13.11s** (0.98, the comparison chart's first bar), **17.47s** (0.99, the outro wordmark). All within the ±0.15s major-reveal tolerance of where the storyboard already wanted them.
- Audio-reactive treatment: subtle — the aperture bracket's stroke opacity and the wordmark's glow may breathe slightly with RMS/treble on the strong cues; no waveform or equalizer visuals.
- SFX posture: 2-3 big cinematic hits plus one small interaction click — restrained, not dense.
- Audio-coupled moments: the "Run the demo" cursor click (scene 2), the waterfall's continuous scroll (ambient, no per-row SFX — would be too dense), the two sequential stat slams (scene 3), the sequential bar reveal (scene 4), the wordmark slam (scene 5).
- Restraint rule: audio must never race ahead of the two real numbers (0.000 / 0.967) — both fully settle on screen before any transition or beat pulls attention away.

## Storyboard

### Scene 1 — Hook — 3.8s
Full-bleed `#0b1020`. No chrome, no UI yet. Two short declaratives land together as one hook unit (not sequential): "A RECEIVER THAT CAN HEAR TWO BANDS AT A TIME." / "LEARNING WHERE TO LISTEN." in Archivo, large, mixed case.
Sequential/interaction: none — both lines arrive as a single beat and hold.
Audio intent: quiet, anticipatory. The bed just started; give the line room.
Audio-coupled idea: none.
Music: vol-12 bed enters at ~0.25-0.28 volume.
Transition mood: dramatic wipe → Scene 2

### Scene 2 — Live receiver — 4.9s
Recreate the Dashboard's real UI: the "Run the demo" button, cursor clicks it, then cut/dissolve into the waterfall itself — cells scrolling downward (teal hits, notched amber misses, slate listened, idle), the receiver's aperture bracket sliding across the band axis with its "LISTENING" mono label, threaded continuously down through the scroll per the real component. Small label: "LIVE RECEIVER."
Sequential/interaction: yes — simulate the cursor clicking "Run the demo," then the waterfall streams continuously (rows arriving one after another, not a single static frame).
Audio intent: the moment turns on — mechanism starting to run.
Audio-coupled idea: `interface/click` or `ui/mouseclick1` at the cursor tap; no SFX on individual waterfall rows (too dense — let the bed carry it).
Music: bed continues, first gentle build starts near the scene's end.
Transition mood: dramatic wipe → Scene 3

### Scene 3 — The claim — 4.4s
Cut to the fixed sweep's real failure stat, stamped large in rose: "FIXED SWEEP — 0.000 DETECTION." Beat later, gold/teal counter-stamp: "INDEX POLICY — 0.967." Both are real numbers from the product's own verified runs (Scenario B / the synchronization-trap case), not invented.
Sequential/interaction: yes — two sequential stat slams, each held to its own reading floor (~2s) before the next lands; not a fast beat-grid dump.
Audio intent: the sting, then the answer — tension into relief.
Audio-coupled idea: `impact/impactBell_heavy_000` (or `_004`) on the "0.000" slam; a lighter accent (`impact/impactSoft_medium`) on the "0.967" counter.
Music: strong cue lock at **8.74s** — the "0.000" slam lands on this beat.
Transition mood: hard cut → Scene 4

### Scene 4 — Head to head — 4.4s
Recreate the lift chart: a zero line, 2-3 metric bars sweeping out from it (e.g. "Spectrum heard," "Listening efficiency," "Distinct bursts caught"), gold/teal reading better than the fixed-sweep reference. Small caption after the bars settle: "MEASURED. NOT ASSERTED."
Sequential/interaction: yes — bars arrive one by one (first the strongest, e.g. "Distinct bursts caught"), each settling before the next starts; caption text arrives only after all bars are in.
Audio intent: confident, additive — each bar is a small win landing.
Audio-coupled idea: accent the first and last bar only (e.g. `interface/drop_001` / `casino/chip-lay-1`), not every bar.
Music: strong cue lock at **13.11s** — first bar's arrival.
Transition mood: dramatic wipe → Scene 5

### Scene 5 — Outro — 4.0s
`#0b1020` ground. The gold "P" brand mark and "PUSHPAK" wordmark slam in together, Archivo, full scale. Tagline beneath: "Learning where to listen." Small, legible final line in mono: "SIMULATION ONLY — NO REAL RF."
Sequential/interaction: yes — wordmark slams first, tagline and scope line settle a beat after (not simultaneous with the slam).
Audio intent: the payoff — confident, then quiet.
Audio-coupled idea: `impact/impactBell_heavy_003` on the wordmark slam.
Music: strong cue lock at **17.47s** for the slam; bed fades out under the final hold.
Transition mood: — (final scene)

**Music mood for this video:** cinematic
**Audio summary:** A steady, clean instrumental bed (vol-12) underscores the whole video at restrained volume, built around three strong-cue locks (8.74s / 13.11s / 17.47s) that carry the claim, the comparison, and the outro logo — with a single interaction click and two stat-hit accents as the only other cues, so the two real numbers stay the loudest thing in the video.
