"""Where ``periodicity_phase`` and ``periodicity_confidence`` come from.

READ THIS BEFORE EDITING -- it encodes a service boundary.

Periodicity estimation belongs to **Ai-ml-2**, not here. In the deployed system the Backend's
StateBuilder calls Ai-ml-2's ``/internal/periodicity/predict``, merges the result into the
StateVector, and only then posts it to our ``/internal/decide``. Ai-ml-1 never calls Ai-ml-2, and
the inference path in this service never computes periodicity -- it reads whatever arrived in the
StateVector. That is the seam every domain is required to respect (API_CONTRACT.md Section 0).

So why is there an estimator in this file at all?

Because standalone *training* has no Backend and no Ai-ml-2 in the loop. If those two features
were pinned at zero for every training episode, the agent would learn that they carry no signal
-- and would then ignore them at inference, when they suddenly do carry signal. That would
quietly defeat PRD Definition-of-Done item 8 ("periodic-emitter prediction measurably improves
detection latency on Scenario B"). ``LocalPeriodicityProvider`` is a training-time stand-in for
Ai-ml-2 so the feature columns are live while the agent learns.

    NullPeriodicityProvider    zeros. Use when the caller supplies the features itself.
    LocalPeriodicityProvider   TRAINING ONLY. Never reachable from ml/api/.

If you want to improve periodicity estimation, improve it in Ai-ml-2.
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable

import numpy as np


@runtime_checkable
class PeriodicityProvider(Protocol):
    """Supplies the two periodicity features for every band at time t."""

    def reset(self, num_bands: int) -> None: ...

    def observe_detection(self, band: int, t: int) -> None: ...

    def features(self, t: int) -> tuple[np.ndarray, np.ndarray]:
        """Returns ``(phase, confidence)``, each shape ``(num_bands,)``, values in [0, 1]."""
        ...


class NullPeriodicityProvider:
    """Zeros for both features -- the correct choice on the inference path."""

    def __init__(self) -> None:
        self.num_bands = 0

    def reset(self, num_bands: int) -> None:
        self.num_bands = num_bands

    def observe_detection(self, band: int, t: int) -> None:  # noqa: D102 - no state to keep
        return None

    def features(self, t: int) -> tuple[np.ndarray, np.ndarray]:
        z = np.zeros(self.num_bands, dtype=np.float32)
        return z, z.copy()


class LocalPeriodicityProvider:
    """TRAINING-ONLY stand-in for Ai-ml-2's estimator.

    Deliberately the simplest thing that produces an honest signal: a bounded ring buffer of
    detection timestamps per band, period estimated as the median inter-arrival, and confidence
    from the consistency of those inter-arrivals scaled by how many we have.

    ``phase`` is the fraction of the estimated period elapsed since the last detection, so a
    value near 1.0 means "this band is about due". Confidence stays near zero for the four
    non-periodic behavior classes, which is the behavior Ai-ml-2's Level 7 requires -- a
    confident-but-wrong periodicity claim is worse than no claim.
    """

    def __init__(self, buffer_size: int = 16, min_samples: int = 4) -> None:
        self.buffer_size = buffer_size
        self.min_samples = max(2, min_samples)
        self.num_bands = 0
        self._timestamps: list[list[int]] = []

    def reset(self, num_bands: int) -> None:
        self.num_bands = num_bands
        self._timestamps = [[] for _ in range(num_bands)]

    def observe_detection(self, band: int, t: int) -> None:
        buf = self._timestamps[band]
        if buf and buf[-1] == t:
            return
        buf.append(int(t))
        if len(buf) > self.buffer_size:
            del buf[0]

    def features(self, t: int) -> tuple[np.ndarray, np.ndarray]:
        phase = np.zeros(self.num_bands, dtype=np.float32)
        confidence = np.zeros(self.num_bands, dtype=np.float32)

        for b, buf in enumerate(self._timestamps):
            if len(buf) < self.min_samples:
                continue
            gaps = np.diff(np.asarray(buf, dtype=np.float64))
            gaps = gaps[gaps > 0]
            if gaps.size < self.min_samples - 1:
                continue

            period = float(np.median(gaps))
            if period <= 0:
                continue

            # Consistency: normalised median absolute deviation of the inter-arrivals. A clean
            # periodic emitter has MAD ~ 0; a random one has MAD comparable to the period.
            mad = float(np.median(np.abs(gaps - period)))
            consistency = max(0.0, 1.0 - mad / period)

            # Sample sufficiency: zero below min_samples, saturating at roughly twice it.
            # Deliberately independent of buffer_size -- that is a memory bound, not evidence.
            # Ten cleanly-spaced detections are strong evidence of a period whether the ring
            # buffer holds 16 timestamps or 64.
            sufficiency = min(1.0, (len(buf) - self.min_samples + 1) / (self.min_samples + 1))

            phase[b] = float(((t - buf[-1]) % period) / period)
            confidence[b] = float(consistency * sufficiency)

        return phase, confidence

    def state(self, band: int) -> dict:
        """Debug view, mirroring Ai-ml-2's ``/internal/periodicity/state`` shape."""
        buf = list(self._timestamps[band])
        gaps = np.diff(np.asarray(buf, dtype=np.float64)).tolist() if len(buf) > 1 else []
        return {"band_id": band, "timestamps": buf, "inter_arrivals": gaps}


class ServicePeriodicityProvider:
    """TRAINING ONLY: Ai-ml-2's own estimator, embedded in-process and fed as the Backend feeds it.

    Why this exists alongside ``LocalPeriodicityProvider``: a model trained offline sees the
    stand-in's features, but a served one sees Ai-ml-2's -- and the two disagree. The stand-in
    counts every hit timestamp, trusts four samples and reports a smooth confidence; Ai-ml-2
    clusters a burst into one activation, folds misses into the fit, and withholds a claim it
    cannot support (six consecutive hits scored 0.60 here and 0.0 there). DQN/PPO are served
    read-only, so they cannot adapt to that shift at run time; training them on Ai-ml-2's actual
    output removes it.

    This does not move estimation into Ai-ml-1's serving path. It is the same code the Backend's
    HTTP calls reach, run in-process only because standalone training has no Backend in the loop.
    Nothing on ``ml/api`` constructs it.
    """

    def __init__(self) -> None:
        self._service = _ai_ml_2_service_class()()
        self._simulation_id = "training"
        self.num_bands = 0

    def reset(self, num_bands: int) -> None:
        self.num_bands = num_bands
        self._service.reset(self._simulation_id)

    def observe_detection(self, band: int, t: int) -> None:
        self._service.update(self._simulation_id, int(band), float(t))

    def observe_miss(self, band: int, t: int) -> None:
        self._service.observe_miss(self._simulation_id, int(band), float(t))

    def features(self, t: int) -> tuple[np.ndarray, np.ndarray]:
        phase = np.zeros(self.num_bands, dtype=np.float32)
        confidence = np.zeros(self.num_bands, dtype=np.float32)
        for band, prediction, band_phase in self._service.predict_many(
            self._simulation_id, list(range(self.num_bands)), float(t)
        ):
            phase[band] = band_phase
            confidence[band] = prediction.confidence
        # The Backend's StateBuilder clamps both into [0, 1] before they reach a model.
        return np.clip(phase, 0.0, 1.0), np.clip(confidence, 0.0, 1.0)


def _ai_ml_2_service_class():
    """Import Ai-ml-2's ``PeriodicityService`` from the sibling service folder."""
    try:
        from periodicity.service import PeriodicityService  # noqa: PLC0415
    except ImportError:
        import os
        import sys
        from pathlib import Path

        root = os.environ.get("AI_ML_2_PATH") or str(
            Path(__file__).resolve().parents[3] / "Ai-ml-2-Periodicity-Estimator"
        )
        if root not in sys.path:
            sys.path.append(root)
        from periodicity.service import PeriodicityService  # noqa: PLC0415
    return PeriodicityService


def serving_periodicity_source() -> str:
    """``"ai-ml-2"`` when training can use Ai-ml-2's own estimator, else ``"local-standin"``.

    Recorded on every trained model, because a checkpoint trained on the stand-in's features is
    served Ai-ml-2's -- the skew this module exists to remove -- and that should be visible in the
    registry rather than only in a warning nobody saw.
    """
    try:
        _ai_ml_2_service_class()
        return "ai-ml-2"
    except ImportError:
        return "local-standin"


def serving_periodicity_provider() -> PeriodicityProvider:
    """The provider whose features match what a served model will see.

    Ai-ml-2's own estimator when its code is importable (the repository layout, or
    ``AI_ML_2_PATH``); otherwise the stand-in, so training still runs in a container that ships
    Ai-ml-1 alone.
    """
    try:
        return ServicePeriodicityProvider()
    except ImportError:
        import warnings

        warnings.warn(
            "Ai-ml-2's estimator is not importable; training on LocalPeriodicityProvider, whose "
            "features differ from what the served model will receive",
            RuntimeWarning,
            stacklevel=2,
        )
        return LocalPeriodicityProvider()
