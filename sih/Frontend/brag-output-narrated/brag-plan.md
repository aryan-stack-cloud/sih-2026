# PUSHPAK — The Receiver That Learns Where to Listen

## Message

When a receiver can hear only a small slice of spectrum, a fixed sweep can be perfectly synchronized with a periodic emitter and miss it forever. PUSHPAK turns that blind loop into a closed-loop simulation: observe, estimate, prioritize, dither, and compare the result live.

## Research grounding

- The repository's solution specification defines the problem as a two-dimensional coincidence: frequency coincidence and temporal coincidence, with energy/dwell sensitivity as a third constraint.
- The repository's research notes identify synchronization as the failure mode of periodic receiver schedules and motivate aperiodic/jittered revisit patterns.
- Clarkson's peer-reviewed ES receiver scheduling paper describes the same synchronization mechanism: a receiver can be tuned to the wrong band every time an emitter illuminates it. Source: https://ietresearch.onlinelibrary.wiley.com/doi/10.1049/iet-rsn.2018.5668
- Every performance number in this video comes from the repository's verified evidence: fixed sweep 0.000 detection in the synchronization-trap scenario, and bandit 0.710 versus index 0.967 on Scenario B hold-out seeds. These are separate comparisons and remain labeled separately.

## Audience and tone

SIH26055 judges and non-specialist technical viewers. Tone: cinematic technical explainer, clear enough to follow without RF background, specific enough to survive specialist scrutiny. Narrated version: full voiceover (Kokoro `af_heart`, offline) carries the story; on-screen copy, diagrams, and motion reinforce it. Music bed is carved under the voice so narration stays intelligible.

## Storyboard — 54 seconds, landscape 1920×1080 (narrated; S4 + S6 extended 1s each for voice fit)

| Scene | Time | Story beat | Visual treatment |
|---|---:|---|---|
| 01 — The blind spot | 0–5s | A receiver is listening, but the signal keeps arriving elsewhere. | 2D split-stage: periodic emitter pulse train above a narrow receiver aperture; two labels land: “RIGHT FREQUENCY” and “RIGHT TIME”. |
| 02 — Two dimensions | 5–11s | Detection requires both coincidences; the aperture is a small window in a large spectrum. | 2D SVG frequency/time grid grows from axes. Signal pulses descend while a receiver window scans. A red “MISS” appears at every near-overlap. |
| 03 — The synchronization trap | 11–17s | A periodic fixed sweep can lock into permanent blindness. | 3D-style perspective spectrum volume: emitter orbit and fixed receiver rail repeat in phase. Camera pulls back, the red trail closes into a loop, then “0.000 DETECTION”. |
| 04 — What we change | 17–25s | PUSHPAK turns open-loop sweeping into observe → estimate → decide → learn. | 2D four-node solution flow draws itself, with arrows and live pulse packets. Each node carries project-native nouns: waterfall, periodicity, index, feedback. |
| 05 — Search / Confirm / Track | 25–32s | SCT ranks bands with beliefs and deadlines, then keeps a randomized floor. | 3D-style tilted receiver plane with six belief bars, a gold index beam, a revisit deadline ring, and phase dither that breaks the loop. |
| 06 — Measured, not asserted | 32–39s | The measured scheduler evolution is the proof. | Split comparison bars: BANDIT 0.710 vs INDEX 0.967, “Scenario B · hold-out seeds”, and a separate sync-trap badge “fixed sweep 0.000”. |
| 07 — Working demo | 39–49s | Show the real product flow: run → waterfall → compare. | Recreated dashboard panel with real “Run the demo” button, cursor click, streaming waterfall, aperture bracket, and metric cards. |
| 08 — Honest close | 49–54s | Name the system and scope it accurately. | PUSHPAK lockup, tagline, and “SIMULATION ONLY · NO REAL RF”. |

## Voiceover script (Kokoro af_heart, 44.5s total, per-scene placement)

- S1 (0.4s): “The signal is there. But are we listening at the right moment?”
- S2 (5.3s): “Two coincidences make a detection: right band, right moment. We hear only two bands at once.”
- S3 (11.4s): “A fixed sweep can lock into blindness, missing every pulse. Detection: zero.”
- S4 (17.4s): “Pushpak stops sweeping, and starts learning. Observe, estimate, decide, and learn. Every observation drives the next choice.”
- S5 (25.3s): “Search, confirm, track. Beliefs plus revisit deadlines, with anti-sync dither, so we never lock out a band.”
- S6 (32.3s): “Measured, not asserted. Bandit: zero point seven one. Index: zero point nine six seven.”
- S7 (39.5s): “Now the working product. Press run the demo, watch the waterfall stream, and see Index pull ahead, live.”
- S8 (49.6s): “Pushpak. Learning where to listen. Simulation only.”

## Motion language

- 2D: SVG stroke-draw connectors, scanline pulses, stepped state changes, and count-up labels.
- 3D: CSS perspective planes and layered depth, not a fake photorealistic object. The receiver aperture moves through a tilted spectrum volume; depth is used to explain coverage and revisit, not as decoration.
- Transitions: hard data wipes and a perspective pull-through between the problem and solution. No generic stock footage or unrelated imagery.

## Audio

Use the existing restrained instrumental bed plus sparse impact/click accents, carved under the voiceover (dynamic carve, strength 0.8). Music supports the arc; it must not overpower the narration. Strong cues land on the synchronization failure, the index comparison, and the final wordmark. Narration: 8 per-scene voice clips (`assets/voice/s1–s8.wav`), grouped as `voiceover`.

## Scope guardrails

- Keep “simulation-only” visible in the close.
- Do not imply real RF interception, jamming, or operational deployment.
- Do not pair the 0.000 figure with 0.967 as if they are one matched experiment.
- Use only the verified numbers listed above.
