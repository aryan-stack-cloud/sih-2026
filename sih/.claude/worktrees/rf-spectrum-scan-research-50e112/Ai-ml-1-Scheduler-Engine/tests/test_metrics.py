"""Metrics engine against hand-computed cases (PRD Phase 5 DoD, TEST-020).

Every Section 12 formula is checked on a tiny spectrum small enough to count by hand, including
the two counting rules that make the baseline-vs-ML comparison honest:

  * Pd counts every band at every step, so unscanned active bands are false negatives.
  * Pfa counts scanned bands only, so an unlooked-at band cannot be a true negative.
"""

from __future__ import annotations

import numpy as np
import pytest

from ml.environments.emitters import Emitter
from ml.environments.spectrum import GroundTruth
from ml.evaluation.evaluator import aggregate, score_episode


def make_ground_truth(occupancy: list[list[int]], priorities: list[float] | None = None):
    """occupancy[t][band] = emitter_id or -1."""
    owner = np.array(occupancy, dtype=np.int32)
    occ = owner >= 0
    ids = sorted({int(o) for o in owner.flatten() if o >= 0})
    priorities = priorities or [1.0] * len(ids)
    emitters = [
        Emitter(emitter_id=i, behavior_class="fixed", bands=(0,), priority=p)
        for i, p in zip(ids, priorities)
    ]
    return GroundTruth(occ, owner, emitters)


def record(t, outcomes, unscanned=(), detected=(), emitters=(), fa=(), reward=0.0,
           valid=True, retuned=False):
    return {
        "t": t,
        "action": 0,
        "scanned_bands": list(outcomes),
        "valid": valid,
        "retuned": retuned,
        "outcomes": outcomes,
        "unscanned_misses": list(unscanned),
        "detected_bands": list(detected),
        "detected_emitters": set(emitters),
        "false_alarm_bands": list(fa),
        "detection_latency": {},
        "reward": reward,
        "terms": {},
    }


def test_pd_counts_unscanned_active_bands_as_misses():
    # 2 bands, 2 steps. Band 0 active throughout, band 1 always idle.
    gt = make_ground_truth([[0, -1], [0, -1]])
    history = [
        record(0, {0: "TP"}, detected=[0], emitters=[0]),
        record(1, {1: "TN"}, unscanned=[0]),          # band 0 active but not scanned
    ]
    m = score_episode(history, gt, num_bands=2)
    assert (m.tp, m.fn) == (1, 1)
    assert m.pd == pytest.approx(0.5)
    assert m.miss_rate == pytest.approx(0.5)
    assert m.recall == m.pd


def test_a_scanner_that_never_moves_does_not_get_a_perfect_pd():
    """The failure mode the counting rule exists to prevent."""
    gt = make_ground_truth([[0, 1]] * 10)
    history = [record(t, {0: "TP"}, detected=[0], emitters=[0], unscanned=[1]) for t in range(10)]
    m = score_episode(history, gt, num_bands=2)
    assert m.pd == pytest.approx(0.5)  # not 1.0
    assert m.coverage == pytest.approx(0.5)


def test_pfa_ignores_unscanned_bands():
    # Band 1 idle and scanned once (TN); band 2 idle and never scanned (contributes nothing).
    gt = make_ground_truth([[-1, -1, -1]])
    history = [record(0, {0: "FP", 1: "TN"}, fa=[0])]
    m = score_episode(history, gt, num_bands=3)
    assert (m.fp, m.tn) == (1, 1)
    assert m.pfa == pytest.approx(0.5)


def test_ait_averages_one_latency_per_activation_run():
    # Band 0 active for t in 0..4 (one run starting at 0), detected first at t = 2.
    gt = make_ground_truth([[0], [0], [0], [0], [0]])
    history = [
        record(0, {0: "FN"}),
        record(1, {0: "FN"}),
        record(2, {0: "TP"}, detected=[0], emitters=[0]),
        record(3, {0: "TP"}, detected=[0], emitters=[0]),
        record(4, {0: "TP"}, detected=[0], emitters=[0]),
    ]
    m = score_episode(history, gt, num_bands=1)
    assert m.latencies == [2]        # one run, one latency -- not three
    assert m.ait == pytest.approx(2.0)
    assert m.detected_runs == 1
    assert m.total_runs == 1


def test_two_separate_runs_contribute_two_latencies():
    # Band 0 active at t in {0,1} and again at {3,4}: two runs.
    gt = make_ground_truth([[0], [0], [-1], [0], [0]])
    history = [
        record(0, {0: "FN"}),
        record(1, {0: "TP"}, detected=[0], emitters=[0]),   # run @0 detected at latency 1
        record(2, {0: "TN"}),
        record(3, {0: "TP"}, detected=[0], emitters=[0]),   # run @3 detected at latency 0
        record(4, {0: "TP"}, detected=[0], emitters=[0]),
    ]
    m = score_episode(history, gt, num_bands=1)
    assert m.latencies == [0, 1]
    assert m.ait == pytest.approx(0.5)
    assert m.total_runs == 2


def test_hpdr_uses_only_high_priority_cells():
    # emitter 0 priority 1.0 on band 0, emitter 1 priority 2.0 on band 1.
    gt = make_ground_truth([[0, 1], [0, 1]], priorities=[1.0, 2.0])
    history = [
        record(0, {0: "TP", 1: "TP"}, detected=[0, 1], emitters=[0, 1]),
        record(1, {0: "TP"}, detected=[0], emitters=[0], unscanned=[1]),
    ]
    m = score_episode(history, gt, num_bands=2)
    assert (m.tp_high_priority, m.fn_high_priority) == (1, 1)
    assert m.hpdr == pytest.approx(0.5)
    assert m.pd == pytest.approx(3 / 4)  # differs from HPDR, as it should


def test_interception_ratio_counts_distinct_emitters():
    gt = make_ground_truth([[0, 1, 2]])
    history = [record(0, {0: "TP", 1: "TP"}, detected=[0, 1], emitters=[0, 1], unscanned=[2])]
    m = score_episode(history, gt, num_bands=3)
    assert m.interception_ratio == pytest.approx(2 / 3)


def test_scan_efficiency_counts_scans_aimed_at_active_bands():
    # Four band-scans; two landed on active bands (one TP, one FN), two on idle bands.
    gt = make_ground_truth([[0, -1], [0, -1]])
    history = [
        record(0, {0: "TP", 1: "TN"}, detected=[0], emitters=[0]),
        record(1, {0: "FN", 1: "FP"}, fa=[1]),
    ]
    m = score_episode(history, gt, num_bands=2)
    assert m.total_scans == 4
    assert m.useful_scans == 2
    assert m.scan_efficiency == pytest.approx(0.5)


def test_precision_recall_and_f1_agree_with_their_definitions():
    gt = make_ground_truth([[0, -1]] * 4)
    history = [
        record(0, {0: "TP", 1: "FP"}, detected=[0], emitters=[0], fa=[1]),
        record(1, {0: "TP", 1: "TN"}, detected=[0], emitters=[0]),
        record(2, {0: "FN", 1: "TN"}),
        record(3, {0: "TP", 1: "TN"}, detected=[0], emitters=[0]),
    ]
    m = score_episode(history, gt, num_bands=2)
    assert (m.tp, m.fn, m.fp) == (3, 1, 1)
    assert m.precision == pytest.approx(3 / 4)
    assert m.recall == pytest.approx(3 / 4)
    assert m.f1 == pytest.approx(0.75)


def test_invalid_steps_are_recorded_and_score_no_scans():
    gt = make_ground_truth([[0], [0]])
    history = [record(0, {}, unscanned=[0], valid=False, retuned=True), record(1, {0: "TP"}, detected=[0], emitters=[0])]
    m = score_episode(history, gt, num_bands=1)
    assert m.invalid_steps == 1 and m.retunes == 1
    assert m.total_scans == 1
    assert m.pd == pytest.approx(0.5)


def test_cumulative_reward_is_the_episode_sum():
    gt = make_ground_truth([[-1]] * 3)
    history = [record(t, {0: "TN"}, reward=r) for t, r in enumerate([1.5, -2.0, 3.0])]
    assert score_episode(history, gt, 1).cumulative_reward == pytest.approx(2.5)


def test_aggregate_pools_counts_rather_than_averaging_rates():
    """A busy episode and a quiet one must not be weighted equally."""
    gt_busy = make_ground_truth([[0]] * 100)
    busy = score_episode(
        [record(t, {0: "TP"}, detected=[0], emitters=[0]) for t in range(100)], gt_busy, 1
    )
    gt_quiet = make_ground_truth([[0]])
    quiet = score_episode([record(0, {0: "FN"})], gt_quiet, 1)

    pooled = aggregate([busy, quiet])
    # Pooled: 100 TP, 1 FN -> 100/101, not the mean of (1.0, 0.0) = 0.5.
    assert pooled["pd"] == pytest.approx(100 / 101)
    assert pooled["counts"] == {"tp": 100, "fn": 1, "fp": 0, "tn": 0}


def test_aggregate_of_nothing_is_empty():
    assert aggregate([]) == {}
