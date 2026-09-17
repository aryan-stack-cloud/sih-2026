"""Synchronisation guard (SCT solution spec Section 6).

The failure open loop cannot see. With period ratio ``alpha`` and tolerance ``epsilon``, an
intercept needs integers p, q with ``|q*alpha - p + beta| <= epsilon/2``. When alpha is rational
with a small denominator and epsilon is small, there are relative phases for which no such pair
exists: a working receiver sweeps forever past a working emitter and never sees it, while
reporting a clean sweep and a Pd of zero, indistinguishable from an empty band.

The exact criterion comes from the three-distance theorem. Over n looks the points {q*alpha}
partition the circle into gaps taking at most three distinct lengths, and every relative phase is
covered once the largest gap has shrunk below epsilon. So "largest gap after n looks" *is* the
worst-case intercept time, computed directly rather than approximated.
"""

from __future__ import annotations

import math

import pytest

from ml.scheduling.sync_guard import (
    GOLDEN,
    dithered_interval,
    dwell_to_break_sync,
    golden_phase,
    golden_revisit,
    is_synchronised,
    looks_to_intercept,
    max_phase_gap,
    sync_risk,
)


# -- the three-distance theorem, which the rest is built on --------------------------------------

def test_gaps_take_at_most_three_distinct_lengths():
    """Three-distance theorem. It holds for every alpha and every n, not special values."""
    for alpha in (GOLDEN, 0.2718, 1.0 / math.pi, 0.61):
        for n in (5, 9, 17, 40):
            assert len(max_phase_gap(alpha, n, return_distinct=True)) <= 3


def test_the_largest_gap_shrinks_as_looks_accumulate():
    a = max_phase_gap(GOLDEN, 5)
    b = max_phase_gap(GOLDEN, 20)
    c = max_phase_gap(GOLDEN, 80)
    assert a > b > c


def test_a_rational_ratio_stops_shrinking_at_its_denominator():
    """alpha = 2/21 reaches a gap of 1/21 and never improves, however long you look."""
    assert max_phase_gap(2 / 21, 21) == pytest.approx(1 / 21, abs=1e-9)
    assert max_phase_gap(2 / 21, 2000) == pytest.approx(1 / 21, abs=1e-9)


def test_a_half_period_receiver_only_ever_sees_two_phases():
    assert max_phase_gap(0.5, 2) == pytest.approx(0.5)
    assert max_phase_gap(0.5, 1000) == pytest.approx(0.5)


# -- the lockout -------------------------------------------------------------------------------

def test_clarksons_trap_is_flagged_when_the_tolerance_is_too_small():
    """alpha = 2/21 with epsilon below 1/21 can never coincide, for some relative phases."""
    assert is_synchronised(alpha=2 / 21, epsilon=0.040, max_looks=500)


def test_widening_the_tolerance_past_the_gap_clears_the_lockout():
    assert not is_synchronised(alpha=2 / 21, epsilon=0.050, max_looks=500)


def test_an_exact_half_ratio_is_locked_out_for_any_realistic_tolerance():
    assert is_synchronised(alpha=0.5, epsilon=0.05, max_looks=10_000)


def test_the_golden_ratio_is_never_locked_out_merely_slow():
    """Irrational alpha always gets there. The question is only how many looks it takes."""
    assert not is_synchronised(alpha=GOLDEN, epsilon=0.001, max_looks=5000)


def test_looks_to_intercept_finds_the_denominator_of_a_rational_ratio():
    assert looks_to_intercept(alpha=2 / 21, epsilon=0.050, max_looks=500) == 21


def test_looks_to_intercept_is_none_when_locked_out():
    assert looks_to_intercept(alpha=2 / 21, epsilon=0.040, max_looks=500) is None


def test_a_wider_tolerance_never_needs_more_looks():
    narrow = looks_to_intercept(GOLDEN, epsilon=0.01, max_looks=5000)
    wide = looks_to_intercept(GOLDEN, epsilon=0.05, max_looks=5000)
    assert wide <= narrow


# -- escape 1: extend the dwell ------------------------------------------------------------------

def test_dwell_needed_to_break_a_lockout_matches_the_hand_derivation():
    """T = 10.5 s, 1 s revisit, 273.6 ms illumination. Gap is 1/21, so the dwell must reach
    (1/21)*10.5 - 0.2736 = 226.4 ms."""
    need = dwell_to_break_sync(
        period_s=10.5, revisit_s=1.0, tau_ill_s=0.2736, min_coincidence_s=0.0, max_looks=500
    )
    assert need == pytest.approx(0.2264, abs=1e-3)


def test_the_extended_dwell_actually_clears_the_condition():
    """The escape has to work, not merely be computed."""
    period, revisit, tau = 10.5, 1.0, 0.2736
    need = dwell_to_break_sync(period, revisit, tau, min_coincidence_s=0.0, max_looks=500)
    epsilon = (tau + need) / period
    assert not is_synchronised(revisit / period, epsilon, max_looks=500)


def test_no_extra_dwell_is_demanded_when_there_is_no_lockout():
    assert dwell_to_break_sync(
        period_s=10.5, revisit_s=1.0, tau_ill_s=0.60, min_coincidence_s=0.0, max_looks=500
    ) == 0.0


def test_identification_time_is_charged_on_top_of_the_dwell():
    """The 2d term: a coincidence has to last long enough to be usable, not merely occur."""
    free = dwell_to_break_sync(10.5, 1.0, 0.2736, min_coincidence_s=0.0, max_looks=500)
    charged = dwell_to_break_sync(10.5, 1.0, 0.2736, min_coincidence_s=0.010, max_looks=500)
    assert charged > free


# -- escape 2: golden-ratio dithering ------------------------------------------------------------

def test_golden_phase_is_deterministic_and_reproducible():
    """Seed-based reproducibility is a project requirement; a pseudorandom dither is not enough."""
    assert golden_phase(7) == golden_phase(7)
    assert golden_phase(7) != golden_phase(8)


def test_dithered_intervals_stay_inside_the_amplitude_bound():
    base, eta = 0.280, 0.15
    for n in range(200):
        r = dithered_interval(base, n, eta=eta)
        assert base * (1 - eta / 2) <= r <= base * (1 + eta / 2)


def test_dithered_intervals_average_to_the_base_interval():
    base = 0.280
    mean = sum(dithered_interval(base, n, eta=0.15) for n in range(1000)) / 1000
    assert mean == pytest.approx(base, rel=1e-3)


def test_golden_spacing_keeps_a_large_minimum_gap_at_every_horizon():
    """The robustness claim. Random points clump; the golden ratio never does.

    Uniform spacing of n points gives gaps of 1/n. Golden spacing holds the smallest gap above
    half of that for every n, which is why it is the most lockout-resistant choice available.
    """
    for n in (5, 10, 20, 50, 100, 233):
        points = sorted(golden_phase(k) for k in range(1, n + 1))
        gaps = [b - a for a, b in zip(points, points[1:])] + [1.0 - points[-1] + points[0]]
        assert min(gaps) > 0.5 / n


def _phases_visited(intervals, period_s):
    """Emitter phases a schedule actually lands on, as fractions of the emitter period."""
    phases, t = [], 0.0
    for r in intervals:
        t += r
        phases.append((t / period_s) % 1.0)
    return sorted(phases)


def _largest_uncovered(phases):
    return max(
        [b - a for a, b in zip(phases, phases[1:])] + [1.0 - phases[-1] + phases[0]]
    )


def test_a_bounded_zero_mean_dither_does_not_break_a_half_period_lockout():
    """A negative result, encoded so nobody reinstates the wrong fix.

    Dithering the *interval* around a base value perturbs arrival times by a bounded amount: the
    partial sums of a centred low-discrepancy sequence stay O(log n), so accumulated drift never
    reaches a full emitter period. The receiver keeps landing near the same two phases. Breaking
    a lockout needs the *ratio* moved, not the interval jittered -- which is what
    :func:`golden_revisit` does.
    """
    period = 2.0
    phases = _phases_visited([dithered_interval(1.0, n, eta=0.15) for n in range(200)], period)
    assert _largest_uncovered(phases) > 0.4


def _continued_fraction(x: float, terms: int = 14) -> list[int]:
    out: list[int] = []
    for _ in range(terms):
        whole = math.floor(x)
        out.append(int(whole))
        x -= whole
        if x < 1e-12:
            break
        x = 1.0 / x
    return out


def test_golden_revisit_returns_a_noble_period_ratio():
    """Noble: a continued fraction ending in all ones, so no small rational comes close.

    The golden constant is one noble number among many; a revisit that has to fit under a tight
    deadline lands on a different one. What the guard needs is the *property* -- worst
    approximability -- not the particular constant, so that is what this asserts.
    """
    for target, period, cap in ((1.0, 2.0, None), (0.28, 20.0, 0.28), (0.5, 0.9, 0.5)):
        alpha = golden_revisit(target, period, cap) / period
        tail = _continued_fraction(alpha)[3:]
        assert tail, f"continued fraction of {alpha} terminated too early"
        assert all(term == 1 for term in tail), f"{alpha} is not noble: {_continued_fraction(alpha)}"


def test_golden_revisit_keeps_phase_gaps_near_the_uniform_bound():
    """Once the phase circle has been wrapped, the spacing is golden-grade: no clumping."""
    alpha = golden_revisit(target_s=1.0, period_s=2.0) / 2.0
    for n in (100, 200):
        points = sorted((q * alpha) % 1.0 for q in range(n))
        gaps = [b - a for a, b in zip(points, points[1:])] + [1.0 - points[-1] + points[0]]
        assert min(gaps) > 0.5 / n


def test_golden_revisit_clears_a_lockout_the_target_interval_cannot_escape():
    """The end-to-end claim: the same emitter, invisible to a fixed sweep, is intercepted."""
    period, tau, dwell = 2.0, 0.040, 0.010
    epsilon = (tau + dwell) / period
    assert is_synchronised(alpha=1.0 / period, epsilon=epsilon, max_looks=2000)

    r = golden_revisit(target_s=1.0, period_s=period)
    assert not is_synchronised(alpha=r / period, epsilon=epsilon, max_looks=2000)


def test_golden_revisit_covers_phase_fast():
    """Coverage in tens of looks, not hundreds, because the gaps are golden-spaced."""
    period, epsilon = 2.0, 0.025
    r = golden_revisit(target_s=1.0, period_s=period)
    assert looks_to_intercept(r / period, epsilon, max_looks=2000) < 60


def test_golden_revisit_never_exceeds_the_deadline():
    """The coverage guarantee outranks the lockout fix; a revisit past the deadline is not a fix."""
    for target, period, cap in ((1.0, 2.0, 1.0), (0.28, 20.0, 0.28), (0.5, 0.9, 0.5)):
        r = golden_revisit(target_s=target, period_s=period, max_s=cap)
        assert 0.0 < r <= cap


def test_golden_revisit_stays_near_the_target_when_it_can():
    r = golden_revisit(target_s=1.0, period_s=0.1)
    assert abs(r - 1.0) < 0.1


def test_golden_revisit_needs_a_period_estimate():
    with pytest.raises(ValueError):
        golden_revisit(target_s=1.0, period_s=0.0)


# -- risk over a period posterior ----------------------------------------------------------------

def test_risk_is_the_posterior_weight_on_locked_out_periods():
    modes = [
        {"period": 2.0, "tau_ill": 0.040, "weight": 0.7},      # locked out at a 1 s revisit
        {"period": 2.7183, "tau_ill": 0.040, "weight": 0.3},   # not locked out
    ]
    risk = sync_risk(revisit_s=1.0, dwell_s=0.010, modes=modes, max_looks=2000)
    assert risk == pytest.approx(0.7)


def test_a_round_looking_period_can_still_be_a_lockout():
    """3.7 s at a 1 s revisit is 10/37, gap 1/37, well above the tolerance. Round numbers are
    exactly the dangerous ones, which is why this is a computed test and not a judgement call."""
    modes = [{"period": 3.7, "tau_ill": 0.040, "weight": 1.0}]
    assert sync_risk(1.0, 0.010, modes, max_looks=2000) == pytest.approx(1.0)


def test_risk_is_zero_when_no_mode_is_locked_out():
    modes = [{"period": 2.7183, "tau_ill": 0.040, "weight": 1.0}]
    assert sync_risk(1.0, 0.010, modes, max_looks=2000) == pytest.approx(0.0)


def test_risk_is_zero_with_no_period_evidence_at_all():
    """A band we know nothing about cannot be diagnosed as locked out."""
    assert sync_risk(1.0, 0.010, modes=[], max_looks=2000) == 0.0


def test_risk_normalises_unnormalised_posterior_weights():
    modes = [
        {"period": 2.0, "tau_ill": 0.040, "weight": 7.0},
        {"period": 2.7183, "tau_ill": 0.040, "weight": 3.0},
    ]
    assert sync_risk(1.0, 0.010, modes, max_looks=2000) == pytest.approx(0.7)
