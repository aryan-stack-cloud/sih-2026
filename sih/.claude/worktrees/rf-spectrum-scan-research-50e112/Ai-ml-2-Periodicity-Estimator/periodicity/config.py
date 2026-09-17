"""Estimator configuration (Ai-ml-2 README, ``configs/``).

Buffer size, minimum-samples-before-prediction and confidence thresholds live here rather than
inline, because Level 5 and Level 7 are both stated in terms of them: confidence must be below a
*documented* threshold when samples are scarce, and near zero for non-periodic emitters.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, replace
from pathlib import Path

import yaml

CONFIG_DIR = Path(__file__).resolve().parent / "configs"


@dataclass(frozen=True)
class EstimatorConfig:
    """Tunables for the periodicity estimator."""

    # -- buffers ---------------------------------------------------------------------------
    buffer_size: int = 64
    """Detection timestamps retained per (simulation_id, band_id). Bounded so a long
    simulation cannot grow memory without limit (NFR-004: >= 5 concurrent simulations,
    >= 64 bands each)."""

    max_tracked_bands: int = 4096
    """Hard ceiling on live (simulation_id, band_id) pairs, evicted least-recently-used."""

    # -- period search ---------------------------------------------------------------------
    min_period: float = 3.0
    """Shortest period we will report.

    Deliberately not 1. A continuously-active emitter produces detections on consecutive steps,
    and *every* timestamp is congruent modulo 1, so a period of 1 always scores a perfect fit.
    Below about 3 the same degeneracy shows up against regular scan patterns rather than against
    emitters. See the "scan-schedule aliasing" note in periodicity_estimator.py."""

    max_period: float = 512.0
    period_resolution: float = 0.25
    """Grid step for the coarse period search, refined afterwards by local search."""

    min_cycles_observed: float = 2.0
    """Require the observation span to cover at least this many candidate periods. A "period"
    longer than half the time we have watched is not evidence, it is one gap."""

    # -- confidence ------------------------------------------------------------------------
    min_samples: int = 8
    """Distinct *activations* needed before any prediction is offered (Level 5 DoD).

    Counted after clustering, so several detections of one burst count once. Eight is where the
    measured false-positive rate on non-periodic emitters settles at the nominal level; below
    about six activations there is almost always some period that aligns them by luck."""

    low_confidence_threshold: float = 0.95
    """The documented threshold below which a prediction is not a periodicity claim.

    High because confidence is ``1 - p``, not a hand-scaled score: 0.95 is the ordinary p < 0.05.
    Measured false-positive rates at this threshold are 0-6% for random, intermittent and
    fixed-frequency emitters, against 100% true-positive for periodic ones from about 20
    activations (70% at 12). Ai-ml-1 receives the raw confidence as a state feature and learns
    its own weighting; nothing gates on this number, it documents what the number means."""

    # -- prediction window -----------------------------------------------------------------
    min_window_halfwidth: float = 1.0
    """Predicted active windows are never narrower than +/- this, even for a perfect fit --
    the receiver still needs a step it can actually schedule."""

    max_window_halfwidth_fraction: float = 0.5
    """Cap the half-width at this fraction of a period. Wider than half a period and the
    "window" covers the whole cycle, which is the same as saying nothing."""

    @classmethod
    def load(cls, path: str | Path | None = None) -> "EstimatorConfig":
        """Load from YAML, falling back to the defaults above."""
        target = Path(path) if path else CONFIG_DIR / "estimator.yaml"
        if not target.exists():
            return cls()
        data = yaml.safe_load(target.read_text(encoding="utf-8")) or {}
        known = {f for f in cls.__dataclass_fields__}
        unknown = set(data) - known
        if unknown:
            raise ValueError(f"unknown estimator config keys: {sorted(unknown)}")
        return cls(**data)

    def with_overrides(self, **kwargs) -> "EstimatorConfig":
        return replace(self, **kwargs)


def default_config() -> EstimatorConfig:
    """Process-wide config, overridable by ``PERIODICITY_CONFIG`` for the Docker profile."""
    return EstimatorConfig.load(os.environ.get("PERIODICITY_CONFIG"))
