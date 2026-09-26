# Hyperframes Composition Brief: PUSHPAK — Spectrum Scan Scheduler

## Objective
Create a short launch-style brag video for PUSHPAK, a live demonstrator for a machine-learned Electronic Support receiver scheduler (SIH26055).

## Output
- Composition directory: `brag-output/composition/`
- Rendered video: `brag-output/brag.mp4`
- Format: landscape — 1920x1080
- Duration: 21.5 seconds

## Source Material
- Project root: `sih/Frontend` (this repo)
- Primary files read: `PRODUCT.md`, `index.html`, `src/styles.css`, `src/app/App.tsx`, `src/pages/DemoPage.tsx`, `src/components/Waterfall.tsx`, `src/components/LiftChart.tsx`
- Product name: PUSHPAK — "Spectrum Scan Scheduler"
- Tagline / strongest claim: "A receiver that can hear two bands at a time, deciding where to listen next — and learning to do it better than a fixed sweep." Strongest verified stat: a fixed sweep scores **0.000 detection** in a synchronization-trap scenario; the second-generation "index" policy holds a **0.967** interception ratio vs the first-generation "bandit" policy's **0.710** on Scenario B hold-out seeds (+36%).
- Key UI or visual moment to recreate: the spectrum waterfall (`Waterfall.tsx`) — frequency across, time down, newest row at top, the receiver's aperture drawn as a bracket threaded down through the scroll — and the Dashboard's own three-beat flow (`DemoPage.tsx`): press "Run the demo" → live waterfall → head-to-head comparison.
- Copy that must appear verbatim:
  - "Run the demo" (real button label)
  - "FIXED SWEEP — 0.000 DETECTION" (real verified figure, synchronization-trap scenario)
  - "0.710" / "0.967" (real verified interception-ratio figures, bandit vs index, Scenario B hold-out seeds)
  - "SIMULATION ONLY — NO REAL RF" (compact form of the product's own standing scope note)

## Creative Direction
- Tone preset: cinematic
- Creative direction: an instrument-panel trailer — the spectrum as a dramatic, high-stakes surface, shot like the product's own SDR waterfall rather than generic dashboard furniture.
- Interpretation: dramatic reveals over quick cuts, full-bleed scenes, large type holding its moment before the next beat lands. Copy stays restrained and factual (short declaratives, real numbers only) even as the visuals go big.
- Angle: the product's strongest material is a number, not a metaphor — a fixed sweep that scores exactly 0.000 detection in a trap scenario, and a measured, verified generational improvement (bandit → index, +36% interception ratio). The video watches the receiver's aperture fail to cover the spectrum, then proves the fix with real numbers, not marketing language.
- Hook: "A RECEIVER THAT CAN HEAR TWO BANDS AT A TIME." / "LEARNING WHERE TO LISTEN." — the product's own standfirst line, split for weight, on full-bleed ground with nothing else on screen.
- Outro / punchline: PUSHPAK wordmark slam, tagline "Learning where to listen.", then "SIMULATION ONLY — NO REAL RF" as a small legible mono readout — the honesty is part of the brand, not a disclaimer bolted on.
- Avoid:
  - Generic SaaS language
  - Abstract filler visuals
  - Unrelated visual redesign of the product's real UI language
  - Any invented/fabricated statistic — every number shown must trace to a verified figure in `PRODUCT.md`'s Evidence section

## Visual Identity
- Background: `#0b1020` (ground); panels `#141b2e` / `#1b2440`; rule `#263054`
- Text: `#e6eaf5` (ink), `#8a93ad` (muted), `#5c6580` (faint)
- Accent: `#e8b84b` brand gold (on-gold ink `#241a05`) — reserved for brand/outro moments only
- Data/status hues (reserved, never repurposed as decoration): intercepted `#0f9e73`, missed `#c87a18`, false-alarm `#d8425f`, listened `#3a445f`, idle `#161d33`
- Display font: Archivo Black (pre-bundled, embeds with zero setup) — hook lines, stat callouts, wordmark
- Body/data font: JetBrains Mono (pre-bundled) — waterfall axis, aperture label, stat readouts, outro scope line
- Visual references from the project: the spectrum waterfall's cell-state legend and aperture bracket (`Waterfall.tsx`), the diverging lift-chart bar form (`LiftChart.tsx`), the masthead's gold "P" brand mark and "Team Pushpak" wordmark (`App.tsx`)

## Storyboard
Use the storyboard in `brag-output/brag-plan.md` as the creative contract, refined below with sourcing corrections made during composition (see note at the end).

Scene summary:
1. Hook — 3.82s — two-line standfirst statement on full-bleed ground, no chrome
2. Live receiver — 4.92s — cursor clicks "Run the demo," then the waterfall streams with the aperture bracket threaded through the scroll and one retune step
3. The claim — 4.37s — "FIXED SWEEP — 0.000 DETECTION" (synchronization-trap scenario) then "LEARNED POLICIES — ESCAPE IT"
4. The fix, measured — 4.36s — bandit (0.710) vs index (0.967) interception-ratio bars, Scenario B hold-out seeds, +36%
5. Outro — 4.03s — PUSHPAK wordmark, tagline, simulation-only scope line

## Audio
- Audio role: cinematic support — a restrained low bed, no melodrama
- Audio arc: fades in under the hook (~0.28), gentle swells into the two reveal moments (scene 3 and scene 4 cuts), settles under the outro, fades to 0 by the last frame
- Music: `happy-beats-business-moves-vol-12-by-ende-dot-app.mp3` ("steady and clean," the bundled track recommended for cinematic/polished)
- Music treatment: volume automation lane (fade in 0→1s, hold ~0.28, small swells at the two reveals, fade out from ~20s to 21.5s) rather than a flat `data-volume`
- Music cue guidance: bundled preset (`music-cues.json`/`.md` for vol-12), 109.96 BPM. Strong-cue locks used: 8.74s (0.99, the "0.000 DETECTION" slam), 13.11s (0.98, the comparison chart's first bar), 17.47s (0.99, the outro wordmark) — all land as scene-cut boundaries, so the visual reveal and the beat coincide exactly.
- Audio-reactive treatment: subtle — skipped for this build in favor of the explicit beat-locked scene cuts above, which already land the major visual moments on the strongest beats; no waveform/equalizer visuals used.
- Audio-coupled moments:
  - Scene 2, cursor click on "Run the demo" — simulated interaction, click SFX
  - Scene 3, "0.000 DETECTION" slam — beat-locked major reveal, impact SFX
  - Scene 3, "ESCAPES IT" counter-stamp — softer accent SFX
  - Scene 4, bars settling — one accent SFX on the second (index) bar's landing
  - Scene 5, wordmark slam — beat-locked major reveal, impact SFX
- SFX selection guidance: restrained cinematic posture — 2-3 big impact hits plus one interaction click and one chart accent, nothing dense; low/medium high-frequency-risk families preferred for the repeated impact family
- Exact SFX choice: `interface/click_001.ogg` (button click), `impact/impactBell_heavy_000.ogg` (claim slam), `impact/impactSoft_medium_000.ogg` (counter-stamp), `interface/drop_001.ogg` (bar 2 landing), `impact/impactBell_heavy_003.ogg` (outro slam)
- Audio files: copied into `brag-output/composition/assets/music/` and `brag-output/composition/assets/sfx/...`

## Sourcing correction from `brag-plan.md`
`brag-plan.md`'s Scene 3/4 draft paired the sync-trap's "0.000 detection" fixed-sweep figure directly against the "0.967" interception-ratio figure as if they were one measured pair. They are two separate verified facts from `PRODUCT.md`'s Evidence section (the 0.000 figure is the fixed sweep's score in a synchronization-trap scenario; the 0.967-vs-0.710 figure is the index policy vs the first-generation bandit policy on Scenario B hold-out seeds). This brief corrects the storyboard so each real number stays attached to the comparison it actually measures — Scene 3 now pairs the fixed-sweep failure with the qualitative, equally-verified claim that both learned policies escape the trap; Scene 4 carries the specific 0.710-vs-0.967 figures as their own beat, framed as the product's own "scheduler evolution" story. No invented percentages are used anywhere in the video.

## Hyperframes Instructions
Composition built directly against `hyperframes-core` (composition contract, `data-*` timing), `hyperframes-animation` (spring-pop-entrance, kinetic-beat-slam, stat-bars-and-fills, ambient-glow-bloom rules), `hyperframes-creative` (house-style background layer, typography), and `hyperframes-cli` (lint/check/preview/render). This is `/brag`'s own workflow — the generic `hyperframes` entry-point intent interview was not used.

Requirements honored:
- Real UI recreated: the "Run the demo" button, the spectrum waterfall with aperture bracket, the diverging comparison bars, the masthead's brand mark.
- All text sized for full-screen viewing (headlines well above 60px, data labels above 16px) and held to its reading-time floor.
- Total duration 21.5s (within 15-25s).
- Music + SFX included (not disabled by the user).
- Beat-lock tolerance honored: all three strong-cue locks land exactly on scene-cut boundaries.
