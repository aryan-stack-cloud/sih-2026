"""What "better" means, expressed so a search can optimise it directly (solution spec Section 10).

The narrow claim this module supports: **nothing in the SCT scheduler optimises a proxy reward.**
Equation 10.1's six weights are a reward-shaping exercise, and the relationship between that
reward and the metrics a reviewer actually reads is an article of faith. The index has six scalars
and they are tuned against the scoreboard itself.

Three design points.

**Scores are ratios to a reference policy on identical seeds.** A score of 0 means "no better than
round-robin", so the sign of every term is unambiguous and the number is comparable across
scenarios whose absolute Pd differs by a factor of two.

**Emitter reach disqualifies; everything else costs.** Choosing which property vetoes took two
attempts. The first version penalised all three coverage metrics asymmetrically, five to one, and
that was not enough to stop a candidate trading a 14% fall in run intercept rate for a 90% rise in
detection. Making all three hard constraints stopped it -- and also made round-robin the only
feasible policy, because held-out measurement showed the sweep beats the index on run intercept
rate at every budget in every scenario. It rewards catching the start of an activation run, which
a perfectly uniform sweep maximises by construction, so any deviation to chase value costs it.

The veto is therefore interception ratio alone: the "did we ever see this emitter" property, which
a mission genuinely cannot give up and which the index holds or improves at nearly every budget.
Run intercept rate and censored intercept time stay inside the weighted sum at five to one against
gains, so a candidate is discouraged from spending them rather than forbidden. The three named
objectives discriminate inside that feasible region, which is where an operating intent belongs.

**Every term is clipped.** A scenario where the reference policy detects nothing must not produce
an infinite score, and one runaway metric must not decide the search.
"""

from __future__ import annotations

from dataclasses import dataclass, fields, replace as _replace
from typing import Mapping

from ml.scheduling.index_policy import IndexWeights

# Metrics where a larger value is better, and those where a smaller one is.
HIGHER_IS_BETTER = ("pd", "hpdr", "run_intercept_rate", "interception_ratio")
LOWER_IS_BETTER = ("ait_censored",)

# Metrics that describe *coverage* rather than detection density. Losing ground on these is what
# disqualified the contextual bandit, so a loss here is weighted far more heavily than a gain.
COVERAGE_METRICS = ("run_intercept_rate", "interception_ratio", "ait_censored")
LOSS_AVERSION = 5.0

# The one coverage property that disqualifies rather than costs: emitter reach. An earlier version
# vetoed on run intercept rate too, and held-out measurement showed round-robin beats the index on
# that metric at every budget in every scenario -- unsurprisingly, since it rewards catching the
# start of an activation run, which a perfectly uniform sweep maximises by construction. A veto no
# non-trivial policy can satisfy encodes the baseline, not an operating intent.
CONSTRAINT_METRICS = ("interception_ratio",)

# How far below the reference the constrained metric may fall before the candidate is disqualified.
# Wide enough to absorb seed-to-seed noise, narrow enough that a real regression cannot hide in it.
COVERAGE_TOLERANCE = 0.02

# Score floor for a disqualified candidate. Any feasible candidate outranks any infeasible one,
# and among infeasible ones the ordering is by total shortfall.
INFEASIBLE_BASE = -100.0

# Per-term clip, and the floor used when a reference metric is zero.
TERM_CAP = 10.0
REFERENCE_FLOOR = 1e-3

OBJECTIVES: dict[str, dict[str, float]] = {
    # Equal weight on detection and coverage. The default, and the one the shipped configuration
    # was chosen under.
    "balanced": {
        "pd": 1.0, "hpdr": 1.0,
        "run_intercept_rate": 1.0, "interception_ratio": 1.0, "ait_censored": 1.0,
    },
    # For a mission that must not miss a transmission it did look at.
    "detection": {
        "pd": 2.0, "hpdr": 2.0,
        "run_intercept_rate": 0.5, "interception_ratio": 0.5, "ait_censored": 0.5,
    },
    # For a mission that must not miss an emitter at all.
    "coverage": {
        "pd": 0.3, "hpdr": 0.3,
        "run_intercept_rate": 2.0, "interception_ratio": 2.0, "ait_censored": 2.0,
    },
}


def _relative(value: float, reference: float, lower_is_better: bool) -> float:
    """Signed fractional improvement over the reference, positive meaning better."""
    denominator = reference if abs(reference) > REFERENCE_FLOOR else REFERENCE_FLOOR
    delta = (reference / value - 1.0) if lower_is_better else (value / denominator - 1.0)
    if lower_is_better and abs(value) <= REFERENCE_FLOOR:
        delta = TERM_CAP
    return max(-TERM_CAP, min(TERM_CAP, delta))


def coverage_shortfall(
    summary: Mapping[str, float],
    reference: Mapping[str, float],
    tolerance: float = COVERAGE_TOLERANCE,
) -> float:
    """Total fractional amount by which this candidate falls short of the reference on emitter reach.

    Zero means feasible. Positive means the constrained metric is worse than the reference by more
    than ``tolerance``, and the magnitude says by how much, so a search keeps a gradient back
    toward the feasible region rather than facing a cliff.
    """
    shortfall = 0.0
    for metric in CONSTRAINT_METRICS:
        delta = _relative(
            float(summary[metric]), float(reference[metric]), metric in LOWER_IS_BETTER
        )
        if delta < -tolerance:
            shortfall += -delta - tolerance
    return shortfall


def objective_score(
    summary: Mapping[str, float],
    reference: Mapping[str, float],
    weights: Mapping[str, float] | None = None,
    coverage_tolerance: float = COVERAGE_TOLERANCE,
) -> float:
    """Score one evaluation summary against a reference policy's summary on the same seeds.

    Both mappings must carry every metric the chosen objective names; a missing key raises rather
    than being silently treated as no change, because "the metric was not computed" and "the metric
    did not move" are very different findings.

    ``coverage_tolerance`` widens the constraint for a mission that has explicitly decided to trade
    emitter reach for detection depth. It is a deliberate act, never a default.
    """
    weights = weights or OBJECTIVES["balanced"]

    shortfall = coverage_shortfall(summary, reference, coverage_tolerance)
    if shortfall > 0.0:
        return INFEASIBLE_BASE - shortfall

    total = 0.0
    for metric, weight in weights.items():
        delta = _relative(
            float(summary[metric]), float(reference[metric]), metric in LOWER_IS_BETTER
        )
        if delta < 0.0 and metric in COVERAGE_METRICS:
            delta *= LOSS_AVERSION
        total += weight * delta
    return total


@dataclass(frozen=True)
class IndexParams:
    """The six scalars a search is allowed to move. Everything else is derived, not tuned."""

    w_value: float
    w_info: float
    w_novelty: float
    w_deadline: float
    rho_min: float
    coverage_budget: float

    @classmethod
    def default(cls) -> "IndexParams":
        from ml.agents.index_agent import COVERAGE_BUDGET  # noqa: PLC0415 - avoids a cycle

        base = IndexWeights()
        return cls(
            w_value=base.w_value,
            w_info=base.w_info,
            w_novelty=base.w_novelty,
            w_deadline=base.w_deadline,
            rho_min=0.10,
            coverage_budget=COVERAGE_BUDGET,
        )

    @staticmethod
    def bounds() -> list[tuple[float, float]]:
        return [
            (0.1, 5.0),    # w_value
            (0.0, 2.0),    # w_info
            (0.0, 2.0),    # w_novelty
            (0.1, 5.0),    # w_deadline
            (0.0, 0.5),    # rho_min -- never allowed to reach 1, the index must stay in charge
            (0.2, 1.0),    # coverage_budget -- 1.0 is round-robin, below 0.2 coverage collapses
        ]

    def to_vector(self) -> list[float]:
        return [float(getattr(self, f.name)) for f in fields(self)]

    @classmethod
    def from_vector(cls, vector) -> "IndexParams":
        names = [f.name for f in fields(cls)]
        if len(vector) != len(names):
            raise ValueError(f"expected {len(names)} parameters, got {len(vector)}")
        return cls(**{name: float(value) for name, value in zip(names, vector)})

    def replace(self, **changes) -> "IndexParams":
        return _replace(self, **changes)


def params_to_agent_kwargs(params: IndexParams, coverage_cycle_s: float) -> dict:
    """Turn a parameter vector into ``IndexAgent`` keyword arguments.

    ``coverage_budget`` is converted into a deadline here rather than being passed through, so the
    agent keeps a single, physical notion of a deadline and the search keeps a dimensionless one
    that transfers between scenarios with different band counts.
    """
    if params.coverage_budget <= 0.0:
        raise ValueError(f"coverage_budget must be positive, got {params.coverage_budget}")
    if coverage_cycle_s <= 0.0:
        raise ValueError(f"coverage_cycle_s must be positive, got {coverage_cycle_s}")

    return {
        "weights": IndexWeights(
            w_value=params.w_value,
            w_info=params.w_info,
            w_novelty=params.w_novelty,
            w_deadline=params.w_deadline,
        ),
        "rho_min": params.rho_min,
        "deadline_s": coverage_cycle_s / params.coverage_budget,
    }


def train_holdout_seeds(
    scenario: Mapping[str, object], train_episodes: int, holdout_episodes: int
) -> tuple[list[int], list[int]]:
    """Split a scenario's episode seeds into a search set and a validation set.

    Not a convenience. Six free parameters against three episodes will always find something, and
    the first tuning run duly reported a +1.84 score against a +0.41 default *on its own search
    seeds*. That is a fit, not a result. A tuned configuration is only worth shipping if it also
    wins on seeds the search never saw, so an empty hold-out is refused rather than defaulted.

    Training takes the scenario's own leading seeds, so a tuning run and an ordinary comparison at
    the same episode count see the same spectra. The hold-out continues past them; seeds are
    consecutive integers, and ``seed_range`` is a convention rather than a supply limit.
    """
    from ml.utils.config import episode_seeds  # noqa: PLC0415 - avoids an import cycle

    if train_episodes < 1:
        raise ValueError(f"train_episodes must be at least 1, got {train_episodes}")
    if holdout_episodes < 1:
        raise ValueError(
            f"holdout_episodes must be at least 1, got {holdout_episodes}: "
            "tuning without validation is how an overfitted configuration gets shipped"
        )

    combined = episode_seeds(dict(scenario), train_episodes + holdout_episodes)
    if len(set(combined)) < len(combined):
        raise ValueError(
            "this scenario does not supply distinct seeds, so a hold-out would not be independent"
        )
    return combined[:train_episodes], combined[train_episodes:]
