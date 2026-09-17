"""Turns a fitted period into the ``/internal/periodicity/predict`` response (Ai-ml-2 Level 6).

The response shape is consumed directly by the Backend's StateBuilder and forwarded into
Ai-ml-1's state vector, so the field names here are fixed by API_CONTRACT.md Section 5 and must
not be renamed.

The window is derived from the fit's own uncertainty rather than a fixed guess. Circular
statistics give the spread of the folded phases directly:

    circular standard deviation  =  sqrt(-2 * ln R)   radians

which converts to a half-width in time units. A tight fit yields a narrow window; a loose one
yields a wide one and low confidence to match. Two guards on top: never narrower than a step the
receiver could actually schedule, and never wider than half a period -- a "window" spanning the
whole cycle says nothing at all.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

from periodicity.config import EstimatorConfig
from periodicity.estimator.periodicity_estimator import PeriodEstimate


@dataclass(frozen=True)
class ActiveWindow:
    start: float
    end: float

    def contains(self, t: float) -> bool:
        return self.start <= t <= self.end


@dataclass(frozen=True)
class Prediction:
    """The Section 5 predict response, plus diagnostics the state endpoint exposes."""

    predicted_next_active_window: ActiveWindow | None
    estimated_period: float | None
    confidence: float
    phase: float
    reason: str = ""

    def to_contract(self) -> dict:
        window = (
            {"start": self.predicted_next_active_window.start,
             "end": self.predicted_next_active_window.end}
            if self.predicted_next_active_window is not None
            else None
        )
        return {
            "predicted_next_active_window": window,
            "estimated_period": self.estimated_period,
            "confidence": self.confidence,
        }


def window_halfwidth(estimate: PeriodEstimate, cfg: EstimatorConfig) -> float:
    """Half-width of the predicted window, from the circular spread of the fit."""
    period = float(estimate.period or 0.0)
    r = min(0.999999, max(1e-9, estimate.resultant_length))
    circular_sd_rad = math.sqrt(-2.0 * math.log(r))
    half = (circular_sd_rad / (2.0 * math.pi)) * period
    return float(
        min(
            max(half, cfg.min_window_halfwidth),
            max(cfg.min_window_halfwidth, period * cfg.max_window_halfwidth_fraction),
        )
    )


def next_activation(estimate: PeriodEstimate, now: float) -> float:
    """The first predicted activation strictly after ``now``.

    Anchored on ``reference_time`` -- a concrete moment the fit places at phase 0 -- and stepped
    forward whole periods. Working from the anchor rather than from the last detection keeps the
    prediction stable when detections arrive out of order.
    """
    period = float(estimate.period or 0.0)
    reference = float(estimate.reference_time or 0.0)
    if period <= 0:
        return now
    cycles = math.floor((now - reference) / period) + 1
    return reference + cycles * period


def predict(estimate: PeriodEstimate, now: float, cfg: EstimatorConfig | None = None) -> Prediction:
    """Build the Section 5 prediction for one band at time ``now``."""
    cfg = cfg or EstimatorConfig()

    if not estimate.usable:
        # An explicit "no claim" -- null window, zero confidence. The Backend still forwards this
        # into the state vector for every band, so it has to be a well-formed nothing rather
        # than an error (Ai-ml-2 Level 7).
        return Prediction(
            predicted_next_active_window=None,
            estimated_period=None,
            confidence=0.0,
            phase=0.0,
            reason=estimate.reason or "no periodicity estimate available",
        )

    centre = next_activation(estimate, now)
    half = window_halfwidth(estimate, cfg)
    return Prediction(
        predicted_next_active_window=ActiveWindow(start=centre - half, end=centre + half),
        estimated_period=estimate.period,
        confidence=estimate.confidence,
        phase=estimate.phase,
    )


def phase_at(estimate: PeriodEstimate, now: float) -> float:
    """Fraction of the cycle elapsed at ``now``, in [0, 1).

    This is the ``periodicity_phase`` feature Ai-ml-1 consumes. A value near 1 means the band is
    about due. Reported alongside the window so the Backend has both without a second call.
    """
    period = float(estimate.period or 0.0)
    if period <= 0 or estimate.reference_time is None:
        return 0.0
    return float(((now - estimate.reference_time) % period) / period)
