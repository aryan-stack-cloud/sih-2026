"""Phase-independent probability of intercept (solution spec Section 11.1).

Every other metric in this project is measured at whatever relative phase the seed happened to
produce. That is fine for comparing policies on identical seeds and useless for the claim a
reviewer actually cares about: *would this schedule have intercepted the emitter whatever time it
switched on?*

Winsor & Hughes answer it by sweeping the emitter's initial phase across its whole range and
reporting the fraction of phases yielding at least one intercept. They compute it by
cross-correlating the two window functions rather than re-simulating at each phase, which is what
this module does: slide the emitter's illumination against the receiver's coverage over cyclic
offsets and count the offsets that coincide at least once.

Two properties make it worth the extra code.

**It exposes the lockout.** A schedule synchronised with an emitter reports a flawless sweep and a
Pd of zero, indistinguishable from a receiver watching an empty band. A sweep period of 8 against
a scan period of 8 intercepts at exactly one phase in eight; an aperiodic schedule with the same
number of looks intercepts at nearly all of them. Nothing else in the metric set separates those
two cases.

**It removes the lucky-seed objection.** A policy cannot post a good phase-independent PI by
happening to start in step with the spectrum.

``worst_case`` is reported beside the mean because that is Clarkson's min-max criterion, and it is
the number that matters operationally: a good average is worthless if the one tracker that could
kill you is in the emitter you never saw.
"""

from __future__ import annotations

from typing import Any, Mapping, Sequence

import numpy as np

DEFAULT_OFFSETS = 64


def phase_independent_pi(
    visits: np.ndarray, activity: np.ndarray, offsets: int = DEFAULT_OFFSETS
) -> float:
    """Fraction of relative phases at which this coverage intercepts this emitter at least once.

    ``visits`` and ``activity`` are both ``(T, N)`` boolean tables: which bands the receiver
    covered at each step, and which bands the emitter illuminated. Offsets are sampled uniformly
    over the episode, and the shift is cyclic, so the sweep covers the whole phase circle rather
    than only the offsets that happen to fit inside the window.
    """
    visits = np.asarray(visits, dtype=bool)
    activity = np.asarray(activity, dtype=bool)
    if visits.shape != activity.shape:
        raise ValueError(f"shape mismatch: visits {visits.shape} vs activity {activity.shape}")
    if offsets < 1:
        raise ValueError(f"offsets must be at least 1, got {offsets}")

    duration = visits.shape[0]
    if duration == 0 or not visits.any() or not activity.any():
        return 0.0

    sampled = np.unique(np.linspace(0, duration, num=min(offsets, duration), endpoint=False).astype(int))
    hits = sum(bool((visits & np.roll(activity, -int(tau), axis=0)).any()) for tau in sampled)
    return hits / len(sampled)


def receiver_coverage(history: Sequence[Mapping[str, Any]], duration: int, num_bands: int) -> np.ndarray:
    """The receiver's ``(T, N)`` coverage table, from an episode history."""
    visits = np.zeros((duration, num_bands), dtype=bool)
    for step, entry in enumerate(history):
        t = int(entry.get("t", step))
        if 0 <= t < duration:
            for band in entry.get("scanned_bands", ()):
                if 0 <= int(band) < num_bands:
                    visits[t, int(band)] = True
    return visits


def phase_sweep_report(
    history: Sequence[Mapping[str, Any]], ground_truth, offsets: int = DEFAULT_OFFSETS
) -> dict:
    """Per-emitter phase-independent PI, plus the aggregates a comparison table needs.

    Scored per *emitter* rather than per band, because a frequency-agile emitter's illumination
    spans several bands and scoring it per band would credit a schedule for covering a band the
    emitter had already left.
    """
    owner = np.asarray(ground_truth.owner)
    duration, num_bands = owner.shape
    visits = receiver_coverage(history, duration, num_bands)

    per_emitter: dict[int, float] = {}
    priorities: dict[int, float] = {}
    for emitter in getattr(ground_truth, "emitters", ()):
        emitter_id = int(emitter.emitter_id)
        activity = owner == emitter_id
        if not activity.any():
            # An emitter that never transmitted in this episode is not evidence about the
            # schedule, so it is left out rather than scored zero.
            continue
        per_emitter[emitter_id] = phase_independent_pi(visits, activity, offsets)
        priorities[emitter_id] = float(getattr(emitter, "priority", 1.0))

    if not per_emitter:
        return {"per_emitter": {}, "mean": 0.0, "priority_weighted": 0.0, "worst_case": 0.0}

    values = np.array(list(per_emitter.values()), dtype=float)
    weights = np.array([priorities[e] for e in per_emitter], dtype=float)
    return {
        "per_emitter": per_emitter,
        "mean": float(values.mean()),
        "priority_weighted": float(np.average(values, weights=weights)),
        "worst_case": float(values.min()),
    }
