"""The randomised floor (SCT solution spec Section 7), and baseline arm B4.

Clarkson & Pollington's result is a theorem, not an obstacle to be argued with: against emitters
with unknown parameters, no deterministic search strategy outperforms a random one. SIH26055 is
explicitly that regime -- "in the absence of prior reliable intelligence of emitters and their
operating characteristics" -- so any system claiming to beat random on genuine unknowns is either
exploiting learned structure or reporting a lucky seed.

The engineering response is to carry the random strategy permanently and let learning operate
strictly above it. El-Mahassni & Howard's continuous-time Markov chain is the one to carry,
because its expected intercept time approaches linearity in the emitter's scan period fastest and
*smoothly*, without the abrupt spikes deterministic sweeps show at rational period ratios.

The chain: hold the current band for an exponentially distributed sojourn, then jump to a
uniformly chosen different band. Sampling the hold as a per-slot Bernoulli gives a geometric
sojourn, the discrete-time counterpart, with mean ``mean_dwell_slots``.

The trade this buys is worth stating plainly, because it is the honest version of the pitch:
**a periodic sweep is usually better than random and occasionally infinite; this is never better
than a tuned schedule and never catastrophic.** Mixing a permanent fraction of it into the index
policy is what bounds worst-case behaviour against an emitter no model predicts.
"""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np

from ml.agents.base import Agent


class CTMCFloorAgent(Agent):
    """Uniform-stationary random band selection with geometric sojourns."""

    policy_type = "ctmc"

    def __init__(
        self,
        num_bands: int,
        mean_dwell_slots: float = 1.0,
        rng=None,
    ) -> None:
        super().__init__(num_bands, rng)
        if mean_dwell_slots < 1.0:
            raise ValueError(
                f"mean_dwell_slots must be at least one slot, got {mean_dwell_slots}"
            )
        self.mean_dwell_slots = float(mean_dwell_slots)
        self._candidates: list[int] | None = None
        self._current: int | None = None

    # -- lifecycle -----------------------------------------------------------------------------

    def start_episode(self, episode: int = 0) -> None:
        self._current = None

    def set_candidates(self, bands) -> None:
        """Restrict the floor to the bands the index has not yet modelled confidently.

        Passing ``None`` or an empty list restores the whole spectrum. Empty is deliberately not
        an error: "every band is characterised" is not a reason to stop looking, and silently
        scanning nothing would be the worst possible failure here.
        """
        self._candidates = [int(b) for b in bands] if bands else None
        if self._candidates is not None and self._current not in self._candidates:
            self._current = None

    # -- decision ------------------------------------------------------------------------------

    def select_action(self, observation: np.ndarray, explore: bool = True) -> int:
        """Choose a band. The observation is ignored: that is the entire point of a floor."""
        pool = self._candidates if self._candidates else list(range(self.num_bands))

        if self._current is None or self._current not in pool:
            self._current = int(self.rng.choice(pool))
            return self._current

        # Geometric sojourn with the requested mean: hold with probability 1 - 1/mean.
        hold = self.rng.random() < 1.0 - 1.0 / self.mean_dwell_slots
        if hold or len(pool) == 1:
            return self._current

        others = [b for b in pool if b != self._current]
        self._current = int(self.rng.choice(others))
        return self._current

    def describe(self) -> dict:
        return {
            "policy_type": self.policy_type,
            "num_bands": self.num_bands,
            "mean_dwell_slots": self.mean_dwell_slots,
            "restricted_to": self._candidates,
        }

    # -- persistence -----------------------------------------------------------------------------
    #
    # Nothing is learned: the chain's only parameter is its mean sojourn. Saving it is what lets
    # this policy carry a real, honestly-labelled registry entry like every other algorithm,
    # instead of being the one policy type the model registry cannot represent.

    def save(self, path: str | Path) -> None:
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        config = {"num_bands": self.num_bands, "mean_dwell_slots": self.mean_dwell_slots}
        path.write_text(json.dumps(config, indent=2), encoding="utf-8")

    @classmethod
    def load(cls, path: str | Path, **kwargs) -> "CTMCFloorAgent":
        config = json.loads(Path(path).read_text(encoding="utf-8"))
        config.update(kwargs)
        return cls(**config)
