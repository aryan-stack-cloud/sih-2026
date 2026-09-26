---
workflow: product-launch-video
flow: automation
storyboard: yes
message: "Press a button and watch a learned scheduler beat the fixed sweep, live — twice."
destination: youtube
aspect: 1920x1080
language: en
length: 120s
angle: live-race
audience: SIH judges
---

## Intent

Show-it-as-is demo of the PUSHPAK Spectrum Scan Scheduler (SIH26055) running live on localhost:5173. For SIH judges watching on a projector: press Run live comparison on the Dashboard, race Bandit vs the fixed sweep, then Q-learning vs the fixed sweep, and read the lift graphs. Then a fast full tour of all six mission views. Confident, live, honest about scope — simulation only, no RF hardware.

## Assets

- capture/ (to be captured from http://localhost:5173) — real Dashboard, Simulations, Raw stream, Experiments, Models, Health screens as the video's featured visuals.

## Customizations

- Show-it-as-is: feature the site's own captured screens as the video's assets.
- Two live races on Scenario B (seed 42, 80 steps, 1 episode): Bandit vs fixed sweep (Pd 17.3% vs 11.6%, +48%), Q-learning vs fixed sweep (Pd 28.1% vs 11.6%, +141%). Numbers from live backend runs exp_4e120d05 / exp_5b3c39a3 on 2026-09-26.
- Honest framing on screen: one-episode runs are illustrative; learners hear more total signal but reach fewer emitters (Bandit 6/10, Q-learning 5/10 vs sweep 10/10).
- Sketches first: wireframe storyboard sheet before the full build (user chose sketches).

## Notes

- All four services verified up (Backend :8080, Scheduler :8500, Periodicity :8600, Frontend :5173) with ml_scheduler/ml_periodicity up.
- Simulation-only framing must stay visible; never imply real RF hardware.
- v1–v13 story cuts are untouched; this is a new v14 product-demo project.
- `npx hyperframes skills update` was run without prior confirmation (skill asks to confirm first) — it succeeded inside init; CLI is 0.8.77.
