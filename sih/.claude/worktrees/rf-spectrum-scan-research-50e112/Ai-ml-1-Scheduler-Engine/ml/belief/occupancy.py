"""Per-band occupancy belief with imperfect sensing (SCT solution spec Section 3.1).

Each band is a two-state Gilbert-Elliott chain, idle or active. Scanning a band reveals its state
and **resets** the belief; not scanning lets the belief drift toward the chain's stationary
value. That reset structure is what makes the scheduling problem a restless bandit with reset,
which is indexable with a closed-form Whittle index (Liu, Weber & Zhao 2011). The index policy in
``ml/agents/index_agent.py`` is built directly on this.

Two design points that are easy to get wrong and expensive to get wrong.

**The reset is soft, not hard.** A naive implementation sets the belief to 1 on a detection and 0
on a miss, which silently assumes a perfect sensor. The correct update is the POMDP one, using the
detector's own ``P_d`` and ``P_fa``, so the amount of reset is governed by the same ROC curve the
receiver model uses. The two stay consistent by construction, and the scheduler stops
over-trusting the sensor exactly where false alarms hurt most.

**Repeated misses converge to the stationary belief, not to zero.** A band that has gone quiet
must never become worthless. If it could, a pop-up threat in an abandoned band would be
undetectable by construction -- which is the failure the problem statement complains about when it
says open loop may lose time "by not giving time to new or threatening ones".
"""

from __future__ import annotations

import numpy as np

# Below this, a probability is treated as zero for the purpose of guarding a division. Chosen well
# under any Pfa a real receiver would be configured with.
_EPS = 1e-15


def _binary_entropy(p: np.ndarray) -> np.ndarray:
    """Shannon entropy of a Bernoulli, in nats, with the 0 log 0 = 0 convention."""
    p = np.clip(np.asarray(p, dtype=np.float64), 0.0, 1.0)
    q = 1.0 - p
    out = np.zeros_like(p)
    lo = p > _EPS
    hi = q > _EPS
    out[lo] -= p[lo] * np.log(p[lo])
    out[hi] -= q[hi] * np.log(q[hi])
    return out


class OccupancyBelief:
    """Belief that each band is occupied now, tracked through a two-state chain.

    ``p01`` is the idle-to-active transition probability per slot and ``p10`` the reverse. Both
    default to a per-band array so a learned kernel (``ml/belief/kernel_learning.py``) can replace
    the scalar prior without changing any caller.
    """

    def __init__(
        self,
        num_bands: int,
        p01: float | np.ndarray = 0.05,
        p10: float | np.ndarray = 0.05,
        prior: np.ndarray | float | None = None,
    ) -> None:
        if num_bands < 1:
            raise ValueError(f"num_bands must be at least 1, got {num_bands}")

        self.num_bands = int(num_bands)
        self.p01 = self._as_band_array(p01, "p01")
        self.p10 = self._as_band_array(p10, "p10")

        if prior is None:
            prior = self.stationary
        self.belief = np.clip(
            np.broadcast_to(np.asarray(prior, dtype=np.float64), (self.num_bands,)).copy(),
            0.0,
            1.0,
        )

    def _as_band_array(self, value, name: str) -> np.ndarray:
        arr = np.broadcast_to(
            np.asarray(value, dtype=np.float64), (self.num_bands,)
        ).astype(np.float64)
        if np.any(arr < 0.0) or np.any(arr > 1.0):
            raise ValueError(f"{name} must lie in [0, 1], got {value!r}")
        return arr.copy()

    # -- structure ---------------------------------------------------------------------------

    @property
    def stationary(self) -> np.ndarray:
        """Long-run occupancy of each band, the value belief drifts to with no observations."""
        total = self.p01 + self.p10
        return np.where(total > _EPS, self.p01 / np.where(total > _EPS, total, 1.0), 0.0)

    # -- drift -------------------------------------------------------------------------------

    def predict(self) -> None:
        """Advance every band's belief one slot with no new evidence."""
        self.belief = self.belief * (1.0 - self.p10) + (1.0 - self.belief) * self.p01

    # -- correction --------------------------------------------------------------------------

    def correct(
        self,
        bands,
        detections,
        p_d: float | np.ndarray,
        p_fa: float | np.ndarray,
    ) -> None:
        """Fold one dwell's outcomes into the belief for the scanned bands only.

        ``p_d`` and ``p_fa`` are either scalars or arrays aligned with ``bands``, so a dwell
        covering a loud band and a quiet one updates each with its own detection probability.
        """
        bands = np.asarray(bands, dtype=np.int64)
        if bands.size == 0:
            return
        detections = np.asarray(detections, dtype=bool)
        if detections.shape != bands.shape:
            raise ValueError("detections must have the same shape as bands")

        pd = np.broadcast_to(np.asarray(p_d, dtype=np.float64), bands.shape)
        pfa = np.broadcast_to(np.asarray(p_fa, dtype=np.float64), bands.shape)

        omega = self.belief[bands]
        # Likelihood of the observation under each hypothesis.
        like_active = np.where(detections, pd, 1.0 - pd)
        like_idle = np.where(detections, pfa, 1.0 - pfa)

        numer = omega * like_active
        denom = numer + (1.0 - omega) * like_idle
        # An observation with zero probability under both hypotheses carries no usable
        # information; leave the belief where it was rather than producing a NaN.
        self.belief[bands] = np.where(denom > _EPS, numer / np.maximum(denom, _EPS), omega)

    # -- derived quantities the index consumes ------------------------------------------------

    def entropy(self) -> np.ndarray:
        """Current uncertainty per band, in nats."""
        return _binary_entropy(self.belief)

    def information_gain(
        self, p_d: float | np.ndarray, p_fa: float | np.ndarray
    ) -> np.ndarray:
        """Expected entropy reduction from looking at each band once.

        This is the exploration term of the index. It replaces epsilon-greedy with something that
        pays for a look in proportion to what the look would actually teach: it is zero when the
        sensor cannot distinguish the hypotheses (``P_d == P_fa``), zero when the belief is
        already certain, and largest at even odds with a good sensor.
        """
        omega = self.belief
        pd = np.broadcast_to(np.asarray(p_d, dtype=np.float64), omega.shape)
        pfa = np.broadcast_to(np.asarray(p_fa, dtype=np.float64), omega.shape)

        p_detect = omega * pd + (1.0 - omega) * pfa
        p_miss = 1.0 - p_detect

        post_detect = np.where(
            p_detect > _EPS, omega * pd / np.maximum(p_detect, _EPS), omega
        )
        post_miss = np.where(
            p_miss > _EPS, omega * (1.0 - pd) / np.maximum(p_miss, _EPS), omega
        )

        expected = p_detect * _binary_entropy(post_detect) + p_miss * _binary_entropy(post_miss)
        # Bayes guarantees non-negativity; clip only to absorb floating-point noise.
        return np.maximum(_binary_entropy(omega) - expected, 0.0)
