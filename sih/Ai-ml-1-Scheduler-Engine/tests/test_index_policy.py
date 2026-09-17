"""The SCT index (solution spec Section 4).

A Whittle-style index over per-band beliefs, normalised by the receiver time a look actually
costs. The rate normalisation is the load-bearing choice: it is what lets the scheduler see that a
detection costing eight slots is worth less than one costing a single slot, which Equation 10.1's
fixed per-detection reward cannot express.

The last test in this file is the regression test for the failure documented in
IMPLEMENTATION.md: a density-greedy policy camps on a permanently active band and lets a quiet one
starve. If it ever fails, the run intercept rate has gone back to losing to round-robin.
"""

from __future__ import annotations

import math

import numpy as np
import pytest

from ml.scheduling.index_policy import (
    IndexInputs,
    IndexWeights,
    apply_deadline_override,
    compute_index,
    select_window,
)

N = 8


def inputs(**overrides) -> IndexInputs:
    """Neutral inputs: every band identical, so a single override isolates one term."""
    base = dict(
        threat=np.full(N, 0.5),
        belief=np.full(N, 0.5),
        p_d=np.full(N, 0.8),
        ident_credit=np.ones(N),
        info_gain=np.zeros(N),
        novelty=np.zeros(N),
        elapsed_s=np.full(N, 0.015),
        pressure=np.zeros(N),
    )
    base.update(overrides)
    return IndexInputs(**base)


# -- the rate normalisation ----------------------------------------------------------------------

def test_the_index_is_value_per_unit_of_receiver_time():
    """Same expected value, twice the time, half the index."""
    quick = compute_index(inputs(elapsed_s=np.full(N, 0.010)), IndexWeights())
    slow = compute_index(inputs(elapsed_s=np.full(N, 0.020)), IndexWeights())
    assert quick[0] == pytest.approx(2.0 * slow[0])


def test_a_longer_dwell_has_to_earn_the_time_it_costs():
    """A dwell that doubles detection probability but quadruples the time is a bad trade."""
    short = compute_index(
        inputs(p_d=np.full(N, 0.4), elapsed_s=np.full(N, 0.015)), IndexWeights()
    )
    long = compute_index(
        inputs(p_d=np.full(N, 0.8), elapsed_s=np.full(N, 0.060)), IndexWeights()
    )
    assert short[0] > long[0]


def test_retune_cost_penalises_a_distant_band():
    """Retune time sits in the same denominator as the dwell, so switching is priced honestly."""
    elapsed = np.full(N, 0.015)
    elapsed[5] = 0.045  # a long tune across the spectrum
    idx = compute_index(inputs(elapsed_s=elapsed), IndexWeights())
    assert idx[5] < idx[0]


# -- the value term ------------------------------------------------------------------------------

def test_threat_weight_scales_the_value_term():
    threat = np.full(N, 0.2)
    threat[3] = 1.0
    idx = compute_index(inputs(threat=threat), IndexWeights())
    assert idx[3] > idx[0]


def test_occupancy_belief_scales_the_value_term():
    belief = np.full(N, 0.1)
    belief[2] = 0.9
    idx = compute_index(inputs(belief=belief), IndexWeights())
    assert idx[2] > idx[0]


def test_a_dwell_too_short_to_identify_is_worth_less():
    """A hit that cannot measure PRI is a detection, not an identification. Partial credit only."""
    credit = np.ones(N)
    credit[4] = 0.25
    idx = compute_index(inputs(ident_credit=credit), IndexWeights())
    assert idx[4] < idx[0]


def test_a_band_with_no_expected_value_still_scores_zero_not_negative():
    idx = compute_index(inputs(belief=np.zeros(N)), IndexWeights())
    assert np.all(idx >= 0.0)


# -- exploration and novelty ---------------------------------------------------------------------

def test_information_gain_can_carry_a_band_with_no_expected_detection():
    """This is what replaces epsilon-greedy: a band we know nothing about is worth a look."""
    gain = np.zeros(N)
    gain[6] = 0.69  # maximum binary entropy, in nats
    idx = compute_index(inputs(belief=np.zeros(N), info_gain=gain), IndexWeights())
    assert idx[6] > idx[0]
    assert int(np.argmax(idx)) == 6


def test_novelty_lifts_a_band_after_a_changepoint():
    novelty = np.zeros(N)
    novelty[1] = 1.0
    idx = compute_index(inputs(novelty=novelty), IndexWeights())
    assert idx[1] > idx[0]


def test_zero_weights_switch_a_term_off_cleanly():
    novelty = np.zeros(N)
    novelty[1] = 1.0
    off = IndexWeights(w_novelty=0.0)
    idx = compute_index(inputs(novelty=novelty), off)
    assert idx[1] == pytest.approx(idx[0])


# -- deadline pressure ---------------------------------------------------------------------------

def test_deadline_pressure_eventually_outbids_value():
    """The coverage guarantee. A quiet band nearing its deadline beats a loud fresh one."""
    belief = np.full(N, 0.05)
    belief[0] = 1.0
    pressure = np.zeros(N)
    pressure[7] = 50.0
    idx = compute_index(inputs(belief=belief, pressure=pressure), IndexWeights())
    assert idx[7] > idx[0]


def test_infinite_pressure_produces_an_infinite_index():
    pressure = np.zeros(N)
    pressure[2] = np.inf
    idx = compute_index(inputs(pressure=pressure), IndexWeights())
    assert math.isinf(float(idx[2]))


# -- explainability ------------------------------------------------------------------------------

def test_the_breakdown_reconstructs_the_index_exactly():
    """The decomposition panel is a demo centrepiece; it must not be a separate approximation."""
    ins = inputs(
        threat=np.linspace(0.1, 1.0, N),
        belief=np.linspace(0.9, 0.1, N),
        info_gain=np.linspace(0.0, 0.5, N),
        novelty=np.linspace(0.5, 0.0, N),
        pressure=np.linspace(0.0, 5.0, N),
    )
    weights = IndexWeights(w_value=1.5, w_info=0.7, w_novelty=0.3, w_deadline=2.0)
    idx = compute_index(ins, weights)
    breakdown = compute_index(ins, weights, breakdown=True)
    total = (
        breakdown["value"]
        + breakdown["information"]
        + breakdown["novelty"]
        + breakdown["deadline"]
    ) / breakdown["elapsed_s"]
    assert total == pytest.approx(idx)


def test_the_breakdown_names_every_term_in_the_formula():
    breakdown = compute_index(inputs(), IndexWeights(), breakdown=True)
    assert set(breakdown) == {"value", "information", "novelty", "deadline", "elapsed_s"}


# -- selection -----------------------------------------------------------------------------------

def test_contiguous_selection_picks_the_best_adjacent_window():
    idx = np.array([0.0, 0.0, 5.0, 5.0, 0.0, 1.0, 1.0, 1.0])
    assert select_window(idx, bandwidth_k=2, mode="contiguous") == (2, [2, 3])


def test_the_contiguous_window_wraps_at_the_top_of_the_spectrum():
    """Matches the receiver model: a block of K bands starting at the action, wrapping."""
    idx = np.array([9.0, 9.0, 0.0, 0.0, 0.0, 0.0, 0.0, 9.0])
    assert select_window(idx, bandwidth_k=3, mode="contiguous") == (7, [7, 0, 1])


def test_channelized_selection_picks_the_top_k_anywhere():
    idx = np.array([0.0, 7.0, 0.0, 0.0, 8.0, 0.0, 0.0, 0.0])
    start, bands = select_window(idx, bandwidth_k=2, mode="channelized")
    assert sorted(bands) == [1, 4]
    assert start == 4  # the best single band leads, so the contract action stays meaningful


def test_selection_rejects_an_unknown_receiver_mode():
    with pytest.raises(ValueError):
        select_window(np.zeros(N), bandwidth_k=2, mode="telepathic")


def test_selection_is_deterministic_under_ties():
    idx = np.zeros(N)
    picks = {
        (start, tuple(bands))
        for start, bands in (select_window(idx, bandwidth_k=2, mode="contiguous") for _ in range(10))
    }
    assert picks == {(0, (0, 1))}


# -- the hard override ---------------------------------------------------------------------------

def test_overdue_bands_are_forced_into_the_action_set():
    chosen = [2, 3]
    assert apply_deadline_override(chosen, overdue=[6], bandwidth_k=2) == [6, 2]


def test_the_override_displaces_the_least_valuable_choice_first():
    """Chosen bands arrive best-first, so the tail is what gets dropped."""
    assert apply_deadline_override([2, 3, 4], overdue=[7], bandwidth_k=3) == [7, 2, 3]


def test_the_override_never_exceeds_the_receivers_bandwidth():
    result = apply_deadline_override([1, 2], overdue=[5, 6, 7], bandwidth_k=2)
    assert len(result) == 2
    assert result == [5, 6]


def test_no_override_leaves_the_selection_untouched():
    assert apply_deadline_override([2, 3], overdue=[], bandwidth_k=2) == [2, 3]


def test_a_band_already_chosen_is_not_duplicated_by_the_override():
    assert apply_deadline_override([2, 3], overdue=[3], bandwidth_k=2) == [3, 2]


# -- the regression test this whole design exists for --------------------------------------------

def test_a_quiet_band_is_never_starved_by_a_permanently_active_one():
    """The IMPLEMENTATION.md failure, encoded.

    Band 0 is always active and always the most valuable single look. Band 7 is nearly always
    idle. A density-greedy policy scans band 0 for ever and band 7's activation runs go
    unintercepted, which is exactly how the bandit lost run intercept rate to round-robin. With
    deadline pressure in the index, band 7 must win within its deadline.
    """
    from ml.scheduling.deadlines import RevisitDeadlines

    deadlines = RevisitDeadlines(deadlines_s=np.full(N, 0.100), slot_s=0.010)  # 10 slots
    belief = np.full(N, 0.02)
    belief[0] = 1.0

    tsls = np.zeros(N, dtype=np.int64)
    scanned_band_7 = False
    for _ in range(40):
        idx = compute_index(
            inputs(belief=belief, pressure=deadlines.pressure(tsls)), IndexWeights()
        )
        start, bands = select_window(idx, bandwidth_k=1, mode="contiguous")
        bands = apply_deadline_override(bands, deadlines.overdue(tsls), bandwidth_k=1)
        tsls += 1
        for b in bands:
            tsls[b] = 0
        if 7 in bands:
            scanned_band_7 = True
            break

    assert scanned_band_7, "band 7 was starved: the coverage guarantee is not binding"
