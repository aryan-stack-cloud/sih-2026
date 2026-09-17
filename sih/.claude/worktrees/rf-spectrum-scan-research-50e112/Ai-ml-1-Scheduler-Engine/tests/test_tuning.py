"""Tuning the index weights against the graded metric (solution spec Section 10).

The claim this supports is narrow and worth defending precisely: **nothing here optimises a proxy
reward.** Equation 10.1's six weights are a reward-shaping exercise, and the relationship between
that reward and the metrics a reviewer reads is an article of faith. The index has seven scalars
and they are optimised directly against the scoreboard.

The objective is expressed as a ratio to a reference policy on identical seeds, so a score of 0
means "no better than round-robin" and the sign of every term is unambiguous.
"""

from __future__ import annotations

import pytest

from ml.tuning.objective import (
    OBJECTIVES,
    IndexParams,
    objective_score,
    params_to_agent_kwargs,
)

BASE = {
    "pd": 0.10,
    "hpdr": 0.10,
    "run_intercept_rate": 0.40,
    "ait_censored": 1200.0,
    "interception_ratio": 0.95,
}


def summary(**overrides) -> dict:
    out = dict(BASE)
    out.update(overrides)
    return out


# -- the objective ---------------------------------------------------------------------------------

def test_matching_the_reference_scores_zero():
    """A score of 0 means 'no better than round-robin', so signs are never ambiguous."""
    assert objective_score(summary(), BASE) == pytest.approx(0.0)


def test_better_detection_scores_higher():
    assert objective_score(summary(pd=0.20), BASE) > 0.0


def test_worse_detection_scores_lower():
    assert objective_score(summary(pd=0.05), BASE) < 0.0


def test_a_shorter_censored_intercept_time_scores_higher():
    """Lower is better for latency, so the objective must invert it rather than add it."""
    assert objective_score(summary(ait_censored=600.0), BASE) > 0.0
    assert objective_score(summary(ait_censored=2400.0), BASE) < 0.0


def test_losing_coverage_is_penalised_even_when_detection_improves():
    """The bandit's trade. Tripling Pd while coverage collapses must not score well."""
    bandit_like = summary(pd=0.34, hpdr=0.29, run_intercept_rate=0.14, ait_censored=1720.0)
    assert objective_score(bandit_like, BASE) < objective_score(summary(pd=0.13), BASE)


# Both candidates below hold coverage at or above the reference. That is deliberate: the coverage
# *constraint* (tests/test_objective_coverage_constraint.py) applies whatever objective is chosen,
# so a candidate that breaches it is disqualified before weighting is ever consulted. These two
# isolate what the named objectives actually change, which is the weighting inside the feasible
# region.
DETECTION_HEAVY = summary(pd=0.25)
COVERAGE_HEAVY = summary(pd=0.11, run_intercept_rate=0.45, ait_censored=1000.0)


def test_the_coverage_objective_prefers_the_coverage_heavy_candidate():
    weights = OBJECTIVES["coverage"]
    assert objective_score(COVERAGE_HEAVY, BASE, weights) > objective_score(
        DETECTION_HEAVY, BASE, weights
    )


def test_the_detection_objective_makes_the_opposite_choice():
    weights = OBJECTIVES["detection"]
    assert objective_score(DETECTION_HEAVY, BASE, weights) > objective_score(
        COVERAGE_HEAVY, BASE, weights
    )


def test_named_objectives_exist_for_the_three_operating_intents():
    assert set(OBJECTIVES) >= {"balanced", "detection", "coverage"}


def test_a_missing_metric_is_rejected_rather_than_scored_as_zero():
    with pytest.raises(KeyError):
        objective_score({"pd": 0.1}, BASE)


def test_a_zero_reference_metric_does_not_blow_up():
    """A scenario where round-robin detects nothing must not produce an infinite score."""
    zeroed = dict(BASE, pd=0.0, hpdr=0.0)
    score = objective_score(summary(pd=0.2, hpdr=0.2), zeroed)
    assert score == score  # not NaN
    assert abs(score) < 1e6


# -- the parameter vector ----------------------------------------------------------------------------

def test_parameters_round_trip_through_the_vector():
    params = IndexParams(
        w_value=1.4, w_info=0.2, w_novelty=0.7, w_deadline=2.1,
        rho_min=0.2, coverage_budget=0.5,
    )
    assert IndexParams.from_vector(params.to_vector()) == params


def test_the_vector_has_one_entry_per_bound():
    assert len(IndexParams.default().to_vector()) == len(IndexParams.bounds())


def test_every_default_sits_inside_its_bound():
    for value, (low, high) in zip(IndexParams.default().to_vector(), IndexParams.bounds()):
        assert low <= value <= high


def test_parameters_become_agent_keyword_arguments():
    kwargs = params_to_agent_kwargs(IndexParams.default(), coverage_cycle_s=0.104)
    assert kwargs["deadline_s"] == pytest.approx(0.104 / IndexParams.default().coverage_budget)
    assert kwargs["rho_min"] == pytest.approx(IndexParams.default().rho_min)
    assert kwargs["weights"].w_value == pytest.approx(IndexParams.default().w_value)


def test_an_impossible_coverage_budget_is_rejected():
    with pytest.raises(ValueError):
        params_to_agent_kwargs(
            IndexParams.default().replace(coverage_budget=0.0), coverage_cycle_s=0.104
        )
