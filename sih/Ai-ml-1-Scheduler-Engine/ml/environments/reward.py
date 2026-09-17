"""Reward function -- PRD Equation 10.1 / ML-003.

    r(t) = w1*D(t) + w2*P(t)*D(t) - w3*L(t) - w4*F(t) - w5*C(t) - w6*M(t)

BOUNDARY NOTE. In the deployed system the *Backend* computes this reward and posts the scalar to
Ai-ml-1's ``/internal/learn`` (API_CONTRACT.md Section 4); this service consumes it and does not
compute it. This module exists because standalone training and evaluation runs have no Backend
in the loop. The two implementations must agree -- that is what tests/test_reward.py pins down
against hand-computed cases, and why every term is reported separately in ``terms`` so a
disagreement can be localised to one term instead of one number.

All six weights are config-driven (ml/configs/*.yaml) and logged per experiment.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field

import numpy as np

from ml.environments.receiver import DetectionOutcome


@dataclass(frozen=True)
class RewardWeights:
    """w1..w6 of Equation 10.1. Non-negative by definition."""

    w1_detection: float = 10.0        # reward a true detection
    w2_priority: float = 2.0          # extra reward scaled by emitter priority P(t)
    w3_latency: float = 3.0           # penalise detecting late
    w4_false_alarm: float = 5.0       # penalise false alarms
    # Coverage/exploitation knob. With C(t) scoring re-detection of an already-intercepted run
    # as 'no new information', raising w5 trades Pd and scan efficiency for distinct-run
    # coverage; lowering it lets the policy camp on the loudest bands. 3.0 keeps most of the
    # Pd win while roughly doubling interception ratio -- see README 'Reward weight w5'.
    w5_redundant: float = 3.0         # penalise re-scanning a band that told us nothing new
    w6_missed: float = 4.0            # penalise leaving a high-priority active band unscanned

    def __post_init__(self) -> None:
        for name, value in asdict(self).items():
            if value < 0:
                raise ValueError(f"reward weight {name} must be non-negative")

    @classmethod
    def from_config(cls, cfg: dict | None) -> "RewardWeights":
        if not cfg:
            return cls()
        known = {f for f in cls.__dataclass_fields__}
        unknown = set(cfg) - known
        if unknown:
            raise ValueError(f"unknown reward weights: {sorted(unknown)}; expected {sorted(known)}")
        return cls(**cfg)

    def as_dict(self) -> dict[str, float]:
        return asdict(self)


@dataclass
class RewardContext:
    """Everything Equation 10.1 needs that is not in the DetectionOutcome itself."""

    time_since_last_scan: np.ndarray   # per band, measured BEFORE this step's update
    high_priority_active: np.ndarray   # per band, ground truth active and priority > 1
    scanned_bands: list[int]
    # Latency of detections that intercepted an activation run for the FIRST time, band -> steps.
    # Re-detections of an already-intercepted run are absent; see L(t) below.
    new_run_latencies: dict[int, int] = field(default_factory=dict)
    latency_horizon: int = 20          # L(t) normaliser: latency at or beyond this scores 1.0
    redundant_window: int = 3          # a re-scan within this many steps that finds nothing


class RewardFunction:
    """Computes r(t) and reports each term of Equation 10.1 separately."""

    def __init__(self, weights: RewardWeights | None = None) -> None:
        self.weights = weights or RewardWeights()

    def compute(
        self, outcome: DetectionOutcome, context: RewardContext
    ) -> tuple[float, dict[str, float]]:
        w = self.weights

        # D(t): 1 if a true detection occurred on a scanned band at t.
        d = 1.0 if outcome.detected_bands else 0.0

        # P(t): priority multiplier of the detected emitter (>= 1); 0 when nothing was detected
        # so the w2 term vanishes rather than paying out a baseline priority for a miss.
        p = float(outcome.max_detected_priority) if d else 0.0

        # L(t): normalised detection latency since the band last became active.
        #
        # Charged ONLY on the first detection of an activation run. A long-lived emitter that we
        # are already successfully tracking is not "late" on every subsequent step -- and if it
        # were charged as such, the reward would fight the metric it exists to serve: AIT counts
        # one latency per activation run (Section 12), while Pd rewards every active cell we
        # observe. Charging stale latency per step made productive dwell look worse than it is
        # and pushed the agent off emitters it had correctly found.
        if context.new_run_latencies:
            worst = max(context.new_run_latencies.values())
            l = min(worst / max(1, context.latency_horizon), 1.0)
        else:
            l = 0.0

        # F(t): 1 if a false alarm occurred.
        f = 1.0 if outcome.false_alarm_bands else 0.0

        # C(t): redundant-scan penalty -- the fraction of this step's scanned bands that were
        # revisited within redundant_window steps and again returned nothing.
        c = self._redundant(outcome, context)

        # M(t): missed opportunity -- fraction of currently-active high-priority bands that were
        # left unscanned this step.
        m = self._missed(outcome, context)

        reward = (
            w.w1_detection * d
            + w.w2_priority * p * d
            - w.w3_latency * l
            - w.w4_false_alarm * f
            - w.w5_redundant * c
            - w.w6_missed * m
        )
        terms = {"D": d, "P": p, "L": l, "F": f, "C": c, "M": m}
        return float(reward), terms

    # -- term helpers ---------------------------------------------------------------------

    @staticmethod
    def _redundant(outcome: DetectionOutcome, context: RewardContext) -> float:
        """C(t): "cost of rescanning a band with no new information" (PRD Equation 10.1).

        "No new information" covers two cases, and the second is the one that matters:

        1. the re-scan found nothing at all; and
        2. the re-scan re-detected an activation run we had **already intercepted**.

        Case 2 is what stops the agent from parking on one emitter. Scoring only case 1 leaves
        camping completely unpenalised -- a band that pays out every step is never "wasted" by
        that reading -- and the policy learns to maximise total detections on a handful of loud
        bands while never discovering the rest of the spectrum. Pd and scan efficiency look
        excellent and the interception mission quietly fails.
        """
        if not context.scanned_bands:
            return 0.0
        informative = set(context.new_run_latencies)
        wasted = sum(
            1
            for b in context.scanned_bands
            if b not in informative and context.time_since_last_scan[b] <= context.redundant_window
        )
        return wasted / len(context.scanned_bands)

    @staticmethod
    def _missed(outcome: DetectionOutcome, context: RewardContext) -> float:
        total_high = int(context.high_priority_active.sum())
        if total_high == 0:
            return 0.0
        missed_high = sum(1 for b in outcome.unscanned_misses if context.high_priority_active[b])
        return missed_high / total_high
