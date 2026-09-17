"""Receiver, Scanner and DetectionEngine (PRD Section 9).

The receiver is what makes this a scheduling problem rather than a lookup: it can only observe
K bands at a time, retuning costs time, and an observation is only valid once the tuning delay
has elapsed and the dwell minimum is met.

Timing model (one simulation step is ``step_ms`` of wall time):

    observe_ms = step_ms - (tuning_delay_ms if the receiver retuned this step else 0)

    observe_ms < dwell_ms  ->  no valid observation at all this step. PRD Section 9.1: "tuning
                               delay must fully elapse before a newly tuned band yields a valid
                               observation", and dwell is the minimum observation duration.

    otherwise              ->  observation quality scales with integration time,
                               snr_gain = sqrt(observe_ms / step_ms)

The graded SNR term matters: a hard on/off switching cost would make retuning either free or
fatal, and the agent would learn a degenerate policy either way. Scaling the effective SNR by
integration time reproduces the real trade-off -- retuning is always possible, but you see less
well on the step you did it.

Instantaneous bandwidth: an action names ``next_band``; the receiver observes the contiguous
block of K bands starting there (wrapping at the top of the spectrum). That is what "K bands
observable per step" means physically (PRD Section 9.2) and it keeps the action space
Discrete(N), matching the ``next_band: int`` action in API_CONTRACT.md Section 4.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field

import numpy as np

# Detection outcome labels, matching detection_type in API_CONTRACT.md Section 6.
TP, FN, FP, TN = "TP", "FN", "FP", "TN"


@dataclass
class ReceiverConfig:
    """Configurable receiver parameters (PRD Section 9.2)."""

    bandwidth_k: int = 2          # bands observable per step
    dwell_ms: int = 4             # minimum observation duration
    tuning_delay_ms: int = 3      # cost of retuning to a different block
    step_ms: int = 10             # wall time of one simulation step
    threshold: float = 1.5        # detection threshold on the observation statistic
    snr_mean: float = 3.0         # mean observation value when ground truth is active
    noise_sigma: float = 1.0      # stddev of the observation noise

    def __post_init__(self) -> None:
        if self.bandwidth_k < 1:
            raise ValueError("bandwidth_k must be >= 1")
        if self.dwell_ms > self.step_ms:
            raise ValueError("dwell_ms cannot exceed step_ms; the receiver could never observe")
        if self.tuning_delay_ms < 0 or self.tuning_delay_ms > self.step_ms:
            raise ValueError("tuning_delay_ms must be within [0, step_ms]")

    @property
    def retune_is_observable(self) -> bool:
        """Whether a step that retunes can still yield a valid observation."""
        return (self.step_ms - self.tuning_delay_ms) >= self.dwell_ms


@dataclass
class ReceiverState:
    """Receiver state R(t) (PRD Section 9.1), mirrored into the StateVector receiver block."""

    tuned_start: int = 0
    dwell_remaining_ms: int = 0
    tuning_delay_countdown_ms: int = 0

    def tuned_bands(self, k: int, num_bands: int) -> list[int]:
        return [(self.tuned_start + i) % num_bands for i in range(min(k, num_bands))]


@dataclass
class Observation:
    """One step of scan output (PRD Section 9.1).

    ``valid`` is False when the tuning delay left too little integration time to meet the dwell
    minimum -- the receiver spent the step retuning and saw nothing.
    """

    t: int
    tuned_bands: list[int]
    values: dict[int, float] = field(default_factory=dict)
    valid: bool = True
    retuned: bool = False
    snr_gain: float = 1.0


@dataclass
class DetectionOutcome:
    """Per-band detection classification for one step, plus the derived reward inputs."""

    t: int
    outcomes: dict[int, str]                      # band -> TP/FN/FP/TN, scanned bands only
    unscanned_misses: list[int]                   # active bands nobody looked at (also FN)
    detected_bands: list[int]
    false_alarm_bands: list[int]
    detected_emitters: set[int]
    max_detected_priority: float
    detection_latency: dict[int, int]             # band -> t - activation_start, per TP


class Receiver:
    """Holds instantaneous bandwidth, dwell time, tuning delay and detection threshold."""

    def __init__(self, config: ReceiverConfig, num_bands: int) -> None:
        self.config = config
        self.num_bands = num_bands
        self.state = ReceiverState()

    def reset(self, tuned_start: int = 0) -> None:
        self.state = ReceiverState(tuned_start=tuned_start)

    def tune(self, next_band: int) -> bool:
        """Point the receiver at a new block. Returns True if this was an actual retune."""
        next_band = int(next_band) % self.num_bands
        retuned = next_band != self.state.tuned_start
        self.state.tuned_start = next_band
        cfg = self.config
        if retuned:
            self.state.tuning_delay_countdown_ms = cfg.tuning_delay_ms
            self.state.dwell_remaining_ms = max(
                0, cfg.dwell_ms - (cfg.step_ms - cfg.tuning_delay_ms)
            )
        else:
            self.state.tuning_delay_countdown_ms = 0
            self.state.dwell_remaining_ms = 0
        return retuned

    @property
    def tuned_bands(self) -> list[int]:
        return self.state.tuned_bands(self.config.bandwidth_k, self.num_bands)

    def tuning_cost_to(self, band: int) -> int:
        """Integer cost of reaching ``band`` from the current tuning, for the StateVector."""
        return 0 if int(band) % self.num_bands == self.state.tuned_start else 1


class Scanner:
    """Executes a scan action against the Receiver and Spectrum, producing an Observation."""

    def __init__(self, receiver: Receiver, rng: np.random.Generator) -> None:
        self.receiver = receiver
        self.rng = rng

    def execute(self, t: int, next_band: int, occupancy_row: np.ndarray) -> Observation:
        cfg = self.receiver.config
        retuned = self.receiver.tune(next_band)
        bands = self.receiver.tuned_bands

        observe_ms = cfg.step_ms - (cfg.tuning_delay_ms if retuned else 0)
        if observe_ms < cfg.dwell_ms:
            return Observation(t=t, tuned_bands=bands, valid=False, retuned=retuned, snr_gain=0.0)

        snr_gain = math.sqrt(observe_ms / cfg.step_ms)
        values = {}
        for b in bands:
            signal = cfg.snr_mean * snr_gain if occupancy_row[b] else 0.0
            values[b] = float(signal + self.rng.normal(0.0, cfg.noise_sigma))
        return Observation(
            t=t, tuned_bands=bands, values=values, valid=True, retuned=retuned, snr_gain=snr_gain
        )


class DetectionEngine:
    """Applies the detection threshold to an Observation, emitting TP/FN/FP/TN events.

    Classification follows PRD Section 9.1 exactly:

        TP  observation exceeds threshold and ground truth is active
        FN  ground truth active but the band was not scanned, OR scanned and below threshold
        FP  observation exceeds threshold but ground truth is inactive
        TN  scanned, inactive, and below threshold

    Note the asymmetry, and it is deliberate: FN includes bands nobody scanned (that is the whole
    cost of a bad schedule), but FP/TN only exist for bands that were actually observed -- an
    unscanned band cannot raise a false alarm. ml/evaluation/evaluator.py relies on this when
    computing Pd across all bands but Pfa across scanned bands only.
    """

    def __init__(self, threshold: float) -> None:
        self.threshold = threshold

    def evaluate(
        self,
        observation: Observation,
        occupancy_row: np.ndarray,
        owner_row: np.ndarray,
        priority_row: np.ndarray,
        activation_row: np.ndarray,
    ) -> DetectionOutcome:
        outcomes: dict[int, str] = {}
        detected_bands: list[int] = []
        false_alarm_bands: list[int] = []
        detected_emitters: set[int] = set()
        latency: dict[int, int] = {}
        max_priority = 0.0

        scanned = set(observation.tuned_bands) if observation.valid else set()

        for b in sorted(scanned):
            active = bool(occupancy_row[b])
            above = observation.values[b] > self.threshold
            if active and above:
                outcomes[b] = TP
                detected_bands.append(b)
                if owner_row[b] >= 0:
                    detected_emitters.add(int(owner_row[b]))
                max_priority = max(max_priority, float(priority_row[b]))
                if activation_row[b] >= 0:
                    latency[b] = int(observation.t - activation_row[b])
            elif active:
                outcomes[b] = FN
            elif above:
                outcomes[b] = FP
                false_alarm_bands.append(b)
            else:
                outcomes[b] = TN

        unscanned_misses = [
            int(b) for b in np.flatnonzero(occupancy_row) if int(b) not in scanned
        ]

        return DetectionOutcome(
            t=observation.t,
            outcomes=outcomes,
            unscanned_misses=unscanned_misses,
            detected_bands=detected_bands,
            false_alarm_bands=false_alarm_bands,
            detected_emitters=detected_emitters,
            max_detected_priority=max_priority,
            detection_latency=latency,
        )
