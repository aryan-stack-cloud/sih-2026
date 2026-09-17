# Product

<!-- impeccable:product-schema 1 -->

## Platform

web

## Users

Two real audiences, in this priority order for the current redesign:

1. **SIH26055 judges**, evaluating this alongside many other student projects, watching a short live demo (minutes, not hours) on a laptop or projector. They need to understand what they're looking at almost immediately, without an RF/ML background explained to them first. *[inferred from the user's explicit answer: "Judges watching a live demo" is the primary audience for this redesign]*
2. **The team itself**, using it as a working test harness to run simulations, compare scheduling policies, and inspect trained models during development. This is the app's original, ongoing purpose and the reason its current UI is dense and utilitarian.

## Product Purpose

A live, working demonstrator for a machine-learning Electronic Support receiver scheduler (SIH26055: "Smart Scan Strategy for Electronic Warfare"). It lets someone run a simulated RF spectrum scenario, watch a scheduler decide in real time which band to listen to next, and compare that decision-making against a fixed sweep and against other learned policies — on real metrics from a real (simulated) run, not canned numbers.

Success for this redesign: a judge who has never seen the project before can watch one live run and correctly understand, within about a minute, what problem is being solved and why the result on screen matters.

## Positioning

Most competing student projects in this space will show a static slide deck or a screen recording. This one is a real, running, interactive system: press a button and it visibly, live, races a machine-learned scheduler against a fixed sweep on a spectrum neither has seen before, with a WebSocket-driven live view and real computed metrics. The mechanism a neighboring project could not truthfully copy: the scheduler evolution itself is the story — a naive learned policy (bandit) that trades away coverage for density, and a second-generation policy (index / Search-Confirm-Track) that was built specifically to fix that trade, with the fix measured and shown, not asserted.

## Operating Context

- Presented live, likely from a laptop screen (projector or judge's own monitor), for a few minutes per team, in a room with several other demos competing for attention.
- Backed by four real running services (a Java Spring Boot backend, two Python ML services, this React frontend) — the data on screen is live simulation output, not mocked. A WebSocket streams per-step frames during a run.
- The underlying subject is electronic warfare / signals-intelligence spectrum scanning, but the system itself is explicitly, repeatedly documented as **simulation-only**: no real RF hardware, no interception, no jamming, no weapon control. That framing is a standing, non-negotiable fact of the product and must stay visible/honest in the UI, not softened or hidden.
- Six scheduling policies exist and are selectable: baseline (fixed sweep), random, bandit, Q-learning, DQN, PPO, plus two newer ones — index (Search-Confirm-Track) and ctmc (randomised floor).

## Capabilities and Constraints

- Real-time live view of the simulated spectrum (a waterfall/spectrogram: frequency across, time down) as a run executes.
- Run a single simulation, or an experiment comparing multiple policies head-to-head on identical seeds.
- Real computed metrics per run/experiment: Pd, Pfa, HPDR, scan efficiency, interception ratio, run intercept rate, AIT / censored AIT, precision/recall/F1.
- A model registry (six trained policies, each with real provenance — seed ranges, training dates) that can be browsed and activated.
- Current implementation: React 18 + TypeScript + Vite, Zustand for state, plain CSS (no component library, no Tailwind) — a from-scratch, unopinionated visual base, so this redesign is not fighting an existing design system.
- No automated frontend tests exist yet; a visual/behavioral regression here would currently only be caught by hand.
- Existing pages: Dashboard/Demo (the judge-facing scripted demo), Simulations, Raw stream, Experiments, Models. The user has explicitly given permission to restructure this set (merge, split, rename, or reduce pages) if that produces a clearer result — the current five-page split is not a constraint to preserve for its own sake.

## Brand Commitments

The team name is **PUSHPAK**, and it is confirmed to appear inside the app itself (a small mark, not just the pitch deck) — the user's direction: "make a little logo of the team pushpak."

A full ceremonial team emblem exists (user-supplied image) and is a real, confirmed visual asset: a gold-and-navy winged aircraft/bird hybrid mark, an Ashoka Chakra motif in the background, a tricolour swoosh, a radar dish + signal tower + mountain silhouette, Sanskrit words (ज्ञानम् / सुरक्षा / समृद्धि — Learn / Secure / Empower), a navy serif "PUSHPAK" wordmark, the tagline "Intelligent Spectrum · Safer Skies · Stronger India," the line "Technology rooted in our heritage," and a small gold lotus. It is highly detailed and built for a cover/ceremonial context (deck title slide, report cover) — not, as-is, a small in-app UI mark. This redesign should derive a simplified in-app mark consistent with its language (gold/navy palette, the aircraft-wing motif and/or the wordmark) rather than shrinking the full emblem into a header.

This confirms the palette and material world are not fully open: gold and navy, with the Indian tricolour as a secondary accent, heritage-rooted rather than generic-tech, are now a real brand commitment for this surface, not just one candidate among many.

## Evidence on Hand

- A fully working, live system (all four services runnable locally) with real simulation output — this is not placeholder or mocked data.
- Real, freshly-verified metrics from this session's own runs (e.g., index policy holding interception ratio at 0.967 vs bandit's 0.710 on Scenario B hold-out seeds; a "synchronization trap" scenario where a fixed sweep scores exactly 0.000 detection and both newer policies escape it).
- Six real trained/registered models with real seed provenance.
- No official SIH dataset (Turing Synthetic Radar, J. C. Wise) is integrated — synthetic simulation data only. State absence, never imply the opposite.
- No user testimonials, external press, or production deployment exist — none should be implied by the redesign.

## Product Principles

1. **Prove it's real, immediately.** The first thing a judge sees must read as live and operating, not staged — motion, real numbers changing, a visible mechanism at work.
2. **Legible to a non-specialist, accurate to a specialist.** A judge with no RF background must be able to follow the headline story; nothing shown may misstate or dumb down what the underlying metrics actually mean.
3. **Honest about scope.** Simulation-only is a fact this product is proud of stating plainly, not a disclaimer to bury — it is explicit throughout the existing system's own documentation.
4. **The comparison is the argument.** The product's central claim (the newer scheduler beats the naive one on the metric that actually matters) is best made by letting the visitor see both run and diverge, not by a static claim.
5. **Density serves the operator, clarity serves the judge.** The team's own working-tool needs and the judge's few-minute first impression are both real audiences; the redesign should not sacrifice one entirely for the other where it doesn't have to.

## Accessibility & Inclusion

No specific standard has been established for this project; no requirement to assume beyond ordinary legible contrast and readable type sizes at demo distance (projector/laptop viewed from a few feet away).
