"""Emitter behavior classes (PRD Section 8.3).

Five strategy objects, one per ``behavior_class`` in API_CONTRACT.md Section 6:

    fixed         continuously or near-continuously active on one assigned band
    periodic      active for a dwell window every Tperiod steps (constant or jittered)
    agile         hops across a defined band set at a given hop rate
    random        activates with a stochastic per-slot probability
    intermittent  bursty ON/OFF with variable-length silent gaps

Every behavior generates its whole activity track in one pass at reset, driven only by the
ground-truth generator. That is what makes a run reproducible (NFR-006) and what guarantees the
baseline and the ML policy see an identical spectrum (Section 13) -- the world is fixed before
any policy gets to act.

Scope reminder: these are synthetic activity generators. No real RF, no real emitters.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Sequence

import numpy as np

BEHAVIOR_CLASSES = ("fixed", "periodic", "agile", "random", "intermittent")


@dataclass
class Emitter:
    """One synthetic emitter and the parameters of its behavior class.

    ``priority`` is the threat/priority multiplier P(t) of reward Equation 10.1 and the
    high-priority flag behind HPDR (Section 12). It is >= 1 by definition.
    """

    emitter_id: int
    behavior_class: str
    bands: tuple[int, ...]
    priority: float = 1.0
    params: dict = field(default_factory=dict)

    def __post_init__(self) -> None:
        if self.behavior_class not in BEHAVIOR_CLASSES:
            raise ValueError(
                f"unknown behavior_class {self.behavior_class!r}; "
                f"must be one of {BEHAVIOR_CLASSES} (API_CONTRACT.md Section 6)"
            )
        if self.priority < 1.0:
            raise ValueError("priority is a multiplier >= 1 (PRD Equation 10.1)")
        if not self.bands:
            raise ValueError("emitter must be assigned at least one band")

    @property
    def is_high_priority(self) -> bool:
        return self.priority > 1.0

    def activity_track(self, duration: int, rng: np.random.Generator) -> np.ndarray:
        """Band occupied at each step, or -1 when silent. Shape ``(duration,)``, dtype int32."""
        track = np.full(duration, -1, dtype=np.int32)
        t = np.arange(duration)

        if self.behavior_class == "fixed":
            duty = float(self.params.get("duty", 0.95))
            on = rng.random(duration) < duty
            track[on] = self.bands[0]

        elif self.behavior_class == "periodic":
            period = int(self.params.get("period", 20))
            on_duration = int(self.params.get("on_duration", max(1, period // 5)))
            phase = int(self.params.get("phase", 0)) % period
            jitter = int(self.params.get("jitter", 0))
            if jitter:
                # Jittered period: walk activation starts forward one period at a time so the
                # jitter accumulates the way a drifting clock does, rather than cancelling out.
                start = phase
                while start < duration:
                    end = min(duration, start + on_duration)
                    track[start:end] = self.bands[0]
                    start += period + int(rng.integers(-jitter, jitter + 1))
                    start = max(start, end)  # never overlap the window just written
            else:
                on = ((t - phase) % period) < on_duration
                on &= t >= phase
                track[on] = self.bands[0]

        elif self.behavior_class == "agile":
            hop_rate = max(1, int(self.params.get("hop_rate", 5)))
            duty = float(self.params.get("duty", 0.9))
            offset = int(self.params.get("hop_offset", 0))
            hop_index = (t // hop_rate + offset) % len(self.bands)
            band_at_t = np.asarray(self.bands, dtype=np.int32)[hop_index]
            on = rng.random(duration) < duty
            track[on] = band_at_t[on]

        elif self.behavior_class == "random":
            p = float(self.params.get("p_active", 0.15))
            on = rng.random(duration) < p
            track[on] = self.bands[0]

        elif self.behavior_class == "intermittent":
            # Two-state Markov chain: bursts of geometric length separated by geometric gaps.
            p_on_to_off = float(self.params.get("p_on_to_off", 0.25))
            p_off_to_on = float(self.params.get("p_off_to_on", 0.05))
            draws = rng.random(duration)
            active = False
            for i in range(duration):
                if active:
                    track[i] = self.bands[0]
                    if draws[i] < p_on_to_off:
                        active = False
                elif draws[i] < p_off_to_on:
                    active = True
                    track[i] = self.bands[0]

        return track


def build_emitters(
    num_emitters: int,
    num_bands: int,
    mix: dict[str, float],
    rng: np.random.Generator,
    high_priority_fraction: float = 0.25,
    params_by_class: dict[str, dict] | None = None,
) -> list[Emitter]:
    """Instantiate a scenario emitter population from a behavior-class mix.

    ``mix`` maps behavior_class -> proportion (the "Emitter Mix" column of PRD Section 13).
    Counts are allocated largest-remainder style so the requested proportions are hit exactly
    rather than drifting with rounding.
    """
    params_by_class = params_by_class or {}
    classes = _allocate_classes(num_emitters, mix)

    emitters: list[Emitter] = []
    for i, behavior in enumerate(classes):
        params = dict(params_by_class.get(behavior, {}))
        bands = _assign_bands(behavior, num_bands, rng, params)
        priority = 2.0 if rng.random() < high_priority_fraction else 1.0
        emitters.append(
            Emitter(
                emitter_id=i,
                behavior_class=behavior,
                bands=bands,
                priority=priority,
                params=_randomize_params(behavior, params, rng),
            )
        )
    return emitters


def _allocate_classes(num_emitters: int, mix: dict[str, float]) -> list[str]:
    unknown = set(mix) - set(BEHAVIOR_CLASSES)
    if unknown:
        raise ValueError(f"unknown behavior classes in mix: {sorted(unknown)}")
    total = sum(mix.values())
    if total <= 0:
        raise ValueError("emitter mix proportions must sum to a positive value")

    exact = {k: num_emitters * v / total for k, v in mix.items()}
    counts = {k: int(v) for k, v in exact.items()}
    remainder = num_emitters - sum(counts.values())
    # Largest remainder first, ties broken by class order for determinism.
    order = sorted(exact, key=lambda k: (-(exact[k] - counts[k]), BEHAVIOR_CLASSES.index(k)))
    for k in order[:remainder]:
        counts[k] += 1

    classes: list[str] = []
    for name in BEHAVIOR_CLASSES:  # stable order regardless of dict insertion order
        classes.extend([name] * counts.get(name, 0))
    return classes


def _assign_bands(
    behavior: str, num_bands: int, rng: np.random.Generator, params: dict
) -> tuple[int, ...]:
    if behavior == "agile":
        hop_set_size = int(params.get("hop_set_size", min(4, num_bands)))
        hop_set_size = max(2, min(hop_set_size, num_bands))
        return tuple(int(b) for b in rng.choice(num_bands, size=hop_set_size, replace=False))
    return (int(rng.integers(0, num_bands)),)


def _randomize_params(behavior: str, params: dict, rng: np.random.Generator) -> dict:
    """Fill in per-emitter parameters the scenario config did not pin."""
    out = dict(params)
    if behavior == "periodic":
        out.setdefault("period", int(rng.integers(12, 41)))
        out.setdefault("on_duration", max(1, int(out["period"] * 0.2)))
        out.setdefault("phase", int(rng.integers(0, out["period"])))
    elif behavior == "agile":
        out.setdefault("hop_rate", int(rng.integers(3, 11)))
        out.setdefault("hop_offset", int(rng.integers(0, 5)))
    elif behavior == "random":
        out.setdefault("p_active", float(rng.uniform(0.05, 0.25)))
    elif behavior == "intermittent":
        out.setdefault("p_on_to_off", float(rng.uniform(0.15, 0.35)))
        out.setdefault("p_off_to_on", float(rng.uniform(0.03, 0.10)))
    return out


def summarize(emitters: Sequence[Emitter]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for e in emitters:
        counts[e.behavior_class] = counts.get(e.behavior_class, 0) + 1
    return counts
