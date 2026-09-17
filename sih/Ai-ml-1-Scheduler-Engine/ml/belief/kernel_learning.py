"""Learning each band's occupancy transition kernel from hits and misses.

The problem statement asks for precisely this: "The model should then be trained based on hits and
misses." Until this module existed the occupancy chain in ``ml/belief/occupancy.py`` used fixed
``p01`` and ``p10``, so an unobserved band drifted toward a prior nobody had measured.

**The estimator sees observations, not states.** A plain count of detections over looks is biased
upward by false alarms and downward by missed detections, and on this receiver both errors are
large: Pd around 0.84, Pfa around 0.067. Undoing the ROC is not a refinement here, it is the
difference between a usable estimate and a wrong one.

Two closed-form corrections do the whole job for a two-state chain.

**Stationary occupancy.** A look detects with probability ``pi*Pd + (1-pi)*Pfa``, so

    pi = ( P(detect) - Pfa ) / ( Pd - Pfa )

**Switching rate.** Write ``lam = 1 - p01 - p10`` for the chain's second eigenvalue. The lag-g
autocovariance of the true state is ``pi (1-pi) lam^g``, and passing through the detector scales
it by ``(Pd - Pfa)^2``, so from pairs of looks at the same band separated by g steps

    lam = ( autocov(g) / [ (Pd - Pfa)^2 pi (1-pi) ] ) ^ (1/g)

Recovering the kernel is then ``p01 = pi (1 - lam)`` and ``p10 = (1 - pi)(1 - lam)``.

Using observation *pairs* rather than consecutive slots is what makes this work against a real
scheduler, which revisits a band every several steps rather than every step. Every pair of looks
contributes at its own gap, so sparse and irregular revisits are evidence rather than a problem.

``lam`` is clipped to be non-negative. A negatively correlated band is physically possible but is
the signature of a periodic emitter, and periodicity is the periodicity estimator's job -- forcing
it through a two-state chain would produce a confident, meaningless kernel.
"""

from __future__ import annotations

import numpy as np

# Longest observation gap that contributes to the autocovariance fit. Beyond this the true
# autocovariance of any chain of interest has decayed into the noise, and the g-th root amplifies
# that noise rather than the signal.
MAX_GAP = 32

# The detector must separate the hypotheses by at least this much before its evidence is used at
# all. Below it, the 1/(Pd - Pfa) correction amplifies sampling noise without bound.
MIN_SEPARATION = 0.05

# Bound on the kernel's total switching probability, so a degenerate fit cannot produce a chain
# that is instantaneously random or completely frozen.
MIN_SWITCH, MAX_SWITCH = 1e-4, 1.0


class KernelEstimator:
    """Per-band ``(p01, p10)`` estimated online from noisy looks."""

    def __init__(
        self,
        num_bands: int,
        p_d: float,
        p_fa: float,
        p01_prior: float = 0.05,
        p10_prior: float = 0.05,
        prior_strength: float = 20.0,
        forgetting: float = 1.0,
        max_gap: int = MAX_GAP,
    ) -> None:
        if num_bands < 1:
            raise ValueError(f"num_bands must be at least 1, got {num_bands}")
        if not 0.0 <= forgetting <= 1.0:
            raise ValueError(f"forgetting must lie in [0, 1], got {forgetting}")
        if prior_strength < 0.0:
            raise ValueError(f"prior_strength must be non-negative, got {prior_strength}")

        self.num_bands = int(num_bands)
        self.p_d = float(p_d)
        self.p_fa = float(p_fa)
        self.p01_prior = float(p01_prior)
        self.p10_prior = float(p10_prior)
        self.prior_strength = float(prior_strength)
        self.forgetting = float(forgetting)
        self.max_gap = int(max_gap)
        self.reset()

    def reset(self) -> None:
        n, g = self.num_bands, self.max_gap
        self._looks = np.zeros(n)                  # discounted count of looks
        self._detects = np.zeros(n)                # discounted count of detections
        self._pair_n = np.zeros((n, g + 1))        # discounted pair counts, by gap
        self._pair_yy = np.zeros((n, g + 1))       # discounted sum of y_prev * y_curr
        self._last_t = np.full(n, -1, dtype=np.int64)
        self._last_y = np.zeros(n, dtype=bool)

    # -- evidence ------------------------------------------------------------------------------

    def observe(self, t: int, bands, detections) -> None:
        """Record one dwell's outcome. ``bands`` and ``detections`` are aligned sequences."""
        bands = [int(b) for b in bands]
        detections = [bool(d) for d in detections]
        if len(bands) != len(detections):
            raise ValueError("bands and detections must be the same length")

        if self.forgetting < 1.0:
            self._looks *= self.forgetting
            self._detects *= self.forgetting
            self._pair_n *= self.forgetting
            self._pair_yy *= self.forgetting

        for band, detected in zip(bands, detections):
            y = 1.0 if detected else 0.0
            self._looks[band] += 1.0
            self._detects[band] += y

            gap = t - self._last_t[band]
            if self._last_t[band] >= 0 and 1 <= gap <= self.max_gap:
                self._pair_n[band, gap] += 1.0
                self._pair_yy[band, gap] += float(self._last_y[band]) * y

            self._last_t[band] = t
            self._last_y[band] = detected

    # -- estimates -----------------------------------------------------------------------------

    @property
    def _separable(self) -> bool:
        return (self.p_d - self.p_fa) >= MIN_SEPARATION

    def evidence_confidence(self) -> np.ndarray:
        """How far each band's estimate has moved from the prior toward the measurements.

        Zero for a band never looked at, approaching one as looks accumulate. This is the same
        blending weight :meth:`stationary` uses, exposed because it is also the right answer to
        "do we understand this band yet".

        Periodicity confidence cannot answer that question on its own: it only rises for cleanly
        periodic emitters, so a band holding a random emitter never earns it and an *empty* band
        never earns it either -- though an empty band is the most thoroughly characterised thing in
        the spectrum. Evidence does not care what the band contains, only how well it is known.
        """
        return self._looks / (self._looks + self.prior_strength)

    def stationary(self) -> np.ndarray:
        """Long-run occupancy per band, corrected for the detector, blended with the prior."""
        prior = self.p01_prior / max(self.p01_prior + self.p10_prior, 1e-12)
        if not self._separable:
            return np.full(self.num_bands, prior)

        with np.errstate(invalid="ignore", divide="ignore"):
            rate = np.divide(
                self._detects, self._looks, out=np.full(self.num_bands, prior), where=self._looks > 0
            )
        corrected = np.clip((rate - self.p_fa) / (self.p_d - self.p_fa), 0.0, 1.0)

        weight = self._looks / (self._looks + self.prior_strength)
        return np.clip(weight * corrected + (1.0 - weight) * prior, 0.0, 1.0)

    def _lambda(self, stationary: np.ndarray) -> np.ndarray:
        """Second eigenvalue of each band's chain, from the lag-g autocovariance of the looks."""
        prior_lam = np.full(
            self.num_bands, max(0.0, 1.0 - self.p01_prior - self.p10_prior)
        )
        if not self._separable:
            return prior_lam

        scale = (self.p_d - self.p_fa) ** 2 * stationary * (1.0 - stationary)
        out = prior_lam.copy()

        for band in range(self.num_bands):
            if scale[band] <= 1e-9:
                continue
            mean_y = (
                self._detects[band] / self._looks[band] if self._looks[band] > 0 else 0.0
            )
            estimates, weights = [], []
            for gap in range(1, self.max_gap + 1):
                pairs = self._pair_n[band, gap]
                if pairs < 5.0:
                    continue
                autocov = self._pair_yy[band, gap] / pairs - mean_y * mean_y
                ratio = autocov / scale[band]
                if ratio <= 0.0:
                    # Non-positive correlation at this lag carries no information about a
                    # positively correlated chain; treat it as a fully decayed observation.
                    estimates.append(0.0)
                else:
                    estimates.append(min(ratio, 1.0) ** (1.0 / gap))
                weights.append(pairs)

            if estimates:
                total_pairs = float(sum(weights))
                fitted = float(np.average(estimates, weights=weights))
                # Blend toward the prior until enough pairs have accumulated, mirroring the
                # stationary estimate so both halves of the kernel earn their confidence the
                # same way.
                w = total_pairs / (total_pairs + self.prior_strength)
                out[band] = w * fitted + (1.0 - w) * prior_lam[band]

        return np.clip(out, 0.0, 1.0 - MIN_SWITCH)

    def kernels(self) -> tuple[np.ndarray, np.ndarray]:
        """``(p01, p10)`` per band, ready to hand to :class:`~ml.belief.occupancy.OccupancyBelief`."""
        stationary = self.stationary()
        switch = np.clip(1.0 - self._lambda(stationary), MIN_SWITCH, MAX_SWITCH)
        p01 = np.clip(stationary * switch, 0.0, 1.0)
        p10 = np.clip((1.0 - stationary) * switch, 0.0, 1.0)
        return p01, p10
