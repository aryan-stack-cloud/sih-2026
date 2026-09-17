"""StateBuilder -- the ML-001 state vector, in both of its representations.

This is the load-bearing file of the service. The same per-band state has to be two things at
once:

* a flat float32 array, because that is what agents and Stable-Baselines3 consume; and
* the exact JSON object in API_CONTRACT.md Section 4, because that is what the Backend sends to
  ``/internal/decide``.

``to_vector()`` and ``to_contract()`` / ``from_contract()`` are the two views. Every agent reads
the vector; the API converts at the boundary and never anywhere else. Keep the field order in
``BAND_FEATURES`` in lockstep with the contract -- if they drift, a model trained offline will
silently mis-read the features the Backend sends it at inference time.

Layout, for N bands (total 8N + 2):

    [0 : 7N)          seven features per band, band-major, in BAND_FEATURES order
    [7N : 8N)         one-hot of the currently tuned bands
    [8N]              dwell_remaining_ms, normalised
    [8N + 1]          tuning_delay_countdown_ms, normalised

``band_id`` is positional in the vector, so it is a contract field but not a feature.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

# Order is authoritative: it must match the per-band key order of API_CONTRACT.md Section 4
# (minus band_id, which is positional here).
BAND_FEATURES = (
    "time_since_last_scan",
    "recent_detection_rate_ewma",
    "consecutive_misses",
    "periodicity_phase",
    "periodicity_confidence",
    "band_priority_weight",
    "tuning_cost_to_band",
)
NUM_BAND_FEATURES = len(BAND_FEATURES)


@dataclass
class StateNormalisation:
    """Divisors that map raw contract values into roughly [0, 1] for the agents.

    The contract carries raw units (steps, milliseconds); agents want bounded inputs. Keeping
    the normalisers here -- rather than inline -- means a model checkpoint can record them and
    an inference-time mismatch becomes detectable instead of silent.
    """

    time_since_last_scan: float = 32.0
    consecutive_misses: float = 10.0
    band_priority_weight: float = 2.0
    tuning_cost: float = 1.0
    dwell_ms: float = 10.0
    tuning_delay_ms: float = 10.0


class StateBuilder:
    """Tracks the ML-001 per-band features across a simulation run."""

    def __init__(
        self,
        num_bands: int,
        band_priority_weights: np.ndarray | None = None,
        ewma_alpha: float = 0.2,
        normalisation: StateNormalisation | None = None,
    ) -> None:
        self.num_bands = num_bands
        self.ewma_alpha = float(ewma_alpha)
        self.norm = normalisation or StateNormalisation()
        self.band_priority_weight = (
            np.ones(num_bands, dtype=np.float32)
            if band_priority_weights is None
            else np.asarray(band_priority_weights, dtype=np.float32)
        )
        self.reset()

    # -- lifecycle ------------------------------------------------------------------------

    def reset(self) -> None:
        n = self.num_bands
        self.time_since_last_scan = np.zeros(n, dtype=np.int32)
        self.recent_detection_rate_ewma = np.zeros(n, dtype=np.float32)
        self.consecutive_misses = np.zeros(n, dtype=np.int32)
        self.periodicity_phase = np.zeros(n, dtype=np.float32)
        self.periodicity_confidence = np.zeros(n, dtype=np.float32)
        self.tuning_cost_to_band = np.ones(n, dtype=np.int32)
        self.tuned_bands: list[int] = []
        self.dwell_remaining_ms = 0
        self.tuning_delay_countdown_ms = 0

    def update(
        self,
        scanned_bands: list[int],
        detected_bands: list[int],
        receiver_state,
        bandwidth_k: int,
    ) -> None:
        """Fold one step of scan outcomes into the per-band features.

        Called after the DetectionEngine has classified the step. Unscanned bands age; scanned
        bands have their detection-rate EWMA and consecutive-miss counter updated.
        """
        self.time_since_last_scan += 1
        detected = set(detected_bands)
        alpha = self.ewma_alpha

        for b in scanned_bands:
            self.time_since_last_scan[b] = 0
            hit = 1.0 if b in detected else 0.0
            self.recent_detection_rate_ewma[b] = (
                alpha * hit + (1.0 - alpha) * self.recent_detection_rate_ewma[b]
            )
            if hit:
                self.consecutive_misses[b] = 0
            else:
                self.consecutive_misses[b] += 1

        self.tuned_bands = receiver_state.tuned_bands(bandwidth_k, self.num_bands)
        self.dwell_remaining_ms = int(receiver_state.dwell_remaining_ms)
        self.tuning_delay_countdown_ms = int(receiver_state.tuning_delay_countdown_ms)
        tuned_start = receiver_state.tuned_start
        self.tuning_cost_to_band = np.ones(self.num_bands, dtype=np.int32)
        self.tuning_cost_to_band[tuned_start] = 0

    def set_periodicity(self, phase: np.ndarray, confidence: np.ndarray) -> None:
        """Inject the two features this service does not compute.

        At inference these arrive inside the StateVector, already populated by the Backend from
        Ai-ml-2's ``/internal/periodicity/predict``. Ai-ml-1 never calls Ai-ml-2 directly.
        """
        self.periodicity_phase = np.asarray(phase, dtype=np.float32)
        self.periodicity_confidence = np.asarray(confidence, dtype=np.float32)

    # -- view 1: the flat vector agents consume -------------------------------------------

    @staticmethod
    def vector_size(num_bands: int) -> int:
        return NUM_BAND_FEATURES * num_bands + num_bands + 2

    def to_vector(self) -> np.ndarray:
        n = self.num_bands
        norm = self.norm
        bands = np.empty((n, NUM_BAND_FEATURES), dtype=np.float32)
        bands[:, 0] = np.minimum(self.time_since_last_scan / norm.time_since_last_scan, 1.0)
        bands[:, 1] = self.recent_detection_rate_ewma
        bands[:, 2] = np.minimum(self.consecutive_misses / norm.consecutive_misses, 1.0)
        bands[:, 3] = self.periodicity_phase
        bands[:, 4] = self.periodicity_confidence
        bands[:, 5] = self.band_priority_weight / norm.band_priority_weight
        bands[:, 6] = self.tuning_cost_to_band / norm.tuning_cost

        tuned = np.zeros(n, dtype=np.float32)
        if self.tuned_bands:
            tuned[np.asarray(self.tuned_bands, dtype=int)] = 1.0

        receiver = np.array(
            [
                min(self.dwell_remaining_ms / norm.dwell_ms, 1.0),
                min(self.tuning_delay_countdown_ms / norm.tuning_delay_ms, 1.0),
            ],
            dtype=np.float32,
        )
        return np.concatenate([bands.reshape(-1), tuned, receiver]).astype(np.float32)

    # -- view 2: the API_CONTRACT.md Section 4 StateVector ---------------------------------

    def to_contract(self) -> dict:
        """The StateVector JSON exactly as the Backend sends and expects it."""
        return {
            "bands": [
                {
                    "band_id": int(b),
                    "time_since_last_scan": int(self.time_since_last_scan[b]),
                    "recent_detection_rate_ewma": float(self.recent_detection_rate_ewma[b]),
                    "consecutive_misses": int(self.consecutive_misses[b]),
                    "periodicity_phase": float(self.periodicity_phase[b]),
                    "periodicity_confidence": float(self.periodicity_confidence[b]),
                    "band_priority_weight": float(self.band_priority_weight[b]),
                    "tuning_cost_to_band": int(self.tuning_cost_to_band[b]),
                }
                for b in range(self.num_bands)
            ],
            "receiver": {
                "tuned_bands": [int(b) for b in self.tuned_bands],
                "dwell_remaining_ms": int(self.dwell_remaining_ms),
                "tuning_delay_countdown_ms": int(self.tuning_delay_countdown_ms),
            },
        }

    @classmethod
    def from_contract(
        cls, state: dict, normalisation: StateNormalisation | None = None
    ) -> "StateBuilder":
        """Rebuild a StateBuilder from an incoming StateVector.

        This is the inference path: the Backend owns the state, we reconstruct just enough of it
        to produce the same feature vector the agent was trained on.
        """
        bands = state["bands"]
        n = len(bands)
        if n == 0:
            raise ValueError("StateVector must contain at least one band")
        # Bands may arrive in any order; band_id is authoritative, not list position.
        bands = sorted(bands, key=lambda b: int(b["band_id"]))
        ids = [int(b["band_id"]) for b in bands]
        if ids != list(range(n)):
            raise ValueError(f"band_id values must be a contiguous 0..N-1 range, got {ids}")

        sb = cls(
            num_bands=n,
            band_priority_weights=np.array(
                [float(b["band_priority_weight"]) for b in bands], dtype=np.float32
            ),
            normalisation=normalisation,
        )
        sb.time_since_last_scan = np.array(
            [int(b["time_since_last_scan"]) for b in bands], dtype=np.int32
        )
        sb.recent_detection_rate_ewma = np.array(
            [float(b["recent_detection_rate_ewma"]) for b in bands], dtype=np.float32
        )
        sb.consecutive_misses = np.array(
            [int(b["consecutive_misses"]) for b in bands], dtype=np.int32
        )
        sb.periodicity_phase = np.array(
            [float(b["periodicity_phase"]) for b in bands], dtype=np.float32
        )
        sb.periodicity_confidence = np.array(
            [float(b["periodicity_confidence"]) for b in bands], dtype=np.float32
        )
        sb.tuning_cost_to_band = np.array(
            [int(b["tuning_cost_to_band"]) for b in bands], dtype=np.int32
        )

        receiver = state.get("receiver") or {}
        sb.tuned_bands = [int(b) for b in receiver.get("tuned_bands", [])]
        sb.dwell_remaining_ms = int(receiver.get("dwell_remaining_ms", 0))
        sb.tuning_delay_countdown_ms = int(receiver.get("tuning_delay_countdown_ms", 0))
        return sb


def vector_from_contract(
    state: dict, normalisation: StateNormalisation | None = None
) -> np.ndarray:
    """Convenience for the inference path: StateVector JSON -> agent input vector."""
    return StateBuilder.from_contract(state, normalisation).to_vector()
