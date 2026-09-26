"""The estimator service: buffers + fitting + a cache, behind the Section 5 operations.

WHY THERE IS A CACHE. This service sits on the scheduler's critical path. Before every single
decision the Backend asks it for a prediction on *every* band -- 64 bands at 5 concurrent
simulations is 320 predictions per simulation step, and the whole Backend -> Ai-ml-2 -> Ai-ml-1
round trip has to fit inside NFR-002's 50 ms budget, of which Ai-ml-1 already uses about 7 ms.

Re-fitting a period sweep per band per step would not fit. The fit is cached: the first few
activations refresh it immediately, then hits and misses are accumulated in bounded batches.
Prediction against a cached fit is arithmetic -- it re-projects the next activation from the
current time without touching the period search.
"""

from __future__ import annotations

import threading
from collections import OrderedDict

from periodicity.buffers.detection_buffer import BufferStore
from periodicity.config import EstimatorConfig
from periodicity.estimator.periodicity_estimator import (
    PeriodEstimate,
    cluster_activations,
    estimate_period,
    estimate_period_with_misses,
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
        self._fits: OrderedDict[tuple[str, int], PeriodEstimate] = OrderedDict()
        self._fit_sources: dict[tuple[str, int], tuple] = {}
        self._misses_since_fit: dict[tuple[str, int], int] = {}
        self._hits_since_fit: dict[tuple[str, int], int] = {}
        self._lock = threading.Lock()

    # -- Section 5 operations ----------------------------------------------------------------

    def update(self, simulation_id: str, band_id: int, detection_timestamp: float) -> bool:
        """Record a detection; refresh the fit at bootstrap or batched hit boundaries."""
        key = (simulation_id, int(band_id))
        refit = False
        with self._lock:
            accepted = self.buffers.record(simulation_id, band_id, detection_timestamp)
            if accepted:
                pending = self._hits_since_fit.get(key, 0) + 1
                activations = len(self.buffers.snapshot(simulation_id, band_id))
                token = self.buffers.fit_token(simulation_id, band_id)
                miss_history = token[2] is not None
                observations_seen = token[1] + token[3]
                hit_interval = self.config.hit_refit_interval if miss_history else 4
                refit = (key not in self._fits or activations <= 4
                         or pending >= hit_interval
                         or observations_seen == self.config.maturity_refit_observations)
                if refit:
                    self._fits.pop(key, None)
                    self._fit_sources.pop(key, None)
                    self._hits_since_fit.pop(key, None)
                    self._misses_since_fit.pop(key, None)
                else:
                    self._hits_since_fit[key] = pending
        if refit:
            self.estimate(simulation_id, band_id)
        return accepted

    def observe_miss(self, simulation_id: str, band_id: int, timestamp: float) -> None:
        """Record a scan that found nothing and batch any resulting refit.

        Solution spec Section 3.2: a look that found nothing rules out every (T, phi) pair that
        predicted illumination there, which is why this is worth recording at all rather than
        only tracking detections -- see estimate_period_with_misses.
        """
        key = (simulation_id, int(band_id))
        refit = False
        with self._lock:
            self.buffers.record_miss(simulation_id, band_id, timestamp)
            # A miss is useful evidence, but invalidating on each one forces the next batch
            # prediction to repeat the full likelihood sweep. During a multi-episode comparison
            # that turns two quiet observed bands per step into thousands of unnecessary fits.
            # Retain every miss and fold them into the next fit after a bounded batch instead.
            if key not in self._fits:
                return
            pending = self._misses_since_fit.get(key, 0) + 1
            token = self.buffers.fit_token(simulation_id, band_id)
            observations_seen = token[1] + token[3]
            interval = min(32, self.config.miss_refit_interval) if observations_seen <= 64 else self.config.miss_refit_interval
            if (pending >= interval
                    or observations_seen == self.config.maturity_refit_observations):
                self._fits.pop(key, None)
                self._fit_sources.pop(key, None)
                self._misses_since_fit.pop(key, None)
                self._hits_since_fit.pop(key, None)
                refit = True
            else:
                self._misses_since_fit[key] = pending
        if refit:
            self.estimate(simulation_id, band_id)

    def estimate(self, simulation_id: str, band_id: int) -> PeriodEstimate:
        """Fitted period for one band, refitting only when new observations have arrived.

        Uses the hits-and-misses estimator once any miss has been recorded for this band -- far
        more informative per observation, see estimate_period_with_misses -- and falls back to
        the hits-only phase-folding estimator otherwise (e.g. before the Backend has reported
        any scan outcome for this band yet, or against a caller that only ever reports hits).
        """
        key = (simulation_id, int(band_id))
        while True:
            with self._lock:
                cached = self._fits.get(key)
                token = self.buffers.fit_token(simulation_id, band_id)
                sources = self._fit_sources.get(key)
                source_valid = (sources is not None and sources[0] is token[0]
                                and (sources[2] is token[2]
                                     or self._misses_since_fit.get(key, 0) > 0))
                if cached is not None and source_valid:
                    self._fits.move_to_end(key)
                    return cached
                self._fits.pop(key, None)
                self._fit_sources.pop(key, None)
                hits, misses, token = self.buffers.fit_snapshot(simulation_id, band_id)

            # The search runs on a consistent copy while updates to other simulations proceed.
            if misses:
                observations = sorted([(t, True) for t in hits] + [(t, False) for t in misses])
                fit = estimate_period_with_misses(observations, self.config)
            else:
                fit = estimate_period(hits, self.config)
            with self._lock:
                if self.buffers.fit_token(simulation_id, band_id) != token:
                    continue  # an update, eviction, or reset made this fit stale
                existing = self._fits.get(key)
                if existing is not None:
                    return existing
                self._fits[key] = fit
                self._fit_sources[key] = token
                self._misses_since_fit.pop(key, None)
                self._hits_since_fit.pop(key, None)
                while len(self._fits) > self.config.max_tracked_bands:
                    old_key, _ = self._fits.popitem(last=False)
                    self._fit_sources.pop(old_key, None)
                    self._misses_since_fit.pop(old_key, None)
                    self._hits_since_fit.pop(old_key, None)
                return fit

    def predict(self, simulation_id: str, band_id: int, now: float) -> Prediction:
        return predict(self.estimate(simulation_id, band_id), now, self.config)

    def phase(self, simulation_id: str, band_id: int, now: float) -> float:
        return phase_at(self.estimate(simulation_id, band_id), now)

    def predict_many(
        self, simulation_id: str, band_ids: list[int], now: float
    ) -> list[tuple[int, Prediction, float]]:
        """Predictions for many bands in one pass.

        Cheap by construction: updates refresh the cache after bounded evidence batches, so
        the usual prediction path is arithmetic on a stored fit.
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
        with self._lock:
            cleared = self.buffers.reset(simulation_id)
            for key in [k for k in self._fits if k[0] == simulation_id]:
                del self._fits[key]
                del self._fit_sources[key]
            for key in [k for k in self._misses_since_fit if k[0] == simulation_id]:
                del self._misses_since_fit[key]
            for key in [k for k in self._hits_since_fit if k[0] == simulation_id]:
                del self._hits_since_fit[key]
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
