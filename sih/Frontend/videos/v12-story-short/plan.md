# v12: the short story cut (1:51)

A 1 min 51 s cut of v11, the Infographics-Show-style solution story. v1 to v11 are unchanged in
the library.

## What the user asked for, and what changed

| Ask | What v12 does |
|---|---|
| Shorter cut, about 1:40 to 1:50, by trimming pauses | 111.2 s (v11: 160.1 s). Pauses between lines are 0.12 to 0.5 s (v11: up to 1.5 s). Cut: the "bigger searchlight" daydream, the rhythm-trap line, the three-families line, the greedy-Bandit beat and the 6.6 ms speed beat. |
| Explain the Bandit more clearly | Each slot machine carries a WINS counter on its tray. The scene runs: a catch pays out ("CATCH = WIN"), the counters light up on "it keeps score", it keeps playing the top scorer ("PLAY THE WINNER"), then it tries another machine ("NOW AND THEN: TRY ANOTHER"), misses and goes back. |
| Explain Q-learning more clearly | The cheat sheet fills with a score for every move in every situation, and the best move in a busy moment is circled. For "a move that sets up a catch a few steps later gets credit", an arrow runs through 3 steps to a catch, and a +5 credit flies back to the move (1 → 6). |
| Compare Bandit and Q-learning (not just Index) with the fixed sweep, in % | New Turing-data scoreboard, all on the same 50 unseen recordings: fixed sweep 11 per 100, Bandit 27 (+147%), Q-learning 24 (+120%), DQN 27 (+146%), PPO 29 (+172%). A "2× old sweep" line shows that all four more than double it. The busy-night Index result (+22%) is kept. |
| Show the detection improvements | The same scoreboard, plus the reach trade-off: the learners reach 58–72% of emitters vs 93% for the sweep. |
| Training time: "about 2 days; Bandit and Q-learning 3 to 4 hours" | Checked against the model registry and re-timed; see below. On screen: "2 days of training runs in all", with each final model's measured time. |
| Dataset size: "80 GB" | The dataset is **70 GB** (69.99 GB, 9,000 HDF5 files) on disk and on Hugging Face. The video says "recordings from the Alan Turing Institute's seventy-gigabyte radar dataset". |

## Fact check behind the new numbers

**Dataset size.**
- The local copy `D:\turing-synthetic-radar-dataset` holds 9,000 files totalling 69,989,685,824 bytes. That matches the Hugging Face repo's `usedStorage`.
- The models did not train on all of it. Bandit and Q-learning trained on 150 scan-mode recordings (65 MB). DQN and PPO trained on 300 (130 MB). All seven methods were tested on the same 50 unseen validation recordings (20 MB).
- The run scripts are `stage3_train.py`, `stage4_deep_train.py`, `stage4b_deep_train_more.py` and `stage5_remaining.py`, all from the 22 Sep session.
- So the video never says "trained on 70 GB".

**Training time.**
- The model registry (`ml/checkpoints/index.json`) holds training runs over two days: 21 Sep (19 entries) and 22 Sep (23 entries). That supports "2 days of training runs in all".
- All Turing-data runs were on 22 Sep, from 15:10 to 21:06 IST, after a 75-minute download of the 70 GB. No single model took hours:

| Model (final Turing run) | Time | How it was measured |
|---|---|---|
| Bandit | 5 min 51 s | Re-run on 25 Sep with the exact 22 Sep script and settings. Reproduced the registered Pd 0.26747 and reach 0.7236 exactly |
| Q-learning | 6 min 47 s | Same re-run. Reproduced Pd 0.23828 and reach 0.6031 exactly |
| DQN (300k steps, 300 recordings) | ≈ 41 min | From script save (14:13 UTC) to registration (14:54 UTC) |
| PPO (300k steps, 300 recordings) | ≈ 42 min | Registered 42 min after DQN, in the same sequential script |

Each time includes loading the recordings, training and the 50-recording evaluation. The video
rounds this to "each final model trains in under an hour". The per-model times are on screen.

## Bug found (and fixed) while building v12

`build.py` tags the overlay cards (number cards, statement cards, stamps) with `data-layout-allow-overlap`
so the layout checker accepts them. The regex that does this had a literal control character (`\x01`)
where the backreference `\1` belonged, so every one of those elements lost its CSS class.

The delivered **v11 MP4 is affected**. Frames at 7.2 s, 29.0 s and 56.6 s show:
- no MISSED!/0 CAUGHT/CAUGHT! stamps;
- no "#1".."#6" cards (only the blur behind them);
- a blank screen where "We can't make the light bigger / We can make it smarter" and "So... did it work?" should be.

v12's `build.py` uses a function replacement instead, and every overlay was checked in snapshots.
v11 was left untouched, following the rule that earlier cuts are never changed without asking.

## Storyboard

| Time | Scene | Picture | Fact |
|---|---|---|---|
| 0:00 | Cold open | Guard, 16 rooms, torch flash, MISSED! | Signals are short |
| 0:09.6 | Hardware limit | Antenna → EW receiver → computer; narrow window on the spectrum; ≥10× narrower; 2 of 16 | Problem statement; simulator window |
| 0:18.7 | Old way | Clock-hand sweep, metronome intruder, "0 CAUGHT" stamp | Rhythm trap: fixed sweep 0 of 4 runs |
| 0:26.4 | Plan | Look → learn → pick every 10 ms; six tiles sort into 3 families | |
| 0:34.2 | #1 CTMC | Tumbling die catches the rhythm signal | Chip: CTMC and Index caught it in 4 of 4 runs |
| 0:40.5 | #2 Index | To-do list: busy and overdue bands jump up | |
| 0:46.5 | #3 Bandit | Slot machines with WINS counters (see above) | Exploit vs explore |
| 0:58.0 | #4 Q-learning | Score sheet; delayed credit (see above) | Situation × move values, credit for later catches |
| 1:06.7 | #5 DQN | Robot and network score all 16 bands | |
| 1:12.9 | #6 PPO | Prize wheel whose winning slice grows | |
| 1:18.9 | Data and training | Case file: simulator + Turing photo with a 70 GB sticker; exam on 50 unseen recordings; 2-days badge and per-model times | See fact check |
| 1:32.7 | Results | "So... did it work?"; busy night Index +22%, same 97% reach; Turing scoreboard; reach trade-off | See source table |
| 1:46.3 | Close | Sunrise, chai, "Same receiver. Same narrow window. Smarter choices." | |

## Source table (every number on screen)

| Shown | Value | Source |
|---|---|---|
| Hardware ratio | ≥10× narrower | SIH problem statement |
| Simulator window | 2 of 16 bands, 10 ms step | `ml/experiments/scenario_b.yaml` |
| Rhythm trap | fixed sweep 0 of 4 runs; CTMC and Index 4 of 4 | `IMPLEMENTATION.md`, synchronisation trap, 4 seeds |
| Dataset | 70 GB, 9,000 recordings | Local copy and Hugging Face `usedStorage` |
| Exam | 50 unseen recordings | `stage3_train.py` etc.: 50 scan-mode validation files |
| Training | 2 days of runs; Bandit 5 min 51 s, Q-learning 6 min 47 s, DQN ≈ 41 min, PPO ≈ 42 min | Fact check above |
| Busy night | 11 → 13 of 100 (+22%), reach 97% for both | `IMPLEMENTATION.md`, Scenario B hold-out: Pd 0.1092 → 0.1334, 6 unseen runs |
| Turing scoreboard | per 100: 11 / 27 / 24 / 27 / 29; +147% / +120% / +146% / +172% | Registry, `turing-replay-scanmode` runs: Pd 0.1083 (baseline), 0.2675 (Bandit), 0.2383 (Q-learning), 0.2666 (DQN 300k), 0.2949 (PPO 300k) |
| Reach | 93% / 72% / 60% / 72% / 58% | Same runs, interception ratio 0.9267 / 0.7236 / 0.6031 / 0.7219 / 0.5820 |

Accuracy notes:
- On the same Turing recordings, CTMC (Pd 0.1068) and Index (0.1082) catch about as much as the fixed sweep, while reaching more emitters (96% vs 93%). They are left off the Turing chart, which is about the learners. The Index's +22% is labelled as the busy-night (Scenario B) test.
- The scoreboard uses the latest registered run for each learner. The 150k-step PPO run scored higher (Pd 0.3064, +183%), but the 300k run is the final model.
- "They camp on busy bands" is the plain-English reading of higher detection with lower reach.

## Production

- **Base:** v11's composition (`composition/`), with 10 re-voiced lines. Kokoro `af_heart` at 1.1×, same gain as v11 (−18 LUFS per clip). The other 20 clips are byte-identical to v11.
- **Music:** the v11 bed, trimmed to 111.2 s with a 2 s fade-out, carved under all 30 voice clips (strength 0.8).
- **New art:**
  - Bandit: tray win counters and callouts.
  - Q-learning: score grid, step dots and the credit chip.
  - Data: the 70 GB sticker and the 2-days badge.
  - Results: the Turing scoreboard with a 2× line and a reach column.
  - All of it is HTML/CSS in the scene files, in the v11 palette.
- **`build.py`:**
  - Fixed the overlay-class bug (above).
  - Each sound effect now goes on a free audio track, so none overlap on one track.

## Verification

- **`hyperframes check`:** passed.
  - Lint: 0 errors; the 19 warnings are single-file structure notes and repeated image sources.
  - Runtime: 0 errors.
  - Layout: 0 errors; 9 warnings, all brief transition moments (card fade-outs, the PPO wheel morph).
  - Motion: 0 errors.
  - Contrast: 79/79 WCAG AA.
- **Overlays:** all 11 (number cards, statement cards, stamps) were checked in snapshots and in frames from the final MP4.
- **Render:** `v12-story-short.mp4`, 111.2 s, 1920×1080, 30 fps, H.264 plus stereo AAC 48 kHz, 77.7 MB with the poster embedded as cover art. Rendered in 20 min 41 s (2 workers).
- **Audio:** −16.0 LUFS integrated, −1.6 dBFS true peak, measured on the final MP4.
- **Frames:**
  - Scene midpoints are in `v12-contact-sheet.jpg`.
  - The poster (`v12-poster.jpg`) is the Turing scoreboard at 101.7 s.
- **Speech-to-text:** all 10 new lines match the script. Whisper misses some sentence-initial short words ("A", "But", "The") on these clips and on approved v11 clips alike. The clips aren't truncated: the silence trim removes under 10 ms of near-silent onset.
