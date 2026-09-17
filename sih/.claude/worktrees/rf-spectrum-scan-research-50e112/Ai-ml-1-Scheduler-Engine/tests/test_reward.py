"""Reward function against hand-computed cases (PRD Phase 5 DoD, TEST-010).

The Backend computes Equation 10.1 in production and posts the scalar to /internal/learn, so
these cases are the shared reference both implementations must reproduce. Each test states the
arithmetic explicitly rather than comparing against another code path.
"""

from __future__ import annotations

import numpy as np
import pytest

from ml.environments.receiver import DetectionOutcome
from ml.environments.reward import RewardContext, RewardFunction, RewardWeights

W = RewardWeights(
    w1_detection=10.0,
    w2_priority=2.0,
    w3_latency=3.0,
    w4_false_alarm=5.0,
    w5_redundant=0.5,
    w6_missed=4.0,
)


def outcome(**kwargs) -> DetectionOutcome:
    base = dict(
        t=10,
        outcomes={},
        unscanned_misses=[],
        detected_bands=[],
        false_alarm_bands=[],
        detected_emitters=set(),
        max_detected_priority=0.0,
        detection_latency={},
    )
    base.update(kwargs)
    return DetectionOutcome(**base)


def context(num_bands: int = 8, **kwargs) -> RewardContext:
    base = dict(
        time_since_last_scan=np.full(num_bands, 99, dtype=np.int32),
        high_priority_active=np.zeros(num_bands, dtype=bool),
        scanned_bands=[],
        new_run_latencies={},
        latency_horizon=20,
        redundant_window=3,
    )
    base.update(kwargs)
    return RewardContext(**base)


def test_nothing_happens_scores_zero():
    r, terms = RewardFunction(W).compute(outcome(), context())
    assert r == 0.0
    assert terms == {"D": 0.0, "P": 0.0, "L": 0.0, "F": 0.0, "C": 0.0, "M": 0.0}


def test_plain_detection_of_priority_one_emitter():
    # r = 10*1 + 2*1*1 = 12
    r, terms = RewardFunction(W).compute(
        outcome(detected_bands=[3], max_detected_priority=1.0),
        context(scanned_bands=[3]),
    )
    assert terms["D"] == 1.0 and terms["P"] == 1.0
    assert r == pytest.approx(12.0)


def test_high_priority_detection_pays_the_priority_multiplier():
    # r = 10*1 + 2*2.0*1 = 14
    r, _ = RewardFunction(W).compute(
        outcome(detected_bands=[3], max_detected_priority=2.0),
        context(scanned_bands=[3]),
    )
    assert r == pytest.approx(14.0)


def test_first_detection_of_a_run_pays_the_latency_penalty():
    # latency 10 of horizon 20 -> L = 0.5; r = 10 + 2 - 3*0.5 = 10.5
    r, terms = RewardFunction(W).compute(
        outcome(detected_bands=[3], max_detected_priority=1.0, detection_latency={3: 10}),
        context(scanned_bands=[3], new_run_latencies={3: 10}),
    )
    assert terms["L"] == pytest.approx(0.5)
    assert r == pytest.approx(10.5)


def test_latency_penalty_is_not_charged_again_on_re_detection():
    """A run we already intercepted is not 'late' every subsequent step.

    This is the alignment that makes the reward agree with Section 12: AIT counts one latency
    per activation run, so L(t) is charged once per run. Charging stale latency per step
    penalised productive dwell and drove the agent off emitters it had correctly found.
    """
    r, terms = RewardFunction(W).compute(
        # detection_latency is populated (we did detect), but new_run_latencies is empty.
        outcome(detected_bands=[3], max_detected_priority=1.0, detection_latency={3: 400}),
        context(scanned_bands=[3], new_run_latencies={}),
    )
    assert terms["L"] == 0.0
    assert r == pytest.approx(12.0)


def test_latency_saturates_at_the_horizon():
    r, terms = RewardFunction(W).compute(
        outcome(detected_bands=[3], max_detected_priority=1.0),
        context(scanned_bands=[3], new_run_latencies={3: 999}, latency_horizon=20),
    )
    assert terms["L"] == 1.0
    assert r == pytest.approx(10.0 + 2.0 - 3.0)


def test_false_alarm_penalty():
    # r = -5*1 = -5
    r, terms = RewardFunction(W).compute(
        outcome(false_alarm_bands=[5]), context(scanned_bands=[5])
    )
    assert terms["F"] == 1.0
    assert r == pytest.approx(-5.0)


def test_redundant_scan_penalty_is_a_fraction_of_scanned_bands():
    # Two bands scanned, both revisited within the window, neither detected -> C = 1.0
    ages = np.full(8, 99, dtype=np.int32)
    ages[2] = 1
    ages[3] = 2
    r, terms = RewardFunction(W).compute(
        outcome(), context(scanned_bands=[2, 3], time_since_last_scan=ages)
    )
    assert terms["C"] == pytest.approx(1.0)
    assert r == pytest.approx(-0.5)


def test_redundant_penalty_ignores_bands_that_intercepted_a_new_run():
    ages = np.full(8, 1, dtype=np.int32)
    _, terms = RewardFunction(W).compute(
        outcome(detected_bands=[2], max_detected_priority=1.0, detection_latency={2: 0}),
        context(scanned_bands=[2, 3], time_since_last_scan=ages, new_run_latencies={2: 0}),
    )
    # Band 2 intercepted a new run, band 3 gave nothing -> C = 1/2
    assert terms["C"] == pytest.approx(0.5)


def test_re_detecting_an_already_intercepted_run_counts_as_redundant():
    """C(t) is "no NEW information" -- a detection we already have is not new.

    Without this, camping on one loud emitter is never penalised: the band pays out every step,
    so it never looks wasted, and the policy maximises detection density while never discovering
    the rest of the spectrum.
    """
    ages = np.full(8, 1, dtype=np.int32)
    _, terms = RewardFunction(W).compute(
        # Detected, but new_run_latencies is empty: this run was already intercepted earlier.
        outcome(detected_bands=[2], max_detected_priority=1.0, detection_latency={2: 300}),
        context(scanned_bands=[2], time_since_last_scan=ages, new_run_latencies={}),
    )
    assert terms["C"] == pytest.approx(1.0)


def test_redundant_penalty_ignores_bands_not_recently_visited():
    ages = np.full(8, 50, dtype=np.int32)
    _, terms = RewardFunction(W).compute(
        outcome(), context(scanned_bands=[2, 3], time_since_last_scan=ages)
    )
    assert terms["C"] == 0.0


def test_missed_opportunity_is_a_fraction_of_active_high_priority_bands():
    hp = np.zeros(8, dtype=bool)
    hp[[1, 4, 6]] = True  # three high-priority bands active
    _, terms = RewardFunction(W).compute(
        outcome(unscanned_misses=[1, 4]),  # two of them unscanned
        context(high_priority_active=hp, scanned_bands=[6]),
    )
    assert terms["M"] == pytest.approx(2 / 3)


def test_missed_opportunity_is_zero_when_no_high_priority_band_is_active():
    _, terms = RewardFunction(W).compute(
        outcome(unscanned_misses=[0, 1, 2]), context(scanned_bands=[5])
    )
    assert terms["M"] == 0.0


def test_full_equation_combines_every_term():
    # D=1, P=2, L=0.25, F=1, C=0.5, M=0.5
    # r = 10 + 2*2 - 3*0.25 - 5 - 0.5*0.5 - 4*0.5 = 10 + 4 - 0.75 - 5 - 0.25 - 2 = 6.0
    hp = np.zeros(8, dtype=bool)
    hp[[0, 7]] = True
    ages = np.full(8, 99, dtype=np.int32)
    ages[1] = 1
    r, terms = RewardFunction(W).compute(
        outcome(
            detected_bands=[0],
            max_detected_priority=2.0,
            false_alarm_bands=[1],
            unscanned_misses=[7],
        ),
        context(
            scanned_bands=[0, 1],
            new_run_latencies={0: 5},
            high_priority_active=hp,
            time_since_last_scan=ages,
        ),
    )
    assert terms == pytest.approx({"D": 1.0, "P": 2.0, "L": 0.25, "F": 1.0, "C": 0.5, "M": 0.5})
    assert r == pytest.approx(6.0)


def test_weights_reject_negative_values():
    with pytest.raises(ValueError, match="non-negative"):
        RewardWeights(w1_detection=-1.0)


def test_weights_reject_unknown_config_keys():
    with pytest.raises(ValueError, match="unknown reward weights"):
        RewardWeights.from_config({"w7_mystery": 1.0})
