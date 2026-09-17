"""Spectrum, FrequencyBand and GroundTruthGenerator (PRD Section 8.1).

The ground truth is an ``(duration, num_bands)`` occupancy table computed once, up front, from
the ground-truth RNG stream alone. Two consequences the rest of the system depends on:

* It is never shown to the scheduler. Per PRD Section 8.1 the GroundTruthGenerator output is
  "used only for metric scoring, never given to the scheduler". Agents only ever see the
  StateVector built from their own scan outcomes.
* It is identical for every policy run at the same seed, which is what makes the Section 13
  baseline-vs-ML comparison fair.

Alongside occupancy we keep the *owner* of each active cell (which emitter is transmitting) so
the metrics engine can compute per-emitter Interception Ratio and priority-weighted HPDR, and
``activation_starts`` so detection latency is measured from the moment a band went active
rather than from the start of the episode.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence

import numpy as np

from ml.environments.emitters import Emitter


@dataclass(frozen=True)
class FrequencyBand:
    """One scannable band. Centre frequency and width are cosmetic for the simulation but are
    what a replay source (ml/data/turing_replay.py) binds real PDW frequencies onto."""

    band_id: int
    centre_hz: float
    width_hz: float
    priority_weight: float = 1.0


class GroundTruth:
    """Pre-computed activity table plus the derived structures the metrics engine needs."""

    def __init__(
        self,
        occupancy: np.ndarray,
        owner: np.ndarray,
        emitters: Sequence[Emitter],
    ) -> None:
        if occupancy.shape != owner.shape:
            raise ValueError("occupancy and owner tables must have the same shape")
        self.occupancy = occupancy.astype(bool, copy=False)
        self.owner = owner.astype(np.int32, copy=False)
        self.emitters = list(emitters)
        self.duration, self.num_bands = self.occupancy.shape

        self.priority = self._priority_table()
        self.activation_starts = self._activation_starts()

    # -- derived tables -------------------------------------------------------------------

    def _priority_table(self) -> np.ndarray:
        """Priority multiplier P(t) of the emitter occupying each active cell; 0.0 when idle."""
        lookup = np.zeros(len(self.emitters) + 1, dtype=np.float32)
        for e in self.emitters:
            lookup[e.emitter_id] = e.priority
        table = np.where(self.owner >= 0, lookup[np.clip(self.owner, 0, None)], 0.0)
        return table.astype(np.float32)

    def _activation_starts(self) -> np.ndarray:
        """For each active cell, the step at which its contiguous activation run began.

        Detection latency (Section 12) is ``t_detect - t_active_start``, so every active cell
        needs to know where its run started. Idle cells hold -1.
        """
        starts = np.full(self.occupancy.shape, -1, dtype=np.int32)
        for b in range(self.num_bands):
            col = self.occupancy[:, b]
            run_start = -1
            for t in range(self.duration):
                if col[t]:
                    if run_start < 0:
                        run_start = t
                    starts[t, b] = run_start
                else:
                    run_start = -1
        return starts

    # -- queries --------------------------------------------------------------------------

    def active_bands(self, t: int) -> np.ndarray:
        return np.flatnonzero(self.occupancy[t])

    def high_priority_mask(self, t: int) -> np.ndarray:
        return self.priority[t] > 1.0

    @property
    def emitters_present(self) -> set[int]:
        return {int(o) for o in np.unique(self.owner) if o >= 0}

    def summary(self) -> dict:
        return {
            "duration": self.duration,
            "num_bands": self.num_bands,
            "occupancy_rate": float(self.occupancy.mean()),
            "emitters_present": len(self.emitters_present),
            "activation_runs": int(
                sum(
                    len(np.unique(self.activation_starts[:, b][self.occupancy[:, b]]))
                    for b in range(self.num_bands)
                )
            ),
        }


class Spectrum:
    """Owns the set of FrequencyBand objects and produces the ground truth for an episode."""

    def __init__(
        self,
        num_bands: int,
        base_hz: float = 1.0e9,
        band_width_hz: float = 20.0e6,
        priority_weights: Sequence[float] | None = None,
    ) -> None:
        if num_bands < 1:
            raise ValueError("num_bands must be >= 1")
        weights = list(priority_weights) if priority_weights is not None else [1.0] * num_bands
        if len(weights) != num_bands:
            raise ValueError("priority_weights must have one entry per band")
        self.num_bands = num_bands
        self.bands = [
            FrequencyBand(
                band_id=i,
                centre_hz=base_hz + (i + 0.5) * band_width_hz,
                width_hz=band_width_hz,
                priority_weight=float(weights[i]),
            )
            for i in range(num_bands)
        ]

    @property
    def priority_weights(self) -> np.ndarray:
        return np.array([b.priority_weight for b in self.bands], dtype=np.float32)

    def generate_ground_truth(
        self, emitters: Sequence[Emitter], duration: int, rng: np.random.Generator
    ) -> GroundTruth:
        """Collapse every emitter activity track into one occupancy/owner table.

        Where several emitters occupy the same band at the same step, the highest-priority one
        is recorded as the owner -- the reward's P(t) and HPDR should reflect the most
        significant emitter present, not an arbitrary one.
        """
        occupancy = np.zeros((duration, self.num_bands), dtype=bool)
        owner = np.full((duration, self.num_bands), -1, dtype=np.int32)
        owner_priority = np.zeros((duration, self.num_bands), dtype=np.float32)

        for emitter in emitters:
            track = emitter.activity_track(duration, rng)
            active_steps = np.flatnonzero(track >= 0)
            if active_steps.size == 0:
                continue
            bands = track[active_steps]
            occupancy[active_steps, bands] = True
            wins = emitter.priority > owner_priority[active_steps, bands]
            winning_steps = active_steps[wins]
            winning_bands = bands[wins]
            owner[winning_steps, winning_bands] = emitter.emitter_id
            owner_priority[winning_steps, winning_bands] = emitter.priority

        return GroundTruth(occupancy, owner, emitters)


class ReplayGroundTruth(GroundTruth):
    """A GroundTruth built from an externally supplied occupancy table.

    This is the seam the Turing replay scenario plugs into (ml/data/turing_replay.py): real PDW
    time-of-arrival/frequency pairs are quantised into an occupancy table and handed to the same
    EWEnvironment, so every agent runs unchanged against recorded pulse timing.
    """

    def __init__(
        self,
        occupancy: np.ndarray,
        owner: np.ndarray | None = None,
        emitters: Sequence[Emitter] | None = None,
    ) -> None:
        occupancy = np.asarray(occupancy, dtype=bool)
        if owner is None:
            # Without emitter labels, treat each band as its own pseudo-emitter so the
            # Interception Ratio metric still has something meaningful to count.
            owner = np.where(
                occupancy, np.arange(occupancy.shape[1], dtype=np.int32)[None, :], -1
            )
        if emitters is None:
            from ml.environments.emitters import Emitter as _E

            emitters = [
                _E(emitter_id=b, behavior_class="fixed", bands=(b,), priority=1.0)
                for b in range(occupancy.shape[1])
            ]
        super().__init__(occupancy, owner, emitters)
