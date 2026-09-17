"""Energy-detector ROC and the dwell decision (SCT solution spec Sections 2 and 4.3.1).

The problem statement lists "Receiver Sensitivity and threshold detection performance" among the
figures of merit, which means Pd and Pfa have to be *derived* from an operating point rather than
configured as free numbers. Here they are: fix the target Pfa, the threshold follows, and Pd
follows from SNR along the ROC.

Under the Gaussian approximation to the energy statistic, valid for the sample counts a real dwell
produces,

    P_fa(lambda) = Q( (lambda - N_s) / sqrt(2 N_s) )
    P_d(lambda)  = Q( (lambda - N_s (1 + snr)) / ((1 + snr) sqrt(2 N_s)) )

with lambda normalised by the noise power. Eliminating lambda gives the operating relation the
whole scheduler uses:

    P_d(N_s, snr) = Q( ( Qinv(P_fa) - snr sqrt(N_s / 2) ) / (1 + snr) )

**On N_s.** Written literally as dwell times analysis bandwidth this is millions of samples, with
a correspondingly tiny per-sample SNR, because a microsecond pulse occupies a vanishing fraction
of a 10 ms dwell. Carrying both extremes through a simulation is numerically pointless. This
module parameterises by ``n_eff``, the effective number of independent integration samples per
slot, with ``snr`` the dwell-averaged post-detection SNR. Those two are the knobs a scenario sets,
and they mean something a radar engineer can argue with.

**The dwell decision.** ``value_rate`` divides detection probability by the wall time the dwell
actually consumes, retune included. That single choice makes the optimal dwell fall out rather
than being tuned, and the answer is non-obvious: it is *non-monotone* in SNR. A strong signal
needs one slot, a marginal signal justifies eight because integration is what lifts it over
threshold, and a hopeless signal goes back to one because no available dwell will reach it.
That third regime is the one a hand-written rule always gets wrong.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Sequence

from scipy.stats import norm


def _q(x: float) -> float:
    """Gaussian upper-tail probability."""
    return float(norm.sf(x))


def _q_inv(p: float) -> float:
    """Inverse of :func:`_q`."""
    return float(norm.isf(p))


def threshold_for_pfa(p_fa: float, n_s: float) -> float:
    """Detection threshold, normalised by noise power, that yields the target false-alarm rate."""
    if not 0.0 < p_fa < 1.0:
        raise ValueError(f"p_fa must lie strictly inside (0, 1), got {p_fa}")
    if n_s <= 0:
        raise ValueError(f"n_s must be positive, got {n_s}")
    return n_s + math.sqrt(2.0 * n_s) * _q_inv(p_fa)


def pfa_for_threshold(threshold: float, n_s: float) -> float:
    """Inverse of :func:`threshold_for_pfa`; kept so the operating point can be round-tripped."""
    if n_s <= 0:
        raise ValueError(f"n_s must be positive, got {n_s}")
    return _q((threshold - n_s) / math.sqrt(2.0 * n_s))


def probability_of_detection(p_fa: float, n_s: float, snr: float) -> float:
    """Detection probability at the operating point set by ``p_fa``."""
    if snr < 0.0:
        raise ValueError(f"snr must be non-negative, got {snr}")
    if n_s <= 0:
        raise ValueError(f"n_s must be positive, got {n_s}")
    return _q((_q_inv(p_fa) - snr * math.sqrt(n_s / 2.0)) / (1.0 + snr))


@dataclass(frozen=True)
class DetectionModel:
    """One receiver's operating point, plus the timing needed to turn value into a rate."""

    p_fa: float = 1e-3
    n_eff: float = 100.0
    slot_s: float = 0.010
    retune_s: float = 0.005

    def __post_init__(self) -> None:
        if not 0.0 < self.p_fa < 1.0:
            raise ValueError(f"p_fa must lie strictly inside (0, 1), got {self.p_fa}")
        if self.n_eff <= 0:
            raise ValueError(f"n_eff must be positive, got {self.n_eff}")
        if self.slot_s <= 0:
            raise ValueError(f"slot_s must be positive, got {self.slot_s}")
        if self.retune_s < 0:
            raise ValueError(f"retune_s must be non-negative, got {self.retune_s}")

    def samples(self, dwell_slots: int) -> float:
        return self.n_eff * float(dwell_slots)

    def p_d(self, dwell_slots: int, snr: float) -> float:
        """Detection probability for a dwell of ``dwell_slots`` slots at this SNR."""
        return probability_of_detection(self.p_fa, self.samples(dwell_slots), snr)

    def elapsed_s(self, dwell_slots: int, retune: bool = True) -> float:
        """Wall time a dwell consumes, including the retune that got us there."""
        return dwell_slots * self.slot_s + (self.retune_s if retune else 0.0)

    def value_rate(self, dwell_slots: int, snr: float, retune: bool = True) -> float:
        """Detection probability per unit of receiver time.

        The denominator is what makes the sensitivity-versus-coverage trade-off visible to the
        scheduler at all. A reward that pays a fixed amount per detection cannot express "this
        detection cost me eight slots and that one cost me one".
        """
        return self.p_d(dwell_slots, snr) / self.elapsed_s(dwell_slots, retune)


def best_dwell(
    model: DetectionModel,
    snr: float,
    options: Sequence[int] = (1, 2, 4, 8),
    retune: bool = True,
) -> int:
    """Dwell length maximising detection probability per unit time.

    Ties break toward the shorter dwell, because coverage is the thing being spent.
    """
    if not options:
        raise ValueError("options must contain at least one dwell length")
    ordered = sorted(int(m) for m in options)
    return max(ordered, key=lambda m: (model.value_rate(m, snr, retune), -m))
