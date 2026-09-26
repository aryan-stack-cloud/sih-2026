# v9 — Smart Scan: the solution

112-second narrated 2D technical chapter for presentation immediately after the problem introduction. Earlier v1–v8 files are preserved.

| Time | Visual | Point |
|---|---|---|
| 0–9 s | Signal gone before the aperture arrives | Bridge from the problem chapter |
| 9–23 s | Antenna → RF front end → tuner → ADC → compute, 16-band range / two-band view | Hardware restricts instantaneous observation |
| 23–34 s | Moving aperture and bursts | Software chooses the next slice; it cannot widen hardware |
| 34–46 s | Observe → update → choose → retune | Same virtual receiver and timing budget for each scheduler |
| 46–58 s | CTMC and Index | Designed policies, with randomized floor versus belief and revisit ranking |
| 58–72 s | Bandit, Q-learning, DQN, PPO | Four ways to learn a scan decision |
| 72–84 s | Generated scenarios and Alan Turing replay | Distinct synthetic input sources feeding virtual receiver |
| 84–96 s | Detection bars | Scenario B holdout Pd: fixed sweep 0.1092, Index 0.1334 (+22% relative) |
| 96–104 s | Emitter reach bars | Both 0.9667; Bandit has a separate detection/coverage tradeoff |
| 104–112 s | Training time, warm service latency, team mark | Wall time absent; p95 scheduler API latency 6.6 ms |

## Sources and claim boundaries

- `Ai-ml-1-Scheduler-Engine/IMPLEMENTATION.md`, Results / Scenario B holdout table: Pd and interception ratio, same six held-out seeds for Index and round-robin, 2,000 steps.
- The same document reports Bandit Pd 0.3375 and interception ratio 0.7100 from 20 evaluation seeds. The film labels this as a tradeoff, not a matched six-seed lift.
- The same document reports warm scheduler service p95 6.6 ms. This is decision API latency, **not training time**.
- `Ai-ml-1-Scheduler-Engine/ml/checkpoints/index.json` records Turing-replay-labelled runs for several algorithms. The repository has a Turing replay adapter. This supports a replay experiment visual, not a claim that all six strategies were trained on the dataset or that a real RF receiver was used.
- The problem statement's typical hardware bandwidth ratio (≥10× narrower) differs from the project's 16-band, K=2 illustrative simulator (8×). Both are labelled separately.

## Validation

HyperFrames 0.8.73 check passed: 0 errors, 0 runtime/layout/motion issues, 86/86 contrast checks. Ten structural Studio warnings arise from this monolithic 2D composition. Final contact-sheet snapshots and a hardware frame from the rendered MP4 were inspected; the animation map was reviewed. Voiceover: offline Kokoro `af_heart`; original electronic score, dynamically carved under narration. The final render is 1920×1080, 30 fps, 112.0 s, H.264/AAC stereo, 13.5 MB, −20.3 LUFS integrated and −1.5 dBFS true peak.
