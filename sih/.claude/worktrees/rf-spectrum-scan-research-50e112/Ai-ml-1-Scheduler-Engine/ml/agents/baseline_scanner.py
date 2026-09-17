"""Open-loop baseline scanner -- the control group (PRD Section 3.1 goal 3, FR-005).

This is the legacy behavior the whole project exists to beat: a fixed pattern that treats every
band as equally likely to be active at every moment, and never looks at its own scan history.

Two modes, both from FR-005:

    round_robin   advance by ``stride`` bands each step, wrapping. With the default stride of
                  the receiver's instantaneous bandwidth K, consecutive steps tile the spectrum
                  without overlap -- the fairest possible version of the fixed sweep.
    fixed_order   walk a configured band list, cyclically.

DESIGN NOTE, worth keeping. A baseline must not be constructed so that it collides with the
emitters in some arithmetically convenient way -- an open-loop sweep and a synthetic target that
share a period produce a meaningless hit rate, high or low, that says nothing about scheduling.
Here the sweep is fixed and the emitters are generated independently from the ground-truth RNG,
so the baseline's score is whatever geometry honestly gives it.

``select_action`` deliberately ignores its ``observation`` argument. That is the definition of
open loop, not an oversight.
"""

from __future__ import annotations

from pathlib import Path
from typing import Sequence

import numpy as np

from ml.agents.base import Agent


class BaselineScanner(Agent):
    """Deterministic open-loop sweep. Given a seed and config, the scan order is fixed."""

    policy_type = "baseline"

    def __init__(
        self,
        num_bands: int,
        mode: str = "round_robin",
        stride: int = 1,
        band_order: Sequence[int] | None = None,
        rng: np.random.Generator | None = None,
    ) -> None:
        super().__init__(num_bands, rng)
        if mode not in ("round_robin", "fixed_order", "random"):
            raise ValueError("mode must be 'round_robin', 'fixed_order' or 'random'")
        if mode == "fixed_order" and not band_order:
            raise ValueError("fixed_order mode requires a band_order")
        self.mode = mode
        self.stride = max(1, int(stride))
        self.band_order = [int(b) % num_bands for b in band_order] if band_order else None
        self.step_index = 0

    def start_episode(self, episode: int = 0) -> None:
        self.step_index = 0

    def select_action(self, observation: np.ndarray, explore: bool = True) -> int:
        # observation is intentionally unused: an open-loop scanner has no feedback path.
        if self.mode == "fixed_order":
            band = self.band_order[self.step_index % len(self.band_order)]
        elif self.mode == "random":
            band = int(self.rng.integers(0, self.num_bands))
        else:
            band = (self.step_index * self.stride) % self.num_bands
        self.step_index += 1
        return int(band)

    def save(self, path: str | Path) -> None:
        np.savez(
            Path(path),
            mode=self.mode,
            stride=self.stride,
            num_bands=self.num_bands,
            band_order=np.array(self.band_order if self.band_order else [], dtype=np.int32),
        )

    @classmethod
    def load(cls, path: str | Path, **kwargs) -> "BaselineScanner":
        data = np.load(Path(path), allow_pickle=False)
        order = data["band_order"].tolist()
        return cls(
            num_bands=int(data["num_bands"]),
            mode=str(data["mode"]),
            stride=int(data["stride"]),
            band_order=order or None,
        )

    def describe(self) -> dict:
        return {
            "policy_type": self.policy_type,
            "num_bands": self.num_bands,
            "mode": self.mode,
            "stride": self.stride,
            "band_order": self.band_order,
        }
