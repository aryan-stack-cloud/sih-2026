# v11: the solution, told as a story

A 2 min 40 s narrated cartoon in the style of The Infographics Show. It follows the problem video.
The guard with one searchlight (which lights 2 of 16 rooms) learns six ways to decide where to look
next. v1 to v10 are unchanged in the library.

## Why v11 exists

The user said v10 "looks like a video lecture" and asked for "a story or infographic show
explanation", pointing at The Infographics Show's *50 Insane Discoveries Voyager II Found*. Sampled
frames from that video set the grammar:
- cartoon characters with speech bubbles;
- white info tags ("LOCATION:", "DATE:");
- giant "#N" cards;
- arrow labels;
- props held up to camera;
- statement cards;
- a new picture every few seconds.

## Storyboard

| Time | Scene | Easy picture | Fact it carries |
|---|---|---|---|
| 0:00 | Cold open | The guard, 16 numbered rooms, a torch flash in room 11, the beam arrives too late, MISSED! | Signals are short; the receiver must be in the right place at the right time |
| 0:12 | Hardware limit | The guard dreams of a giant searchlight; the engineer says "Not in real hardware!"; then antenna, EW receiver and computer, with a narrow window on the spectrum | Instantaneous bandwidth: problem statement ≥10× narrower than the watched band; simulator: 2 of 16 bands |
| 0:31 | The old way | A clock-hand sweep over 16 bands; an intruder with a metronome flashes out of step | Fixed sweep caught the rhythm-trap signal 0 times |
| 0:44 | The plan | Look, then learn, then pick, drawn on a whiteboard; six tiles sort into 3 families | A decision every 10 ms; 2 rule-based, 2 learn from experience, 2 neural networks |
| 0:56 | #1 CTMC | A tumbling 3D die; random hops at random times catch the intruder | Randomised hops cannot be timed |
| 1:03 | #2 Index | A to-do clipboard: busy pairs and overdue pairs jump to the top; an alarm clock rings | Busy-looking and overdue bands rise; revisit deadlines |
| 1:10 | #3 Bandit | Slot machines labelled with band pairs; keep playing the one that pays, sometimes try a new one | Exploit versus explore |
| 1:17 | #4 Q-learning | A cheat sheet of situation × move; a crossed-out move pays off later | Learns delayed payoff |
| 1:26 | #5 DQN | The cheat sheet is tossed; a robot and a network on the wall screen score all 16 bands at once | Neural network value estimate |
| 1:33 | #6 PPO | A prize wheel whose winning slice grows | Learns choice probabilities |
| 1:40 | Data and training | A case file with two photos (simulator worlds; Alan Turing Institute radar pulses binned into 16 bands); an exam on unseen runs; a training-time race | Measured training times (below) |
| 2:03 | Results | Rhythm-trap scoreboard, 100-square grids, reach gauges, the greedy Bandit, a stopwatch | See source table |
| 2:37 | Close | Sunrise, the guard with chai, "Same receiver. Same narrow window. Smarter choices." | |

## Source table (every number on screen)

| Shown | Value | Source |
|---|---|---|
| Hardware ratio | ≥10× narrower | SIH problem statement (typical instantaneous bandwidth) |
| Simulator window | 2 of 16 bands, 10 ms step | `ml/experiments/scenario_b.yaml` (`bands: 16`, `bandwidth_k: 2`, `step_ms: 10`) |
| Rhythm trap | fixed sweep 0 of 4 runs; CTMC and Index 4 of 4 runs | `IMPLEMENTATION.md`: synchronisation trap, four seeds, emitters intercepted 0.000 / 1.000 / 1.000 |
| Busy night | 11 → 13 of every 100 signal moments, +22% | `IMPLEMENTATION.md` Results, Scenario B hold-out: Pd 0.1092 → 0.1334 (six unseen runs, 2,000 steps). Pd counts every active band-step, so "signal moments" |
| Reach | 97% for both | Interception ratio 0.9667, same table |
| Bandit | 34 of 100 caught, 71% reach | Same table, Bandit column (20 evaluation seeds), labelled "separate test" on screen |
| Training time | Bandit 1 min 21 s, Q-learning 3 min 33 s, DQN 5 min 27 s, PPO 7 min 27 s; CTMC and Index none | Measured for v11 with `ml/training/trainer.py` (`train_seconds`), Scenario B, shipped settings, Intel i5-13420H laptop CPU. Bandit and Q-learning are medians of 3 runs; DQN and PPO are 1 run each at 50,000 steps |
| Decision time | 6.6 ms | `IMPLEMENTATION.md`: warm scheduler API p95 over HTTP |
| Data | Simulator worlds + Alan Turing Institute synthetic radar dataset | `ml/data/turing_replay.py`; registry has runs labelled turing-replay for all six methods |

Accuracy notes:
- The Bandit narration says "about eighty seconds", matching the 81 s median. PPO's 7 min 27 s is said as "about seven and a half minutes".
- The rhythm-trap test is an 8-band, one-signal setup; the tag on screen says "rhythm trap", not Scenario B.
- The CTMC and Index scene art is illustrative. The measured claims are only the ones in this table.

## Production

- **Characters:** the guard, engineer and intruder are generated SVG rigs (`composition/tools/cast.py`) with animatable heads, eyes, mouths and arms.
- **Procedural art:** the band clock, slot machines, robot, prize wheel, network diagram and 100-square grids come from `tools/gen.py`.
- **Other art:** the props, hardware and backgrounds were drawn by opencode subagents and reviewed. The dice, slot machine, robot and wheel were redrawn in-house after that review.
- **Voice:** offline Kokoro `af_heart` at 1.1×, 38 clips, matched to −18 LUFS.
- **Music:** "happy-beats-business-moves vol 9" (brag skill library, 115 BPM), carved dynamically under the narration at strength 0.8.
- **Sound effects:** brag library dice, chips, impacts and UI sounds, plus synthesized whooshes, pops, chimes and ratchets.
- **Assembly:** `composition/build.py` assembles one composition from `scenes/*.html` + `scenes/*.js`, timed by the real clip durations in `plan.json`.

## Verification

- **HyperFrames 0.8.73 `check`:** passed.
  - Lint: 0 errors. Its 21 warnings are the intentional single-file structure notes plus repeated image sources.
  - Runtime, layout and motion: 0 errors each.
  - Contrast: 46/46 text checks pass WCAG AA.
  - Layout info notes cover deliberate overlays (#N cards, statement cards, stamps) and small camera-push overscan.
- **Render:** `v11-story-solution.mp4`, 160.1 s, 1920×1080, 30 fps.
  - Streams: H.264 at 4.7 Mbps and stereo AAC at 48 kHz, 93.9 MB with the poster embedded as cover art.
  - Rendered in 21 min 35 s (2 workers, hardware GPU capture).
- **Audio:** −16.0 LUFS integrated, −1.6 dBFS true peak, measured on the final MP4. The music bed is dynamically carved under all 38 voice clips (strength 0.8).
- **Review:** encoded frames at every scene midpoint were checked in `v11-contact-sheet.jpg`. The poster (`v11-poster.jpg`) is the Scenario B result frame.
