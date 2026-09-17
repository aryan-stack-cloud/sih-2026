"""Revisit deadlines -- the coverage guarantee (SCT solution spec Section 5).

These are the tests for the fix to the one metric the current bandit loses on. A deadline is
derived from intercept-time theory, not tuned, and it binds before value maximisation. If any of
these fail, a band can be starved and the run intercept rate goes back to losing.
"""

from __future__ import annotations

import math

import numpy as np
import pytest

from ml.scheduling.deadlines import (
    RevisitDeadlines,
    coverage_cycle_seconds,
    required_bandwidth_k,
    revisit_deadline_seconds,
)

# The worked example of solution spec Section 5: 3 rpm search radar, 1.5 deg beam, 10 ms dwell,
# 60 s worst-case intercept requirement.
T_MAX = 20.0
TAU_ILL = (1.5 / 360.0) * T_MAX  # 83.3 ms
DWELL = 0.010
T_REQ = 60.0


# -- deriving the deadline ---------------------------------------------------------------------

def test_revisit_deadline_matches_the_worked_derivation():
    d = revisit_deadline_seconds(t_req_s=T_REQ, tau_ill_s=TAU_ILL, dwell_s=DWELL, t_max_s=T_MAX)
    assert d == pytest.approx(0.280, abs=5e-4)


def test_deadline_scales_with_the_intercept_requirement():
    """Halving the worst-case requirement must halve the revisit interval."""
    slow = revisit_deadline_seconds(T_REQ, TAU_ILL, DWELL, T_MAX)
    fast = revisit_deadline_seconds(T_REQ / 2, TAU_ILL, DWELL, T_MAX)
    assert fast == pytest.approx(slow / 2)


def test_deadline_tightens_as_the_emitter_scans_slower():
    """A slower emitter illuminates us a smaller fraction of the time, so we must look sooner."""
    quick = revisit_deadline_seconds(T_REQ, TAU_ILL, DWELL, t_max_s=5.0)
    slow = revisit_deadline_seconds(T_REQ, TAU_ILL, DWELL, t_max_s=40.0)
    assert slow < quick


def test_a_longer_dwell_buys_a_longer_deadline():
    """Dwell and revisit trade against each other; that is the whole point of the formula."""
    short = revisit_deadline_seconds(T_REQ, TAU_ILL, dwell_s=0.010, t_max_s=T_MAX)
    long = revisit_deadline_seconds(T_REQ, TAU_ILL, dwell_s=0.080, t_max_s=T_MAX)
    assert long > short


def test_a_continuous_illuminator_is_bounded_by_the_requirement_itself():
    """Clarkson: a non-scanning emitter is trivial. tau_ill == t_max means D approaches T_req."""
    d = revisit_deadline_seconds(t_req_s=2.0, tau_ill_s=1.0, dwell_s=0.0, t_max_s=1.0)
    assert d == pytest.approx(2.0)


def test_zero_scan_period_is_rejected_rather_than_dividing_by_zero():
    with pytest.raises(ValueError):
        revisit_deadline_seconds(T_REQ, TAU_ILL, DWELL, t_max_s=0.0)


# -- feasibility and receiver sizing ------------------------------------------------------------

def test_coverage_cycle_visits_every_band_once():
    """16 bands, 2 at a time, 10 ms dwell + 5 ms retune = 8 dwells = 120 ms."""
    assert coverage_cycle_seconds(
        num_bands=16, bandwidth_k=2, dwell_s=0.010, retune_s=0.005
    ) == pytest.approx(0.120)


def test_required_bandwidth_rounds_up_to_a_whole_receiver():
    """64 bands against a 186 ms deadline needs 5.16 bands of instantaneous bandwidth, so 6."""
    assert required_bandwidth_k(
        num_bands=64, dwell_s=0.010, retune_s=0.005, min_deadline_s=0.186
    ) == 6


def test_relaxing_the_requirement_reduces_the_receivers_needed():
    tight = required_bandwidth_k(64, 0.010, 0.005, min_deadline_s=0.186)
    relaxed = required_bandwidth_k(64, 0.010, 0.005, min_deadline_s=0.280)
    assert relaxed < tight


def test_the_demo_configuration_is_feasible():
    dl = RevisitDeadlines(deadlines_s=np.full(16, 0.186), slot_s=0.010)
    report = dl.feasibility(bandwidth_k=2, dwell_s=0.010, retune_s=0.005)
    assert report.feasible
    assert report.committed_fraction == pytest.approx(0.120 / 0.186, rel=1e-3)


def test_an_oversubscribed_configuration_reports_infeasible_instead_of_starving_bands():
    """The failure mode this replaces is silent starvation. It must be loud."""
    dl = RevisitDeadlines(deadlines_s=np.full(64, 0.050), slot_s=0.010)
    report = dl.feasibility(bandwidth_k=2, dwell_s=0.010, retune_s=0.005)
    assert not report.feasible
    assert report.required_bandwidth_k > 2
    assert "infeasible" in report.message.lower()


# -- staleness pressure ------------------------------------------------------------------------

def test_pressure_is_zero_immediately_after_a_scan():
    dl = RevisitDeadlines(deadlines_s=np.full(4, 0.280), slot_s=0.010)
    assert dl.pressure(np.zeros(4, dtype=int)) == pytest.approx(np.zeros(4))


def test_pressure_grows_without_bound_as_the_deadline_approaches():
    dl = RevisitDeadlines(deadlines_s=np.full(1, 0.100), slot_s=0.010)  # 10 slots
    rising = [float(dl.pressure(np.array([k]))[0]) for k in (1, 3, 5, 7, 9)]
    assert all(b > a for a, b in zip(rising, rising[1:]))
    assert rising[-1] > 10 * rising[0]


def test_pressure_is_infinite_once_the_deadline_has_passed():
    dl = RevisitDeadlines(deadlines_s=np.full(1, 0.100), slot_s=0.010)
    assert math.isinf(float(dl.pressure(np.array([10]))[0]))
    assert math.isinf(float(dl.pressure(np.array([25]))[0]))


def test_overdue_bands_come_back_most_stale_first():
    """Ordering is the starvation guard: with several bands past deadline, the oldest wins.

    Returning them in band order would let a low-numbered band monopolise the override and
    starve a high-numbered one indefinitely -- the exact bug the deadline exists to prevent.
    """
    dl = RevisitDeadlines(deadlines_s=np.full(5, 0.100), slot_s=0.010)  # 10 slots each
    tsls = np.array([12, 3, 40, 11, 0])
    assert dl.overdue(tsls) == [2, 0, 3]


def test_a_lookahead_brings_the_override_forward_to_drain_the_queue():
    """A hard deadline alone cannot absorb bands that all expire in the same slot.

    With K=1 and eight bands, eight simultaneous expiries take eight slots to clear, so the last
    one is served a full coverage cycle late. Subtracting that cycle from the trigger point serves
    them early enough that the *last* one still lands on its deadline rather than past it.
    """
    dl = RevisitDeadlines(deadlines_s=np.full(8, 0.300), slot_s=0.010)  # 30 slots
    assert dl.overdue(np.full(8, 23)) == []
    assert len(dl.overdue(np.full(8, 23), lookahead=7)) == 8


def test_a_lookahead_never_pushes_the_trigger_below_one_slot():
    """A freshly scanned band is never overdue, whatever the lookahead."""
    dl = RevisitDeadlines(deadlines_s=np.full(4, 0.030), slot_s=0.010)  # 3 slots
    assert dl.overdue(np.zeros(4, dtype=int), lookahead=99) == []


def test_a_lookahead_of_zero_is_the_plain_deadline():
    dl = RevisitDeadlines(deadlines_s=np.full(3, 0.100), slot_s=0.010)
    assert dl.overdue(np.array([9, 10, 11]), lookahead=0) == [2, 1]


def test_no_bands_are_overdue_before_their_deadlines():
    dl = RevisitDeadlines(deadlines_s=np.full(3, 0.100), slot_s=0.010)
    assert dl.overdue(np.array([1, 5, 9])) == []


def test_per_band_deadlines_are_independent():
    """A tracker band gets a tighter deadline than a surveillance band, and both are honoured."""
    dl = RevisitDeadlines(deadlines_s=np.array([0.030, 0.280]), slot_s=0.010)
    assert dl.overdue(np.array([5, 5])) == [0]


def test_deadline_slots_are_at_least_one_slot():
    """A deadline shorter than a slot must still be schedulable, not rounded to zero."""
    dl = RevisitDeadlines(deadlines_s=np.full(2, 0.004), slot_s=0.010)
    assert dl.deadline_slots.min() >= 1
