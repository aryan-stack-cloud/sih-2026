"""Coverage as a constraint in the objective, not merely a heavily weighted term.

**Which coverage property is the veto took two attempts and a decisive measurement.**

The first version vetoed on run intercept rate too. Held-out measurement then showed that
round-robin beats the index on that metric at *every* budget in *every* scenario, and that looser
budgets make it worse rather than better. That is not a defect in the scheduler: run intercept rate
rewards catching the start of an activation run, which a perfectly uniform sweep maximises by
construction, so any deviation to chase value costs it. As a hard constraint it therefore admits
only round-robin, and a constraint no non-trivial policy can satisfy is not encoding an operating
intent, it is encoding the baseline.

So the veto is **emitter reach**: interception ratio, the "did we ever see this emitter at all"
metric, which the index holds or improves at nearly every budget and which is the property a
mission actually cannot give up. Run intercept rate and censored intercept time stay as costs,
weighted five to one against gains, so a candidate is discouraged from spending them rather than
forbidden. The three named objectives then discriminate inside that feasible region, which is
where an operating intent belongs.

Disqualified candidates are still ordered by how far short they fall, so a search has a gradient
back toward the feasible region rather than a cliff it cannot see over.
"""

from __future__ import annotations

import pytest

from ml.tuning.objective import OBJECTIVES, objective_score

REFERENCE = {
    "pd": 0.1065,
    "hpdr": 0.1064,
    "run_intercept_rate": 0.4011,
    "interception_ratio": 0.9750,
    "ait_censored": 1198.59,
}

# The configuration that slipped through, measured on hold-out seeds.
TUNED = {
    "pd": 0.2029,
    "hpdr": 0.1876,
    "run_intercept_rate": 0.3429,
    "interception_ratio": 1.0000,
    "ait_censored": 1314.82,
}

# The shipped defaults on the same seeds.
DEFAULT = {
    "pd": 0.1259,
    "hpdr": 0.1270,
    "run_intercept_rate": 0.4060,
    "interception_ratio": 1.0000,
    "ait_censored": 1188.81,
}


def test_a_candidate_that_reaches_more_emitters_is_feasible():
    """Both of these see every emitter the sweep sees, or more, so both may compete."""
    assert objective_score(TUNED, REFERENCE) > 0.0
    assert objective_score(DEFAULT, REFERENCE) > 0.0


def test_the_coverage_objective_still_prefers_the_one_that_holds_run_coverage():
    """Run coverage stops being a veto and stays an expensive cost the objectives weigh."""
    weights = OBJECTIVES["coverage"]
    assert objective_score(DEFAULT, REFERENCE, weights) > objective_score(
        TUNED, REFERENCE, weights
    )


def test_losing_emitters_is_a_veto_whatever_the_detection_numbers_say():
    blind = dict(TUNED, interception_ratio=REFERENCE["interception_ratio"] * 0.8)
    assert objective_score(blind, REFERENCE) < 0.0
    assert objective_score(blind, REFERENCE, OBJECTIVES["detection"]) < 0.0


def test_matching_the_reference_exactly_is_feasible_and_scores_zero():
    assert objective_score(dict(REFERENCE), REFERENCE) == pytest.approx(0.0)


def test_a_dip_inside_the_tolerance_is_allowed():
    """Seed-to-seed noise must not disqualify an otherwise good configuration."""
    nudged = dict(DEFAULT, interception_ratio=REFERENCE["interception_ratio"] * 0.99)
    assert objective_score(nudged, REFERENCE) > 0.0


def test_a_dip_past_the_tolerance_is_not():
    beyond = dict(DEFAULT, interception_ratio=REFERENCE["interception_ratio"] * 0.90)
    assert objective_score(beyond, REFERENCE) < 0.0


def test_disqualified_candidates_are_ordered_by_how_far_they_fall_short():
    """A search needs a gradient back toward feasibility, not a cliff."""
    mild = dict(DEFAULT, interception_ratio=REFERENCE["interception_ratio"] * 0.90)
    severe = dict(DEFAULT, interception_ratio=REFERENCE["interception_ratio"] * 0.50)
    assert objective_score(severe, REFERENCE) < objective_score(mild, REFERENCE)


def test_run_coverage_is_an_expensive_cost_rather_than_a_veto():
    """The split measurement forced. See the module docstring."""
    for metric, factor in (("run_intercept_rate", 0.80), ("ait_censored", 1.25)):
        candidate = dict(DEFAULT, **{metric: REFERENCE[metric] * factor})
        assert objective_score(candidate, REFERENCE) > -1.0, metric
        assert objective_score(candidate, REFERENCE) < objective_score(DEFAULT, REFERENCE)


def test_detection_metrics_are_not_vetoed_either():
    """Only emitter reach vetoes. Everything else is a cost, and costs are tradeable."""
    weaker = dict(DEFAULT, pd=REFERENCE["pd"] * 0.5)
    assert objective_score(weaker, REFERENCE) > -1.0


def test_a_detection_first_mission_can_relax_the_constraint():
    """The veto encodes an operating intent, so an explicit intent may widen it."""
    blind = dict(TUNED, interception_ratio=REFERENCE["interception_ratio"] * 0.8)
    assert objective_score(
        blind, REFERENCE, OBJECTIVES["detection"], coverage_tolerance=0.3
    ) > 0.0


def test_relaxing_the_tolerance_does_not_silently_become_the_default():
    blind = dict(TUNED, interception_ratio=REFERENCE["interception_ratio"] * 0.8)
    assert objective_score(blind, REFERENCE, OBJECTIVES["detection"]) < 0.0
