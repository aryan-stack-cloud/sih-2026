---
workflow: general-video
flow: automation
storyboard: no
message: "Show how the virtual receiver makes better use of a narrow instantaneous bandwidth, then compare six scheduling approaches with honest measured evidence."
destination: presentation
aspect: "16:9"
language: English
audience: SIH judges and technical reviewers
length: "about 1 minute 50 seconds"
---

## Intent

This is a standalone solution chapter following the existing problem introduction. Show an accurate 2D hardware diagram and spectrum instrument, not another human analogy. Explain the immutable receiver bandwidth limit, feedback loop, six schedulers, synthetic and Alan Turing synthetic radar replay inputs, and a sourced baseline comparison. Preserve earlier numbered videos.

## Evidence and limits

The actual product is a simulation. No real RF receiver is connected. Scenario B holdout values in `Ai-ml-1-Scheduler-Engine/IMPLEMENTATION.md` are the plotted source: round-robin Pd 0.1092, Index Pd 0.1334; both interception ratio 0.9667. Bandit Pd 0.3375 but interception ratio 0.7100 is a tradeoff, not a blanket win. The registry contains Turing-replay-labelled checkpoint runs, while exact training wall times are absent; the film must not invent training durations or claim every method was trained on both sources. CTMC and Index are designed policies rather than neural models.

## Design

Original vector technical graphics. Deep navy, cyan for observed spectrum, gold for decisions, coral for missed bursts. Large Archivo headings and JetBrains Mono readouts. Crisp RF hardware schematic, animated spectrum, compact model cards, two single-metric charts. Voiceover plus a restrained electronic score.
