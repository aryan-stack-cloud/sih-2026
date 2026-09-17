"""The estimator service: buffers + fitting + a cache, behind the Section 5 operations.

WHY THERE IS A CACHE. This service sits on the scheduler's critical path. Before every single
decision the Backend asks it for a prediction on *every* band -- 64 bands at 5 concurrent
simulations is 320 predictions per simulation step, and the whole Backend -> Ai-ml-2 -> Ai-ml-1
round trip has to fit inside NFR-002's 50 ms budget, of which Ai-ml-1 already uses about 7 ms.

Re-fitting a period sweep per band per step would not fit. But it also is not necessary: the fit
only changes when a *new detection* arrives for that band. So the fit is cached and invalidated
on update. Prediction against a cached fit is arithmetic -- it re-projects the next activation
from the current time without touching the period search.
"""

from __future__ import annotations

import threading

from periodicity.buffers.detection_buffer import BufferStore
from periodicity.config import EstimatorConfig
from periodicity.estimator.periodicity_estimator import (
    PeriodEstimate,
    cluster_activations,
    estimate_period,
)
from periodicity.inference.prediction import Prediction, phase_at, predict
from periodicity.utils.logging import get_logger

log = get_logger(__name__)


class PeriodicityService:
    """Owns the buffers, the fit cache, and the Section 5 operations."""

    def __init__(self, config: EstimatorConfig | None = None) -> None:
        self.config = config or EstimatorConfig()
        self.buffers = BufferStore(
            capacity=self.config.buffer_size,
            max_tracked=self.config.max_tracked_bands,
            # One burst is one sample, enforced on the way in - see DetectionBuffer.
            activation_gap=self.config.min_period,
        )
        self._fits: dict[tuple[str, int], PeriodEstimate] = {}
        self._lock = threading.Lock()

    # -- Section 5 operations ----------------------------------------------------------------

    def update(self, simulation_id: str, band_id: int, detection_timestamp: float) -> bool:
        """Record a confirmed detection and invalidate that band's cached fit."""
        accepted = self.buffers.record(simulation_id, band_id, detection_timestamp)
        if accepted:
            with self._lock:
                self._fits.pop((simulation_id, int(band_id)), None)
        return accepted

    def estimate(self, simulation_id: str, band_id: int) -> PeriodEstimate:
        """Fitted period for one band, refitting only when new detections have arrived."""
        key = (simulation_id, int(band_id))
        with self._lock:
            cached = self._fits.get(key)
        if cached is not None:
            return cached

        # Fit outside the lock: the buffer snapshot is a copy, so an update arriving mid-fit is
        # not lost -- it just invalidates the entry we are about to store, and the next call
        # refits. Holding the lock across the sweep would serialise every band instead.
        fit = estimate_period(self.buffers.snapshot(simulation_id, band_id), self.config)
        with self._lock:
            self._fits.setdefault(key, fit)
            return self._fits[key]

    def predict(self, simulation_id: str, band_id: int, now: float) -> Prediction:
        return predict(self.estimate(simulation_id, band_id), now, self.config)

    def phase(self, simulation_id: str, band_id: int, now: float) -> float:
        return phase_at(self.estimate(simulation_id, band_id), now)

    def predict_many(
        self, simulation_id: str, band_ids: list[int], now: float
    ) -> list[tuple[int, Prediction, float]]:
        """Predictions for many bands in one pass.

        Cheap by construction: fits are cached and only a band with a new detection since the
        last call refits, so per step at most K bands (the receiver's instantaneous bandwidth)
        do real work. The rest is arithmetic on a stored fit.
        """
        out = []
        for band_id in band_ids:
            estimate = self.estimate(simulation_id, band_id)
            out.append(
                (int(band_id), predict(estimate, now, self.config), phase_at(estimate, now))
            )
        return out

    def latest_detection(self, simulation_id: str, band_ids: list[int]) -> float:
        """Most recent detection across the given bands, used when the caller omits ``now``."""
        latest = 0.0
        for band_id in band_ids:
            seen = self.buffers.snapshot(simulation_id, band_id)
            if seen:
                latest = max(latest, seen[-1])
        return latest

    def reset(self, simulation_id: str) -> int:
        """Clear every band of one simulation, buffers and cached fits alike."""
        cleared = self.buffers.reset(simulation_id)
        with self._lock:
            for key in [k for k in self._fits if k[0] == simulation_id]:
                del self._fits[key]
        log.info("periodicity reset", extra={"simulation_id": simulation_id, "bands": cleared})
        return cleared

    def state(self, simulation_id: str, band_id: int, now: float | None = None) -> dict:
        """Raw buffer plus the current estimate -- the debugging view of Section 5."""
        import numpy as np

        timestamps = self.buffers.snapshot(simulation_id, band_id)
        stats = self.buffers.stats(simulation_id, band_id)
        arr = np.asarray(timestamps, dtype=float)
        activations = cluster_activations(arr, self.config.min_period) if arr.size else arr

        fit = self.estimate(simulation_id, band_id)
        at = float(now if now is not None else (timestamps[-1] if timestamps else 0.0))

        return {
            "simulation_id": simulation_id,
            "band_id": int(band_id),
            "timestamps": timestamps,
            "inter_arrivals": np.diff(arr).tolist() if arr.size > 1 else [],
            "activations": int(activations.size),
            "detections_retained": stats["retained"],
            "detections_total": stats["total_seen"],
            "estimate": fit.as_dict(),
            "prediction": self.predict(simulation_id, band_id, at).to_contract(),
        }

    # -- introspection -----------------------------------------------------------------------

    def tracked_bands(self) -> int:
        return self.buffers.tracked()
