# Hyperframes Composition Brief: PUSHPAK — The Receiver That Learns Where to Listen

## Objective

Create a 52-second, landscape explainer that first makes the problem legible, then animates the SCT solution, then proves the idea with the real working dashboard flow.

## Source material

- Repository: `sih/Frontend` and `sih/docs/superpowers/specs/`
- Primary files: `PRODUCT.md`, `src/pages/DemoPage.tsx`, `src/components/Waterfall.tsx`, `src/components/LiftChart.tsx`, `2026-09-11-smart-scan-strategy-design.md`, `2026-09-11-sct-scheduler-solution.md`
- Product: PUSHPAK — Smart Scan Strategy for Electronic Warfare / Spectrum Scan Scheduler
- Product claim: a simulated receiver that can listen to a limited number of bands, decide where to listen next, learn from hits/misses, and compare policy performance on identical seeds.
- Real evidence: fixed sweep 0.000 detection in the synchronization trap; bandit 0.710 versus index 0.967 on Scenario B hold-out seeds.

## Creative direction

- Workflow: custom/general-video explainer, not the short /brag teaser template.
- Tone: cinematic technical explainer with an instrument-panel visual language.
- Story order: problem → failure → solution loop → anti-synchronization mechanism → measured comparison → working demo → honest scope.
- 2D animation: inline SVG diagrams and flow lines.
- 3D animation: CSS perspective spectrum volume, layered depth planes, orbiting emitter pulse, and a moving aperture.
- Avoid: generic SaaS cards, stock footage, fake operational RF claims, invented metrics, and voiceover unless explicitly requested.

## Visual identity

- Ground: `#0b1020`; panels: `#141b2e` / `#1b2440`; rules: `#263054`
- Ink: `#e6eaf5`; muted: `#8a93ad`; brand gold: `#e8b84b`
- Status hues: intercepted `#0f9e73`, missed `#c87a18`, false-alarm/failure `#d8425f`, listened `#3a445f`
- Use system-safe sans/mono stacks so the render does not depend on network fonts.

## Scene contract

1. `0–5`: 2D coincidence hook.
2. `5–11`: 2D frequency/time explanation.
3. `11–17`: 3D-style synchronization trap and 0.000 failure.
4. `17–24`: 2D closed-loop solution flow.
5. `24–31`: 3D-style SCT belief/deadline/dither visual.
6. `31–37`: measured bandit/index comparison.
7. `37–47`: working demo recreation with real UI copy and waterfall behavior.
8. `47–52`: PUSHPAK close and simulation-only scope.

## Audio

- Music: existing `happy-beats-business-moves-vol-12-by-ende-dot-app.mp3` bed.
- SFX: click on the real demo button; impact on sync-trap failure; soft hit on SCT reveal; impact on measured comparison; final impact on wordmark.
- No voiceover.
- Use subtle audio-reactive scale/opacity on the 3D depth glow only if it remains readable.

## Technical constraints

- One deterministic, seek-safe GSAP timeline registered as `window.__timelines["pushpak-explainer"]`.
- Root duration 52 seconds, 1920×1080.
- Timed scenes use `class="clip"` and `data-start`/`data-duration`.
- No render-time clocks, random values, network fetches, or infinite repeats.
- Verify with `npx hyperframes check`; render only after the preview/check gate.
