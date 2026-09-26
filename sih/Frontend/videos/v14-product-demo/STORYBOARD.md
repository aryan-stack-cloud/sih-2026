---
format: 1920x1080
duration: 120s
message: "Press a button and watch a learned scheduler beat the fixed sweep, live — twice."
arc: Demo Loop → question → product intro → demo cycle 1 → demo cycle 2 → trust → CTA
audience: SIH judges watching a live demo
music: confident minimal tech underscore
---

## Locked (layout confirmed 2026-09-26)

- All 8 frames approved as sketched in storyboard.html v1; user: "everything is okay".
- Frame 4 verified: +48% badge is exact (48.28% backend lift, exp_4e120d05). Rounded display values must stay paired with backend-exact badges.

## Decisions (locked at plan approval)

- **Message**: Press one button and watch a learned scheduler beat the fixed sweep, live — twice.
- **Audience and arc**: SIH judges on a projector; Demo Loop (question → intro → race → graph → race → graph → trust → CTA).
- **Format**: 1920×1080, ~120s, Kokoro af_heart voiceover, confident minimal tech underscore, captions keep-out top ~83%.
- **The spine**: the captured Dashboard window is the persistent hero prop; the Run live comparison button is the callback object — pressed in F3, pressed again in F5, its invitation returns in F8.
- **Brand** (from capture/tokens.json): canvas `#0B1020`, panel `#141B2E`, ink `#E6EAF5`, muted `#8A93AD`, gold `#E8B84B`, electric `#77A8FF`, caught-green `#0F9E73`, missed-amber `#C87A18`; display Barlow Condensed 600, body Archivo, data JetBrains Mono; radius 4px, easings ease-out.
- **Bans**: no fake product UI (captured screens or plain stand-in panels only); no glow; no invented numbers (all from exp_4e120d05 / exp_5b3c39a3); no slideshow cards, no screensaver motion; simulation-only line stays visible.
- **Held frame**: F8 outro, 5s near-still while the tagline lands.
- Truthfulness: waterfall/graph stand-ins are labelled placeholders holding slots for the real captured screens the build dresses in; race numbers are the real 1-episode runs, footnoted as illustrative.

## Video direction

- **Palette** (from frame.md, code-editorial remixed onto brand): canvas deep navy `#0B1020`; panels `#141B2E`/`#1B2440`; ink `#E6EAF5`, muted `#8A93AD`; gold `#E8B84B` for badges, wins and the Run button; electric `#77A8FF` for aperture accents; caught-green `#0F9E73`, missed-amber `#C87A18`, alarm-red reserved. Type by role: display Barlow Condensed 600, body Archivo, data JetBrains Mono with tabular-nums.
- **Motion grammar**: smooth long-tail settles (`power3`) everywhere; reveals fire on spoken cues across the back ~50%, never dumped in the first 25%; entrances state from-states (`fromTo`); all motion lives in the paused GSAP timeline — no CSS transitions/keyframes, no `repeat`/`yoyo`, no randomness.
- **Shot model**: one continuous film, one camera feel; races use push-slide seams, section turns use zoom-through, same-world graphs use crossfade.
- **Held frames**: F4 tail, F6 tail and F8 hold still (subtle jitter at most on the badge/lockup); F3/F5 tails stay alive only through the subject's own motion (streaming rows, ticking tiles — live internals, not breathing cards).
- **Negative list**: no fake product UI; no glow/bloom; no bouncy or elastic entrances; no slideshow front-loads; no screensaver drift; no browser chrome or cursors except the two scripted Run presses; content stays in the top ~83% (caption keep-out).

## Frame 1 — The spectrum is wide

- scene: Hook type over the live hero; aperture ruler glints, K = 2 badge pulses
- voiceover: "The spectrum is wide. Your receiver is not. Watch ours learn to listen better — live, twice."
- duration: 8s
- transition_in: cut
- status: animated
- src: compositions/frames/01-hook.html
- type: hook
- persuasion: Pain validation
- beat: tension → curiosity
- asset_candidates: assets/scroll-000.png — masthead plus hero plus aperture card, viewport top

The hook speaks outcome language, never features. Lands the value claim in beat 1: a live learned scheduler beating the sweep, twice.

narrativeRole: Give the judge a reason to keep watching: a narrow receiver that learns, proven live.
keyMessage: A receiver that hears 2 of 16 bands can still beat a fixed sweep — and you will see it happen.

- blueprint: kinetic-type-beats (Reproduce)
- focal: assets/scroll-000.png
- roles: scroll-000 = background (full-bleed hero, dim ~45%)
- sfx: riser

Reproduce: keep the in-place word-swap signature; the four key words are the slots.
Scene 1 (0.0–2.5s): bare canvas over dimmed hero; "THE SPECTRUM IS WIDE." assembles via per-word staggered reveal → dynamic-content-sequencing, Centered hero ~60%.
Scene 2 (2.5–5.5s): "NOT." hard-cuts in via flash word-swap → discrete-text-sequence on the spoken "not"; LIVE and TWICE chips scale in with a smooth long-tail settle on "live, twice".
Scene 3 (5.5–8s): hold; a tiny finite positional jitter on the TWICE chip (single tween, no repeat); otherwise still.

## Frame 2 — Two bands at a time

- scene: Full Dashboard plate; aperture ruler highlights bands, honesty chip settles
- voiceover: "Ours hears two bands of sixteen. Simulation only — no real radio. Same spectrum, same seeds — only the listening changes."
- duration: 12s
- transition_in: zoom-through
- status: animated
- src: compositions/frames/02-aperture.html
- type: product_intro
- persuasion: Friction reduction
- beat: clarity → trust
- asset_candidates: assets/full-page.png — whole Dashboard plate at 1920 wide; assets/scroll-100.png — controls plus waterfall plus tiles

Sets the fair-fight rules before any number appears: K = 2 of 16, simulation-only, identical seeds so only the listening differs.

narrativeRole: Make the demo legible and honest before the races.
keyMessage: Two bands at once, same spectrum for both runners, simulation only.

- blueprint: cursor-ui-demo (Adapt)
- focal: assets/full-page.png
- roles: full-page = background (dim ~40%); scroll-100 = supporting (controls close-up in Scene 4)
- sfx: click-soft

Adapt: keep the cursor-led first look; change: a cursorless aperture glint opens the shot (handoff from F1) and the cursor only travels ruler to Run button.
Scene 1 (0.0–3.5s): full plate dimmed; aperture ruler glints via keyword glow → asr-keyword-glow as the VO says "two bands of sixteen"; Centered ruler ~50%.
Scene 2 (3.5–6.5s): cursor sweeps in; honesty chip types on via type-on with caret → discrete-text-sequence on "Simulation only — no real radio".
Scene 3 (6.5–9.5s): twin seed badges ("same spectrum", "same seeds") reveal sequentially via cluster→outward expansion → center-outward-expansion, asymmetric 60/40.
Scene 4 (9.5–12s): cursor lands on the Run button with press ripple and button compression → cursor-click-ripple; hold.

## Frame 3 — Race one: Bandit

- scene: Cursor picks Bandit, presses Run live comparison; waterfall streams, tiles tick up
- voiceover: "Race one: the Bandit. Pick it, press run, and watch the waterfall. Green is caught, amber slips past."
- duration: 25s
- transition_in: push-slide LEFT
- status: animated
- src: compositions/frames/03-bandit-race.html
- type: feature_showcase
- persuasion: Show-don't-tell proof
- beat: anticipation → excitement
- asset_candidates: assets/scroll-100.png — controls plus waterfall plus tiles, the live-race backdrop

Demo cycle 1 of 2. The machine visibly works: trigger (press), theater (waterfall + tiles), receipt lands in Frame 4.

narrativeRole: First live proof — the Bandit run happens on screen.
keyMessage: Press one button; the Bandit races the sweep on unseen spectrum.

- blueprint: agent-progress-theater (Reproduce)
- focal: assets/scroll-100.png
- roles: scroll-100 = background (dim ~35%, full-bleed race stage)
- sfx: click-soft, typing

Reproduce: trigger hands to the machine, theater plays, receipt teases at the tail.
Scene 1 (0.0–4s): challenger tag "Bandit" flips in via hard-cut word-swap → discrete-text-sequence; cursor presses Run: click + ripple with button compression → cursor-click-ripple.
Scene 2 (4–10s): waterfall rows stream newest-first as the VO says "watch the waterfall" (live internals → svg-icon-enrichment on row ticks); tiles tick up.
Scene 3 (10–22s): machine theater continues — rows land, counters tick; camera holds locked, no back-half push.
Scene 4 (22–25s): stream settles; heard-tile glows via keyword glow → asr-keyword-glow on "Green is caught"; hold into the harness transition.

## Frame 4 — Bandit: plus forty-eight percent

- scene: Lift chart builds; 17.3 vs 11.6 counts up; coverage footnote fades in
- voiceover: "Bandit hears seventeen percent of the spectrum — the sweep, eleven. Plus forty-eight percent. Fewer emitters, more signal."
- duration: 15s
- transition_in: crossfade
- status: animated
- src: compositions/frames/04-bandit-graph.html
- type: benefit_highlight
- persuasion: Statistical proof
- beat: triumph → confidence
- asset_candidates: assets/scroll-100.png — head-to-head lift chart region of the Dashboard

Receipt for race one. Numbers are the live 1-episode run (exp_4e120d05, Scenario B seed 42, 80 steps): Bandit Pd 17.3% vs sweep 11.6% (+48%), efficiency 31.9% vs 22.5%. Honest footnote: Bandit reached 6 of 10 emitters vs the sweep's 10.

narrativeRole: Turn the run just watched into one remembered number, honestly caveated.
keyMessage: Bandit +48% detection on the same spectrum — and the trade-off stated plainly.

- blueprint: dataviz-countup (Reproduce)
- focal: assets/scroll-100.png
- roles: scroll-100 = supporting (lift-chart region behind the hero stat)
- sfx: ping, pop

Reproduce: count-up number landing on one hero metric; the badge is the payoff.
Scene 1 (0–3.5s): "17.3%" counts 0→17.3 via value-scaled counter → counting-dynamic-scale with ring fill → stat-bars-and-fills; Centered hero ~55%.
Scene 2 (3.5–6s): "vs 11.6%" wipes in beside via velocity-matched cut-the-curve → cut-catalog.md.
Scene 3 (6–10s): "+48%" badge spring-pops → spring-pop-entrance (smooth settle, no overshoot) on the spoken "plus forty-eight percent".
Scene 4 (10–15s): coverage footnote fades in last so the win lands before the caveat; full still hold.

## Frame 5 — Race two: Q-learning

- scene: Challenger switches to Q-learning; second run streams faster, efficiency tile climbs
- voiceover: "Race two: Q-learning. Same button, same spectrum — a scheduler that values the future, not just the moment."
- duration: 25s
- transition_in: push-slide LEFT
- status: animated
- src: compositions/frames/05-qlearning-race.html
- type: feature_showcase
- persuasion: Show-don't-tell proof
- beat: anticipation → excitement
- asset_candidates: assets/scroll-100.png — controls plus waterfall plus tiles, the live-race backdrop

Demo cycle 2 of 2. Same ritual, new challenger — the repetition is the rhetoric: it works again.

narrativeRole: Second live proof — Q-learning on the identical setup.
keyMessage: Same button, same spectrum, second learner — watch it work again.

- blueprint: cursor-ui-demo (Adapt)
- focal: assets/scroll-100.png
- roles: scroll-100 = background (dim ~35%, full-bleed race stage)
- sfx: click-soft, typing

Adapt: keep the end-to-end press-to-result workflow; change: opens with the challenger tag swap (callback to F3) instead of a fresh intro.
Scene 1 (0–4s): "Bandit" hard-swaps to "Q-learning" → discrete-text-sequence; cursor re-presses Run with click ripple and button compression → cursor-click-ripple.
Scene 2 (4–9s): hotter waterfall streams (denser green rows); efficiency tile climbs as the VO says "values the future".
Scene 3 (9–22s): theater continues, locked camera, no back-half push.
Scene 4 (22–25s): settle; hold into the harness transition.

## Frame 6 — Q-learning: plus one-forty-one

- scene: Second lift chart; 28.1 vs 11.6 counts up; side-by-side Bandit vs Q-learning recap
- voiceover: "Twenty-eight percent heard — plus one hundred forty-one. Two learners, two wins, one button."
- duration: 15s
- transition_in: crossfade
- status: animated
- src: compositions/frames/06-qlearning-graph.html
- type: benefit_highlight
- persuasion: Statistical proof
- beat: awe → conviction
- asset_candidates: assets/scroll-100.png — head-to-head lift chart region of the Dashboard

Receipt for race two (exp_5b3c39a3, same setup): Q-learning Pd 28.1% vs 11.6% (+141%), efficiency 46.9% vs 22.5%. Footnote: 5 of 10 emitters reached; one-episode runs are illustrative, not stable estimates.

narrativeRole: The climax number, plus the side-by-side recap of both races.
keyMessage: Q-learning +141% — two learners, two wins, one button.

- blueprint: video-text-pivot (Reproduce)
- focal: assets/scroll-100.png
- roles: scroll-100 = supporting (race tail sliding aside)
- sfx: ping, pop

Reproduce: the run holds center, slides aside to hand weight to the hero stat, recap seals it.
Scene 1 (0–3s): frozen race tail holds center; "28.1%" counts up via value-scaled counter → counting-dynamic-scale.
Scene 2 (3–6s): run panel slides aside and "+141%" badge pops → spring-pop-entrance; split asymmetry 60/40.
Scene 3 (6–11s): recap strip (Bandit +48% · Q-learning +141% · one button) wipes in word by word → per-word staggered reveal → dynamic-content-sequencing.
Scene 4 (11–15s): full still hold.

## Frame 7 — The whole machine

- scene: Six mission-view cards assemble; Models provenance and Health status glow
- voiceover: "Behind the button: six mission views — simulations, raw stream, experiments, trained models, health. All live, all real."
- duration: 15s
- transition_in: zoom-through
- status: animated
- src: compositions/frames/07-tour.html
- type: feature_showcase
- persuasion: Value stacking
- beat: confidence → trust
- asset_candidates: assets/full-page.png — Dashboard plate grounding the tour; assets/contact-sheet.jpg — labeled grid for review reference

The full tour the user asked for, compressed: six views, real registry provenance (model_bandit_0496bb32, model_q_learning_3ab4031f served 80/80 ML decisions, zero fallbacks), backend + both ML services up.

narrativeRole: Prove depth behind the demo — a working system, not a staged clip.
keyMessage: Six live views, real trained models, everything up.

- blueprint: grid-card-assemble (Reproduce)
- focal: assets/full-page.png
- roles: full-page = background (dim ~45%, Dashboard grounding the tour)
- sfx: sparkle

Reproduce: cards self-assemble in staggered cascade; Models and Health lock in gold last.
Scene 1 (0–3s): bare stage; "Behind the button:" assembles word by word → per-word staggered reveal → dynamic-content-sequencing.
Scene 2 (3–9s): six view cards assemble in cascade → center-outward-expansion, 3-column grid ~70% of frame, each landing on its spoken name.
Scene 3 (9–12s): Models and Health lock gold; proof line ("80/80 ML decisions · 0 fallbacks · all services up") lights via keyword glow → asr-keyword-glow.
Scene 4 (12–15s): hold still.

## Frame 8 — Team Pushpak

- scene: Calm end card; wordmark, simulation-only line, try-it-live line
- voiceover: "Team Pushpak. Intelligent spectrum — safer skies."
- duration: 5s
- transition_in: blur-crossfade
- status: animated
- src: compositions/frames/08-outro.html
- type: cta
- persuasion: Status seeking
- beat: peace of mind → motivation
- asset_candidates: assets/scroll-000.png — masthead wordmark region as the lockup backdrop

Calm is the confidence: no hype, just the name and the invitation to run it live.

narrativeRole: Close with the team and the invitation.
keyMessage: Team Pushpak — run it yourself, live.

- blueprint: titlecard-reveal (Reproduce)
- focal: assets/scroll-000.png
- roles: scroll-000 = background (masthead wordmark region, dim ~55%)
- sfx: chime

Reproduce: one restrained move, then a still hold — low motion is the payload.
Scene 1 (0–1.5s): lockup rises via a single slide-up crossfade, Centered ~50%.
Scene 2 (1.5–5s): full still hold while the tagline and run-it-live line read; at most subtle jitter → sine-wave-loop (low amplitude) on the lockup. No exit motion — the render holds the final frame.
