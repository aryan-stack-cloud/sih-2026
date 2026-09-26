# v14-product-demo — plan and source table

Show-it-as-is demo of the PUSHPAK Spectrum Scan Scheduler (SIH26055), 120s, 1920×1080.
8 frames: hook → fair-fight rules → Bandit race → Bandit +48% → Q-learning race → Q-learning +141% → six-view tour → Team Pushpak outro.

## Every number on screen, and where it comes from

| On screen | Value | Source |
|---|---|---|
| K = 2 bands heard at once, 16 under surveillance | product fact | `Frontend/src/pages/DemoPage.tsx` + live UI |
| Bandit Pd 17.3% vs sweep 11.6%, +48% | live 1-episode run | backend `exp_4e120d05`, Scenario B, seed 42, 80 steps, 2026-09-26 (backend comparison: +48.2758…%) |
| Bandit reach 6/10, sweep 10/10 | same run | `emitters_detected` 6 vs 10 |
| Bandit efficiency 31.9% vs 22.5% | same run | `scan_efficiency` (race tiles, mid-run values differ) |
| Q-learning Pd 28.1% vs 11.6%, +141% | live 1-episode run | backend `exp_5b3c39a3`, same setup (comparison: +141.3793…%) |
| Q-learning reach 5/10 | same run | `emitters_detected` 5 vs 10 |
| 80/80 ML decisions, 0 fallbacks | same runs | `ml_decisions: 80, fallback_decisions: 0` in both learners |
| All services up | verified live | `/ready`: backend + ml_scheduler + ml_periodicity up |
| model_bandit_0496bb32, model_q_learning_3ab4031f | serving checkpoints | experiment `model_ids` |
| One-episode runs are illustrative | honesty footnote | DemoPage copy + RUNNING.md (compare on `ait_censored`, coverage trade-off) |
| Simulation only, no RF hardware | standing fact | PRODUCT.md, RUNNING.md, live UI scope-note |

Rounded display values (17.3 vs 11.6) would naively give 49.1%; badges use backend-exact lifts (+48.28% → +48%, +141.38% → +141%).

## Corrections to requested figures (carried from v12)

- Turing dataset is 70 GB / 9,000 files, not 80 GB — not mentioned in this cut (no dataset claim on screen).
- No per-model training-time claim on screen in this cut (races are live runs, not training).

## Build lessons (v14)

- `querySelector(All)` / `gsap.utils.toArray` with a digit-leading id (`#06-…`) throws SyntaxError and kills the whole frame IIFE: 07-tour froze invisible (throw after fromTo authoring), 06-graph froze fully visible with dead counter (throw before any authoring). Fix: `getElementById(…).querySelectorAll('.w')`. Treat `id_requires_css_escape` lint warnings as fatal in frame JS.
- onUpdate-driven counters DO render on snapshot seeks (04 verified 13.9% mid-count) — a frozen counter + live siblings means the tween never got added, not a seek limitation.
- audio.mjs `fetch-sfx` regenerates `audio_meta.json` voices from engine state and drops hand-patched entries — patch voices LAST; never run engine subcommands you haven't read.
- `sync-durations` overwrites designed frame durations with VO lengths — restore demo-paced durations after syncing.
- Bundled SFX names only (chime, click-soft, ping, pop, riser, sparkle, typing, …); custom names silently skip.
- Fonts: no captured .woff2 exists — use Windows-bundled Arial / Arial Narrow / Consolas + local() @font-face so lint's font check passes and headless Chrome renders them.
