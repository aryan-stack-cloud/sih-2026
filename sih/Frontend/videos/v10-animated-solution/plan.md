# v10 — Animated solution chapter

119-second narrated 2D technical film. This is a new numbered version; v1–v9 remain in the library.

## Story and shot design

| Time | Shot | What the viewer learns |
|---|---|---|
| 0–8 s | The burst fades before the aperture arrives | A signal can exist and still be missed. |
| 8–24 s | Antenna, tuner gate, ADC; wide particles narrow to two bands | Instantaneous bandwidth is a hardware limit. The problem statement's typical ≥10× ratio and the simulator's 2 of 16 ratio are separately labeled. |
| 24–34 s | The same 16-band rail, moving aperture, brief missed bursts | Software selects the next tuning position. |
| 34–45 s | A token travels Observe → Update → Choose → Retune while beliefs change | Every scheduling decision uses feedback under the same receiver budget. |
| 45–57 s | CTMC's irregular visits beside Index's belief/revisit ranking | Two designed strategies make distinct choices. |
| 57–67 s | Bandit reward bars and Q-learning value cells update | Reward can change a future choice. |
| 67–77 s | DQN network activity beside PPO probability bars | Two deeper learning representations. |
| 77–89 s | Generated patterns and Turing synthetic pulse replay converge on one virtual receiver | Inputs are simulation sources, not field measurements. |
| 89–101 s | Measured bars grow on an explicitly zoomed 0–0.15 axis | Scenario B detection: 0.1092 → 0.1334, +22% relative. |
| 101–110 s | Emitter reach bars and a separate Bandit tradeoff | Index preserves reach at 0.9667; Bandit's 0.7100 reach belongs to a separate evaluation. |
| 110–119 s | Tuner window and wordmark settle | Training wall time unlogged; warm scheduler API p95 6.6 ms is decision latency. |

The frequency rail persists in the same screen position through the film. Amber marks the chosen scan position, cyan marks observation and data, and coral marks a missed burst. Each section has a moving aperture or animated decision state, with a gentle camera drift and short overlaps between shots. Narration was rewritten to use plain language before introducing each model name.

## Source boundaries

- `Ai-ml-1-Scheduler-Engine/IMPLEMENTATION.md`, Results: Scenario B, six held-out seeds for fixed sweep and Index, 2,000 steps, Pd 0.1092 and 0.1334, both interception ratio 0.9667. The graph labels the 0–0.15 zoom so its bars cannot be mistaken for a 0–1 scale.
- The Bandit column uses 20 evaluation seeds: Pd 0.3375 and interception ratio 0.7100. It is shown as a separate tradeoff, not a matched six-seed lift.
- The same implementation document reports warm scheduler HTTP p95 6.6 ms. It is not training time or full pipeline latency.
- The registry and replay adapter support labeled Turing synthetic radar replay runs. This film does not claim that all six methods were trained on both inputs, nor that Turing replay produced the Scenario B lift.
- Training wall times are not recorded comparably in the saved run metadata, so no training duration appears.

## Production

Original 2D SVG/CSS illustrations, seek-safe GSAP motion, offline Kokoro narration, original electronic score and restrained transition SFX. Composition source and audio are in `composition/`. Earlier numbered videos were not changed.

## Verification

- HyperFrames 0.8.73 `check`: 0 errors; 0 runtime, layout, or motion issues; 147/147 contrast checks passed. Eleven structural warnings flag the intentionally monolithic shot composition. Nine layout info notices correspond to the small camera crop at shot edges.
- Rendered MP4: 119.000 s, 1920×1080, 30 fps, H.264 video, stereo AAC, 76.9 MB. Audio analysis: −20.4 LUFS integrated, −1.6 dBFS true peak. Encoded frames across the full film were reviewed.
- A downscaled one-second frame-difference audit found no near-still one-second intervals in v10 (0/116 under 0.002 normalized difference), versus 57/109 in v9. This is a motion proxy, not a perceptual quality score.
- `graphify update .` was attempted after editing composition code but the existing installation returned `uv trampoline failed to canonicalize script path`.
