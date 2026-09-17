"""Synchronisation guard and golden-ratio dithering (SCT solution spec Section 6).

The failure mode open loop cannot detect in itself. With period ratio ``alpha = revisit / period``,
normalised relative phase ``beta`` and tolerance ``epsilon = (tau_ill + dwell - 2d) / period``, an
intercept requires integers p, q with

    | q*alpha - p + beta |  <=  epsilon / 2

When alpha is rational with a small denominator and epsilon is small, there are values of beta for
which no such pair exists. Intercept time is infinite. The receiver sweeps flawlessly, reports a
Pd of zero, and looks exactly like a receiver watching an empty band. Clarkson's own worked
example has an emitter invisible to a 1 s sweep until the dwell in its band is raised past 400 ms.

**The exact test.** Rather than approximating with continued fractions, use the three-distance
theorem directly. Over n looks the points ``{q*alpha}`` partition the phase circle into gaps
taking at most three distinct lengths. Every relative phase is covered exactly once the largest
gap has fallen below ``epsilon``. So "largest gap after n looks" is not a proxy for worst-case
intercept time; it *is* worst-case intercept time, and :func:`looks_to_intercept` reads it off.

**Two escapes.**

1. Extend the dwell until ``epsilon`` exceeds the gap the ratio converges to
   (:func:`dwell_to_break_sync`). Take this route on a high-threat band where the time is
   affordable.
2. Dither the revisit interval with a golden-ratio Kronecker sequence
   (:func:`dithered_interval`). The golden ratio is chosen for three stacking reasons: it is
   irrational, so the lockout has measure zero; by the three-distance theorem its phase coverage
   has at most three distinct gap lengths at *every* prefix length, so no clumping; and its
   continued fraction is all ones, making it the real number worst approximable by rationals,
   hence furthest from every lockout condition at once. It is also deterministic, which a
   pseudorandom dither is not, and this project's reproducibility rests on that.
"""

from __future__ import annotations

import math
from typing import Iterable, Mapping, Sequence

# Conjugate of the golden ratio, (sqrt(5) - 1) / 2. Continued fraction [0; 1, 1, 1, ...].
GOLDEN = (math.sqrt(5.0) - 1.0) / 2.0

# Absolute slack when comparing a gap against a tolerance. Both sides are computed from the same
# floating-point quantities, so exact equality must be treated as "covered" rather than "locked
# out" -- otherwise the dwell that :func:`dwell_to_break_sync` prescribes fails its own check.
_TOL = 1e-12

# Gaps are rounded to this many decimals before being counted as distinct, so floating-point noise
# does not turn the three gap lengths of the theorem into n of them.
_GAP_DECIMALS = 9


def _phase_gaps(alpha: float, n_looks: int) -> list[float]:
    """Gap lengths between consecutive phases visited in ``n_looks`` looks."""
    if n_looks < 1:
        raise ValueError(f"n_looks must be at least 1, got {n_looks}")
    points = sorted(((q * alpha) % 1.0) for q in range(n_looks))
    gaps = [b - a for a, b in zip(points, points[1:])]
    gaps.append(1.0 - points[-1] + points[0])
    return gaps


def max_phase_gap(alpha: float, n_looks: int, return_distinct: bool = False):
    """Largest uncovered stretch of emitter phase after ``n_looks`` looks.

    With ``return_distinct`` set, returns the set of distinct gap lengths instead, which the
    three-distance theorem says has at most three members.
    """
    gaps = _phase_gaps(alpha, n_looks)
    if return_distinct:
        return {round(g, _GAP_DECIMALS) for g in gaps if g > 10.0 ** -_GAP_DECIMALS}
    return max(gaps)


def looks_to_intercept(alpha: float, epsilon: float, max_looks: int = 2000) -> int | None:
    """Worst-case number of looks before every relative phase has been covered.

    ``None`` means the schedule is synchronised: the gap never falls below the tolerance within
    the horizon, so some relative phases are never intercepted.
    """
    if epsilon <= 0.0:
        return None
    if max_phase_gap(alpha, max_looks) > epsilon + _TOL:
        return None
    # The largest gap is non-increasing in the number of looks, so the smallest sufficient n can
    # be bisected rather than scanned.
    lo, hi = 1, max_looks
    while lo < hi:
        mid = (lo + hi) // 2
        if max_phase_gap(alpha, mid) <= epsilon + _TOL:
            hi = mid
        else:
            lo = mid + 1
    return lo


def is_synchronised(alpha: float, epsilon: float, max_looks: int = 2000) -> bool:
    """True when this revisit interval can never intercept this emitter at some relative phase."""
    return looks_to_intercept(alpha, epsilon, max_looks) is None


def dwell_to_break_sync(
    period_s: float,
    revisit_s: float,
    tau_ill_s: float,
    min_coincidence_s: float = 0.0,
    max_looks: int = 2000,
) -> float:
    """Extra dwell needed so the tolerance exceeds the gap this ratio converges to.

    Returns zero when there is no lockout to break. The ``2 * min_coincidence_s`` term is
    Clarkson's ``2d``: a coincidence has to last long enough to be *usable*, not merely to occur,
    so the pulses needed for identification are charged against the tolerance.
    """
    if period_s <= 0.0:
        raise ValueError(f"period_s must be positive, got {period_s}")
    gap = max_phase_gap(revisit_s / period_s, max_looks)
    needed = gap * period_s - tau_ill_s + 2.0 * min_coincidence_s
    return max(0.0, needed)


# -- golden-ratio dithering -----------------------------------------------------------------------

def golden_phase(n: int) -> float:
    """The n-th point of the golden Kronecker sequence, ``frac(n * GOLDEN)``."""
    return (n * GOLDEN) % 1.0


def dithered_interval(base_s: float, n: int, eta: float = 0.15) -> float:
    """The n-th revisit interval, dithered around ``base_s`` by a fraction ``eta``.

    Deterministic in ``n``, so a run replays identically from a seed, while the arrival times are
    aperiodic and unpredictable to an adversary watching our schedule.

    **This does not break a lockout, and must not be used as if it did.** The partial sums of a
    centred low-discrepancy sequence stay O(log n), so the accumulated timing perturbation never
    reaches a full emitter period and the receiver keeps landing near the same few phases.
    Breaking a lockout means moving the *ratio*, which is :func:`golden_revisit`.
    ``tests/test_sync_guard.py`` pins this negative result down so it is not quietly "fixed" back.
    """
    if base_s <= 0.0:
        raise ValueError(f"base_s must be positive, got {base_s}")
    if not 0.0 <= eta < 2.0:
        raise ValueError(f"eta must lie in [0, 2), got {eta}")
    return base_s * (1.0 + eta * (golden_phase(n) - 0.5))


def golden_revisit(
    target_s: float, period_s: float, max_s: float | None = None
) -> float:
    """Revisit interval closest to ``target_s`` whose period ratio is a noble number.

    A *noble* number is one whose continued fraction ends in all ones -- the golden ratio and
    everything reachable from it. These are the reals worst approximable by rationals, so they sit
    as far as it is possible to sit from every synchronisation condition at once, and the phases
    they visit are the golden Kronecker sequence with its optimal three-gap spacing.

    Two families are searched, covering both regimes:

    * ``R = T * (m + f)`` when the revisit is comparable to or longer than the emitter period, and
    * ``R = T / (m + f)`` when it is much shorter, which is the usual case for a fast sweep
      against a slow search radar,

    with ``f`` either the golden ratio or its reflection, both of which give identical coverage.

    ``max_s`` is the band's revisit deadline. It is a hard cap: the coverage guarantee outranks the
    lockout fix, and a revisit past the deadline is not a fix. If no noble ratio fits under the
    cap, the target is returned clamped, and the caller's risk check will still see the lockout.
    """
    if period_s <= 0.0:
        raise ValueError(f"period_s must be positive, got {period_s}")
    if target_s <= 0.0:
        raise ValueError(f"target_s must be positive, got {target_s}")

    cap = float(max_s) if max_s is not None else math.inf
    candidates: list[float] = []

    for f in (GOLDEN, 1.0 - GOLDEN):
        # Family A: revisit is a noble multiple of the emitter period.
        near_a = int(round(target_s / period_s - f))
        bound_a = int(math.floor(cap / period_s - f)) if math.isfinite(cap) else near_a
        for m in {near_a + d for d in range(-3, 4)} | {bound_a}:
            if m < 0:
                continue
            r = period_s * (m + f)
            if 0.0 < r <= cap:
                candidates.append(r)

        # Family B: emitter period is a noble multiple of the revisit.
        near_b = int(round(period_s / target_s - f))
        bound_b = int(math.ceil(period_s / cap - f)) if cap > 0.0 and math.isfinite(cap) else near_b
        for m in {near_b + d for d in range(-3, 4)} | {bound_b}:
            if m + f <= 0.0:
                continue
            r = period_s / (m + f)
            if 0.0 < r <= cap:
                candidates.append(r)

    if not candidates:
        return min(target_s, cap)
    # Ties break toward the shorter interval: it spends less of the deadline budget.
    return min(candidates, key=lambda r: (abs(r - target_s), r))


# -- risk over a period posterior -------------------------------------------------------------

def sync_risk(
    revisit_s: float,
    dwell_s: float,
    modes: Sequence[Mapping[str, float]] | Iterable[Mapping[str, float]],
    min_coincidence_s: float = 0.0,
    max_looks: int = 2000,
) -> float:
    """Posterior weight sitting on period hypotheses this revisit interval cannot intercept.

    ``modes`` are the top candidate periods from Ai-ml-2, each ``{period, tau_ill, weight}``. The
    posterior is used rather than a point estimate because after a handful of intercepts a period
    and its halves are genuinely confusable, and a scheduler that commits to the argmax will
    happily lock itself out against the runner-up.
    """
    modes = list(modes)
    if not modes:
        return 0.0

    total = sum(float(m["weight"]) for m in modes)
    if total <= 0.0:
        return 0.0

    at_risk = 0.0
    for mode in modes:
        period = float(mode["period"])
        if period <= 0.0:
            continue
        tau = float(mode.get("tau_ill", 0.0))
        epsilon = (tau + dwell_s - 2.0 * min_coincidence_s) / period
        if is_synchronised(revisit_s / period, epsilon, max_looks):
            at_risk += float(mode["weight"])
    return at_risk / total
