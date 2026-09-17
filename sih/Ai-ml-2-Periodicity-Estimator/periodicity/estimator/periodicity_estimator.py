"""Periodicity estimation from sparse detection timestamps (Ai-ml-2 Levels 4, 5, 7).

## Why not just take the median inter-arrival

That is the obvious approach and it does not work here, for a reason specific to this system:
**we do not observe the emitter, we observe our own detections of it.** The receiver has to be
tuned to a band to detect anything, and it is tuned elsewhere most of the time. So a periodic
emitter with period 20 does not produce inter-arrival gaps of 20 -- it produces gaps of 20, 40,
60, 100, whichever activations the scan schedule happened to catch. The median of that is not
the period, and it drifts with the scheduler's behaviour rather than the emitter's.

## What is used instead: phase concentration

Fold every timestamp onto a candidate period P and look at where the detections land within the
cycle:

    phase(t) = 2*pi * (t mod P) / P

If P is the true period, every detection lands at roughly the same phase, however many cycles
were skipped in between -- gaps of 20 and 60 fold to the same place. If P is wrong, the phases
scatter around the circle. The concentration is measured by the **mean resultant length**

    R = | mean( exp(i * phase) ) |        R = 0 scattered, R = 1 perfectly aligned

This is the standard treatment for period-finding in sparse, irregularly-sampled event series,
and it is exactly the shape of data the contract hands us. It is also cheap: a vectorised sweep
over a period grid, no iteration, no training.

## Subharmonics

Every divisor of the true period scores as well as the period itself: if detections sit at
0, 20, 40, then P = 10 and P = 5 also fold them all to phase 0. So among candidates that score
within a whisker of the best, the **largest** is chosen. Doubling, by contrast, breaks
concentration (0, 20, 40 folded on P = 40 gives phases 0, 0.5, 0), so there is no matching risk
at the top end.

The residual bias is toward *over*-estimating when detections are very sparse: given only
0, 40, 80 from a period-20 emitter, 40 is genuinely the best-supported hypothesis and 40 is what
gets reported. That is the safe direction to be wrong in -- the predicted window still contains a
real activation, it just does not enumerate all of them.

## Confidence

Not a hand-tuned formula: the Rayleigh test for circular uniformity. It asks how unlikely this
much concentration would be if the detections were scattered at random, and it accounts for the
sample count directly -- three detections landing near each other is not evidence, thirty is.

    confidence = 1 - p_rayleigh

so a random emitter (phases uniform) and a barely-observed one both land near zero, which is what
Level 7 requires: no confident-but-wrong periodicity claims on the four non-periodic classes.

## One activation is one sample

The Rayleigh test assumes independent observations, and raw detection timestamps are not
independent: a receiver dwelling on an active band reports the same burst several steps running,
and those are one activation observed repeatedly. Feeding all of them in as separate samples
inflates the evidence enormously -- a bursty (intermittent) emitter with ten bursts but forty
detections was scoring above 95% confidence, exactly the false periodic claim Level 7 forbids.

So detections closer together than ``min_period`` are collapsed into a single activation, timed
at the first detection in the group. This is self-consistent rather than arbitrary: the estimator
will not report a period shorter than ``min_period``, so on its own terms two detections closer
than that *cannot* be separate cycles.

## Known limitation: scan-schedule aliasing

We see detections, which are the product of emitter activity *and* the scan schedule. A perfectly
regular scanner revisiting a band every 8 steps can imprint its own period on the timestamps.
``min_period`` in the config exists to keep the shortest, most degenerate aliases out (a period of
1 fits any data at all). It is not a complete defence, and the honest mitigation is that the
scheduler this feeds is adaptive rather than fixed-cadence. If the contract ever carries
scanned-but-empty observations as well as detections, that would remove the ambiguity properly.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, asdict
from typing import Sequence

import numpy as np

from periodicity.config import EstimatorConfig

# A harmonic multiple scoring within this fraction of the best is treated as tied, and the
# largest tied multiple wins -- see "Subharmonics" above. Kept tight on purpose: true divisors
# score *identically* (up to floating point), so anything needing real slack is not a divisor,
# it is a different and worse period.
TIE_TOLERANCE = 0.995


@dataclass(frozen=True)
class PeriodEstimate:
    """The fitted period for one band, or an explicit "no claim"."""

    period: float | None
    confidence: float
    phase: float
    """Mean phase of the observed detections within the cycle, in [0, 1)."""
    reference_time: float | None
    """A concrete time at which the emitter was, by the fit, at phase 0."""
    resultant_length: float
    """Rayleigh R: how tightly the detections cluster once folded. Diagnostic."""
    samples: int
    span: float
    reason: str = ""
    """Why there is no usable estimate, when there is not."""

    @property
    def usable(self) -> bool:
        return self.period is not None and self.period > 0

    def as_dict(self) -> dict:
        return asdict(self)


def _no_estimate(reason: str, samples: int, span: float = 0.0) -> PeriodEstimate:
    return PeriodEstimate(
        period=None, confidence=0.0, phase=0.0, reference_time=None,
        resultant_length=0.0, samples=samples, span=span, reason=reason,
    )


def rayleigh_p(n: int, r: float) -> float:
    """p-value of the Rayleigh test of circular uniformity, for ONE pre-specified period.

    Uses the Wilkie approximation, which stays accurate at the small sample counts this service
    actually runs at -- the asymptotic ``exp(-n R^2)`` is too generous below about 15 detections,
    and being generous here means claiming periodicity that is not there.
    """
    if n < 2:
        return 1.0
    r = min(1.0, max(0.0, float(r)))
    return float(
        min(1.0, max(0.0,
            math.exp(math.sqrt(1.0 + 4.0 * n + 4.0 * (n * n) * (1.0 - r * r)) - (1.0 + 2.0 * n))
        ))
    )


def independent_trials(span: float, min_period: float, max_period: float) -> float:
    """How many *independent* periods the search effectively tried.

    Candidate periods on a fine grid are not independent -- neighbouring ones fold the data
    almost identically. The number that actually matters is set by the frequency resolution a
    baseline of ``span`` can resolve, which is 1/span. So the count is the width of the searched
    frequency range in units of that resolution.
    """
    if span <= 0 or max_period <= min_period:
        return 1.0
    freq_range = (1.0 / min_period) - (1.0 / max_period)
    return max(1.0, span * freq_range)


def rayleigh_confidence(n: int, r: float, trials: float = 1.0) -> float:
    """Confidence that this concentration is real, corrected for the look-elsewhere effect.

    This is the correction that makes Level 7 work. The estimator does not test one period, it
    sweeps a few thousand and keeps the best -- and the best of many draws from noise looks
    impressive on its own terms. Scoring the winner with a single-trial p-value rated a purely
    random emitter at 0.99 confidence, which is precisely the confident-but-wrong claim Level 7
    forbids. Correcting for the number of independent trials drops the same emitter below the
    documented low-confidence threshold, while a genuinely periodic one is unaffected: its
    p-value is small enough that a few hundred trials cannot rescue it.
    """
    p_single = rayleigh_p(n, r)
    trials = max(1.0, float(trials))
    # 1 - (1 - p)^trials, computed via expm1/log1p so it stays exact for tiny p.
    p_global = -math.expm1(trials * math.log1p(-min(p_single, 1.0 - 1e-15)))
    return float(min(1.0, max(0.0, 1.0 - p_global)))


def cluster_activations(timestamps: np.ndarray, gap: float) -> np.ndarray:
    """Collapse runs of detections closer than ``gap`` into one activation each.

    Returns the first timestamp of each group -- the moment the activation was first seen, which
    is the quantity a period actually describes.
    """
    if timestamps.size == 0:
        return timestamps
    breaks = np.flatnonzero(np.diff(timestamps) > gap) + 1
    starts = np.concatenate(([0], breaks))
    return timestamps[starts]


def _resultant(timestamps: np.ndarray, periods: np.ndarray) -> np.ndarray:
    """Mean resultant length of the folded phases, for each candidate period. Vectorised."""
    # (n_periods, n_timestamps)
    phases = 2.0 * np.pi * (np.mod(timestamps[None, :], periods[:, None]) / periods[:, None])
    cos_mean = np.cos(phases).mean(axis=1)
    sin_mean = np.sin(phases).mean(axis=1)
    return np.hypot(cos_mean, sin_mean)


def _mean_phase(timestamps: np.ndarray, period: float) -> tuple[float, float]:
    """Mean phase in [0, 1) and the resultant length, for one period."""
    phases = 2.0 * np.pi * (np.mod(timestamps, period) / period)
    c, s = np.cos(phases).mean(), np.sin(phases).mean()
    angle = math.atan2(s, c) % (2.0 * math.pi)
    return angle / (2.0 * math.pi), float(math.hypot(c, s))


def _prefer_fundamental(ts: np.ndarray, period: float, upper: float) -> float:
    """Return the largest integer multiple of ``period`` that folds the data as tightly."""
    base_r = _mean_phase(ts, period)[1]
    best = period
    k = 2
    while period * k <= upper:
        candidate = period * k
        if _mean_phase(ts, candidate)[1] >= TIE_TOLERANCE * base_r:
            best = candidate
        k += 1
    return best


def estimate_period(
    timestamps: Sequence[float], config: EstimatorConfig | None = None
) -> PeriodEstimate:
    """Fit a period to one band's detection history."""
    cfg = config or EstimatorConfig()
    raw = np.unique(np.asarray(list(timestamps), dtype=np.float64))
    detections = int(raw.size)

    # One activation is one sample -- see the module docstring.
    ts = cluster_activations(raw, cfg.min_period)
    n = int(ts.size)

    if n < cfg.min_samples:
        return _no_estimate(
            f"need >= {cfg.min_samples} distinct activations, have {n} "
            f"(from {detections} detections)",
            n,
        )

    span = float(ts[-1] - ts[0])
    if span <= 0:
        return _no_estimate("all detections share one timestamp", n)

    # A period longer than span / min_cycles_observed has not been seen to repeat: it is one gap,
    # not evidence of a cycle.
    upper = min(cfg.max_period, span / cfg.min_cycles_observed)
    if upper <= cfg.min_period:
        return _no_estimate(
            f"observation span {span:.1f} too short to support a period >= {cfg.min_period}",
            n, span,
        )

    grid = np.arange(cfg.min_period, upper + cfg.period_resolution, cfg.period_resolution)
    if grid.size == 0:
        return _no_estimate("empty period search grid", n, span)

    scores = _resultant(ts, grid)
    period = float(grid[int(np.argmax(scores))])

    # Local refinement around the winner, finer than the coarse grid.
    fine_step = cfg.period_resolution / 10.0
    fine = np.arange(
        max(cfg.min_period, period - cfg.period_resolution),
        min(upper, period + cfg.period_resolution) + fine_step,
        fine_step,
    )
    if fine.size:
        fine_scores = _resultant(ts, fine)
        period = float(fine[int(np.argmax(fine_scores))])

    # Climb the harmonic ladder: if an integer multiple of the winner folds the data just as
    # tightly, the winner was a divisor of the real period. Only multiples are considered --
    # searching arbitrary nearby periods for a "tie" lets a slightly worse period win instead.
    period = _prefer_fundamental(ts, period, upper)

    phase, r = _mean_phase(ts, period)
    # Period and phase are both fitted from these same activations, so two degrees of freedom
    # are already spent before the concentration is scored.
    confidence = rayleigh_confidence(
        max(2, n - 2), r, independent_trials(span, cfg.min_period, upper)
    )

    # Anchor: a concrete time at which the emitter was at phase 0, taken near the most recent
    # detection so the forward prediction extrapolates the shortest distance.
    reference = float(ts[-1] - (np.mod(ts[-1], period) - phase * period))

    return PeriodEstimate(
        period=period,
        confidence=confidence,
        phase=float(phase),
        reference_time=reference,
        resultant_length=float(r),
        samples=n,
        span=span,
    )


def estimate_period_with_misses(
    observations: Sequence[tuple[float, bool]], config: EstimatorConfig | None = None
) -> PeriodEstimate:
    """Fit (period, phase, duty) to one band's full scan record -- hits and misses alike.

    Solution spec Section 3.2. ``estimate_period`` above only ever sees detection timestamps,
    so a band watched for one cycle can never reach ``min_samples`` distinct activations. A miss
    is informative on its own terms: a look that found nothing at time t rules out every
    (T, phi, u) hypothesis that predicted illumination there. Scoring every candidate against
    the *whole* record, hits and misses together, is what lets one clean cycle -- a couple of
    hits and the rest misses -- produce a confident estimate the hits-only method cannot.

    Grid search over T in [min_period, upper], phase in [0, 1), duty in ``config.duty_candidates``
    (adapted here to this simulator's step-based timeline; the spec's own grid was specified in
    real seconds for an RF receiver). Posterior over T marginalises phase and duty out with a
    uniform prior via log-sum-exp, then normalises across the T grid -- so confidence is a
    genuine "probability mass on this period among the hypotheses considered", not a rescaled
    likelihood ratio.

    P_d/P_fa are not carried per-simulation by the contract yet; ``config.detect_p_d`` /
    ``detect_p_fa`` default to the values the reference scenario's receiver model implies (the
    same derivation Ai-ml-1's ``IndexAgent.from_scenario`` uses), which is the documented scope
    limit -- see the periodicity-fix-plan artifact.
    """
    cfg = config or EstimatorConfig()
    obs = sorted(observations, key=lambda o: o[0])
    n = len(obs)
    if n == 0:
        return _no_estimate("no observations", 0)

    times = np.array([t for t, _ in obs], dtype=np.float64)
    hit = np.array([bool(z) for _, z in obs])
    n_hits = int(hit.sum())

    if n_hits == 0:
        return _no_estimate(f"no detections among {n} observations", n)

    span = float(times[-1] - times[0])
    if span <= 0:
        return _no_estimate("all observations share one timestamp", n)

    upper = min(cfg.max_period, span / cfg.min_cycles_observed)
    if upper <= cfg.min_period:
        return _no_estimate(
            f"observation span {span:.1f} too short to support a period >= {cfg.min_period}",
            n, span,
        )

    # T needs a genuinely fine grid, not one sized to "independent" resolution: a candidate a
    # fraction of a step off the truth drifts out of phase over dozens of repeated cycles and
    # can score *worse* than no periodicity at all (a coarse ~2.5-step grid missed period 37
    # over a 2000-step span entirely, losing to the degenerate "always predict quiet" fit at
    # T=3, by a wide margin -- this is not a hypothetical). Reuse estimate_period's own
    # min_period..upper sweep at period_resolution for the same reason it uses that resolution.
    # The phase and duty axes are cheaper to search coarsely and refine after, so this is kept
    # to ``phase_grid_points`` and the small ``duty_candidates`` set to bound the cost of the
    # full (T, phase, duty) evaluation, which is not free the way estimate_period's pure
    # circular-mean sweep is -- an explicit illuminated-window indicator does not admit the same
    # trick.
    periods = np.arange(cfg.min_period, upper + cfg.period_resolution, cfg.period_resolution)
    phases = np.linspace(0.0, 1.0, cfg.phase_grid_points, endpoint=False)  # (F,)
    duties = np.asarray(cfg.duty_candidates, dtype=np.float64)
    n_period_points = int(periods.size)

    p_d = min(1.0 - 1e-9, max(1e-9, cfg.detect_p_d))
    p_fa = min(1.0 - 1e-9, max(1e-9, cfg.detect_p_fa))
    log_pd, log_1mpfa = math.log(p_d), math.log(1.0 - p_fa)
    log_pfa, log_1mpd = math.log(p_fa), math.log(1.0 - p_d)

    # frac[T, k]: where timestamp k falls within candidate period T, as a fraction of the cycle.
    frac = np.mod(times[None, :], periods[:, None]) / periods[:, None]  # (P, N)
    # rel[T, F, k]: same, relative to candidate phase F. Broadcasts to (P, F, N).
    rel = np.mod(frac[:, None, :] - phases[None, :, None], 1.0)

    best_per_T = np.full(n_period_points, -np.inf)
    best_fi_per_T = np.zeros(n_period_points, dtype=int)
    best_ui_per_T = np.zeros(n_period_points, dtype=int)
    logZ_per_T = np.full(n_period_points, -np.inf)  # log-sum-exp over (phase, duty) per T

    for ui, u in enumerate(duties):
        illuminated = rel < u  # w_k(T, phi, u), (P, F, N)
        ll_if_hit = np.where(illuminated, log_pd, log_pfa)
        ll_if_miss = np.where(illuminated, log_1mpd, log_1mpfa)
        ll = np.where(hit[None, None, :], ll_if_hit, ll_if_miss).sum(axis=2)  # (P, F)

        fi = np.argmax(ll, axis=1)
        best_this_u = ll[np.arange(n_period_points), fi]
        better = best_this_u > best_per_T
        best_per_T = np.where(better, best_this_u, best_per_T)
        best_fi_per_T = np.where(better, fi, best_fi_per_T)
        best_ui_per_T = np.where(better, ui, best_ui_per_T)

        row_max = ll.max(axis=1)
        row_logZ = row_max + np.log(np.exp(ll - row_max[:, None]).sum(axis=1))
        combined_max = np.maximum(logZ_per_T, row_logZ)
        logZ_per_T = combined_max + np.log(
            np.exp(logZ_per_T - combined_max) + np.exp(row_logZ - combined_max)
        )

    winner = int(np.argmax(best_per_T))
    period = float(periods[winner])
    phase = float(phases[int(best_fi_per_T[winner])])
    duty = float(duties[int(best_ui_per_T[winner])])

    # Posterior P(T | data): the log-sum-exp of every (phase, duty) evaluated for that T (a
    # uniform prior over both), binned down to how many *independent* periods this span can
    # actually distinguish -- see independent_trials's own docstring on the look-elsewhere
    # effect. Without the binning, a fine T grid packs many near-duplicate candidates around
    # the true period that would otherwise split its own posterior mass and understate
    # confidence in a winner the data actually pins down tightly.
    n_bins = int(min(n_period_points, max(1, round(independent_trials(span, cfg.min_period, upper)))))
    bin_of = np.minimum(n_bins - 1, ((periods - cfg.min_period) / (upper - cfg.min_period + 1e-12) * n_bins).astype(int))
    bin_logZ = np.full(n_bins, -np.inf)
    for b in range(n_bins):
        mask = bin_of == b
        if not mask.any():
            continue
        m = logZ_per_T[mask].max()
        bin_logZ[b] = m + np.log(np.exp(logZ_per_T[mask] - m).sum())
    grand_max = bin_logZ.max()
    posterior_bins = np.exp(bin_logZ - grand_max)
    posterior_bins /= posterior_bins.sum()
    confidence = float(posterior_bins[bin_of[winner]])

    # Local phase refinement only -- T is already on a fine grid above; phase benefits from one
    # more level, same coarse-then-fine pattern estimate_period uses.
    fine_phi = np.linspace(0.0, 1.0, 4 * cfg.phase_grid_points, endpoint=False)
    fine_frac = np.mod(times, period) / period  # (N,)
    fine_rel = np.mod(fine_frac[None, :] - fine_phi[:, None], 1.0)  # (F', N)
    fine_illum = fine_rel < duty
    fine_ll = np.where(
        hit[None, :], np.where(fine_illum, log_pd, log_pfa), np.where(fine_illum, log_1mpd, log_1mpfa)
    ).sum(axis=1)  # (F',)
    phase = float(fine_phi[int(np.argmax(fine_ll))])

    # Diagnostic resultant length for prediction.py's window-width formula: how tightly the
    # actual detections (not the misses) cluster once folded onto the fitted period, so the
    # geometry downstream stays meaningful regardless of which estimator produced the fit.
    hit_times = times[hit]
    _, r = _mean_phase(hit_times, period) if hit_times.size else (0.0, 0.0)

    reference = float(times[-1] - (np.mod(times[-1], period) - phase * period))

    return PeriodEstimate(
        period=period,
        confidence=confidence,
        phase=phase,
        reference_time=reference,
        resultant_length=float(r),
        samples=n_hits,
        span=span,
    )
