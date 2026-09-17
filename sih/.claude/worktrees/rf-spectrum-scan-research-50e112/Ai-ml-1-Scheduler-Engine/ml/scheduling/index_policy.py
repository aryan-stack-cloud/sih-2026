"""The SCT index and the selection rule (solution spec Section 4).

Scanning a band reveals its state and resets the belief; not scanning lets the belief drift toward
stationarity. That is a restless bandit with reset, which Liu, Weber & Zhao proved indexable with
a closed-form Whittle index. So the policy is an index: score every band, take the best K.

    I_i  =  w_v * threat_i * belief_i * P_d_i * ident_i  +  w_I * infogain_i
            +  w_n * novelty_i  +  w_D * deadline_pressure_i
            ------------------------------------------------------------------
                          dwell + retune time for band i

Scope, stated rather than overclaimed: the exact Whittle result is proved for stochastically
identical arms under perfect sensing. Our arms are heterogeneous and our sensing is imperfect, so
this is a Whittle-*style* index that coincides with the exact one in that special case and is a
one-step lookahead otherwise. That is the standard construction and it should be described that
way.

**Why the denominator carries the design.** Dividing by the receiver time a look actually costs
turns the index into value per unit time, and three things follow with no tuning constant. The
dwell-length choice resolves itself, because detection probability saturates while time does not.
Retune cost is priced in the same units as the dwell, so locally sweep-like behaviour emerges
instead of being hard-coded. And it is the correct objective for a decision problem whose actions
have different durations. Equation 10.1's fixed per-detection reward can express none of this: it
pays the same for a detection that cost eight slots as for one that cost a single slot.

**Why the deadline term is inside the division too.** An earlier draft added it afterwards, on the
argument that a constraint multiplier is not value. Measurement rejected that: the value terms
carry units of "per second" while a bare barrier is dimensionless, so the barrier only outbid
value in the last few percent before the deadline -- far too late to drain a queue of stale bands
through a receiver that can serve one at a time. Staleness overran a 29-slot deadline by ten
slots. Dividing it too makes the whole index one rate, the barrier starts winning around 40% of
the deadline, and coverage stays ahead. It still dominates any finite value, because the barrier
diverges. ``tests/test_index_agent.py`` pins the end-to-end guarantee down.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

RECEIVER_MODES = ("contiguous", "channelized")


@dataclass(frozen=True)
class IndexWeights:
    """The four scalars CMA-ES tunes, against the graded metric rather than a proxy reward."""

    w_value: float = 1.0
    w_info: float = 0.3
    w_novelty: float = 0.5
    w_deadline: float = 1.0

    def __post_init__(self) -> None:
        for name in ("w_value", "w_info", "w_novelty", "w_deadline"):
            if getattr(self, name) < 0.0:
                raise ValueError(f"{name} must be non-negative, got {getattr(self, name)}")


@dataclass(frozen=True)
class IndexInputs:
    """One decision epoch's per-band inputs. Every array is length ``num_bands``.

    ``p_d`` and ``ident_credit`` are evaluated at the dwell length under consideration, so the
    caller scores each candidate dwell by building one of these per dwell option.
    """

    threat: np.ndarray          # learned threat weight, [0, 1]
    belief: np.ndarray          # occupancy belief, [0, 1]
    p_d: np.ndarray             # detection probability at this dwell and this band's SNR
    ident_credit: np.ndarray    # 1 if the dwell can measure PRI, else the fraction of the way there
    info_gain: np.ndarray       # expected entropy reduction, nats
    novelty: np.ndarray         # changepoint probability, [0, 1]
    elapsed_s: np.ndarray       # dwell + retune time if this band is chosen next
    pressure: np.ndarray        # deadline barrier, possibly +inf

    def __post_init__(self) -> None:
        sizes = {
            name: np.asarray(getattr(self, name)).shape
            for name in (
                "threat", "belief", "p_d", "ident_credit",
                "info_gain", "novelty", "elapsed_s", "pressure",
            )
        }
        if len(set(sizes.values())) != 1:
            raise ValueError(f"all inputs must share one shape, got {sizes}")
        if np.any(np.asarray(self.elapsed_s) <= 0.0):
            raise ValueError("elapsed_s must be positive: a look always costs time")


def compute_index(inputs: IndexInputs, weights: IndexWeights, breakdown: bool = False):
    """Score every band. With ``breakdown``, return the named terms instead of the total.

    The breakdown is what the dashboard's decomposition panel renders and what the decision log
    stores, so it is computed from the same expressions as the total rather than re-derived.
    """
    value = weights.w_value * inputs.threat * inputs.belief * inputs.p_d * inputs.ident_credit
    information = weights.w_info * inputs.info_gain
    novelty = weights.w_novelty * inputs.novelty
    deadline = weights.w_deadline * inputs.pressure
    elapsed = np.asarray(inputs.elapsed_s, dtype=np.float64)

    if breakdown:
        return {
            "value": value,
            "information": information,
            "novelty": novelty,
            "deadline": deadline,
            "elapsed_s": elapsed,
        }
    return (value + information + novelty + deadline) / elapsed


def select_window(
    index: np.ndarray, bandwidth_k: int, mode: str = "contiguous"
) -> tuple[int, list[int]]:
    """Choose what to tune to next. Returns the contract's ``next_band`` and the bands covered.

    ``contiguous`` is a single swept superheterodyne: the receiver covers ``bandwidth_k`` adjacent
    bands starting at the action, wrapping at the top of the spectrum, which is what
    ``ml/environments/receiver.py`` already models. ``channelized`` is a digital channelised
    receiver that can take any K bands at once.

    Ties break toward the lowest band index, so a run replays identically from a seed.
    """
    index = np.asarray(index, dtype=np.float64)
    num_bands = index.size
    if mode not in RECEIVER_MODES:
        raise ValueError(f"unknown receiver mode {mode!r}; expected one of {RECEIVER_MODES}")
    if not 1 <= bandwidth_k <= num_bands:
        raise ValueError(f"bandwidth_k must lie in [1, {num_bands}], got {bandwidth_k}")

    if mode == "channelized":
        # argsort on the negated index puts the best first; stable keeps band order on ties.
        order = np.argsort(-index, kind="stable")
        bands = [int(b) for b in order[:bandwidth_k]]
        return bands[0], bands

    # Contiguous: score every wrapping window of K adjacent bands.
    doubled = np.concatenate([index, index])
    sums = np.array([doubled[w : w + bandwidth_k].sum() for w in range(num_bands)])
    start = int(np.argmax(sums))
    return start, [(start + offset) % num_bands for offset in range(bandwidth_k)]


def apply_deadline_override(
    chosen: list[int], overdue: list[int], bandwidth_k: int
) -> list[int]:
    """Force past-deadline bands into the action set, displacing the weakest choices.

    ``chosen`` arrives best-first and ``overdue`` most-stale-first, so truncation drops exactly
    what it should from each. Deadlines bind before value maximisation: this is the hard half of
    the coverage guarantee, and the soft barrier in ``deadlines.pressure`` exists so it rarely has
    to fire.
    """
    if bandwidth_k < 1:
        raise ValueError(f"bandwidth_k must be at least 1, got {bandwidth_k}")
    if not overdue:
        return list(chosen)

    result = list(overdue[:bandwidth_k])
    for band in chosen:
        if len(result) >= bandwidth_k:
            break
        if band not in result:
            result.append(band)
    return result
