"""Emitter behavior classes against hand-computed activity tables (TEST-001 analogue).

PRD Section 24 lists "Data/labeling errors in ground truth" as a high-impact risk whose
mitigation is exactly this: unit tests per emitter class against hand-computed activity tables.
"""

from __future__ import annotations

import numpy as np
import pytest

from ml.environments.emitters import BEHAVIOR_CLASSES, Emitter, build_emitters, summarize
from ml.environments.spectrum import Spectrum


def rng(seed: int = 0) -> np.random.Generator:
    return np.random.default_rng([seed, 0])


def test_periodic_emitter_matches_hand_computed_track():
    # period 10, on_duration 3, phase 2 -> active at t in {2,3,4, 12,13,14, 22,23,24}
    e = Emitter(0, "periodic", (5,), 1.0, {"period": 10, "on_duration": 3, "phase": 2})
    track = e.activity_track(25, rng())
    expected = np.full(25, -1, dtype=np.int32)
    for start in (2, 12, 22):
        expected[start : min(25, start + 3)] = 5
    assert np.array_equal(track, expected)


def test_periodic_phase_zero_starts_immediately():
    e = Emitter(0, "periodic", (1,), 1.0, {"period": 4, "on_duration": 1, "phase": 0})
    assert e.activity_track(9, rng()).tolist() == [1, -1, -1, -1, 1, -1, -1, -1, 1]


def test_agile_emitter_hops_on_schedule():
    e = Emitter(0, "agile", (1, 5, 9), 1.0, {"hop_rate": 3, "duty": 1.0, "hop_offset": 0})
    assert e.activity_track(9, rng()).tolist() == [1, 1, 1, 5, 5, 5, 9, 9, 9]


def test_agile_wraps_through_its_hop_set():
    e = Emitter(0, "agile", (2, 7), 1.0, {"hop_rate": 2, "duty": 1.0})
    assert e.activity_track(8, rng()).tolist() == [2, 2, 7, 7, 2, 2, 7, 7]


def test_fixed_emitter_is_near_continuous():
    e = Emitter(0, "fixed", (4,), 1.0, {"duty": 1.0})
    track = e.activity_track(100, rng())
    assert np.all(track == 4)


def test_random_emitter_matches_its_activation_probability():
    e = Emitter(0, "random", (3,), 1.0, {"p_active": 0.25})
    track = e.activity_track(20_000, rng())
    assert (track >= 0).mean() == pytest.approx(0.25, abs=0.02)


def test_intermittent_emitter_produces_bursts_and_gaps():
    e = Emitter(0, "intermittent", (6,), 1.0, {"p_on_to_off": 0.2, "p_off_to_on": 0.1})
    track = e.activity_track(5_000, rng())
    active = track >= 0
    assert active.any() and not active.all()
    # Transitions should be far rarer than steps: this is bursty, not per-slot random.
    transitions = int(np.sum(active[1:] != active[:-1]))
    assert transitions < 0.35 * len(track)


def test_emitter_only_ever_occupies_its_assigned_bands():
    for behavior in BEHAVIOR_CLASSES:
        bands = (2, 7, 11) if behavior == "agile" else (7,)
        e = Emitter(0, behavior, bands, 1.0, {})
        track = e.activity_track(500, rng())
        occupied = set(track[track >= 0].tolist())
        assert occupied <= set(bands), f"{behavior} escaped its band set"


def test_unknown_behavior_class_is_rejected():
    with pytest.raises(ValueError, match="unknown behavior_class"):
        Emitter(0, "teleporting", (1,), 1.0, {})


def test_priority_below_one_is_rejected():
    with pytest.raises(ValueError, match="multiplier >= 1"):
        Emitter(0, "fixed", (1,), 0.5, {})


def test_mix_proportions_are_allocated_exactly():
    emitters = build_emitters(
        20, 16, {"fixed": 0.5, "periodic": 0.25, "agile": 0.25}, rng()
    )
    assert summarize(emitters) == {"fixed": 10, "periodic": 5, "agile": 5}


def test_mix_uses_largest_remainder_so_counts_always_sum():
    emitters = build_emitters(10, 16, {c: 0.2 for c in BEHAVIOR_CLASSES}, rng())
    assert sum(summarize(emitters).values()) == 10


def test_mix_rejects_unknown_classes():
    with pytest.raises(ValueError, match="unknown behavior classes"):
        build_emitters(5, 8, {"fixed": 0.5, "quantum": 0.5}, rng())


def test_ground_truth_gives_the_highest_priority_emitter_ownership_of_a_shared_cell():
    low = Emitter(0, "fixed", (3,), 1.0, {"duty": 1.0})
    high = Emitter(1, "fixed", (3,), 2.0, {"duty": 1.0})
    gt = Spectrum(8).generate_ground_truth([low, high], 20, rng())
    assert np.all(gt.owner[:, 3] == 1)
    assert np.all(gt.priority[:, 3] == 2.0)
    assert gt.high_priority_mask(0)[3]


def test_activation_starts_mark_the_beginning_of_each_run():
    e = Emitter(0, "periodic", (0,), 1.0, {"period": 5, "on_duration": 2, "phase": 0})
    gt = Spectrum(1).generate_ground_truth([e], 12, rng())
    # Runs begin at t = 0, 5, 10.
    assert gt.activation_starts[:, 0].tolist() == [0, 0, -1, -1, -1, 5, 5, -1, -1, -1, 10, 10]
