"""Revisit deadlines -- the coverage guarantee (SCT solution spec Section 5).

This is the structural fix for the one figure of merit the contextual bandit loses on. A scalar
reward that pays per detection buys *density*: the policy camps on the busiest bands and its run
intercept rate falls below a plain round-robin sweep. Intercept time and interception ratio are
**coverage** objectives with deadline structure, and no reward weight recovers them -- the
``w5_redundant`` sweep in IMPLEMENTATION.md walks that Pareto frontier monotonically, which is
the proof.

So coverage stops being a penalty term and becomes a constraint.

The deadline is derived, not tuned. If a band may hold a periodic emitter with scan period at
most ``t_max`` and illumination time ``tau_ill``, and the receiver revisits with interval ``R``
and dwells ``dwell``, then for non-commensurate periods each look hits the illumination window
with probability about ``(tau_ill + dwell) / t_max``, so

    E[time to intercept]  ~=  R * t_max / (tau_ill + dwell)

Imposing the mission's worst-case requirement ``t_req`` on that expectation and solving for R
gives ``revisit_deadline_seconds`` below. Every constant in it is a mission requirement or a
measured emitter parameter; none of them is a hyperparameter.

The same algebra run backwards is a **receiver sizing formula** (``required_bandwidth_k``): given
a band count and a worst-case intercept requirement, it says how much instantaneous bandwidth the
receiver needs. When the requirement cannot be met, ``RevisitDeadlines.feasibility`` says so
loudly. The failure mode being replaced is silent starvation, so silence is the one unacceptable
outcome.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

import numpy as np

from ml.scheduling.sync_guard import golden_phase

# Barrier exponent of the staleness pressure. 2 is steep enough that a band nearing its deadline
# outbids ordinary value long before the hard override fires, and shallow enough that a freshly
# scanned band contributes essentially nothing.
BARRIER_EXPONENT = 2.0

# Default fraction of the trigger point the golden dither may advance it by. Zero keeps the trigger
# fixed, which is what gave the schedule a period of its own; see ``RevisitDeadlines.trigger``.
TRIGGER_DITHER = 0.25


def revisit_deadline_seconds(
    t_req_s: float,
    tau_ill_s: float,
    dwell_s: float,
    t_max_s: float,
) -> float:
    """Longest revisit interval that still meets a worst-case intercept requirement.

    ``t_max_s`` must be **this band's own** slowest plausible scan period, never a global worst
    case. Feeding a tracker requirement a 20 s global scan period produces a 9 ms deadline, which
    demands a sweep an order of magnitude faster than the receiver can physically manage, and
    makes a perfectly satisfiable requirement look impossible. A tracker's own scan period is
    around a second, and its deadline lands near 186 ms, which fits comfortably.
    """
    if t_max_s <= 0.0:
        raise ValueError(f"t_max_s must be positive, got {t_max_s}")
    if t_req_s <= 0.0:
        raise ValueError(f"t_req_s must be positive, got {t_req_s}")
    return t_req_s * (tau_ill_s + dwell_s) / t_max_s


def coverage_cycle_seconds(
    num_bands: int, bandwidth_k: int, dwell_s: float, retune_s: float
) -> float:
    """Wall time for one guaranteed pass over every band."""
    if bandwidth_k < 1:
        raise ValueError(f"bandwidth_k must be at least 1, got {bandwidth_k}")
    dwells = math.ceil(num_bands / bandwidth_k)
    return dwells * (dwell_s + retune_s)


def required_bandwidth_k(
    num_bands: int, dwell_s: float, retune_s: float, min_deadline_s: float
) -> int:
    """Instantaneous bandwidth, in bands, needed for the deadlines to be satisfiable.

    The feasibility condition is ``(N / K) * (dwell + retune) <= min_i D_i``. Rearranged, this
    sizes the receiver rather than merely scheduling it, which is a deliverable in its own right:
    it answers "how much receiver do I need for this threat set" instead of only "what should
    this receiver do next".
    """
    if min_deadline_s <= 0.0:
        raise ValueError(f"min_deadline_s must be positive, got {min_deadline_s}")
    return math.ceil(num_bands * (dwell_s + retune_s) / min_deadline_s)


@dataclass(frozen=True)
class FeasibilityReport:
    """Whether a receiver can honour its deadlines, and what it would take if it cannot."""

    feasible: bool
    cycle_s: float
    min_deadline_s: float
    committed_fraction: float
    required_bandwidth_k: int
    message: str


class RevisitDeadlines:
    """Per-band revisit deadlines, staleness pressure and the hard override.

    Deadlines are per band on purpose. Once the threat classifier calls a band a tracker, its
    ``t_req`` drops by an order of magnitude and its deadline tightens with it, so threat priority
    acts on *both* halves of the scheduler: the value it computes and the coverage it owes.
    """

    def __init__(
        self, deadlines_s: np.ndarray, slot_s: float, trigger_dither: float = 0.0
    ) -> None:
        deadlines_s = np.asarray(deadlines_s, dtype=np.float64)
        if deadlines_s.ndim != 1 or deadlines_s.size == 0:
            raise ValueError("deadlines_s must be a non-empty 1-D array, one entry per band")
        if np.any(deadlines_s <= 0.0):
            raise ValueError("every deadline must be positive")
        if slot_s <= 0.0:
            raise ValueError(f"slot_s must be positive, got {slot_s}")
        if trigger_dither < 0.0:
            raise ValueError(f"trigger_dither must be non-negative, got {trigger_dither}")

        self.trigger_dither = float(trigger_dither)
        self.deadlines_s = deadlines_s
        self.slot_s = float(slot_s)
        self.num_bands = int(deadlines_s.size)
        # Round up, and never below one slot: a deadline shorter than a slot is still a real
        # requirement, and flooring it to zero would make every band permanently overdue.
        self.deadline_slots = np.maximum(
            1, np.ceil(deadlines_s / slot_s).astype(np.int64)
        )

    # -- the soft half: pressure that outbids value before the override is needed -----------

    def pressure(self, time_since_last_scan: np.ndarray) -> np.ndarray:
        """Barrier term ``s^p / (1 - s)`` with ``s`` the fraction of the deadline elapsed.

        Zero on a freshly scanned band, unbounded as the deadline approaches, infinite past it.
        The infinity is deliberate: if a caller ignores :meth:`overdue`, an infinite index still
        forces the band into the action set rather than letting it be quietly dropped.
        """
        tsls = np.asarray(time_since_last_scan, dtype=np.float64)
        s = tsls / self.deadline_slots
        out = np.full(s.shape, np.inf, dtype=np.float64)
        soft = s < 1.0
        out[soft] = np.power(s[soft], BARRIER_EXPONENT) / (1.0 - s[soft])
        return out

    # -- the hard half: the override --------------------------------------------------------

    def trigger(
        self, lookahead: int = 0, revisit_counts: np.ndarray | None = None
    ) -> np.ndarray:
        """Staleness at which each band is forced into the action set.

        Two adjustments to the plain deadline, both of which only ever bring the trigger *earlier*,
        so the coverage guarantee is untouched by either.

        ``lookahead`` is arithmetic: a receiver serving K bands at a time cannot clear several
        simultaneous expiries in one slot, so the override must fire a coverage cycle ahead or the
        last band in the queue lands past its deadline.

        The dither is the synchronisation guard applied to the trigger. A fixed trigger gives the
        visit pattern a period of its own, and a period can alias with an emitter: in the trap
        scenario the same policy scored 1.000 and 0.080 on detection across a 20% change in the
        deadline. Advancing the trigger by a golden-ratio Kronecker sequence indexed on the band's
        revisit count breaks that period, deterministically, so a run still replays from its seed.
        Passing no counts leaves the trigger undithered, so a caller that has not adopted it keeps
        the previous behaviour exactly.
        """
        base = np.maximum(1, self.deadline_slots - int(max(0, lookahead)))
        if self.trigger_dither <= 0.0 or revisit_counts is None:
            return base

        phase = np.array(
            [golden_phase(int(n)) for n in np.asarray(revisit_counts).ravel()],
            dtype=np.float64,
        )
        advance = np.floor(self.trigger_dither * base * phase).astype(np.int64)
        return np.maximum(1, base - advance)

    def overdue(
        self,
        time_since_last_scan: np.ndarray,
        lookahead: int = 0,
        revisit_counts: np.ndarray | None = None,
    ) -> list[int]:
        """Bands at or past their deadline, **most stale first**.

        The ordering is the starvation guard. Returning these in band order would let a
        low-numbered band monopolise the override and starve a high-numbered one indefinitely,
        which is precisely the bug the deadline exists to prevent.

        ``lookahead`` brings the trigger forward by that many slots, and it is not a safety margin
        but arithmetic. A receiver serving one band at a time cannot clear several simultaneous
        expiries in one slot: with eight bands expiring together, the last is served a full
        coverage cycle late however promptly the override fires. Subtracting that cycle serves them
        early enough that the last one still lands on its deadline. Callers pass one coverage cycle
        minus one slot.

        The trigger never drops below one slot, so a band scanned this step is never overdue.
        """
        tsls = np.asarray(time_since_last_scan, dtype=np.int64)
        late = np.nonzero(tsls >= self.trigger(lookahead, revisit_counts))[0]
        if late.size == 0:
            return []
        # Stable sort on the negated staleness keeps band order as the tie-break, so the result
        # is deterministic for a given seed.
        order = np.argsort(-tsls[late], kind="stable")
        return [int(b) for b in late[order]]

    # -- sizing ------------------------------------------------------------------------------

    def feasibility(
        self, bandwidth_k: int, dwell_s: float, retune_s: float
    ) -> FeasibilityReport:
        """Can this receiver honour these deadlines, and if not, what would?"""
        cycle = coverage_cycle_seconds(self.num_bands, bandwidth_k, dwell_s, retune_s)
        min_deadline = float(self.deadlines_s.min())
        needed = required_bandwidth_k(self.num_bands, dwell_s, retune_s, min_deadline)
        feasible = cycle <= min_deadline

        if feasible:
            message = (
                f"feasible: {cycle * 1e3:.0f} ms coverage cycle inside a {min_deadline * 1e3:.0f} ms "
                f"deadline, committing {cycle / min_deadline:.0%} of receiver time to coverage"
            )
        else:
            message = (
                f"INFEASIBLE: {cycle * 1e3:.0f} ms coverage cycle exceeds the {min_deadline * 1e3:.0f} ms "
                f"deadline with K={bandwidth_k}. Options: raise instantaneous bandwidth to "
                f"K={needed}, shorten the dwell, or relax the worst-case intercept requirement."
            )

        return FeasibilityReport(
            feasible=feasible,
            cycle_s=cycle,
            min_deadline_s=min_deadline,
            committed_fraction=cycle / min_deadline,
            required_bandwidth_k=needed,
            message=message,
        )
