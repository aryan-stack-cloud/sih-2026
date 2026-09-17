"""Phase-independent probability of intercept (solution spec Section 11.1).

Winsor & Hughes' construction, and the metric that makes a "beats open loop" claim survive
scrutiny. Every other number in this project is measured at whatever relative phase the seed
happened to produce. This one sweeps the emitter's initial phase across its whole range and asks
what fraction of phases yield at least one intercept, so a lucky seed cannot flatter a schedule.

It is computed by cross-correlating the receiver's coverage against the emitter's illumination
over cyclic offsets, exactly as the paper does, rather than by re-simulating at each phase.

The two tests that matter most are the last pair. A schedule synchronised with an emitter
intercepts it at only a handful of phases and reports a clean sweep at all the others, which is
the failure open loop cannot see in itself.
"""

from __future__ import annotations

import numpy as np
import pytest

from ml.evaluation.phase_sweep import phase_independent_pi, phase_sweep_report

T, N = 240, 8


def visits_every(period: int, band: int = 0, phase: int = 0) -> np.ndarray:
    v = np.zeros((T, N), dtype=bool)
    v[np.arange(phase, T, period), band] = True
    return v


def activity_every(period: int, on: int = 1, band: int = 0, phase: int = 0) -> np.ndarray:
    a = np.zeros((T, N), dtype=bool)
    for k in range(on):
        a[np.arange((phase + k) % period, T, period), band] = True
    return a


# -- degenerate cases ------------------------------------------------------------------------------

def test_a_band_never_visited_is_never_intercepted():
    visits = np.zeros((T, N), dtype=bool)
    visits[:, 3] = True
    assert phase_independent_pi(visits, activity_every(10, band=0)) == 0.0


def test_a_continuously_illuminating_emitter_is_intercepted_at_every_phase():
    """Clarkson: a non-scanning emitter is trivial. Any schedule that visits the band wins."""
    activity = np.zeros((T, N), dtype=bool)
    activity[:, 0] = True
    assert phase_independent_pi(visits_every(20), activity) == pytest.approx(1.0)


def test_an_emitter_that_never_transmits_is_never_intercepted():
    assert phase_independent_pi(visits_every(2), np.zeros((T, N), dtype=bool)) == 0.0


def test_staring_at_the_right_band_intercepts_every_phase():
    visits = np.zeros((T, N), dtype=bool)
    visits[:, 0] = True
    assert phase_independent_pi(visits, activity_every(16, on=1)) == pytest.approx(1.0)


# -- the lockout, measured ------------------------------------------------------------------------

def test_a_synchronised_schedule_intercepts_only_a_sliver_of_phases():
    """Sweep period 8 against scan period 8: the receiver ever sees exactly one emitter phase.

    A schedule in this state reports a flawless sweep and a Pd of zero, indistinguishable from a
    receiver watching an empty band. Phase-independent PI is what makes it visible.
    """
    pi = phase_independent_pi(visits_every(8), activity_every(8, on=1), offsets=240)
    assert pi == pytest.approx(1.0 / 8.0, abs=0.02)


def test_widening_the_illumination_widens_the_intercepted_phase_range():
    narrow = phase_independent_pi(visits_every(8), activity_every(8, on=1), offsets=240)
    wide = phase_independent_pi(visits_every(8), activity_every(8, on=4), offsets=240)
    assert wide > 3.0 * narrow


def test_an_aperiodic_schedule_beats_a_synchronised_one_by_a_wide_margin():
    """The claim, in one comparison. Same number of looks, same emitter, different pattern."""
    rng = np.random.default_rng(0)
    aperiodic = np.zeros((T, N), dtype=bool)
    chosen = rng.choice(T, size=T // 8, replace=False)
    aperiodic[chosen, 0] = True

    synced = phase_independent_pi(visits_every(8), activity_every(8, on=1), offsets=240)
    scattered = phase_independent_pi(aperiodic, activity_every(8, on=1), offsets=240)
    assert scattered > 4.0 * synced


# -- sampling ---------------------------------------------------------------------------------------

def test_more_offsets_do_not_change_the_answer_much():
    """The sweep is a sampling of a cyclic quantity; the estimate must be stable in the sample size."""
    coarse = phase_independent_pi(visits_every(5), activity_every(13, on=2), offsets=32)
    fine = phase_independent_pi(visits_every(5), activity_every(13, on=2), offsets=240)
    assert coarse == pytest.approx(fine, abs=0.08)


def test_offsets_must_be_positive():
    with pytest.raises(ValueError):
        phase_independent_pi(visits_every(4), activity_every(4), offsets=0)


def test_mismatched_shapes_are_rejected():
    with pytest.raises(ValueError):
        phase_independent_pi(np.zeros((T, N), dtype=bool), np.zeros((T, N + 1), dtype=bool))


# -- the report ---------------------------------------------------------------------------------------

class _Emitter:
    def __init__(self, emitter_id: int, priority: float) -> None:
        self.emitter_id = emitter_id
        self.priority = priority


class _GroundTruth:
    def __init__(self, owner: np.ndarray, emitters) -> None:
        self.owner = owner
        self.emitters = emitters
        self.duration, self.num_bands = owner.shape


def _history(visits: np.ndarray):
    return [
        {"t": t, "scanned_bands": [int(b) for b in np.nonzero(row)[0]]}
        for t, row in enumerate(visits)
    ]


def _ground_truth_with(activities: dict[int, np.ndarray], priorities: dict[int, float]):
    owner = np.full((T, N), -1, dtype=np.int32)
    for emitter_id, activity in activities.items():
        owner[activity] = emitter_id
    return _GroundTruth(owner, [_Emitter(e, priorities[e]) for e in sorted(activities)])


def test_the_report_scores_each_emitter_separately():
    gt = _ground_truth_with(
        {0: activity_every(8, on=1, band=0), 1: activity_every(8, on=1, band=5)},
        {0: 1.0, 1: 1.0},
    )
    report = phase_sweep_report(_history(visits_every(8, band=0)), gt, offsets=240)
    assert report["per_emitter"][0] > report["per_emitter"][1]
    assert report["per_emitter"][1] == 0.0


def test_the_report_carries_the_worst_case_alongside_the_mean():
    """Clarkson's min-max criterion. A good mean is worthless if one tracker is never seen."""
    gt = _ground_truth_with(
        {0: activity_every(8, on=1, band=0), 1: activity_every(8, on=1, band=5)},
        {0: 1.0, 1: 1.0},
    )
    report = phase_sweep_report(_history(visits_every(8, band=0)), gt, offsets=240)
    assert report["worst_case"] == 0.0
    assert report["mean"] > report["worst_case"]


def test_the_report_weights_by_emitter_priority():
    gt = _ground_truth_with(
        {0: activity_every(8, on=1, band=0), 1: activity_every(8, on=1, band=5)},
        {0: 2.0, 1: 1.0},
    )
    report = phase_sweep_report(_history(visits_every(8, band=0)), gt, offsets=240)
    assert report["priority_weighted"] > report["mean"]


def test_the_report_survives_a_scenario_with_no_emitters():
    gt = _GroundTruth(np.full((T, N), -1, dtype=np.int32), [])
    report = phase_sweep_report(_history(visits_every(4)), gt)
    assert report["mean"] == 0.0
    assert report["per_emitter"] == {}
