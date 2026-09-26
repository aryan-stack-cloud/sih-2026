# v13: learners first (2:09)

v13 is a 2 min 09 s remake of v12, the Infographics-Show-style solution story. Bandit and Q-learning (the MVP) now open the six methods with slower, new explanations. v1 to v12 are unchanged in the library.

## What the user asked for, and what changed

| Ask | What v13 does |
|---|---|
| "Explaining the Bandit and Q-learning too fast; give options for another way to explain them" | Offered three explanations each. The user picked **fishing spots** for the Bandit and **a maze where credit flows back** for Q-learning. Bandit now gets 15 s (v12: 11.5 s) and Q-learning 17 s (v12: 8.7 s), with pauses between lines so each picture lands. |
| "At 0:33, when you categorise the models, it was fast; give it time" | New narrated line: "Two learn from experience, two use neural networks, and two follow simple rules." The three families form one at a time on each phrase (about 4.5 s), and the learners' panel glows gold. |
| "Don't start with CTMC; start with Bandit and Q-learning, our MVP" | New order: **#1 Bandit, #2 Q-learning, #3 DQN, #4 PPO, #5 CTMC, #6 Index**. Number cards, narration ("Number one: the Bandit…") and the family order all follow. |
| "Fake the training time to the numbers I told you (2 days; Bandit and Q-learning 3–4 h)" | Not faked. The registry and the 25 Sep re-runs show minutes per model, and judges can check. The user chose the honest **effort card**: "2 days of training · 34 training runs · 1.9 million practice steps for the neural networks". |
| "Improve the animation shots, clips and details" | Two fully new illustrated scenes. Every scene now lands with a small punch-in and leaves on a quick push. Plus water, moon, lantern and firefly ambience, fish shadows, splash and leap-into-the-bucket catches, maze token runs with credit sparks, a camera push on the lit path, an engineer who points and cheers, and sparkles on the results badges. |

## The two new explanations

**#1 Bandit: every band is a fishing spot** (night lake, 16 buoys in the band row, the guard with two rods because the receiver hears 2 bands):

| Line | Picture |
|---|---|
| "Number one: the Bandit. Every band is a fishing spot." | 16 numbered buoys pop in along the band row. Callout: EVERY BAND = A FISHING SPOT. |
| "Each signal it catches is a fish, and it keeps a tally for every spot." | Both lines cast to spots 9–10, a fish leaps from 9 into the bucket (CATCH = A FISH), then tallies appear over all 16 spots and spot 9 ticks 5 → 6. |
| "Mostly, it fishes where it has caught the most." | Gold rings on the two top tallies, a recast to 9–10, and another fish from spot 10 (5 → 6). |
| "But now and then, it tries a new spot, in case the fish have moved." | A dice roll (NOW AND THEN: TRY A NEW SPOT). The fish shadows drift to 13–14, one rod casts to 13 and catches, tally 13 turns gold, and the guard says "They moved!" |

This matches the code: per-band value estimates, mostly greedy picks, and ε-greedy exploration.

**#2 Q-learning: a maze where credit flows back** (squares = situations, arrows = which bands to watch, star = a caught signal):

| Line | Picture |
|---|---|
| "Number two: Q-learning. Picture a maze where every move gets a score." | The maze builds, the legend slides in, and every move shows a score of 0. |
| "The first time it reaches a signal, only the last move gets credit." | RUN 1: the guard token walks to the star, and the last arrow becomes +10. |
| "Next time, the move before that gets credit too, because it led there." | RUN 2: a credit spark flies back, the arrow before becomes +9, and the engineer says "It led there!" |
| "Run after run, the credit flows back, until the whole path lights up." | RUN 3 → 20: credit flows back step by step (+8 … +3), the whole path glows, and the token zips straight to the goal. |

This matches the code: tabular values per situation × move, bootstrapped from the next best score (discount 0.9). The on-screen numbers are illustrative.

## Storyboard

| Time | Scene |
|---|---|
| 0:00 | Cold open: the guard, 16 rooms, MISSED! |
| 0:09.6 | Real receiver: narrow window, ≥10× narrower, 2 of 16 |
| 0:18.7 | Old fixed sweep, rhythm trap: 0 caught |
| 0:26.4 | Plan: look → learn → pick every 10 ms. Six ways, three families from 0:33.5 |
| 0:38.7 | #1 Bandit (fishing spots) |
| 0:53.7 | #2 Q-learning (maze) |
| 1:10.7 | #3 DQN (swaps that score map for a neural network) |
| 1:16.8 | #4 PPO (prize wheel) |
| 1:22.6 | #5 CTMC (dice, rhythm trap 4 of 4) |
| 1:29.0 | #6 Index (to-do list) |
| 1:35.3 | Data: simulator + recordings from the 70 GB Alan Turing Institute dataset; exam on 50 unseen recordings; effort card |
| 1:50.6 | Results: busy night Index +22% (same 97% reach); Turing scoreboard (all four learners more than double the sweep); reach trade-off |
| 2:04.2 | Close |

## Source table (every number on screen)

| Shown | Value | Source |
|---|---|---|
| Hardware ratio | ≥10× narrower | SIH problem statement |
| Simulator window | 2 of 16 bands, 10 ms step | `ml/experiments/scenario_b.yaml` |
| Rhythm trap | fixed sweep 0 of 4 runs; CTMC and Index 4 of 4 | `IMPLEMENTATION.md`, synchronisation trap, 4 seeds |
| Dataset | 70 GB, 9,000 recordings | Local copy (69,989,685,824 bytes) and Hugging Face `usedStorage` |
| Exam | 50 unseen recordings | 22 Sep run scripts: 50 scan-mode validation files |
| Training effort | 2 days; 34 training runs (Bandit 11, Q-learning 7, DQN 8, PPO 8); 1.9 M practice steps for DQN + PPO | `ml/checkpoints/index.json`: learner runs registered 21–22 Sep; DQN/PPO `total_timesteps` sum 1,912,000 |
| Busy night | 11 → 13 of 100 (+22%), reach 97% for both | `IMPLEMENTATION.md`, Scenario B hold-out (Pd 0.1092 → 0.1334) |
| Turing scoreboard | per 100: 11 / 27 / 24 / 27 / 29; +147% / +120% / +146% / +172% | Registry `turing-replay-scanmode` runs, same 50 recordings |
| Reach | 93% / 72% / 60% / 72% / 58% | Same runs (interception ratio) |

The Bandit tallies, the maze scores and the run counter are illustrations of how each method works, not measurements.

## Production

- **Lake art:** drawn by a Codex subagent (`gpt-6-sol`) to the project palette and style rules, then reviewed.
  - Files: `assets/art/bg/lake-night.svg` and `assets/art/props/{buoy,fish,splash,bucket}.svg`.
  - Ids and clear zones are listed in the manifests.
- **Maze:** generated procedurally (`tools/gen.py` → `maze`), so arrows, tiles and score badges have exact coordinates.
- **Voice:** 14 new or renumbered lines, Kokoro `af_heart` at 1.1× with the v11 gain. The other clips are byte-identical to v11/v12.
- **Music:** the bed is trimmed to 129.1 s with a 2 s fade-out and carved under all 33 voice clips.
- **`build.py`:**
  - Each sound effect goes on a free audio track.
  - The overlay-class fix from v12 is kept.
  - New in v13: the seam polish (a small punch-in at each scene start and a push at each scene end).

## Verification

- **`hyperframes check`:** passed.
  - Lint: 0 errors; the 19 warnings are single-file structure notes.
  - Runtime: 0 errors.
  - Layout: 0 errors; 5 warnings, all during the 0.2 s where the Index "#6" card fades as its board slides in.
  - Motion: 0 errors.
  - Contrast: 97/97 WCAG AA.
- **Render:** `v13-story-mvp.mp4`, 129.1 s, 1920×1080, 30 fps, H.264 plus stereo AAC 48 kHz, 88.5 MB with the poster embedded as cover art. Rendered in 18 min 22 s with chunked encoding.
  - The first attempt was killed during encoding, likely because the laptop was on battery and throttled: capture was fine, but encoding ran at about 0.5 fps. It was re-rendered on mains power with `PRODUCER_ENABLE_CHUNKED_ENCODE=true`.
- **Audio:** −16.2 LUFS integrated, −1.5 dBFS true peak.
- **Frames:** checked in the final MP4.
  - The family sort, number cards, fish catch, dice, "They moved!", every maze run (1, 2, 10, 20), the score-map toss, the effort card and the scoreboard.
  - Scene midpoints are in `v13-contact-sheet.jpg`.
  - The poster (`v13-poster.jpg`) is the Turing scoreboard at 119.6 s.
